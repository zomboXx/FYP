from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TrafficState = Literal["light", "normal", "heavy"]
WeatherState = Literal["clear", "rain", "storm"]
NodeType = Literal["depot", "order", "intersection", "landmark"]
OrderCategory = Literal["food", "ride", "parcel", "grocery"]
OrderUrgency = Literal["low", "normal", "urgent"]
UserRole = Literal["admin", "shipper"]


class Node(BaseModel):
    id: str
    name: str
    x: float
    y: float
    lat: float | None = None
    lng: float | None = None
    type: NodeType = "intersection"


class Edge(BaseModel):
    source: str
    target: str
    distance_km: float = Field(gt=0)
    base_minutes: float = Field(gt=0)
    traffic: TrafficState = "normal"
    blocked: bool = False


class Order(BaseModel):
    id: str
    node_id: str
    pickup_node_id: str | None = None
    dropoff_node_id: str | None = None
    category: OrderCategory = "parcel"
    urgency: OrderUrgency = "normal"
    demand_kg: float = Field(ge=0)
    ready_min: int = Field(ge=0)
    due_min: int = Field(ge=0)
    service_min: int = Field(ge=0)
    priority: int = Field(default=1, ge=1, le=5)


class Scenario(BaseModel):
    depot_id: str
    capacity_kg: float
    nodes: list[Node]
    edges: list[Edge]
    orders: list[Order]


class DeliveryState(BaseModel):
    position_id: str
    current_min: float = 0
    carrying_order_ids: list[str] = Field(default_factory=list)
    pending_order_ids: list[str] = Field(default_factory=list)
    delivered_order_ids: list[str] = Field(default_factory=list)
    weather: WeatherState = "clear"
    traffic_summary: dict[TrafficState, int] = Field(default_factory=dict)
    blocked_edges: list[str] = Field(default_factory=list)


class PathfindingRequest(BaseModel):
    algorithm: Literal["bfs", "dfs", "greedy", "astar"]
    startId: str
    goalId: str
    debug: bool = False
    scenario: Scenario | None = None


class DeliveryOptimizeRequest(BaseModel):
    algorithm: Literal[
        "simple_hill_climbing",
        "simulated_annealing",
    ]
    orderIds: list[str] | None = None
    capacityKg: float | None = None
    startId: str | None = None
    goalId: str | None = None
    routingStrategy: Literal["nearest_neighbor", "global_optimization"] = "global_optimization"
    debug: bool = False
    scenario: Scenario | None = None


class ConstraintCheckRequest(BaseModel):
    route: list[str]
    capacityKg: float | None = None
    debug: bool = False
    scenario: Scenario | None = None


class CspSolveRequest(BaseModel):
    algorithm: Literal["backtracking", "forward_checking"] = "forward_checking"
    orderIds: list[str] | None = None
    capacityKg: float | None = None
    debug: bool = False
    scenario: Scenario | None = None


class EventSimulateRequest(BaseModel):
    eventType: Literal["rain", "accident", "peak_hour"] = "rain"
    affectedEdge: tuple[str, str] | None = None
    debug: bool = False
    scenario: Scenario | None = None


class ComplexSearchRequest(BaseModel):
    algorithm: Literal["online_replan", "and_or"] = "online_replan"
    startId: str
    goalId: str
    sensorRadius: int = Field(default=1, ge=0, le=4)
    hiddenEvent: Literal["accident", "rain", "peak_hour"] = "accident"
    debug: bool = False
    scenario: Scenario | None = None


class AdversarialSearchRequest(BaseModel):
    algorithm: Literal["minimax", "alpha_beta"] = "minimax"
    startId: str | None = None
    goalId: str | None = None
    disruptionBudget: int = Field(default=1, ge=1, le=2)
    debug: bool = False
    scenario: Scenario | None = None

class TraceStep(BaseModel):
    stepIndex: int
    phase: str
    currentNode: str | None = None
    previousNode: str | None = None
    frontier: list[str] = Field(default_factory=list)
    visitedNodes: list[str] = Field(default_factory=list)
    candidatePath: list[str] = Field(default_factory=list)
    previewPath: list[str] = Field(default_factory=list)
    costSoFar: float = 0
    heuristic: float = 0
    decisionReason: str
    debugData: dict[str, Any] = Field(default_factory=dict)


class AlgorithmResponse(BaseModel):
    path: list[str]
    visitedNodes: list[str]
    metrics: dict[str, Any]
    runtimeMs: float
    explanation: str
    traceSteps: list[TraceStep] = Field(default_factory=list)


class ScenarioResponse(Scenario):
    pass


class MapSummary(BaseModel):
    id: int
    name: str
    description: str = ""
    algorithmGroup: str
    isDefault: bool = False
    nodeCount: int = 0
    edgeCount: int = 0
    updatedAt: int


class MapDetail(MapSummary):
    scenario: Scenario


class MapCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=240)
    algorithmGroup: str = Field(default="informed", min_length=1, max_length=40)
    isDefault: bool = False
    scenario: Scenario | None = None


class MapPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=240)
    algorithmGroup: str | None = Field(default=None, min_length=1, max_length=40)
    isDefault: bool | None = None
    scenario: Scenario | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    user: "UserPublic"


class UserPublic(BaseModel):
    id: int
    username: str
    role: UserRole
    shipperGroup: str | None = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: UserRole = "shipper"
    shipperGroup: str | None = "on_demand"


class PermissionRow(BaseModel):
    shipperGroup: str
    algorithmGroup: str
    algorithmName: str
    enabled: bool


class PermissionPatchRequest(BaseModel):
    shipperGroup: str
    algorithmGroup: str
    algorithmName: str
    enabled: bool


class UserGroupPatchRequest(BaseModel):
    shipperGroup: str


class AvailableOrder(BaseModel):
    id: str
    category: OrderCategory
    urgency: OrderUrgency
    pickupNodeId: str
    dropoffNodeId: str
    demandKg: float
    priority: int
    dueMin: int
    status: str


class AcceptOrdersRequest(BaseModel):
    orderIds: list[str]


class CompleteOrderRequest(BaseModel):
    orderId: str


class ShipperPlanRequest(BaseModel):
    algorithm: Literal[
        "simple_hill_climbing",
        "simulated_annealing",
    ] = "simple_hill_climbing"
    startId: str | None = None
    goalId: str | None = None
    routingStrategy: Literal["nearest_neighbor", "global_optimization"] = "global_optimization"
    debug: bool = True
