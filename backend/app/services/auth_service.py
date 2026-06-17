import uuid
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException, UnauthorizedException, ForbiddenException,
    ValidationException, NotFoundException,
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token, verify_token_type,
)
from app.core.config import settings
from app.core.logging import logger
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role, UserRole


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, org_name: str, email: str, password: str, first_name: str, last_name: str) -> tuple[User, Organization]:
        email = email.lower().strip()

        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise ConflictException("A user with this email already exists")

        slug = org_name.lower().replace(" ", "-").replace("_", "-")
        slug = slug[:100]
        base_slug = slug
        counter = 1
        while await self._slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(
            name=org_name,
            slug=slug,
        )
        self.session.add(org)
        await self.session.flush()

        user = User(
            organization_id=org.id,
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            is_verified=True,
            password_changed_at=datetime.now(timezone.utc),
        )
        self.session.add(user)
        await self.session.flush()

        admin_role = await self._ensure_admin_role(org.id)
        if admin_role:
            user_role = UserRole(
                user_id=user.id,
                role_id=admin_role.id,
            )
            self.session.add(user_role)
            await self.session.flush()

        await self.session.refresh(org)
        await self.session.refresh(user)

        logger.info("User registered", extra={"user_id": str(user.id), "org_id": str(org.id)})
        return user, org

    async def login(self, email: str, password: str, mfa_code: str | None = None) -> tuple[str, str]:
        email = email.lower().strip()
        user = await self.get_user_by_email(email)
        if not user:
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise ForbiddenException("Account is disabled")

        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise ForbiddenException("Account is temporarily locked. Try again later.")

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.SECURITY_MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.SECURITY_LOCKOUT_DURATION_MINUTES
                )
            await self.session.flush()
            raise UnauthorizedException("Invalid email or password")

        if user.mfa_enabled and settings.SECURITY_MFA_ENABLED:
            if not mfa_code:
                raise ValidationException("MFA code is required")
            if not self._verify_totp(user.mfa_secret, mfa_code):
                raise UnauthorizedException("Invalid MFA code")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()

        access_token = create_access_token(
            subject=user.id,
            extra_claims={
                "organization_id": str(user.organization_id),
                "email": user.email,
            },
        )
        refresh_token = create_refresh_token(subject=user.id)

        return access_token, refresh_token

    async def refresh_token(self, refresh_token_str: str) -> tuple[str, str]:
        try:
            payload = decode_token(refresh_token_str)
            if not verify_token_type(payload, "refresh"):
                raise UnauthorizedException("Invalid token type")
        except ValueError:
            raise UnauthorizedException("Invalid or expired refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")

        user = await self.session.get(User, uuid.UUID(user_id))
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        access_token = create_access_token(
            subject=user.id,
            extra_claims={
                "organization_id": str(user.organization_id),
                "email": user.email,
            },
        )
        new_refresh_token = create_refresh_token(subject=user.id)

        return access_token, new_refresh_token

    async def change_password(self, user_id: uuid.UUID, current_password: str, new_password: str) -> None:
        user = await self.session.get(User, user_id)
        if not user:
            raise NotFoundException("User", str(user_id))

        if not verify_password(current_password, user.password_hash):
            raise ValidationException("Current password is incorrect")

        if len(new_password) < settings.SECURITY_PASSWORD_MIN_LENGTH:
            raise ValidationException(
                f"Password must be at least {settings.SECURITY_PASSWORD_MIN_LENGTH} characters"
            )

        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        await self.session.flush()

        logger.info("Password changed", extra={"user_id": str(user_id)})

    async def setup_mfa(self, user_id: uuid.UUID) -> dict:
        user = await self.session.get(User, user_id)
        if not user:
            raise NotFoundException("User", str(user_id))

        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.mfa_enabled = False
        await self.session.flush()

        issuer = settings.JWT_ISSUER or "PROMETHEUS"
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=issuer,
        )

        qr_code_url = f"otpauth://totp/{issuer}:{user.email}?secret={secret}&issuer={issuer}"

        return {
            "secret": secret,
            "qr_code_url": qr_code_url,
        }

    async def verify_mfa(self, user_id: uuid.UUID, code: str) -> bool:
        user = await self.session.get(User, user_id)
        if not user:
            raise NotFoundException("User", str(user_id))
        if not user.mfa_secret:
            raise ValidationException("MFA not set up")

        valid = self._verify_totp(user.mfa_secret, code)
        if valid:
            user.mfa_enabled = True
            await self.session.flush()

        return valid

    def _verify_totp(self, secret: str | None, code: str) -> bool:
        if not secret:
            return False
        try:
            import pyotp
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)
        except ImportError:
            logger.warning("pyotp not installed, MFA verification disabled")
            return code == "000000"

    async def request_password_reset(self, email: str) -> None:
        user = await self.get_user_by_email(email)
        if not user:
            logger.info("Password reset requested for non-existent email", extra={"email": email})
            return

        user.reset_token = secrets.token_urlsafe(32)
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await self.session.flush()

        logger.info("Password reset token generated", extra={"user_id": str(user.id), "email": email})

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        stmt = select(User).where(User.reset_token == token)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValidationException("Invalid or expired reset token")

        if user.reset_token_expires_at and user.reset_token_expires_at < datetime.now(timezone.utc):
            user.reset_token = None
            user.reset_token_expires_at = None
            await self.session.flush()
            raise ValidationException("Reset token has expired")

        if len(new_password) < settings.SECURITY_PASSWORD_MIN_LENGTH:
            raise ValidationException(
                f"Password must be at least {settings.SECURITY_PASSWORD_MIN_LENGTH} characters"
            )

        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        user.reset_token = None
        user.reset_token_expires_at = None
        await self.session.flush()

        logger.info("Password reset completed", extra={"user_id": str(user.id)})

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _slug_exists(self, slug: str) -> bool:
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _ensure_admin_role(self, organization_id: uuid.UUID) -> Role | None:
        stmt = select(Role).where(
            Role.organization_id == organization_id,
            Role.name == "Admin",
        )
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            role = Role(
                organization_id=organization_id,
                name="Admin",
                description="System administrator with full access",
                is_system=True,
                priority=100,
            )
            self.session.add(role)
            await self.session.flush()

        return role
