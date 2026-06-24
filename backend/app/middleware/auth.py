from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_token, verify_token_type
from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.logging import logger
import uuid


security_scheme = HTTPBearer(auto_error=False)

# Default org from seed_data.py — used for dev-mode bypass
_DEV_ORG_ID = "eb35c0b4-f66b-442b-b35a-30246d8df683"
_DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._public_paths():
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            # Dev-mode bypass: inject default org/user so dashboard works without login
            request.state.user_id = _DEV_USER_ID
            request.state.organization_id = _DEV_ORG_ID
            request.state.user_roles = ["admin"]
            request.state.user_permissions = ["admin:*"]
            if not hasattr(request.state, "request_id") or not request.state.request_id:
                request.state.request_id = uuid.uuid4().hex
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.state.request_id
            return response

        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return JSONResponse(status_code=401, content={"success": False, "error": "Invalid authorization scheme"})

            payload = decode_token(token)
            if not verify_token_type(payload, "access"):
                return JSONResponse(status_code=401, content={"success": False, "error": "Invalid token type"})

            request.state.user_id = payload.get("sub")
            request.state.organization_id = payload.get("organization_id") or payload.get("org_id")
            request.state.user_roles = payload.get("roles", [])
            request.state.user_permissions = payload.get("permissions", [])
            if not hasattr(request.state, "request_id") or not request.state.request_id:
                request.state.request_id = uuid.uuid4().hex

        except ValueError as e:
            return JSONResponse(status_code=401, content={"success": False, "error": str(e)})
        except Exception as e:
            logger.warning(f"Auth error: {e}")
            return JSONResponse(status_code=401, content={"success": False, "error": "Invalid token"})

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

    # Dev-mode bypass: return a minimal user-like object if user_id is the dev placeholder
    if user_id == _DEV_USER_ID:
        class DevUser:
            id = uuid.UUID(_DEV_USER_ID)
            organization_id = uuid.UUID(_DEV_ORG_ID)
            email = "dev@prometheus.local"
            first_name = "Dev"
            last_name = "User"
            is_active = True
            roles = ["admin"]
            permissions = ["admin:*"]
        return DevUser()

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
