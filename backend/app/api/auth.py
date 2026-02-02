"""
Authentication API endpoints for Grana Platform
- User management (admin only)
- API key management
"""
import os
import secrets
import hashlib
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from psycopg2.extras import RealDictCursor

from app.core.auth import (
    TokenUser,
    get_current_user,
    require_admin,
)
from app.core.database import get_db_connection_with_retry


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Password hashing context (same as frontend bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# Pydantic Models
# =============================================================================

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str = "user"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str] = []
    rate_limit: int = 100


class APIKeyResponse(BaseModel):
    id: int
    name: str
    permissions: List[str]
    rate_limit: int
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
    # Note: key is only returned on creation


class APIKeyCreated(APIKeyResponse):
    key: str  # Only returned when creating a new key


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# =============================================================================
# Database Helpers
# =============================================================================

def get_db_cursor():
    """Get a database cursor with RealDictCursor"""
    conn = get_db_connection_with_retry()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cursor


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256"""
    return hashlib.sha256(key.encode()).hexdigest()


# =============================================================================
# User Management Endpoints (Admin Only)
# =============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    user: TokenUser = Depends(require_admin)
):
    """List all users (admin only)"""
    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            SELECT id, email, name, role, is_active, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
        """)
        users = cursor.fetchall()
        return users
    finally:
        cursor.close()
        conn.close()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: TokenUser = Depends(require_admin)
):
    """Create a new user (admin only)"""
    conn, cursor = get_db_cursor()
    try:
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash the password
        password_hash = pwd_context.hash(user_data.password)

        # Insert the user
        cursor.execute("""
            INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, TRUE, NOW(), NOW())
            RETURNING id, email, name, role, is_active, created_at, updated_at
        """, (user_data.email, password_hash, user_data.name, user_data.role))

        new_user = cursor.fetchone()
        conn.commit()
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: TokenUser = Depends(require_admin)
):
    """Get a specific user (admin only)"""
    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            SELECT id, email, name, role, is_active, created_at, updated_at
            FROM users
            WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user
    finally:
        cursor.close()
        conn.close()


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: TokenUser = Depends(require_admin)
):
    """Update a user (admin only)"""
    conn, cursor = get_db_cursor()
    try:
        # Build update query dynamically based on provided fields
        update_fields = []
        values = []

        if user_data.email is not None:
            update_fields.append("email = %s")
            values.append(user_data.email)
        if user_data.name is not None:
            update_fields.append("name = %s")
            values.append(user_data.name)
        if user_data.role is not None:
            update_fields.append("role = %s")
            values.append(user_data.role)
        if user_data.is_active is not None:
            update_fields.append("is_active = %s")
            values.append(user_data.is_active)

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        update_fields.append("updated_at = NOW()")
        values.append(user_id)

        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, email, name, role, is_active, created_at, updated_at
        """

        cursor.execute(query, values)
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        conn.commit()
        return user
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: TokenUser = Depends(require_admin)
):
    """Delete a user (admin only) - permanently removes user from database"""
    # Prevent self-deletion
    if str(user_id) == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            DELETE FROM users
            WHERE id = %s
            RETURNING id
        """, (user_id,))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# Admin Password Reset
# =============================================================================

class PasswordReset(BaseModel):
    new_password: str


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_user_password(
    user_id: int,
    password_data: PasswordReset,
    current_user: TokenUser = Depends(require_admin)
):
    """Reset a user's password (admin only)"""
    # Prevent resetting own password via this endpoint
    if str(user_id) == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /me/change-password to change your own password"
        )

    conn, cursor = get_db_cursor()
    try:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Hash and set new password
        new_hash = pwd_context.hash(password_data.new_password)
        cursor.execute("""
            UPDATE users SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
        """, (new_hash, user_id))

        conn.commit()
        return {"message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# Current User Endpoints
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenUser = Depends(get_current_user)
):
    """Get current user information"""
    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            SELECT id, email, name, role, is_active, created_at, updated_at
            FROM users
            WHERE id = %s
        """, (int(current_user.id),))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user
    finally:
        cursor.close()
        conn.close()


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: TokenUser = Depends(get_current_user)
):
    """Change current user's password"""
    conn, cursor = get_db_cursor()
    try:
        # Get current password hash
        cursor.execute("""
            SELECT password_hash FROM users WHERE id = %s
        """, (int(current_user.id),))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not pwd_context.verify(password_data.current_password, result['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash and set new password
        new_hash = pwd_context.hash(password_data.new_password)
        cursor.execute("""
            UPDATE users SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
        """, (new_hash, int(current_user.id)))

        conn.commit()
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# API Key Management
# =============================================================================

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: TokenUser = Depends(get_current_user)
):
    """List all API keys for the current user"""
    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            SELECT id, name, permissions, rate_limit, is_active, last_used_at, created_at
            FROM api_keys
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (int(current_user.id),))
        keys = cursor.fetchall()
        return keys
    except Exception as e:
        # If api_keys table doesn't exist, return empty list with info
        if "relation \"api_keys\" does not exist" in str(e):
            return []
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.post("/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: TokenUser = Depends(get_current_user)
):
    """Create a new API key"""
    conn, cursor = get_db_cursor()
    try:
        # Generate a secure API key
        raw_key = f"grana_{secrets.token_urlsafe(32)}"
        key_hash = hash_api_key(raw_key)

        # Insert the key
        cursor.execute("""
            INSERT INTO api_keys (key_hash, name, user_id, permissions, rate_limit, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            RETURNING id, name, permissions, rate_limit, is_active, last_used_at, created_at
        """, (
            key_hash,
            key_data.name,
            int(current_user.id),
            key_data.permissions,
            key_data.rate_limit
        ))

        new_key = cursor.fetchone()
        conn.commit()

        # Return the key with the raw key (only time it's shown)
        return APIKeyCreated(
            id=new_key['id'],
            name=new_key['name'],
            permissions=new_key['permissions'] or [],
            rate_limit=new_key['rate_limit'],
            is_active=new_key['is_active'],
            last_used_at=new_key['last_used_at'],
            created_at=new_key['created_at'],
            key=raw_key
        )
    except Exception as e:
        conn.rollback()
        if "relation \"api_keys\" does not exist" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API keys table not yet created. Please run database migrations."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    current_user: TokenUser = Depends(get_current_user)
):
    """Revoke an API key"""
    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            UPDATE api_keys SET is_active = FALSE
            WHERE id = %s AND user_id = %s
            RETURNING id
        """, (key_id, int(current_user.id)))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# API Key Authentication Middleware
# =============================================================================

async def verify_api_key(api_key: str) -> Optional[dict]:
    """
    Verify an API key and return the associated user and permissions.
    Updates last_used_at timestamp.
    """
    if not api_key.startswith("grana_"):
        return None

    key_hash = hash_api_key(api_key)

    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            SELECT ak.id, ak.user_id, ak.permissions, ak.rate_limit, u.email, u.role
            FROM api_keys ak
            JOIN users u ON u.id = ak.user_id
            WHERE ak.key_hash = %s AND ak.is_active = TRUE AND u.is_active = TRUE
        """, (key_hash,))
        result = cursor.fetchone()

        if result:
            # Update last_used_at
            cursor.execute("""
                UPDATE api_keys SET last_used_at = NOW()
                WHERE id = %s
            """, (result['id'],))
            conn.commit()

            return {
                'key_id': result['id'],
                'user_id': result['user_id'],
                'email': result['email'],
                'role': result['role'],
                'permissions': result['permissions'] or [],
                'rate_limit': result['rate_limit']
            }

        return None
    except Exception:
        return None
    finally:
        cursor.close()
        conn.close()
