"""
Rate limiting middleware for Grana Platform Backend
Uses in-memory storage with sliding window algorithm
"""
import time
from typing import Optional, Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production with multiple instances, consider using Redis.
    """

    def __init__(self):
        # {identifier: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        # Clean up old entries periodically
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # seconds

    def _cleanup_old_entries(self, window_seconds: int = 60):
        """Remove entries older than the largest window we care about"""
        now = time.time()

        # Only cleanup periodically to avoid overhead
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - window_seconds * 2  # Keep 2x the window for safety

        for identifier in list(self._requests.keys()):
            self._requests[identifier] = [
                (ts, count) for ts, count in self._requests[identifier]
                if ts > cutoff
            ]
            # Remove empty entries
            if not self._requests[identifier]:
                del self._requests[identifier]

        self._last_cleanup = now

    def is_allowed(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed under the rate limit.

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        self._cleanup_old_entries(window_seconds)

        now = time.time()
        window_start = now - window_seconds

        # Get requests within the window
        requests_in_window = [
            (ts, count) for ts, count in self._requests[identifier]
            if ts > window_start
        ]

        total_requests = sum(count for _, count in requests_in_window)

        if total_requests >= max_requests:
            # Calculate when the oldest request in window will expire
            if requests_in_window:
                oldest_timestamp = min(ts for ts, _ in requests_in_window)
                retry_after = int(oldest_timestamp + window_seconds - now) + 1
            else:
                retry_after = 1

            return False, 0, retry_after

        # Add this request
        self._requests[identifier].append((now, 1))

        remaining = max_requests - total_requests - 1
        return True, remaining, 0


# Global rate limiter instance
rate_limiter = RateLimiter()


# Rate limit configurations
RATE_LIMITS = {
    "authenticated": 1000,    # 1000 requests per minute for authenticated users
    "api_key": 100,          # 100 requests per minute for API keys (can be overridden)
    "unauthenticated": 100,  # 100 requests per minute for unauthenticated requests (dashboard makes many calls)
}

# Paths that are exempt from rate limiting
EXEMPT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that applies rate limiting based on authentication status.

    Rate limits:
    - Authenticated users (JWT): 1000 req/min
    - API key users: configurable per key (default 100 req/min)
    - Unauthenticated: 10 req/min

    Headers returned:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Remaining requests in current window
    - X-RateLimit-Reset: Seconds until the window resets (when limited)
    """

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Determine the identifier and rate limit
        identifier, limit = self._get_identifier_and_limit(request)

        # Check rate limit
        is_allowed, remaining, retry_after = rate_limiter.is_allowed(
            identifier=identifier,
            max_requests=limit,
            window_seconds=60
        )

        if not is_allowed:
            # Return JSONResponse instead of raising HTTPException
            # This ensures the response goes through the CORS middleware
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                    "Retry-After": str(retry_after),
                }
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    def _get_identifier_and_limit(self, request: Request) -> Tuple[str, int]:
        """
        Determine the rate limit identifier and limit based on auth status.

        Priority:
        1. API key (X-API-Key header)
        2. JWT token (Authorization: Bearer header)
        3. IP address (unauthenticated)
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key.startswith("grana_"):
            # For API keys, use the key itself as identifier
            # In production, you'd look up the specific rate limit for this key
            return f"api_key:{api_key[:20]}", RATE_LIMITS["api_key"]

        # Check for JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # For JWT, use a hash of the token as identifier
            # This ensures the same user is rate limited across requests
            token_hash = hash(auth_header)
            return f"jwt:{token_hash}", RATE_LIMITS["authenticated"]

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}", RATE_LIMITS["unauthenticated"]

    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP, considering proxies"""
        # Check X-Forwarded-For header first (for proxied requests)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Fall back to the direct client IP
        if request.client:
            return request.client.host

        return "unknown"


# Dependency for per-endpoint rate limiting
async def rate_limit_check(
    request: Request,
    max_requests: int = 100,
    window_seconds: int = 60
):
    """
    Dependency for applying rate limits to specific endpoints.

    Usage:
        @router.get("/expensive-operation")
        async def expensive_op(
            _: None = Depends(rate_limit_check)  # Uses default 100/min
        ):
            pass

        @router.get("/very-expensive")
        async def very_expensive(
            _: None = Depends(lambda r: rate_limit_check(r, max_requests=10))
        ):
            pass
    """
    # Get identifier based on authentication
    auth_header = request.headers.get("Authorization")
    api_key = request.headers.get("X-API-Key")

    if api_key and api_key.startswith("grana_"):
        identifier = f"endpoint:{request.url.path}:api_key:{api_key[:20]}"
    elif auth_header and auth_header.startswith("Bearer "):
        identifier = f"endpoint:{request.url.path}:jwt:{hash(auth_header)}"
    else:
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip and request.client:
            client_ip = request.client.host
        identifier = f"endpoint:{request.url.path}:ip:{client_ip}"

    is_allowed, remaining, retry_after = rate_limiter.is_allowed(
        identifier=identifier,
        max_requests=max_requests,
        window_seconds=window_seconds
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for this endpoint. Try again in {retry_after} seconds.",
            headers={
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(retry_after),
            }
        )
