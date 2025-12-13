from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.crud.user import user as user_crud
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenWithRefresh,
    RefreshTokenRequest,
    RegisterResponse,
    LoginResponse
)

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register a new user
    """
    # Check if user exists
    user = await user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create user
    user = await user_crud.create(db, obj_in=user_in)
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "success": True,
        "data": {
            "userId": user.id,
            "email": user.email,
            "token": access_token,
            "refreshToken": refresh_token,
            "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserLogin,
) -> Any:
    """
    Login user and return tokens
    """
    # Authenticate user
    user = await user_crud.get_by_email(db, email=user_in.email)
    if not user or not security.verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "success": True,
        "data": {
            "userId": user.id,
            "token": access_token,
            "refreshToken": refresh_token,
            "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    }


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_token(
    *,
    token_in: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    payload = security.verify_token(token_in.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Check if user exists
    user_id = payload.get("sub")
    # We need to convert string UUID back to UUID object for DB query if needed, 
    # but here we just need it for the new token
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user_id, "email": payload.get("email")},
        expires_delta=access_token_expires
    )
    # Rotate refresh token
    new_refresh_token = security.create_refresh_token(
        data={"sub": user_id, "email": payload.get("email")}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user
    """
    return current_user
