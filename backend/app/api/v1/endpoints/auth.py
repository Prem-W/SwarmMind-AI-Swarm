"""
Authentication API Endpoints

Handles login, registration, token refresh, and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.logging import get_logger
from app.middleware.auth import get_current_user, require_admin
from app.models.user import User
from app.services.auth import AuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate and get JWT tokens."""
    user = await AuthService.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    tokens = AuthService.create_auth_tokens(user)
    logger.info("User logged in", user_id=str(user.id), email=user.email)
    return TokenResponse(**tokens)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new user account."""
    try:
        user = await AuthService.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
        return UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        )
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    from app.core.security import verify_token, create_access_token

    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    new_access = create_access_token({
        "sub": payload["sub"],
        "email": payload.get("email"),
        "name": payload.get("name"),
        "role": payload.get("role"),
    })

    return TokenResponse(
        access_token=new_access,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
    )


@router.get("/teams")
async def get_my_teams(user: User = Depends(get_current_user)):
    """Get teams the current user belongs to."""
    teams = await AuthService.get_user_teams(user.id)
    return {"teams": teams}
