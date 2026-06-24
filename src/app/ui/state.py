from __future__ import annotations

from dataclasses import dataclass, field

from app.models.schemas import AlgorithmResponse, AvailableOrder, PermissionRow, Scenario, UserPublic


@dataclass
class ComparisonRow:
    label: str
    mode: str
    response: AlgorithmResponse


@dataclass
class FletState:
    user: UserPublic | None = None
    scenario: Scenario | None = None
    result: AlgorithmResponse | None = None
    comparisons: list[ComparisonRow] = field(default_factory=list)
    workspace: str = "defense"
    group: str = "informed"
    algorithm: str = "astar"
    start_id: str = ""
    goal_id: str = ""
    csp_order_ids: str = "O4"
    capacity_kg: float = 18.0
    sensor_radius: int = 1
    hidden_event: str = "accident"
    disruption_budget: int = 1
    shipper_start_id: str = ""
    shipper_routing_strategy: str = "global_optimization"
    shipper_playback_index: int = 0
    shipper_playback_auto: bool = False
    shipper_playback_token: int = 0
    map_tiles_enabled: bool = True
    trace_index: int = 0
    auto_run: bool = False
    auto_run_token: int = 0
    permissions: list[PermissionRow] = field(default_factory=list)
    orders: list[AvailableOrder] = field(default_factory=list)
    accepted_orders: list[AvailableOrder] = field(default_factory=list)
    selected_orders: set[str] = field(default_factory=set)
    arrival_prompted_order_ids: set[str] = field(default_factory=set)
    category_filter: str = "all"
    urgency_filter: str = "all"
    error: str = ""
