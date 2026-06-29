from __future__ import annotations

import math
import random

from app.algorithms.search import astar
from app.models.schemas import DeliveryState, Order, Scenario, TraceStep

CATEGORY_PRIORITY_BONUS = {"ride": 18, "food": 12, "parcel": 5, "grocery": 3}
URGENCY_PENALTY = {"urgent": 2.0, "normal": 1.0, "low": 0.6}
LOCAL_DEMO_ORDER_LIMIT = 3


def selected_orders(scenario: Scenario, order_ids: list[str] | None, limit: int | None = None) -> list[Order]:
    wanted = set(order_ids) if order_ids is not None else {order.id for order in scenario.orders}
    orders = [order for order in scenario.orders if order.id in wanted]
    return orders[:limit] if limit is not None else orders


def route_stops_for_orders(
    scenario: Scenario,
    orders: list[Order],
    start_id: str | None = None,
    goal_id: str | None = None,
) -> list[str]:
    start = start_id or scenario.depot_id
    goal = goal_id or start
    stops = [start]
    for order in orders:
        pickup = order.pickup_node_id or start
        dropoff = order.dropoff_node_id or order.node_id
        if pickup != stops[-1]:
            stops.append(pickup)
        if dropoff != stops[-1]:
            stops.append(dropoff)
    if stops[-1] != goal:
        stops.append(goal)
    return stops


def traffic_summary(scenario: Scenario) -> dict[str, int]:
    summary = {"light": 0, "normal": 0, "heavy": 0}
    for edge in scenario.edges:
        summary[edge.traffic] += 1
    return summary


def state_snapshot(
    scenario: Scenario,
    position_id: str,
    current_min: float,
    carrying: list[str],
    pending: list[str],
    delivered: list[str],
    weather: str = "clear",
) -> DeliveryState:
    return DeliveryState(
        position_id=position_id,
        current_min=round(current_min, 2),
        carrying_order_ids=carrying[:],
        pending_order_ids=pending[:],
        delivered_order_ids=delivered[:],
        weather=weather,
        traffic_summary=traffic_summary(scenario),
        blocked_edges=[f"{edge.source}-{edge.target}" for edge in scenario.edges if edge.blocked],
    )


def expand_route_with_astar(scenario: Scenario, stops: list[str]) -> tuple[list[str], list[str], float, float]:
    path: list[str] = []
    visited: list[str] = []
    total_minutes = 0.0
    total_distance = 0.0
    for start, goal in zip(stops, stops[1:]):
        result = astar(scenario, start, goal)
        if not result.path:
            return [], visited + result.visited_nodes, math.inf, math.inf
        path.extend(result.path if not path else result.path[1:])
        visited.extend(result.visited_nodes)
        total_minutes += result.total_minutes
        total_distance += result.distance_km
    return path, list(dict.fromkeys(visited)), round(total_minutes, 2), round(total_distance, 2)


def _append_trace(
    trace_steps: list[TraceStep],
    phase: str,
    current: str,
    route: list[str],
    cost: float,
    reason: str,
    debug_data: dict | None = None,
    heuristic: float = 0,
) -> None:
    trace_steps.append(
        TraceStep(
            stepIndex=len(trace_steps),
            phase=phase,
            currentNode=current,
            frontier=[],
            visitedNodes=list(dict.fromkeys(route)),
            candidatePath=route[:],
            costSoFar=round(cost, 2),
            heuristic=round(heuristic, 2),
            decisionReason=reason,
            debugData=debug_data or {},
        )
    )


def _order_state(orders: list[Order]) -> list[str]:
    return [order.id for order in orders]


def _order_route(
    scenario: Scenario,
    orders: list[Order],
    start_id: str | None = None,
    goal_id: str | None = None,
) -> list[str]:
    return route_stops_for_orders(scenario, orders, start_id, goal_id)


def _state_key(orders: list[Order]) -> tuple[str, ...]:
    return tuple(order.id for order in orders)


def _state_cost(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> float:
    return float(evaluate_delivery_order(scenario, orders, capacity_kg, start_id=start_id, goal_id=goal_id)["totalCost"])


def _state_value(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> float:
    return -_state_cost(scenario, orders, capacity_kg, start_id, goal_id)


def _state_node(scenario: Scenario, orders: list[Order]) -> str:
    if not orders:
        return scenario.depot_id
    return orders[0].pickup_node_id or orders[0].node_id or scenario.depot_id


def _swap_neighbors(orders: list[Order]) -> list[tuple[int, int, list[Order]]]:
    neighbors: list[tuple[int, int, list[Order]]] = []
    for i in range(len(orders)):
        for j in range(i + 1, len(orders)):
            candidate = orders[:]
            candidate[i], candidate[j] = candidate[j], candidate[i]
            neighbors.append((i, j, candidate))
    return neighbors


def _trace_local_state(
    trace_steps: list[TraceStep],
    scenario: Scenario,
    phase: str,
    state: list[Order],
    cost: float,
    reason: str,
    debug_data: dict,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> None:
    start = start_id or scenario.depot_id
    goal = goal_id or start
    _append_trace(
        trace_steps,
        phase,
        _state_node(scenario, state),
        _order_route(scenario, state, start, goal),
        cost,
        reason,
        {
            "traceType": "local_search",
            "routeStart": start,
            "routeGoal": goal,
            "state": _order_state(state),
            "h": round(cost, 2),
            "value": round(-cost, 2),
            "bestCost": round(cost, 2),
            "bestValue": round(-cost, 2),
            **debug_data,
        },
        heuristic=cost,
    )


def evaluate_delivery_order(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    start = start_id or scenario.depot_id
    goal = goal_id or start
    stops = route_stops_for_orders(scenario, orders, start, goal)
    path, visited, travel_minutes, distance_km = expand_route_with_astar(scenario, stops)
    capacity = capacity_kg or scenario.capacity_kg
    load = 0.0
    max_load = 0.0
    current_time = 0.0
    wait_minutes = 0.0
    service_minutes = 0.0
    late_orders = 0
    penalty = 0.0
    priority_bonus = 0.0
    arrival_times: dict[str, float] = {}
    pickup_times: dict[str, float] = {}
    trace_steps: list[TraceStep] = []
    current_position = start
    carrying: list[str] = []
    pending = [order.id for order in orders]
    delivered: list[str] = []
    state_history = [
        state_snapshot(scenario, current_position, current_time, carrying, pending, delivered).model_dump()
    ]
    for order in orders:
        pickup = order.pickup_node_id or start
        dropoff = order.dropoff_node_id or order.node_id
        pickup_path, _, pickup_minutes, _ = expand_route_with_astar(scenario, [current_position, pickup])
        if not pickup_path:
            penalty += 500
            continue
        current_time += pickup_minutes
        if current_time < order.ready_min:
            wait_minutes += order.ready_min - current_time
            current_time = order.ready_min
        pickup_times[order.id] = round(current_time, 2)
        if order.id in pending:
            pending.remove(order.id)
        carrying.append(order.id)
        load += order.demand_kg
        max_load = max(max_load, load)
        if load > capacity:
            penalty += (load - capacity) * 40
        if debug:
            _append_trace(
                trace_steps,
                "pickup_order",
                pickup,
                pickup_path,
                current_time,
                f"Nhan don {order.id} tai {pickup}: tai {load:.1f}/{capacity:.1f}kg, ready {order.ready_min}.",
            )
        service_minutes += 1
        current_time += 1
        state_history.append(state_snapshot(scenario, pickup, current_time, carrying, pending, delivered).model_dump())

        dropoff_path, _, dropoff_minutes, _ = expand_route_with_astar(scenario, [pickup, dropoff])
        if not dropoff_path:
            penalty += 500
            continue
        current_time += dropoff_minutes
        arrival_times[order.id] = round(current_time, 2)
        if current_time > order.due_min:
            late_orders += 1
            penalty += (current_time - order.due_min) * (2 + order.priority) * URGENCY_PENALTY[order.urgency]
        priority_bonus += CATEGORY_PRIORITY_BONUS[order.category]
        if order.id in carrying:
            carrying.remove(order.id)
        delivered.append(order.id)
        load -= order.demand_kg
        if debug:
            _append_trace(
                trace_steps,
                "deliver_order",
                dropoff,
                dropoff_path,
                current_time,
                f"Giao don {order.id} ({order.category}/{order.urgency}) luc {current_time:.1f}, deadline {order.due_min}.",
            )
        service_minutes += order.service_min
        current_time += order.service_min
        current_position = dropoff
        state_history.append(state_snapshot(scenario, current_position, current_time, carrying, pending, delivered).model_dump())

    return_path, _, return_minutes, _ = expand_route_with_astar(scenario, [current_position, goal])
    if return_path:
        current_time += return_minutes
        service_path = path
    else:
        service_path = path
    total_cost = current_time + penalty - priority_bonus * 0.05
    return {
        "path": service_path,
        "visited": visited,
        "stops": stops,
        "distanceKm": distance_km,
        "travelMinutes": round(travel_minutes, 2),
        "waitMinutes": round(wait_minutes, 2),
        "serviceMinutes": round(service_minutes, 2),
        "totalMinutes": round(current_time, 2),
        "lateOrders": late_orders,
        "loadKg": round(max_load, 2),
        "capacityKg": capacity,
        "penalty": round(penalty, 2),
        "priorityBonus": round(priority_bonus, 2),
        "totalCost": round(total_cost, 2),
        "pickupTimes": pickup_times,
        "arrivalTimes": arrival_times,
        "initialState": state_history[0],
        "goalState": state_history[-1],
        "stateHistory": state_history,
        "traceSteps": trace_steps,
    }


def _nearest_neighbor(scenario: Scenario, orders: list[Order], start_id: str | None = None) -> list[Order]:
    remaining = orders[:]
    current = start_id or scenario.depot_id
    planned: list[Order] = []
    while remaining:
        next_order = min(
            remaining,
            key=lambda order: (
                astar(scenario, current, order.pickup_node_id or current).total_minutes
                + astar(scenario, order.pickup_node_id or current, order.dropoff_node_id or order.node_id).total_minutes
            ),
        )
        planned.append(next_order)
        remaining.remove(next_order)
        current = next_order.dropoff_node_id or next_order.node_id
    return planned


def simple_hill_climbing(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    from app.algorithms.graph import build_adjacency, edge_time, heuristic_minutes, BLOCKED_COST

    adjacency = build_adjacency(scenario)
    start = start_id or scenario.depot_id
    goal = goal_id or start
    if not goal or goal == start:
        last_order = orders[-1] if orders else None
        goal = (last_order.dropoff_node_id or last_order.node_id) if last_order else start

    current_node = start
    current_h = heuristic_minutes(scenario, current_node, goal)
    visited_path: list[str] = [current_node]
    trace_steps: list[TraceStep] = []
    iterations = 0

    def _frontier_ids(node: str) -> list[str]:
        return [nid for nid, edge in adjacency.get(node, []) if edge_time(edge) < BLOCKED_COST and nid not in visited_path]

    if debug:
        trace_steps.append(TraceStep(
            stepIndex=0,
            phase="hill_climbing_init",
            currentNode=current_node,
            frontier=[],
            visitedNodes=visited_path[:],
            candidatePath=visited_path[:],
            costSoFar=0,
            heuristic=round(current_h, 2),
            decisionReason=f"Bat dau tai {current_node}, h={current_h:.2f}. Di toi node gan dich hon (h nho hon) theo do thi.",
            debugData={
                "traceType": "local_search",
                "courseConcept": "Simple Hill Climbing / First-Improvement tren do thi.",
                "rule": "Xet neighbor ke; gap neighbor dau tien co h(neighbor) < h(current) thi buoc sang.",
                "currentH": round(current_h, 2),
                "goal": goal,
                "result": "INIT",
            },
        ))

    max_steps = len(scenario.nodes) * 3
    while current_node != goal and iterations < max_steps:
        iterations += 1
        moved = False
        neighbors = adjacency.get(current_node, [])

        for neighbor_id, edge in neighbors:
            travel = edge_time(edge)
            if travel >= BLOCKED_COST:
                continue
            if neighbor_id in visited_path:
                continue
            
            neighbor_h = heuristic_minutes(scenario, neighbor_id, goal)

            if debug:
                is_better = neighbor_h < current_h
                trace_steps.append(TraceStep(
                    stepIndex=len(trace_steps),
                    phase="first_better_check",
                    currentNode=current_node,
                    frontier=[neighbor_id],
                    visitedNodes=visited_path[:],
                    candidatePath=visited_path + [neighbor_id],
                    costSoFar=round(travel, 2),
                    heuristic=round(neighbor_h, 2),
                    decisionReason=f"Xet neighbor {neighbor_id}: h={neighbor_h:.2f}, current h={current_h:.2f}.",
                    debugData={
                        "traceType": "local_search",
                        "courseConcept": "So sanh h(neighbor) voi h(current). Neu nho hon thi buoc di.",
                        "currentNode": current_node,
                        "neighborNode": neighbor_id,
                        "currentH": round(current_h, 2),
                        "neighborH": round(neighbor_h, 2),
                        "edgeTime": round(travel, 2),
                        "comparison": "h(neighbor) < h(current)",
                        "result": "ACCEPT_FIRST_BETTER" if is_better else "REJECT",
                    },
                ))

            if neighbor_h < current_h:
                current_node = neighbor_id
                current_h = neighbor_h
                visited_path.append(current_node)
                moved = True
                break

        if not moved:
            if debug:
                trace_steps.append(TraceStep(
                    stepIndex=len(trace_steps),
                    phase="hill_stop",
                    currentNode=current_node,
                    frontier=[],
                    visitedNodes=visited_path[:],
                    candidatePath=visited_path[:],
                    costSoFar=round(current_h, 2),
                    heuristic=round(current_h, 2),
                    decisionReason=f"Khong co neighbor nao gan dich hon. Ket tai local optimum: {current_node}.",
                    debugData={
                        "traceType": "local_search",
                        "courseConcept": "Hill Climbing ket o cuc tri cuc bo vi khong co neighbor ke nao co h nho hon.",
                        "trap": "local_optimum",
                        "stuckAt": current_node,
                        "currentH": round(current_h, 2),
                        "result": "STOP",
                        "complete": True,
                    },
                ))
            break

    if debug and current_node == goal:
        trace_steps.append(TraceStep(
            stepIndex=len(trace_steps),
            phase="goal_found",
            currentNode=goal,
            frontier=[],
            visitedNodes=visited_path[:],
            candidatePath=visited_path[:],
            costSoFar=0,
            heuristic=0,
            decisionReason=f"Da den dich {goal} sau {iterations} buoc leo doi.",
            debugData={
                "traceType": "local_search",
                "courseConcept": "Hill Climbing da tim duoc duong di toi dich.",
                "path": visited_path,
                "iterations": iterations,
                "result": "GOAL_REACHED",
                "complete": True,
            },
        ))

    result = evaluate_delivery_order(scenario, orders, capacity_kg, False, start_id, goal_id)
    result["iterations"] = iterations
    result["hillClimbingPath"] = visited_path
    result["reachedGoal"] = current_node == goal
    result["path"] = visited_path
    result["visited"] = list(dict.fromkeys(visited_path))
    result["stops"] = visited_path
    result["traceSteps"] = trace_steps
    return result


def steepest_ascent_hill_climbing(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    current = _nearest_neighbor(scenario, orders, start_id)
    current_cost = _state_cost(scenario, current, capacity_kg, start_id, goal_id)
    trace_steps: list[TraceStep] = []
    iterations = 0
    while iterations < 80:
        iterations += 1
        current_value = -current_cost
        best_neighbor = current
        best_cost = current_cost
        best_value = current_value
        best_swap: list[int] | None = None
        neighbor_count = 0
        for i, j, candidate in _swap_neighbors(current):
            neighbor_count += 1
            candidate_cost = _state_cost(scenario, candidate, capacity_kg, start_id, goal_id)
            candidate_value = -candidate_cost
            if candidate_value > best_value:
                best_neighbor = candidate
                best_cost = candidate_cost
                best_value = candidate_value
                best_swap = [i, j]
        if debug:
            _trace_local_state(
                trace_steps,
                scenario,
                "steepest_scan",
                best_neighbor,
                best_cost,
                f"Da quet {neighbor_count} neighbor va chon neighbor co value lon nhat.",
                {
                    "courseConcept": "Steepest-Ascent Hill Climbing: xet tat ca neighbor, chon neighbor tot nhat.",
                    "currentState": _order_state(current),
                    "currentValue": round(current_value, 2),
                    "bestNeighborValue": round(best_value, 2),
                    "bestSwap": best_swap,
                    "neighborCount": neighbor_count,
                    "comparison": "bestNeighborValue > currentValue",
                    "result": "MOVE" if best_value > current_value else "STOP",
                },
                start_id,
                goal_id,
            )
        if best_value <= current_value:
            break
        current = best_neighbor
        current_cost = best_cost
    result = evaluate_delivery_order(scenario, current, capacity_kg, debug, start_id, goal_id)
    result["iterations"] = iterations
    result["traceSteps"] = trace_steps + result["traceSteps"]
    return result


def sideways_hill_climbing(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    sideways_limit: int = 12,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    current = _nearest_neighbor(scenario, orders, start_id)
    current_cost = _state_cost(scenario, current, capacity_kg, start_id, goal_id)
    trace_steps: list[TraceStep] = []
    seen = {_state_key(current)}
    sideways_moves = 0
    iterations = 0
    while iterations < 80:
        iterations += 1
        current_value = -current_cost
        candidates: list[tuple[float, float, int, int, list[Order]]] = []
        for i, j, candidate in _swap_neighbors(current):
            if _state_key(candidate) in seen:
                continue
            candidate_cost = _state_cost(scenario, candidate, capacity_kg, start_id, goal_id)
            candidate_value = -candidate_cost
            if candidate_value >= current_value:
                candidates.append((candidate_value, candidate_cost, i, j, candidate))
        if not candidates:
            if debug:
                _trace_local_state(
                    trace_steps,
                    scenario,
                    "sideways_stop",
                    current,
                    current_cost,
                    "Khong con neighbor nao thoa value(neighbor) >= value(current) ma chua di qua.",
                    {
                        "courseConcept": "Sideways Moves dung dieu kien >= de di ngang tren plateau.",
                        "sidewaysMoves": sideways_moves,
                        "sidewaysLimit": sideways_limit,
                        "result": "STOP",
                    },
                    start_id,
                    goal_id,
                )
            break
        candidates.sort(key=lambda item: item[0], reverse=True)
        candidate_value, candidate_cost, i, j, candidate = candidates[0]
        is_sideways = candidate_value == current_value
        if is_sideways and sideways_moves >= sideways_limit:
            if debug:
                _trace_local_state(
                    trace_steps,
                    scenario,
                    "sideways_limit",
                    current,
                    current_cost,
                    "Da dat gioi han sideways move nen dung de tranh lap vo han tren plateau.",
                    {
                        "courseConcept": "Sideways Moves can limit de tranh di vong lap.",
                        "sidewaysMoves": sideways_moves,
                        "sidewaysLimit": sideways_limit,
                        "result": "STOP",
                    },
                    start_id,
                    goal_id,
                )
            break
        sideways_moves = sideways_moves + 1 if is_sideways else 0
        if debug:
            _trace_local_state(
                trace_steps,
                scenario,
                "sideways_move",
                candidate,
                candidate_cost,
                f"Chap nhan swap {i}-{j} vi value(neighbor) >= value(current).",
                {
                    "courseConcept": "Hill Climbing with Sideways Moves.",
                    "currentState": _order_state(current),
                    "currentValue": round(current_value, 2),
                    "candidateValue": round(candidate_value, 2),
                    "swap": [i, j],
                    "comparison": ">=",
                    "isSideways": is_sideways,
                    "sidewaysMoves": sideways_moves,
                    "sidewaysLimit": sideways_limit,
                    "candidatePoolSize": len(candidates),
                    "result": "MOVE",
                },
                start_id,
                goal_id,
            )
        current = candidate
        current_cost = candidate_cost
        seen.add(_state_key(current))
    result = evaluate_delivery_order(scenario, current, capacity_kg, debug, start_id, goal_id)
    result["iterations"] = iterations
    result["traceSteps"] = trace_steps + result["traceSteps"]
    return result


def random_restart_hill_climbing(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    restarts: int = 8,
    sideways_limit: int = 10,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    rng = random.Random(41)
    if len(orders) < 2:
        result = evaluate_delivery_order(scenario, orders, capacity_kg, debug, start_id, goal_id)
        result["iterations"] = 0
        result["restarts"] = 0
        return result
    trace_steps: list[TraceStep] = []
    best_state: list[Order] = []
    best_cost = math.inf
    total_iterations = 0
    restart_count = max(1, restarts)
    for restart_index in range(restart_count):
        current = _nearest_neighbor(scenario, orders, start_id) if restart_index == 0 else rng.sample(orders, len(orders))
        current_cost = _state_cost(scenario, current, capacity_kg, start_id, goal_id)
        sideways_moves = 0
        seen = {_state_key(current)}
        if debug:
            _trace_local_state(
                trace_steps,
                scenario,
                "restart_init",
                current,
                current_cost,
                f"Restart {restart_index + 1}/{restart_count}: khoi tao state {'co dinh' if restart_index == 0 else 'ngau nhien'}.",
                {
                    "courseConcept": "Random-Restart Hill Climbing: thu nhieu diem bat dau de thoat cuc tri cuc bo.",
                    "restartIndex": restart_index + 1,
                    "restartCount": restart_count,
                    "randomized": restart_index > 0,
                    "result": "INIT_RESTART",
                },
                start_id,
                goal_id,
            )
        for _ in range(40):
            total_iterations += 1
            current_value = -current_cost
            pool: list[tuple[float, float, int, int, list[Order]]] = []
            for i, j, candidate in _swap_neighbors(current):
                if _state_key(candidate) in seen:
                    continue
                candidate_cost = _state_cost(scenario, candidate, capacity_kg, start_id, goal_id)
                candidate_value = -candidate_cost
                if candidate_value >= current_value:
                    pool.append((candidate_value, candidate_cost, i, j, candidate))
            if not pool:
                break
            better_pool = [item for item in pool if item[0] > current_value]
            choice_pool = better_pool or pool
            candidate_value, candidate_cost, i, j, candidate = rng.choice(choice_pool)
            is_sideways = candidate_value == current_value
            if is_sideways and sideways_moves >= sideways_limit:
                break
            sideways_moves = sideways_moves + 1 if is_sideways else 0
            if debug:
                _trace_local_state(
                    trace_steps,
                    scenario,
                    "restart_random_move",
                    candidate,
                    candidate_cost,
                    f"Chon ngau nhien trong tap neighbor thoa {'>' if better_pool else '>='}; swap {i}-{j}.",
                    {
                        "courseConcept": "Ket hop Sideways Moves voi random choice de moi restart co huong leo khac nhau.",
                        "restartIndex": restart_index + 1,
                        "currentState": _order_state(current),
                        "currentValue": round(current_value, 2),
                        "candidateValue": round(candidate_value, 2),
                        "candidatePoolSize": len(pool),
                        "betterPoolSize": len(better_pool),
                        "comparison": ">" if better_pool else ">=",
                        "isSideways": is_sideways,
                        "swap": [i, j],
                        "result": "MOVE",
                    },
                    start_id,
                    goal_id,
                )
            current = candidate
            current_cost = candidate_cost
            seen.add(_state_key(current))
        if current_cost < best_cost:
            best_state = current[:]
            best_cost = current_cost
    result = evaluate_delivery_order(scenario, best_state, capacity_kg, debug, start_id, goal_id)
    result["iterations"] = total_iterations
    result["restarts"] = restart_count
    result["traceSteps"] = trace_steps[:140] + result["traceSteps"]
    return result


def simulated_annealing(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    import math
    import random
    from app.algorithms.graph import build_adjacency, edge_time, heuristic_minutes, BLOCKED_COST

    rng = random.Random(7)
    adjacency = build_adjacency(scenario)
    start = start_id or scenario.depot_id
    goal = goal_id or start
    if not goal or goal == start:
        last_order = orders[-1] if orders else None
        goal = (last_order.dropoff_node_id or last_order.node_id) if last_order else start

    current_node = start
    current_h = heuristic_minutes(scenario, current_node, goal)
    visited_path: list[str] = [current_node]
    trace_steps: list[TraceStep] = []
    
    T = 100.0
    Tmin = 0.01
    alpha = 0.95
    iterations = 0

    def _frontier_ids(node: str) -> list[str]:
        return [nid for nid, edge in adjacency.get(node, []) if edge_time(edge) < BLOCKED_COST]

    if debug:
        trace_steps.append(TraceStep(
            stepIndex=0,
            phase="annealing_init",
            currentNode=current_node,
            frontier=[],
            visitedNodes=visited_path[:],
            candidatePath=visited_path[:],
            costSoFar=0,
            heuristic=round(current_h, 2),
            decisionReason=f"Bat dau tai {current_node}, h={current_h:.2f}. T0={T}, alpha={alpha}.",
            debugData={
                "traceType": "local_search",
                "courseConcept": "Simulated Annealing tren do thi.",
                "rule": "Chon random neighbor. Neu h nho hon thi di, neu h lon hon thi xac suat p = exp(-delta/T).",
                "currentH": round(current_h, 2),
                "goal": goal,
                "result": "INIT",
            },
        ))

    max_steps = 1000
    while T > Tmin and current_node != goal and iterations < max_steps:
        iterations += 1
        neighbors = _frontier_ids(current_node)
        if not neighbors:
            if debug:
                trace_steps.append(TraceStep(
                    stepIndex=len(trace_steps),
                    phase="annealing_stop",
                    currentNode=current_node,
                    frontier=[],
                    visitedNodes=visited_path[:],
                    candidatePath=visited_path[:],
                    costSoFar=round(current_h, 2),
                    heuristic=round(current_h, 2),
                    decisionReason=f"Kẹt ở {current_node} do khong co neighbor.",
                    debugData={
                        "traceType": "local_search",
                        "trap": "dead_end",
                        "stuckAt": current_node,
                        "result": "STOP",
                        "complete": True,
                    },
                ))
            break

        next_node = rng.choice(neighbors)
        # Find travel cost just for display if needed
        travel = 1.0
        for nid, edge in adjacency.get(current_node, []):
            if nid == next_node:
                travel = edge_time(edge)
                break
                
        next_h = heuristic_minutes(scenario, next_node, goal)
        delta = next_h - current_h
        
        probability = 1.0 if delta < 0 else math.exp(-delta / T)
        random_draw = 0.0 if delta < 0 else rng.random()
        accept = random_draw < probability

        if debug:
            trace_steps.append(TraceStep(
                stepIndex=len(trace_steps),
                phase="annealing_step",
                currentNode=current_node,
                frontier=[next_node],
                visitedNodes=visited_path[:],
                candidatePath=visited_path + [next_node],
                costSoFar=round(travel, 2),
                heuristic=round(next_h, 2),
                decisionReason=f"Thu random neighbor {next_node} (h={next_h:.2f}). delta={delta:.2f}. T={T:.2f}, p={probability:.3f}. {'Chap nhan' if accept else 'Tu choi'}.",
                debugData={
                    "traceType": "local_search",
                    "courseConcept": "Neu delta < 0, p=1. Nguoc lai p = exp(-delta/T).",
                    "currentNode": current_node,
                    "neighborNode": next_node,
                    "currentH": round(current_h, 2),
                    "neighborH": round(next_h, 2),
                    "deltaValue": round(delta, 2),
                    "temperature": round(T, 2),
                    "acceptanceProbability": round(probability, 4),
                    "randomDraw": round(random_draw, 4),
                    "accepted": accept,
                    "result": "ACCEPT" if accept else "REJECT",
                },
            ))

        if accept:
            current_node = next_node
            current_h = next_h
            visited_path.append(current_node)
            
        T *= alpha

    if debug and current_node == goal:
        trace_steps.append(TraceStep(
            stepIndex=len(trace_steps),
            phase="goal_found",
            currentNode=goal,
            frontier=[],
            visitedNodes=visited_path[:],
            candidatePath=visited_path[:],
            costSoFar=0,
            heuristic=0,
            decisionReason=f"Da den dich {goal} sau {iterations} buoc.",
            debugData={
                "traceType": "local_search",
                "courseConcept": "Simulated Annealing da toi dich.",
                "path": visited_path,
                "iterations": iterations,
                "result": "GOAL_REACHED",
                "complete": True,
            },
        ))

    result = evaluate_delivery_order(scenario, orders, capacity_kg, False, start_id, goal_id)
    result["iterations"] = iterations
    result["hillClimbingPath"] = visited_path
    result["reachedGoal"] = current_node == goal
    result["path"] = visited_path
    result["visited"] = list(dict.fromkeys(visited_path))
    result["stops"] = visited_path
    result["traceSteps"] = trace_steps
    return result


def local_beam_search(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    rng = random.Random(23)
    if len(orders) < 2:
        result = evaluate_delivery_order(scenario, orders, capacity_kg, debug, start_id, goal_id)
        result["iterations"] = 0
        return result
    base = _nearest_neighbor(scenario, orders, start_id)
    beam = [base]
    while len(beam) < min(4, math.factorial(len(orders))):
        candidate = rng.sample(base, len(base))
        if candidate not in beam:
            beam.append(candidate)
    trace_steps: list[TraceStep] = []
    iterations = 0
    for _ in range(35):
        iterations += 1
        candidates: list[list[Order]] = []
        for route in beam:
            candidates.append(route)
            for i in range(len(route)):
                for j in range(i + 1, len(route)):
                    neighbor = route[:]
                    neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
                    candidates.append(neighbor)
        scored = sorted(
            candidates,
            key=lambda route: _state_value(scenario, route, capacity_kg, start_id, goal_id),
            reverse=True,
        )
        next_beam: list[list[Order]] = []
        for route in scored:
            if route not in next_beam:
                next_beam.append(route)
            if len(next_beam) == 4:
                break
        beam = next_beam
        if debug:
            best_cost = _state_cost(scenario, beam[0], capacity_kg, start_id, goal_id)
            _trace_local_state(
                trace_steps,
                scenario,
                "beam_select_k_best",
                beam[0],
                best_cost,
                (
                    f"Local Beam sinh successor tu {len(beam)} state, roi giu k={len(beam)} "
                    f"state co value lon nhat."
                ),
                {
                    "courseConcept": "Local Beam Search: luu dong thoi k trang thai ung vien thay vi chi 1 current.",
                    "iteration": iterations,
                    "beamSize": len(beam),
                    "candidateCount": len(candidates),
                    "selectionRule": "chon k successor co value=-totalCost lon nhat trong toan bo tap sinh ra",
                    "beamStates": [_order_state(route) for route in beam],
                    "bestValue": round(-best_cost, 2),
                    "result": "KEEP_K_BEST",
                },
                start_id,
                goal_id,
            )
    result = evaluate_delivery_order(scenario, beam[0], capacity_kg, debug, start_id, goal_id)
    result["iterations"] = iterations
    result["traceSteps"] = trace_steps + result["traceSteps"]
    return result


def hill_climbing(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
    start_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    return simple_hill_climbing(scenario, orders, capacity_kg, debug, start_id, goal_id)


DELIVERY_ALGORITHMS = {
    "simple_hill_climbing": simple_hill_climbing,
    "hill_climbing": hill_climbing,
    "steepest_ascent": steepest_ascent_hill_climbing,
    "sideways_hill_climbing": sideways_hill_climbing,
    "random_restart": random_restart_hill_climbing,
    "local_beam": local_beam_search,
    "simulated_annealing": simulated_annealing,
}
