from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SimulationCreate(BaseModel):
    name: str
    description: str | None = None
    type: str = "campaign"
    campaign_id: str | None = None
    configuration: dict[str, Any] = {}
    parameters: dict[str, Any] = {}
    agent_configuration: dict[str, Any] = {}
    monte_carlo_iterations: int = 1000
    confidence_level: float = 0.95
    time_horizon_days: int = 30
    iterations: int | None = None
    time_horizon: int | None = None
    segment_ids: list[str] = []
    sample_size: int = 10000
    include_control: bool = True
    expected_outputs: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _map_frontend_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "iterations" in data and data["iterations"] is not None:
                data["monte_carlo_iterations"] = data.pop("iterations")
            if "time_horizon" in data and data["time_horizon"] is not None:
                data["time_horizon_days"] = data.pop("time_horizon")
        return data

    @field_validator("monte_carlo_iterations")
    @classmethod
    def validate_iterations(cls, v: int) -> int:
        if v < 1:
            raise ValueError("monte_carlo_iterations must be at least 1")
        return v

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0 < v < 1:
            raise ValueError("confidence_level must be between 0 and 1")
        return v

    @field_validator("time_horizon_days")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        if v < 1:
            raise ValueError("time_horizon_days must be at least 1")
        return v


class SimulationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    campaign_id: str | None = None
    configuration: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None
    agent_configuration: dict[str, Any] | None = None
    monte_carlo_iterations: int | None = None
    confidence_level: float | None = None
    time_horizon_days: int | None = None
    segment_ids: list[str] | None = None
    sample_size: int | None = None
    include_control: bool | None = None
    expected_outputs: list[str] | None = None


class SimulationConfigResponse(BaseModel):
    iterations: int = 1000
    time_horizon: int = 30
    confidence_level: float = 0.95
    segment_ids: list[str] = []
    parameters: dict[str, Any] = {}


class SimulationResponse(BaseModel):
    id: UUID
    name: str
    config: SimulationConfigResponse
    status: str | None = None
    results: Any | None = None
    forecast: Any | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _build_nested(cls, data: Any) -> Any:
        if isinstance(data, dict):
            config = {
                "iterations": data.pop("monte_carlo_iterations", 1000) or 1000,
                "time_horizon": data.pop("time_horizon_days", 30) or 30,
                "confidence_level": data.pop("confidence_level", 0.95) or 0.95,
                "segment_ids": data.pop("segment_ids", []) or [],
                "parameters": data.pop("parameters", {}) or {},
            }
            data["config"] = config
            for key in ("organization_id", "description", "type", "campaign_id", "configuration",
                        "agent_configuration", "sample_size", "include_control",
                        "expected_outputs", "created_by", "started_at",
                        "completed_at", "updated_at"):
                data.pop(key, None)
            data.setdefault("results", None)
            data.setdefault("forecast", None)
        elif hasattr(data, "monte_carlo_iterations"):
            config = SimulationConfigResponse(
                iterations=getattr(data, "monte_carlo_iterations", 1000) or 1000,
                time_horizon=getattr(data, "time_horizon_days", 30) or 30,
                confidence_level=getattr(data, "confidence_level", 0.95) or 0.95,
                segment_ids=getattr(data, "segment_ids", []) or [],
                parameters=getattr(data, "parameters", {}) or {},
            )
            data = {
                "id": data.id,
                "name": data.name,
                "config": config,
                "status": getattr(data, "status", None),
                "results": None,
                "forecast": None,
                "created_at": getattr(data, "created_at", None),
            }
        return data


class SimulationRunResponse(BaseModel):
    id: UUID
    simulation_id: UUID
    run_number: int
    status: str | None = None
    seed: int | None = None
    agents_count: int | None = None
    iterations_executed: int | None = None
    runtime_seconds: float | None = None
    cpu_usage: float | None = None
    memory_usage_bytes: int | None = None
    error_message: str | None = None
    logs: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SimulationResultResponse(BaseModel):
    id: UUID
    simulation_id: UUID
    run_id: UUID | None = None
    aggregated_metrics: dict[str, Any] = {}
    customer_projections: dict[str, Any] = {}
    segment_projections: dict[str, Any] = {}
    campaign_impact: dict[str, Any] = {}
    confidence_intervals: dict[str, Any] = {}
    monte_carlo_distribution: dict[str, Any] = {}
    expected_outcomes: dict[str, Any] = {}
    risk_assessment: dict[str, Any] = {}
    recommendations: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class SimulationForecastResponse(BaseModel):
    expected_revenue: float | None = None
    expected_conversions: float | None = None
    expected_open_rate: float | None = None
    expected_click_rate: float | None = None
    revenue_confidence_interval: list[float] = []
    conversion_confidence_interval: list[float] = []
    scenarios: dict[str, Any] = {}
    sensitivity: list[dict[str, Any]] = []
    risk_assessment: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class SimulationStatusResponse(BaseModel):
    id: UUID
    status: str
    progress: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None


class SimulationProgressResponse(BaseModel):
    progress: float = 0.0
    status: str


class SimulationListResponse(SimulationResponse):
    pass
