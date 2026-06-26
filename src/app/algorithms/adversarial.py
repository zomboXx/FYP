from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import math

from app.algorithms.graph import BLOCKED_COST, edge_key, find_edge, path_time
from app.algorithms.search import astar, bfs, greedy, ucs
from app.models.schemas import Scenario, TraceStep


def _candidate_routes(scenario: Scenario, start: str, goal: str) -> list[list[str]]:
    routes: list[list[str]] = []
    for search in (astar, ucs, greedy, bfs):
        path = search(scenario, start, goal).path
        if path and path not in routes:
            routes.append(path)
    base = astar(scenario, start, goal).path
    for source, target in zip(base, base[1:]):
        branch = deepcopy(scenario)
        edge = find_edge(branch, source, target)
        if edge:
            edge.blocked = True
        path = astar(branch, start, goal).path
        if path and path not in routes:
            routes.append(path)
        if len(routes) >= 5:
            break
    return routes[:5]


def _disruptions(routes: list[list[str]], budget: int) -> list[tuple[tuple[str, str], ...]]:
    edges: list[tuple[str, str]] = []
    for route in routes:
        for source, target in zip(route, route[1:]):
            key = edge_key(source, target)
            if key not in edges:
                edges.append(key)
    disruptions: list[tuple[tuple[str, str], ...]] = [tuple()]
    for size in range(1, min(budget, 2) + 1):
        disruptions.extend(combinations(edges[:8], size))
    # A bounded tree keeps Minimax explainable in the UI while still giving Alpha-Beta branches to prune.
    return disruptions[:12]


def _evaluate_leaf(
    scenario: Scenario,
    route: list[str],
    disruption: tuple[tuple[str, str], ...],
    start: str,
    goal: str,
) -> tuple[float, list[str]]:
    branch = deepcopy(scenario)
    for key in disruption:
        edge = find_edge(branch, *key)
        if edge:
            edge.blocked = True
            edge.traffic = "heavy"
    selected_cost = path_time(branch, route)
    if selected_cost < BLOCKED_COST:
        return selected_cost, route
    recovery = astar(branch, start, goal)
    if not recovery.path:
        return BLOCKED_COST, []
    # Re-planning is not free in the worst-case model; this keeps robust initial routes meaningful.
    switch_penalty = 3.0 + len(disruption)
    return recovery.total_minutes + switch_penalty, recovery.path


def adversarial_search(
    scenario: Scenario,
    algorithm: str,
    start: str | None = None,
    goal: str | None = None,
    disruption_budget: int = 1,
    debug: bool = False,
) -> dict:
    start_id = start or scenario.depot_id
    goal_id = goal or next(
        (order.dropoff_node_id or order.node_id for order in scenario.orders),
        scenario.nodes[-1].id,
    )
    routes = _candidate_routes(scenario, start_id, goal_id)
    disruptions = _disruptions(routes, disruption_budget)
    traces: list[TraceStep] = []
    branches: list[dict] = []
    expanded_nodes = 1
    pruned_branches = 0
    alpha = float("-inf")
    best_utility = float("-inf")
    best_route: list[str] = []
    best_worst_path: list[str] = []

    def trace_event(
        phase: str,
        role: str,
        current: str,
        route: list[str],
        utility: float,
        reason: str,
        frontier: list[str] | None = None,
        extra: dict | None = None,
    ) -> None:
        if not debug:
            return
        safe_utility = utility if math.isfinite(utility) else 0.0
        safe_alpha = alpha if math.isfinite(alpha) else None
        raw_beta = extra.get("beta") if extra else None
        safe_beta = raw_beta if isinstance(raw_beta, (int, float)) and math.isfinite(raw_beta) else None
        safe_extra = {
            key: (value if not isinstance(value, float) or math.isfinite(value) else None)
            for key, value in (extra or {}).items()
        }
        traces.append(
            TraceStep(
                stepIndex=len(traces),
                phase=phase,
                currentNode=current,
                frontier=frontier or [],
                visitedNodes=list(dict.fromkeys(route)),
                candidatePath=route,
                costSoFar=round(safe_utility, 2),
                heuristic=0,
                decisionReason=reason,
                debugData={
                    "traceType": "adversarial_search",
                    "courseConcept": "Minimax/Alpha-Beta dung cay game voi MAX, MIN, utility va backup value.",
                    "event": phase,
                    "role": role,
                    "alpha": safe_alpha,
                    "beta": safe_beta,
                    **safe_extra,
                },
            )
        )

    for route_index, route in enumerate(routes):
        expanded_nodes += 1
        min_utility = float("inf")
        worst_path = route
        event_rows: list[dict] = []
        beta = float("inf")
        trace_event(
            "ENTER",
            "MAX",
            start_id,
            route,
            best_utility,
            f"ENTER MAX: xet nuoc di/candidate route {route_index + 1}.",
            [" -> ".join(candidate) for candidate in routes],
            {"routeIndex": route_index, "nodeType": "MAX", "result": "ENTER_MAX"},
        )

        for disruption_index, disruption in enumerate(disruptions):
            expanded_nodes += 1
            event_name = "no_disruption" if not disruption else ", ".join("-".join(key) for key in disruption)
            trace_event(
                "DESCEND",
                "MAX_TO_MIN",
                start_id,
                route,
                min_utility if min_utility < float("inf") else 0,
                f"DESCEND: tu MAX di xuong successor MIN ung voi disruption {event_name}.",
                ["-".join(key) for key in disruption],
                {
                    "routeIndex": route_index,
                    "disruptionIndex": disruption_index,
                    "disruption": event_name,
                    "nodeType": "EDGE_TO_MIN",
                    "beta": beta,
                    "result": "DESCEND",
                },
            )
            cost, recovery_path = _evaluate_leaf(scenario, route, disruption, start_id, goal_id)
            utility = -cost
            min_utility = min(min_utility, utility)
            if utility == min_utility:
                worst_path = recovery_path
            beta = min(beta, min_utility)
            event_rows.append({"event": event_name, "cost": round(cost, 2), "utility": round(utility, 2), "recoveryPath": recovery_path})
            trace_event(
                "LEAF",
                "MIN",
                goal_id,
                recovery_path,
                utility,
                f"LEAF: ap dung disruption {event_name}, tinh utility cua MAX = -cost = {utility:.2f}.",
                ["-".join(key) for key in disruption],
                {
                    "routeIndex": route_index,
                    "disruptionIndex": disruption_index,
                    "disruption": event_name,
                    "cost": round(cost, 2),
                    "utility": round(utility, 2),
                    "nodeType": "LEAF",
                    "beta": beta,
                    "result": "UTILITY",
                },
            )
            trace_event(
                "UPDATE",
                "MIN",
                goal_id,
                worst_path,
                min_utility,
                f"UPDATE MIN: beta=min(beta, utility), worst utility hien tai cua route = {min_utility:.2f}.",
                ["-".join(key) for key in disruption],
                {
                    "routeIndex": route_index,
                    "disruptionIndex": disruption_index,
                    "disruption": event_name,
                    "utility": round(utility, 2),
                    "minUtility": round(min_utility, 2),
                    "nodeType": "MIN",
                    "beta": beta,
                    "result": "UPDATE_MIN",
                },
            )
            if algorithm == "alpha_beta" and beta <= alpha:
                pruned_branches += len(disruptions) - disruption_index - 1
                trace_event(
                    "PRUNE",
                    "ALPHA_BETA",
                    goal_id,
                    route,
                    min_utility,
                    f"PRUNE: cat {len(disruptions) - disruption_index - 1} nhanh vi beta <= alpha.",
                    [],
                    {
                        "routeIndex": route_index,
                        "disruptionIndex": disruption_index,
                        "nodeType": "PRUNE",
                        "alpha": alpha,
                        "beta": beta,
                        "condition": "beta <= alpha",
                        "pruned": len(disruptions) - disruption_index - 1,
                        "result": "PRUNE",
                    },
                )
                break

        branches.append({"route": route, "worstUtility": round(min_utility, 2), "events": event_rows})
        trace_event(
            "RETURN",
            "MIN_TO_MAX",
            start_id,
            worst_path,
            min_utility,
            f"RETURN: MIN tra worst utility {min_utility:.2f} cua route {route_index + 1} ve MAX.",
            [],
            {"routeIndex": route_index, "nodeType": "RETURN_TO_MAX", "beta": beta, "result": "RETURN_MIN_VALUE"},
        )
        if min_utility > best_utility:
            best_utility = min_utility
            best_route = route
            best_worst_path = worst_path
            trace_event(
                "UPDATE",
                "MAX",
                start_id,
                best_route,
                best_utility,
                f"UPDATE MAX: alpha=max(alpha, value), route {route_index + 1} tam thoi tot nhat.",
                [],
                {
                    "routeIndex": route_index,
                    "nodeType": "MAX",
                    "bestUtility": round(best_utility, 2),
                    "beta": beta,
                    "result": "UPDATE_MAX",
                },
            )
        alpha = max(alpha, best_utility)

    return {
        "path": best_route,
        "visited": list(dict.fromkeys(node for route in routes for node in route)),
        "algorithm": algorithm,
        "start": start_id,
        "goal": goal_id,
        "gameValue": round(best_utility, 2),
        "worstCaseCost": round(-best_utility, 2),
        "worstCaseRecoveryPath": best_worst_path,
        "branches": branches,
        "expandedNodes": expanded_nodes,
        "prunedBranches": pruned_branches,
        "disruptionBudget": disruption_budget,
        "traceSteps": traces,
    }
