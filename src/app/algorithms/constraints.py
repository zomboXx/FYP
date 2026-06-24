from __future__ import annotations

from app.algorithms.graph import BLOCKED_COST, find_edge, path_time
from app.algorithms.search import astar
from app.models.schemas import Order, Scenario, TraceStep


def check_route_constraints(scenario: Scenario, route: list[str], capacity_kg: float | None = None, debug: bool = False) -> dict:
    capacity = capacity_kg or scenario.capacity_kg
    pickups_by_node: dict[str, list] = {}
    dropoffs_by_node: dict[str, list] = {}
    for order in scenario.orders:
        pickups_by_node.setdefault(order.pickup_node_id or scenario.depot_id, []).append(order)
        dropoffs_by_node.setdefault(order.dropoff_node_id or order.node_id, []).append(order)
    violations: list[str] = []
    load = 0.0
    max_load = 0.0
    current_time = 0.0
    carrying: set[str] = set()
    served: set[str] = set()
    blocked_segments: list[str] = []
    trace_steps: list[TraceStep] = []

    def process_node(node_id: str) -> None:
        nonlocal load, max_load, current_time
        for order in pickups_by_node.get(node_id, []):
            if order.id in served or order.id in carrying:
                continue
            if current_time < order.ready_min:
                current_time = order.ready_min
            carrying.add(order.id)
            load += order.demand_kg
            max_load = max(max_load, load)
            if load > capacity:
                violations.append(f"Vuot tai khi nhan {order.id}: {load:.1f}kg / {capacity:.1f}kg.")
        for order in dropoffs_by_node.get(node_id, []):
            if order.id in served:
                continue
            if order.id not in carrying:
                violations.append(f"Don {order.id} duoc giao tai {node_id} truoc khi nhan hang.")
                continue
            if current_time > order.due_min:
                violations.append(f"Don {order.id} giao tre: den phut {current_time:.1f}, han {order.due_min}.")
            carrying.remove(order.id)
            load -= order.demand_kg
            served.add(order.id)
            current_time += order.service_min

    if route:
        process_node(route[0])

    for a, b in zip(route, route[1:]):
        edge = find_edge(scenario, a, b)
        if edge is None:
            violations.append(f"Khong co duong noi {a}-{b}.")
            continue
        if edge.blocked:
            blocked_segments.append(f"{a}-{b}")
        current_time += path_time(scenario, [a, b])
        process_node(b)
        if debug:
            trace_steps.append(
                TraceStep(
                    stepIndex=len(trace_steps),
                    phase="constraint_check",
                    currentNode=b,
                    frontier=[],
                    visitedNodes=route[: route.index(b) + 1] if b in route else [a, b],
                    candidatePath=[a, b],
                    costSoFar=round(current_time, 2),
                    heuristic=0,
                    decisionReason=f"Kiem tra canh {a}-{b}: dang mang {len(carrying)} don, tai {load:.1f}/{capacity:.1f}kg, thoi gian {current_time:.1f}, vi pham hien co {len(violations)}.",
                )
            )

    if carrying:
        violations.append("Con don chua giao: " + ", ".join(sorted(carrying)) + ".")
    if blocked_segments:
        violations.append("Di qua duong bi chan: " + ", ".join(blocked_segments) + ".")
    if path_time(scenario, route) >= BLOCKED_COST:
        violations.append("Lo trinh co chi phi khong kha thi do duong chan hoac thieu canh.")

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "servedOrders": len(served),
        "loadKg": round(max_load, 2),
        "capacityKg": capacity,
        "totalMinutes": round(current_time, 2),
        "traceSteps": trace_steps,
    }


def solve_delivery_csp(
    scenario: Scenario,
    algorithm: str,
    order_ids: list[str] | None = None,
    capacity_kg: float | None = None,
    debug: bool = False,
) -> dict:
    orders = [order for order in scenario.orders if order_ids is None or order.id in set(order_ids)]
    capacity = capacity_kg or scenario.capacity_kg
    order_by_id = {order.id: order for order in orders}
    trace_steps: list[TraceStep] = []
    expanded_states = 0
    backtracks = 0

    def location(order: Order, action: str) -> str:
        return (order.pickup_node_id or scenario.depot_id) if action == "pickup" else (order.dropoff_node_id or order.node_id)

    def travel(current: str, target: str) -> tuple[list[str], float]:
        if current == target:
            return [current], 0.0
        result = astar(scenario, current, target)
        return result.path, result.total_minutes

    def available_actions(picked: set[str], delivered: set[str], load: float) -> list[tuple[str, str]]:
        actions: list[tuple[str, str]] = []
        for order in orders:
            if order.id not in picked and load + order.demand_kg <= capacity:
                actions.append((order.id, "pickup"))
            elif order.id in picked and order.id not in delivered:
                actions.append((order.id, "dropoff"))
        # Dropoffs are tried first because they release capacity and tighten deadline checks early.
        return sorted(
            actions,
            key=lambda item: (
                0 if item[1] == "dropoff" else 1,
                order_by_id[item[0]].due_min,
                -order_by_id[item[0]].priority,
            ),
        )

    def forward_feasible(current: str, current_time: float, picked: set[str], delivered: set[str]) -> bool:
        for order in orders:
            if order.id in delivered:
                continue
            pickup = order.pickup_node_id or scenario.depot_id
            dropoff = order.dropoff_node_id or order.node_id
            if order.id in picked:
                _, eta = travel(current, dropoff)
            else:
                _, to_pickup = travel(current, pickup)
                _, to_dropoff = travel(pickup, dropoff)
                eta = to_pickup + to_dropoff
            if eta >= BLOCKED_COST or current_time + eta > order.due_min:
                return False
        return True

    def trace(
        phase: str,
        current: str,
        route: list[str],
        current_time: float,
        actions: list[tuple[str, str]],
        assignment: list[str],
        reason: str,
        load: float,
    ) -> None:
        if not debug:
            return
        trace_steps.append(
            TraceStep(
                stepIndex=len(trace_steps),
                phase=phase,
                currentNode=current,
                frontier=[f"{action}:{order_id}" for order_id, action in actions],
                visitedNodes=list(dict.fromkeys(route)),
                candidatePath=route[:],
                costSoFar=round(current_time, 2),
                heuristic=float(len(actions)),
                decisionReason=reason,
                debugData={
                    "assignment": assignment[:],
                    "domain": [f"{action}:{order_id}" for order_id, action in actions],
                    "loadKg": round(load, 2),
                    "capacityKg": capacity,
                },
            )
        )

    def backtrack(
        current: str,
        current_time: float,
        load: float,
        picked: set[str],
        delivered: set[str],
        route: list[str],
        assignment: list[str],
    ) -> tuple[list[str], list[str], float] | None:
        nonlocal expanded_states, backtracks
        expanded_states += 1
        if len(delivered) == len(orders):
            trace("csp_solution", current, route, current_time, [], assignment, "Tat ca don da duoc gan hop le.", load)
            return route, assignment, current_time

        actions = available_actions(picked, delivered, load)
        trace("select_variable", current, route, current_time, actions, assignment, "MRV chon hanh dong kha thi tiep theo.", load)
        for order_id, action in actions:
            order = order_by_id[order_id]
            target = location(order, action)
            segment, travel_minutes = travel(current, target)
            if not segment or travel_minutes >= BLOCKED_COST:
                continue
            next_time = max(current_time + travel_minutes, order.ready_min) if action == "pickup" else current_time + travel_minutes
            next_load = load + order.demand_kg if action == "pickup" else load - order.demand_kg
            if action == "dropoff" and next_time > order.due_min:
                trace("reject_value", current, route, next_time, actions, assignment, f"Loai dropoff {order_id}: tre deadline {order.due_min}.", load)
                continue
            next_picked = picked | {order_id} if action == "pickup" else set(picked)
            next_delivered = delivered | {order_id} if action == "dropoff" else set(delivered)
            next_route = route + (segment[1:] if route else segment)
            next_assignment = assignment + [f"{action}:{order_id}@{target}"]
            if algorithm == "forward_checking" and not forward_feasible(target, next_time, next_picked, next_delivered):
                trace("forward_prune", target, next_route, next_time, actions, next_assignment, "Forward checking phat hien mien rong/infeasible.", next_load)
                continue
            result = backtrack(target, next_time, next_load, next_picked, next_delivered, next_route, next_assignment)
            if result is not None:
                return result
        backtracks += 1
        trace("backtrack", current, route, current_time, actions, assignment, "Khong con gia tri hop le; quay lui.", load)
        return None

    solution = backtrack(scenario.depot_id, 0.0, 0.0, set(), set(), [scenario.depot_id], [])
    return {
        "valid": solution is not None,
        "path": solution[0] if solution else [],
        "assignment": solution[1] if solution else [],
        "totalMinutes": round(solution[2], 2) if solution else None,
        "servedOrders": len(orders) if solution else 0,
        "capacityKg": capacity,
        "expandedStates": expanded_states,
        "backtracks": backtracks,
        "algorithm": algorithm,
        "traceSteps": trace_steps,
    }
