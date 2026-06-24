from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenRefreshRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    MFAVerifyRequest,
    TokenResponse,
    AuthUserResponse,
    MFASetupResponse,
)
from app.schemas.common import APIResponse
from app.models.user import User
from app.middleware.auth import get_current_user
from app.core.exceptions import NotFoundException, ForbiddenException, ValidationException
from app.core.config import settings
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    access_token, refresh_token = await service.login(
        email=payload.email,
        password=payload.password,
        mfa_code=payload.mfa_code,
    )
    user = await service.get_user_by_email(payload.email)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


@router.post("/register", response_model=LoginResponse)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    user, org = await service.register(
        org_name=payload.organization_name,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    access_token, refresh_token = await service.login(
        email=payload.email,
        password=payload.password,
    )
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=AuthUserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: TokenRefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    access_token, refresh_token = await service.refresh_token(payload.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/password-change", response_model=APIResponse)
async def change_password(
    payload: PasswordChangeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(session)
    await service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return APIResponse(message="Password changed successfully")


@router.post("/password-reset", response_model=APIResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    await service.request_password_reset(payload.email)
    return APIResponse(message="Password reset email sent if account exists")


@router.post("/password-reset/confirm", response_model=APIResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    await service.confirm_password_reset(payload.token, payload.new_password)
    return APIResponse(message="Password reset successful")


@router.get("/me", response_model=AuthUserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return AuthUserResponse.model_validate(current_user)


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(session)
    result = await service.setup_mfa(current_user.id)
    return result


@router.post("/mfa/verify", response_model=APIResponse)
async def verify_mfa(
    payload: MFAVerifyRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(session)
    valid = await service.verify_mfa(current_user.id, payload.code)
    if not valid:
        raise ValidationException("Invalid MFA code")
    return APIResponse(message="MFA verified successfully")


@router.post("/logout", response_model=APIResponse)
async def logout(
    current_user: User = Depends(get_current_user),
):
    logger.info("User logged out", extra={"user_id": str(current_user.id)})
    return APIResponse(message="Logged out successfully")
