from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_session
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    RoleCreate,
    RoleResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.user import User
from app.models.role import Role
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(User).where(User.organization_id == org_id, User.is_active.is_(True))

    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(User, sort_by, User.created_at) if sort_by else User.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    users = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    existing = await session.execute(
        select(User).where(User.email == payload.email, User.organization_id == org_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User with this email already exists")

    user = User(organization_id=org_id, **payload.model_dump(exclude={"roles"}))
    session.add(user)
    await session.flush()

    if payload.roles:
        role_query = await session.execute(
            select(Role).where(Role.id.in_(payload.roles), Role.organization_id == org_id)
        )
        user.roles = role_query.scalars().all()

    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(User).where(User.id == user_id, User.organization_id == org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(User).where(User.id == user_id, User.organization_id == org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    update_data = payload.model_dump(exclude_unset=True, exclude={"roles"})
    for field, value in update_data.items():
        setattr(user, field, value)

    if payload.roles is not None:
        role_query = await session.execute(
            select(Role).where(Role.id.in_(payload.roles), Role.organization_id == org_id)
        )
        user.roles = role_query.scalars().all()

    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=APIResponse)
async def deactivate_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(User).where(User.id == user_id, User.organization_id == org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    user.is_active = False
    await session.commit()
    return APIResponse(message="User deactivated successfully")


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Role).where(Role.organization_id == org_id)
    )
    roles = result.scalars().all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    payload: RoleCreate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    existing = await session.execute(
        select(Role).where(Role.name == payload.name, Role.organization_id == org_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Role with this name already exists")

    role = Role(organization_id=org_id, **payload.model_dump())
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return RoleResponse.model_validate(role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    payload: RoleCreate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Role).where(Role.id == role_id, Role.organization_id == org_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundException("Role not found")

    for field, value in payload.model_dump().items():
        setattr(role, field, value)
    await session.commit()
    await session.refresh(role)
    return RoleResponse.model_validate(role)


@router.delete("/roles/{role_id}", response_model=APIResponse)
async def delete_role(
    role_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Role).where(Role.id == role_id, Role.organization_id == org_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundException("Role not found")

    await session.delete(role)
    await session.commit()
    return APIResponse(message="Role deleted successfully")


@router.put("/{user_id}/roles", response_model=UserResponse)
async def assign_user_roles(
    user_id: str,
    role_ids: list[str],
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(User).where(User.id == user_id, User.organization_id == org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    role_query = await session.execute(
        select(Role).where(Role.id.in_(role_ids), Role.organization_id == org_id)
    )
    roles = role_query.scalars().all()
    user.roles = roles
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)
