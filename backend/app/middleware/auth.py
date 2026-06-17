from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_token, verify_token_type
from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.logging import logger
import uuid


security_scheme = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._public_paths():
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise UnauthorizedException("Missing authorization header")

        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise UnauthorizedException("Invalid authorization scheme")

            payload = decode_token(token)
            if not verify_token_type(payload, "access"):
                raise UnauthorizedException("Invalid token type")

            request.state.user_id = payload.get("sub")
            request.state.organization_id = payload.get("organization_id") or payload.get("org_id")
            request.state.user_roles = payload.get("roles", [])
            request.state.user_permissions = payload.get("permissions", [])
            request.state.request_id = uuid.uuid4().hex

        except ValueError as e:
            raise UnauthorizedException(str(e))
        except Exception as e:
            logger.warning(f"Auth error: {e}")
            raise UnauthorizedException("Invalid token")

        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def _public_paths(self) -> set:
        return {
            "/health",
            "/ready",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/password-reset",
            "/api/v1/auth/password-reset/confirm",
            "/docs",
            "/openapi.json",
            "/redoc",
        }


async def get_current_user(request: Request):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise UnauthorizedException()
    from app.models.user import User
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        user = await session.get(User, uuid.UUID(user_id))
        if not user:
            raise UnauthorizedException()
        return user


async def get_current_organization(request: Request):
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise UnauthorizedException()
    return org_id


async def require_permission(resource: str, action: str):
    async def permission_dependency(request: Request):
        permissions = getattr(request.state, "user_permissions", [])
        required = f"{resource}:{action}"
        if required not in permissions and "admin:*" not in permissions:
            raise ForbiddenException(f"Missing permission: {required}")
        return True
    return permission_dependency


class OrganizationContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        org_id = getattr(request.state, "organization_id", None)
        if org_id:
            request.state.db_org_filter = {"organization_id": org_id}
        return await call_next(request)
