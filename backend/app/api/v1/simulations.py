from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_session
from app.schemas.simulation import (
    SimulationCreate,
    SimulationUpdate,
    SimulationResponse,
    SimulationListResponse,
    SimulationResultResponse,
    SimulationForecastResponse,
    SimulationRunResponse,
    SimulationStatusResponse,
    SimulationProgressResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.simulation import Simulation, SimulationRun, SimulationResult
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.simulation_service import SimulationService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=PaginatedResponse[SimulationListResponse])
async def list_simulations(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(Simulation).where(Simulation.organization_id == org_id)

    if status:
        query = query.where(Simulation.status == status)
    if search:
        query = query.where(Simulation.name.ilike(f"%{search}%"))

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(Simulation, sort_by, Simulation.created_at) if sort_by else Simulation.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    simulations = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[SimulationListResponse.model_validate(s) for s in simulations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("/", response_model=APIResponse[SimulationResponse])
async def create_simulation(
    payload: SimulationCreate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    simulation = Simulation(organization_id=org_id, **payload.model_dump())
    session.add(simulation)
    await session.commit()
    await session.refresh(simulation)
    return APIResponse(data=SimulationResponse.model_validate(simulation))


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.organization_id == org_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise NotFoundException("Simulation not found")
    return SimulationResponse.model_validate(simulation)


@router.put("/{simulation_id}", response_model=SimulationResponse)
async def update_simulation(
    simulation_id: str,
    payload: SimulationUpdate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.organization_id == org_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise NotFoundException("Simulation not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(simulation, field, value)
    await session.commit()
    await session.refresh(simulation)
    return SimulationResponse.model_validate(simulation)


@router.delete("/{simulation_id}", response_model=APIResponse)
async def delete_simulation(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.organization_id == org_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise NotFoundException("Simulation not found")

    await session.delete(simulation)
    await session.commit()
    return APIResponse(message="Simulation deleted successfully")


@router.post("/{simulation_id}/run", response_model=APIResponse)
async def run_simulation(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.organization_id == org_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise NotFoundException("Simulation not found")

    service = SimulationService(session)
    await service.run(simulation, org_id)
    return APIResponse(message="Simulation execution triggered successfully")


@router.get("/{simulation_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.organization_id == org_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise NotFoundException("Simulation not found")

    return SimulationStatusResponse(
        id=simulation.id,
        status=simulation.status,
        progress=simulation.progress,
        started_at=simulation.started_at,
        completed_at=simulation.completed_at,
    )


@router.get("/{simulation_id}/results", response_model=SimulationResultResponse)
async def get_simulation_results(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(SimulationResult).where(
            SimulationResult.simulation_id == simulation_id,
            SimulationResult.organization_id == org_id,
        )
    )
    sim_result = result.scalar_one_or_none()
    if not sim_result:
        raise NotFoundException("Simulation results not available")

    return SimulationResultResponse.model_validate(sim_result)


@router.get("/{simulation_id}/forecast", response_model=SimulationForecastResponse)
async def get_simulation_forecast(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = SimulationService(session)
    forecast = await service.get_forecast(simulation_id, org_id)
    if not forecast:
        raise NotFoundException("Forecast not available")
    return SimulationForecastResponse.model_validate(forecast)


@router.get("/{simulation_id}/runs", response_model=list[SimulationRunResponse])
async def get_simulation_runs(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(SimulationRun)
        .where(
            SimulationRun.simulation_id == simulation_id,
            SimulationRun.organization_id == org_id,
        )
        .order_by(SimulationRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [SimulationRunResponse.model_validate(r) for r in runs]


@router.get("/{simulation_id}/progress", response_model=SimulationProgressResponse)
async def get_simulation_progress(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.organization_id == org_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise NotFoundException("Simulation not found")

    return SimulationProgressResponse(
        progress=simulation.progress,
        status=simulation.status,
    )
