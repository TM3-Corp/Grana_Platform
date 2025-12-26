"""
Authentication middleware for Grana Platform Backend
Validates JWT tokens from NextAuth v5 and provides user context
"""
import os
from typing import Optional
from datetime import datetime

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel


# Security scheme for bearer tokens
security = HTTPBearer(auto_error=False)


class TokenUser(BaseModel):
    """User data extracted from JWT token"""
    id: str
    email: str
    name: Optional[str] = None
    role: str = "user"


class AuthConfig:
    """Authentication configuration"""

    @staticmethod
    def get_auth_secret() -> str:
        """Get the AUTH_SECRET from environment"""
        secret = os.getenv("AUTH_SECRET")
        if not secret:
            raise ValueError("AUTH_SECRET environment variable is not set")
        return secret

    @staticmethod
    def get_jwt_algorithm() -> str:
        """JWT algorithm used by NextAuth"""
        # NextAuth v5 uses HS256 by default for JWT sessions
        return "HS256"


def decode_nextauth_token(token: str) -> dict:
    """
    Decode and validate a NextAuth JWT token.

    NextAuth v5 JWT structure:
    {
        "name": "Paul",
        "email": "paul@tm3.ai",
        "sub": "user_id",
        "id": "user_id",
        "role": "admin",
        "iat": 1234567890,
        "exp": 1234567890,
        "jti": "unique_token_id"
    }
    """
    try:
        secret = AuthConfig.get_auth_secret()

        # NextAuth uses the AUTH_SECRET directly for HS256
        # In NextAuth v5, the secret might be hashed - try direct first
        decoded = jwt.decode(
            token,
            secret,
            algorithms=[AuthConfig.get_jwt_algorithm()],
            options={"verify_aud": False}  # NextAuth doesn't set audience by default
        )
        return decoded
    except JWTError as e:
        error_msg = str(e).lower()
        if "expired" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenUser:
    """
    Dependency that extracts and validates the current user from JWT.

    Usage:
        @router.get("/protected")
        async def protected_route(user: TokenUser = Depends(get_current_user)):
            return {"message": f"Hello {user.email}"}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_nextauth_token(token)

    # Extract user data from NextAuth token payload
    user_id = payload.get("id") or payload.get("sub")
    email = payload.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user id or email",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return TokenUser(
        id=user_id,
        email=email,
        name=payload.get("name"),
        role=payload.get("role", "user")
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenUser]:
    """
    Optional authentication - returns None if no valid token provided.

    Usage:
        @router.get("/public-or-private")
        async def flexible_route(user: Optional[TokenUser] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello guest"}
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_nextauth_token(token)

        user_id = payload.get("id") or payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            return None

        return TokenUser(
            id=user_id,
            email=email,
            name=payload.get("name"),
            role=payload.get("role", "user")
        )
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            user: TokenUser = Depends(require_role("admin"))
        ):
            # Only admins can delete users
            pass
    """
    async def role_checker(
        user: TokenUser = Depends(get_current_user)
    ) -> TokenUser:
        # Role hierarchy: admin > user > viewer
        role_hierarchy = {
            "admin": 3,
            "user": 2,
            "viewer": 1
        }

        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}, your role: {user.role}"
            )

        return user

    return role_checker


# Convenience dependencies for common role requirements
require_admin = require_role("admin")
require_user = require_role("user")
require_viewer = require_role("viewer")
