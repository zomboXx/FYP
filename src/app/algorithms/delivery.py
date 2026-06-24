from __future__ import annotations

import math
import random
from itertools import permutations

from app.algorithms.search import astar
from app.models.schemas import DeliveryState, Order, Scenario, TraceStep

CATEGORY_PRIORITY_BONUS = {"ride": 18, "food": 12, "parcel": 5, "grocery": 3}
URGENCY_PENALTY = {"urgent": 2.0, "normal": 1.0, "low": 0.6}


def selected_orders(scenario: Scenario, order_ids: list[str] | None) -> list[Order]:
    wanted = set(order_ids) if order_ids is not None else {order.id for order in scenario.orders}
    return [order for order in scenario.orders if order.id in wanted]


def route_stops_for_orders(scenario: Scenario, orders: list[Order]) -> list[str]:
    stops = [scenario.depot_id]
    for order in orders:
        pickup = order.pickup_node_id or scenario.depot_id
        dropoff = order.dropoff_node_id or order.node_id
        if pickup != stops[-1]:
            stops.append(pickup)
        if dropoff != stops[-1]:
            stops.append(dropoff)
    if stops[-1] != scenario.depot_id:
        stops.append(scenario.depot_id)
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
            heuristic=0,
            decisionReason=reason,
            debugData=debug_data or {},
        )
    )


def evaluate_delivery_order(
    scenario: Scenario,
    orders: list[Order],
    capacity_kg: float | None = None,
    debug: bool = False,
) -> dict:
    stops = route_stops_for_orders(scenario, orders)
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
    current_position = scenario.depot_id
    carrying: list[str] = []
    pending = [order.id for order in orders]
    delivered: list[str] = []
    state_history = [
        state_snapshot(scenario, current_position, current_time, carrying, pending, delivered).model_dump()
    ]
    for order in orders:
        pickup = order.pickup_node_id or scenario.depot_id
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

    return_path, _, return_minutes, _ = expand_route_with_astar(scenario, [current_position, scenario.depot_id])
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


def _nearest_neighbor(scenario: Scenario, orders: list[Order]) -> list[Order]:
    remaining = orders[:]
    current = scenario.depot_id
    planned: list[Order] = []
    while remaining:
        next_order = min(
            remaining,
            key=lambda order: (
                astar(scenario, current, order.pickup_node_id or scenario.depot_id).total_minutes
                + astar(scenario, order.pickup_node_id or scenario.depot_id, order.dropoff_node_id or order.node_id).total_minutes
            ),
        )
        planned.append(next_order)
        remaining.remove(next_order)
        current = next_order.dropoff_node_id or next_order.node_id
    return planned


def hill_climbing(scenario: Scenario, orders: list[Order], capacity_kg: float | None = None, debug: bool = False) -> dict:
    current = _nearest_neighbor(scenario, orders)
    current_score = evaluate_delivery_order(scenario, current, capacity_kg)["totalCost"]
    trace_steps: list[TraceStep] = []
    improved = True
    iterations = 0
    while improved and iterations < 60:
        improved = False
        iterations += 1
        for i in range(len(current)):
            for j in range(i + 1, len(current)):
                candidate = current[:]
                candidate[i], candidate[j] = candidate[j], candidate[i]
                score = evaluate_delivery_order(scenario, candidate, capacity_kg)["totalCost"]
                if debug:
                    _append_trace(
                        trace_steps,
                        "neighbor_swap",
                        candidate[0].node_id if candidate else scenario.depot_id,
                        route_stops_for_orders(scenario, candidate),
                        score,
                        f"Thu doi vi tri {i}-{j}: cost {score:.2f} so voi best {current_score:.2f}.",
                        {"candidateCost": round(score, 2), "bestCost": round(current_score, 2), "swap": [i, j]},
                    )
                if score < current_score:
                    current, current_score = candidate, score
                    improved = True
                    if debug:
                        _append_trace(trace_steps, "accept", current[0].node_id, route_stops_for_orders(scenario, current), current_score, "Chap nhan vi cost giam.")
    result = evaluate_delivery_order(scenario, current, capacity_kg, debug)
    result["iterations"] = iterations
    result["traceSteps"] = trace_steps + result["traceSteps"]
    return result


def simulated_annealing(scenario: Scenario, orders: list[Order], capacity_kg: float | None = None, debug: bool = False) -> dict:
    rng = random.Random(7)
    current = _nearest_neighbor(scenario, orders)
    if len(current) < 2:
        result = evaluate_delivery_order(scenario, current, capacity_kg, debug)
        result["iterations"] = 0
        return result
    best = current[:]
    current_score = evaluate_delivery_order(scenario, current, capacity_kg)["totalCost"]
    best_score = current_score
    temperature = 30.0
    iterations = 0
    trace_steps: list[TraceStep] = []
    while temperature > 0.2 and iterations < 250:
        iterations += 1
        candidate = current[:]
        i, j = rng.sample(range(len(candidate)), 2)
        candidate[i], candidate[j] = candidate[j], candidate[i]
        score = evaluate_delivery_order(scenario, candidate, capacity_kg)["totalCost"]
        delta = score - current_score
        accept = delta < 0 or rng.random() < math.exp(-delta / temperature)
        if debug:
            _append_trace(
                trace_steps,
                "anneal_candidate",
                candidate[0].node_id,
                route_stops_for_orders(scenario, candidate),
                score,
                f"Delta {delta:.2f}, nhiet do {temperature:.2f}, {'chap nhan' if accept else 'tu choi'}.",
                {"delta": round(delta, 2), "temperature": round(temperature, 2), "accepted": accept, "bestCost": round(best_score, 2)},
            )
        if accept:
            current, current_score = candidate, score
        if current_score < best_score:
            best, best_score = current[:], current_score
        temperature *= 0.95
    result = evaluate_delivery_order(scenario, best, capacity_kg, debug)
    result["iterations"] = iterations
    result["traceSteps"] = trace_steps[:80] + result["traceSteps"]
    return result


def local_beam_search(scenario: Scenario, orders: list[Order], capacity_kg: float | None = None, debug: bool = False) -> dict:
    rng = random.Random(23)
    if len(orders) < 2:
        result = evaluate_delivery_order(scenario, orders, capacity_kg, debug)
        result["iterations"] = 0
        return result
    base = _nearest_neighbor(scenario, orders)
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
        scored = sorted(candidates, key=lambda route: evaluate_delivery_order(scenario, route, capacity_kg)["totalCost"])
        next_beam: list[list[Order]] = []
        for route in scored:
            if route not in next_beam:
                next_beam.append(route)
            if len(next_beam) == 4:
                break
        beam = next_beam
        if debug:
            best_score = evaluate_delivery_order(scenario, beam[0], capacity_kg)["totalCost"]
            _append_trace(
                trace_steps,
                "beam_select",
                beam[0][0].pickup_node_id or scenario.depot_id,
                route_stops_for_orders(scenario, beam[0]),
                best_score,
                f"Local Beam giu {len(beam)} ung vien tot nhat o vong {iterations}, best cost {best_score:.2f}.",
                {"iteration": iterations, "beamSize": len(beam), "candidateCount": len(candidates), "bestCost": round(best_score, 2)},
            )
    result = evaluate_delivery_order(scenario, beam[0], capacity_kg, debug)
    result["iterations"] = iterations
    result["traceSteps"] = trace_steps + result["traceSteps"]
    return result


def genetic_algorithm(scenario: Scenario, orders: list[Order], capacity_kg: float | None = None, debug: bool = False) -> dict:
    rng = random.Random(11)
    if len(orders) < 2:
        result = evaluate_delivery_order(scenario, orders, capacity_kg, debug)
        result["iterations"] = 0
        return result
    population = [list(p) for p in permutations(orders)] if len(orders) <= 5 else []
    if not population:
        base = _nearest_neighbor(scenario, orders)
        population = [rng.sample(base, len(base)) for _ in range(24)]
    population = population[:24]
    generations = 35
    trace_steps: list[TraceStep] = []
    for generation in range(generations):
        scored = sorted(population, key=lambda route: evaluate_delivery_order(scenario, route, capacity_kg)["totalCost"])
        survivors = scored[:8]
        if debug:
            best_score = evaluate_delivery_order(scenario, survivors[0], capacity_kg)["totalCost"]
            _append_trace(
                trace_steps,
                "generation",
                survivors[0][0].node_id,
                route_stops_for_orders(scenario, survivors[0]),
                best_score,
                f"Chon 8 ca the tot nhat cua the he {generation + 1}.",
                {"generation": generation + 1, "populationSize": len(population), "survivorCount": len(survivors), "bestCost": round(best_score, 2)},
            )
        children = survivors[:]
        while len(children) < 24:
            p1, p2 = rng.sample(survivors, 2)
            cut = rng.randint(1, len(orders) - 1)
            child = p1[:cut] + [order for order in p2 if order not in p1[:cut]]
            if rng.random() < 0.35:
                i, j = rng.sample(range(len(child)), 2)
                child[i], child[j] = child[j], child[i]
            children.append(child)
        population = children
    best = min(population, key=lambda route: evaluate_delivery_order(scenario, route, capacity_kg)["totalCost"])
    result = evaluate_delivery_order(scenario, best, capacity_kg, debug)
    result["iterations"] = generations
    result["traceSteps"] = trace_steps + result["traceSteps"]
    return result


DELIVERY_ALGORITHMS = {
    "hill_climbing": hill_climbing,
    "simulated_annealing": simulated_annealing,
    "local_beam": local_beam_search,
    "genetic": genetic_algorithm,
}
