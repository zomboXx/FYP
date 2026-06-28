from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from fastapi import HTTPException, status

from app.algorithms.adversarial import adversarial_search
from app.algorithms.complex import complex_search
from app.algorithms.constraints import check_route_constraints, solve_delivery_csp
from app.algorithms.delivery import DELIVERY_ALGORITHMS, selected_orders
from app.algorithms.events import expectimax_event_choice, replan_after_event
from app.algorithms.search import SEARCH_ALGORITHMS, astar
from app.data.scenario import default_scenario, load_osm_cached_scenario
from app.models.schemas import (
    AlgorithmResponse,
    AdversarialSearchRequest,
    ConstraintCheckRequest,
    ComplexSearchRequest,
    CspSolveRequest,
    DeliveryOptimizeRequest,
    EventSimulateRequest,
    Order,
    PathfindingRequest,
    Scenario,
    TraceStep,
    UserPublic,
)
from app.services.auth_service import (
    accepted_order_models,
    allowed_order_categories,
    assert_algorithm_allowed,
    shipper_operation_profile,
)


def scenario_or_default(scenario: Scenario | None) -> Scenario:
    return scenario or load_osm_cached_scenario()


def scenario_has_nodes(scenario: Scenario, node_ids: list[str | None]) -> bool:
    available = {node.id for node in scenario.nodes}
    return all(node_id in available for node_id in node_ids if node_id)


def _enrich_trace_steps(trace_steps: list[TraceStep]) -> list[TraceStep]:
    for step in trace_steps:
        if not step.previewPath and step.candidatePath:
            step.previewPath = step.candidatePath[:]
        if step.previousNode is None and len(step.previewPath) >= 2:
            step.previousNode = step.previewPath[-2]
    return trace_steps


def run_pathfinding(request: PathfindingRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, request.algorithm)
    scenario = scenario_or_default(request.scenario)
    if request.scenario is None and not scenario_has_nodes(scenario, [request.startId, request.goalId]):
        scenario = default_scenario()
    started = perf_counter()
    result = SEARCH_ALGORITHMS[request.algorithm](scenario, request.startId, request.goalId, request.debug)
    runtime_ms = (perf_counter() - started) * 1000
    return AlgorithmResponse(
        path=result.path,
        visitedNodes=result.visited_nodes,
        runtimeMs=round(runtime_ms, 3),
        metrics={
            "algorithm": request.algorithm,
            "distanceKm": result.distance_km,
            "totalMinutes": result.total_minutes,
            "visitedCount": len(result.visited_nodes),
            "pathCost": result.cost,
        },
        explanation=(
            f"{request.algorithm.upper()} tim duong tu {request.startId} den {request.goalId}, "
            f"mo rong {len(result.visited_nodes)} nut va uoc tinh {result.total_minutes} phut."
        ),
        traceSteps=_enrich_trace_steps(result.trace_steps),
    )


def optimize_delivery(request: DeliveryOptimizeRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, request.algorithm)
    scenario = scenario_or_default(request.scenario)
    orders = selected_orders(scenario, request.orderIds)
    started = perf_counter()
    result = DELIVERY_ALGORITHMS[request.algorithm](scenario, orders, request.capacityKg, request.debug)
    runtime_ms = (perf_counter() - started) * 1000
    order_text = " -> ".join(result["stops"])
    return AlgorithmResponse(
        path=result["path"],
        visitedNodes=result["visited"],
        runtimeMs=round(runtime_ms, 3),
        metrics={
            "algorithm": request.algorithm,
            "stops": result["stops"],
            "distanceKm": result["distanceKm"],
            "travelMinutes": result["travelMinutes"],
            "waitMinutes": result["waitMinutes"],
            "serviceMinutes": result["serviceMinutes"],
            "totalMinutes": result["totalMinutes"],
            "lateOrders": result["lateOrders"],
            "loadKg": result["loadKg"],
            "capacityKg": result["capacityKg"],
            "penalty": result["penalty"],
            "priorityBonus": result["priorityBonus"],
            "totalCost": result["totalCost"],
            "iterations": result["iterations"],
            "pickupTimes": result["pickupTimes"],
            "arrivalTimes": result["arrivalTimes"],
            "initialState": result["initialState"],
            "goalState": result["goalState"],
            "stateHistory": result["stateHistory"],
        },
        explanation=f"{request.algorithm} chon thu tu diem dung {order_text} voi tong chi phi {result['totalCost']}.",
        traceSteps=_enrich_trace_steps(result["traceSteps"]),
    )


def check_constraints(request: ConstraintCheckRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, "constraint")
    scenario = scenario_or_default(request.scenario)
    started = perf_counter()
    result = check_route_constraints(scenario, request.route, request.capacityKg, request.debug)
    runtime_ms = (perf_counter() - started) * 1000
    return AlgorithmResponse(
        path=request.route,
        visitedNodes=list(dict.fromkeys(request.route)),
        runtimeMs=round(runtime_ms, 3),
        metrics={key: value for key, value in result.items() if key != "traceSteps"},
        explanation="Lo trinh hop le." if result["valid"] else "Phat hien rang buoc vi pham: " + " ".join(result["violations"]),
        traceSteps=_enrich_trace_steps(result["traceSteps"]),
    )


def solve_csp(request: CspSolveRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, request.algorithm)
    scenario = scenario_or_default(request.scenario)
    started = perf_counter()
    result = solve_delivery_csp(scenario, request.algorithm, request.orderIds, request.capacityKg, request.debug)
    runtime_ms = (perf_counter() - started) * 1000
    return AlgorithmResponse(
        path=result["path"],
        visitedNodes=list(dict.fromkeys(result["path"])),
        runtimeMs=round(runtime_ms, 3),
        metrics={key: value for key, value in result.items() if key not in {"path", "traceSteps"}},
        explanation=(
            f"{request.algorithm} tim duoc lich pickup/dropoff thoa tat ca rang buoc."
            if result["valid"]
            else f"{request.algorithm} ket luan bai toan CSP khong co nghiem voi rang buoc hien tai."
        ),
        traceSteps=_enrich_trace_steps(result["traceSteps"]),
    )


def run_complex_search(request: ComplexSearchRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, request.algorithm)
    scenario = scenario_or_default(request.scenario)
    started = perf_counter()
    result = complex_search(
        scenario,
        request.algorithm,
        request.startId,
        request.goalId,
        request.sensorRadius,
        request.hiddenEvent,
        request.debug,
    )
    runtime_ms = (perf_counter() - started) * 1000
    metrics = {key: value for key, value in result.items() if key not in {"path", "visited", "traceSteps", "actualScenario"}}
    return AlgorithmResponse(
        path=result["path"],
        visitedNodes=result["visited"],
        runtimeMs=round(runtime_ms, 3),
        metrics=metrics,
        explanation=(
            f"{request.algorithm} lap conditional plan cho hidden event {request.hiddenEvent}; "
            f"complete={result.get('complete', False)} tren mo hinh AND-OR."
            if request.algorithm == "and_or"
            else f"{request.algorithm} xu ly {request.hiddenEvent} trong moi truong partial observable; "
            f"sensor radius={request.sensorRadius}, re-plan {result.get('replans', 0)} lan."
        ),
        traceSteps=_enrich_trace_steps(result["traceSteps"]),
    )


def simulate_dynamic_event(request: EventSimulateRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, "expectimax")
    scenario = scenario_or_default(request.scenario)
    started = perf_counter()
    replan = replan_after_event(scenario, request.eventType, request.affectedEdge)
    updated = replan["updatedScenario"]
    expectimax = expectimax_event_choice(updated)
    runtime_ms = (perf_counter() - started) * 1000
    trace_steps = [
        TraceStep(
            stepIndex=index,
            phase="expectimax_branch",
            currentNode=None,
            frontier=[],
            visitedNodes=[],
            candidatePath=[],
            costSoFar=branch["minutes"],
            heuristic=branch["probability"],
            decisionReason=f"Nhanh {branch['event']} co xac suat {branch['probability']} va chi phi {branch['minutes']} phut.",
        )
        for index, branch in enumerate(expectimax["branches"])
    ] if request.debug else []
    if request.debug:
        trace_steps.insert(
            0,
            TraceStep(
                stepIndex=0,
                phase="online_replan",
                currentNode=replan["start"],
                frontier=[replan["goal"]],
                visitedNodes=replan["visited"],
                candidatePath=replan["replannedPath"],
                costSoFar=replan["replannedMinutes"],
                heuristic=0,
                decisionReason=(
                    f"Truoc su kien: {' -> '.join(replan['originalPath'])} ({replan['originalMinutes']} phut). "
                    f"Sau su kien: {' -> '.join(replan['replannedPath'])} ({replan['replannedMinutes']} phut)."
                ),
            ),
        )
        for index, step in enumerate(trace_steps):
            step.stepIndex = index
    return AlgorithmResponse(
        path=replan["replannedPath"] or expectimax["path"],
        visitedNodes=replan["visited"] or expectimax["visited"],
        runtimeMs=round(runtime_ms, 3),
        metrics={
            "eventType": request.eventType,
            "onlineSearchMode": "sense event -> update environment state -> re-plan with A* -> evaluate uncertainty with Expectimax",
            "originalPath": replan["originalPath"],
            "originalMinutes": replan["originalMinutes"],
            "replannedPath": replan["replannedPath"],
            "replannedMinutes": replan["replannedMinutes"],
            "changedEdges": replan["changedEdges"],
            "expectedMinutes": expectimax["expectedMinutes"],
            "branches": expectimax["branches"],
            "updatedScenario": updated.model_dump(),
        },
        explanation=replan["eventMessage"] + " He thong cap nhat state moi va re-plan truoc khi tinh chi phi ky vong.",
        traceSteps=_enrich_trace_steps(trace_steps),
    )


def run_adversarial_search(request: AdversarialSearchRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, request.algorithm)
    scenario = scenario_or_default(request.scenario)
    started = perf_counter()
    result = adversarial_search(
        scenario,
        request.algorithm,
        request.startId,
        request.goalId,
        request.disruptionBudget,
        request.debug,
    )
    runtime_ms = (perf_counter() - started) * 1000
    return AlgorithmResponse(
        path=result["path"],
        visitedNodes=result["visited"],
        runtimeMs=round(runtime_ms, 3),
        metrics={
            "algorithm": result["algorithm"],
            "chosenGoal": result["goal"],
            "gameValue": result["gameValue"],
            "worstCaseCost": result["worstCaseCost"],
            "worstCaseRecoveryPath": result["worstCaseRecoveryPath"],
            "branches": result["branches"],
            "expandedNodes": result["expandedNodes"],
            "prunedBranches": result["prunedBranches"],
            "disruptionBudget": result["disruptionBudget"],
        },
        explanation=(
            f"{request.algorithm} chon robust route tu {result['start']} den {result['goal']} trong khi "
            f"MIN ap dung disruption bat loi; worst-case cost {result['worstCaseCost']}."
        ),
        traceSteps=_enrich_trace_steps(result["traceSteps"]),
    )

def _order_dropoff(order: Order) -> str:
    return order.dropoff_node_id or order.node_id


def _order_pickup(scenario: Scenario, order: Order) -> str:
    return order.pickup_node_id or scenario.depot_id


def _is_batchable_on_demand_order(order: Order) -> bool:
    return order.category != "ride"


def _route_minutes_for_orders(scenario: Scenario, start_id: str, orders: list[Order]) -> float:
    current = start_id
    total = 0.0
    for order in orders:
        goal = _order_dropoff(order)
        result = astar(scenario, current, goal)
        if not result.path:
            return float("inf")
        total += result.total_minutes
        current = goal
    return total


def _nearest_delivery_order(scenario: Scenario, start_id: str, orders: list[Order]) -> list[Order]:
    remaining = orders[:]
    ordered = []
    current = start_id
    while remaining:
        next_order = min(
            remaining,
            key=lambda order: astar(scenario, current, _order_dropoff(order)).total_minutes,
        )
        ordered.append(next_order)
        remaining.remove(next_order)
        current = _order_dropoff(next_order)
    return ordered


def _globally_improved_delivery_order(scenario: Scenario, start_id: str, orders: list[Order]) -> list[Order]:
    ordered = _nearest_delivery_order(scenario, start_id, orders)
    best_cost = _route_minutes_for_orders(scenario, start_id, ordered)
    improved = True
    while improved:
        improved = False
        for left in range(len(ordered)):
            for right in range(left + 1, len(ordered)):
                candidate = ordered[:]
                candidate[left], candidate[right] = candidate[right], candidate[left]
                candidate_cost = _route_minutes_for_orders(scenario, start_id, candidate)
                if candidate_cost < best_cost:
                    ordered, best_cost, improved = candidate, candidate_cost, True
    return ordered


@dataclass
class ShipperRouteDraft:
    scenario: Scenario
    debug: bool
    path: list[str]
    current: str
    visited: list[str] = field(default_factory=list)
    route_legs: list[dict] = field(default_factory=list)
    trace_steps: list[TraceStep] = field(default_factory=list)
    total_minutes: float = 0.0
    total_distance: float = 0.0

    def append_leg(self, goal: str, kind: str, order_id: str, label: str) -> bool:
        from_node = self.current
        if self.current == goal:
            leg_path = [from_node, goal]
            visited_nodes: list[str] = [goal]
            minutes = 0.0
            distance_km = 0.0
        else:
            result = astar(self.scenario, self.current, goal)
            if not result.path:
                return False
            leg_path = result.path
            visited_nodes = result.visited_nodes
            minutes = result.total_minutes
            distance_km = result.distance_km

        self.path.extend(leg_path[1:])
        self.visited.extend(visited_nodes)
        self.total_minutes += minutes
        self.total_distance += distance_km
        leg = {
            "index": len(self.route_legs),
            "from": from_node,
            "to": goal,
            "kind": kind,
            "orderId": order_id,
            "label": label,
            "path": leg_path,
            "minutes": minutes,
            "distanceKm": distance_km,
        }
        self.route_legs.append(leg)

        # Playback needs both a flattened path and semantic legs so repeated edges still keep their direction.
        if self.debug:
            self.trace_steps.append(
                TraceStep(
                    stepIndex=len(self.trace_steps),
                    phase=kind,
                    currentNode=goal,
                    frontier=[],
                    visitedNodes=list(dict.fromkeys(self.visited)),
                    candidatePath=self.path[:],
                    costSoFar=round(self.total_minutes, 2),
                    heuristic=0,
                    decisionReason=label,
                    debugData={"orderId": order_id, "leg": leg, "direction": f"{from_node}->{goal}"},
                )
            )
        self.current = goal
        return True


def _default_mobile_start(scenario: Scenario) -> str:
    return next(
        (node.id for node in scenario.nodes if node.id != scenario.depot_id and node.type == "intersection"),
        scenario.depot_id,
    )


def _resolve_shipper_start(scenario: Scenario, profile: str, requested_start: str | None) -> str:
    if profile == "warehouse":
        return "W1" if any(node.id == "W1" for node in scenario.nodes) else scenario.depot_id
    fallback = _default_mobile_start(scenario)
    return requested_start if requested_start in {node.id for node in scenario.nodes} else fallback


def _routeable_orders(scenario: Scenario, user: UserPublic) -> list[Order]:
    allowed_categories = set(allowed_order_categories(user))
    return [
        order
        for order in accepted_order_models(user)
        if order.category in allowed_categories
        and scenario_has_nodes(scenario, [order.pickup_node_id, order.dropoff_node_id, order.node_id])
    ]


def _ordered_for_shipper_profile(
    scenario: Scenario,
    profile: str,
    strategy: str,
    start_id: str,
    orders: list[Order],
) -> list[Order]:
    if profile == "on_demand":
        return _ordered_for_on_demand_profile(scenario, start_id, orders)
    if profile != "warehouse":
        return orders
    if strategy == "nearest_neighbor":
        return _nearest_delivery_order(scenario, start_id, orders)
    return _globally_improved_delivery_order(scenario, start_id, orders)


def _ordered_for_on_demand_profile(scenario: Scenario, start_id: str, orders: list[Order]) -> list[Order]:
    remaining = orders[:]
    ordered: list[Order] = []
    current = start_id
    while remaining:
        next_order = min(
            remaining,
            key=lambda order: astar(scenario, current, _order_pickup(scenario, order)).total_minutes,
        )
        pickup = _order_pickup(scenario, next_order)
        if _is_batchable_on_demand_order(next_order):
            bundle = [
                order
                for order in remaining
                if _is_batchable_on_demand_order(order) and _order_pickup(scenario, order) == pickup
            ]
            bundle = _globally_improved_delivery_order(scenario, pickup, bundle)
        else:
            bundle = [next_order]
        ordered.extend(bundle)
        for order in bundle:
            remaining.remove(order)
        current = _order_dropoff(bundle[-1])
    return ordered


def _build_shipper_route(
    scenario: Scenario,
    profile: str,
    start_id: str,
    orders: list[Order],
    debug: bool,
) -> tuple[ShipperRouteDraft, int]:
    draft = ShipperRouteDraft(scenario=scenario, debug=debug, path=[start_id], current=start_id)
    late_orders = 0
    index = 0
    while index < len(orders):
        order = orders[index]
        pickup = _order_pickup(scenario, order)
        dropoff = _order_dropoff(order)
        if profile == "on_demand":
            bundle = [order]
            if _is_batchable_on_demand_order(order):
                next_index = index + 1
                while next_index < len(orders):
                    candidate = orders[next_index]
                    if not _is_batchable_on_demand_order(candidate) or _order_pickup(scenario, candidate) != pickup:
                        break
                    bundle.append(candidate)
                    next_index += 1
            draft.append_leg(
                pickup,
                "approach_pickup",
                order.id,
                f"Di tu vi tri hien tai den diem nhan {len(bundle)} don tai {pickup}.",
            )
            for bundled_order in bundle:
                bundled_dropoff = _order_dropoff(bundled_order)
                draft.append_leg(
                    bundled_dropoff,
                    "serve_order",
                    bundled_order.id,
                    f"Da nhan hang tai {pickup}, giao {bundled_order.id} den {bundled_dropoff}.",
                )
                if draft.total_minutes > bundled_order.due_min:
                    late_orders += 1
            index += len(bundle)
            continue
        else:
            draft.append_leg(dropoff, "warehouse_delivery", order.id, f"Giao {order.id} tu tuyen kho den {dropoff}.")
        if draft.total_minutes > order.due_min:
            late_orders += 1
        index += 1
    return draft, late_orders


def plan_accepted_orders(request: DeliveryOptimizeRequest, user: UserPublic) -> AlgorithmResponse:
    assert_algorithm_allowed(user, request.algorithm)
    scenario = scenario_or_default(request.scenario)
    profile = shipper_operation_profile(user)
    start_id = _resolve_shipper_start(scenario, profile, request.startId)
    orders = _routeable_orders(scenario, user)
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chua co don hang da nhan phu hop de lap lo trinh.",
        )
    ordered = _ordered_for_shipper_profile(scenario, profile, request.routingStrategy, start_id, orders)
    started = perf_counter()
    draft, late_orders = _build_shipper_route(scenario, profile, start_id, ordered, request.debug)

    capacity = request.capacityKg or scenario.capacity_kg
    load_kg = sum(order.demand_kg for order in ordered) if profile == "warehouse" else max(
        (order.demand_kg for order in ordered),
        default=0.0,
    )
    runtime_ms = (perf_counter() - started) * 1000
    strategy_label = "nearest next stop" if request.routingStrategy == "nearest_neighbor" else "global route optimization"
    return AlgorithmResponse(
        path=draft.path,
        visitedNodes=list(dict.fromkeys(draft.visited)),
        runtimeMs=round(runtime_ms, 3),
        metrics={
            "algorithm": request.algorithm,
            "operationProfile": profile,
            "routingStrategy": request.routingStrategy,
            "startNode": start_id,
            "orderSequence": [order.id for order in ordered],
            "stops": [start_id] + [leg["to"] for leg in draft.route_legs],
            "routeLegs": draft.route_legs,
            "directional": True,
            "distanceKm": round(draft.total_distance, 2),
            "travelMinutes": round(draft.total_minutes, 2),
            "totalMinutes": round(draft.total_minutes, 2),
            "lateOrders": late_orders,
            "loadKg": round(load_kg, 2),
            "capacityKg": capacity,
            "totalCost": round(draft.total_minutes + max(0.0, load_kg - capacity) * 40, 2),
        },
        explanation=(
            f"On-demand: {start_id} -> pickup -> dropoff cho {len(ordered)} don."
            if profile == "on_demand"
            else f"Warehouse delivery dung {strategy_label} qua {len(ordered)} diem giao."
        ),
        traceSteps=_enrich_trace_steps(draft.trace_steps),
    )
