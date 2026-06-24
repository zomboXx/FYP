from __future__ import annotations

from copy import deepcopy
from itertools import combinations

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

    for route_index, route in enumerate(routes):
        expanded_nodes += 1
        min_utility = float("inf")
        worst_path = route
        event_rows: list[dict] = []
        beta = float("inf")
        if debug:
            traces.append(
                TraceStep(
                    stepIndex=len(traces),
                    phase="max_choose_route",
                    currentNode=start_id,
                    frontier=[" -> ".join(candidate) for candidate in routes],
                    visitedNodes=[],
                    candidatePath=route,
                    costSoFar=0,
                    heuristic=0,
                    decisionReason=f"MAX danh gia candidate route {route_index + 1}.",
                    debugData={"role": "MAX", "alpha": alpha, "beta": None, "routeIndex": route_index},
                )
            )

        for disruption_index, disruption in enumerate(disruptions):
            expanded_nodes += 1
            cost, recovery_path = _evaluate_leaf(scenario, route, disruption, start_id, goal_id)
            utility = -cost
            min_utility = min(min_utility, utility)
            if utility == min_utility:
                worst_path = recovery_path
            beta = min(beta, min_utility)
            event_name = "no_disruption" if not disruption else ", ".join("-".join(key) for key in disruption)
            event_rows.append({"event": event_name, "cost": round(cost, 2), "utility": round(utility, 2), "recoveryPath": recovery_path})
            if debug:
                traces.append(
                    TraceStep(
                        stepIndex=len(traces),
                        phase="min_apply_disruption",
                        currentNode=goal_id,
                        frontier=["-".join(key) for key in disruption],
                        visitedNodes=list(dict.fromkeys(recovery_path)),
                        candidatePath=recovery_path,
                        costSoFar=round(cost, 2),
                        heuristic=0,
                        decisionReason=f"MIN thu disruption {event_name}; utility cua MAX={utility:.2f}.",
                        debugData={"role": "MIN", "alpha": alpha, "beta": beta, "disruption": event_name},
                    )
                )
            if algorithm == "alpha_beta" and beta <= alpha:
                pruned_branches += len(disruptions) - disruption_index - 1
                if debug:
                    traces.append(
                        TraceStep(
                            stepIndex=len(traces),
                            phase="alpha_beta_prune",
                            currentNode=goal_id,
                            frontier=[],
                            visitedNodes=[],
                            candidatePath=route,
                            costSoFar=round(-beta, 2),
                            heuristic=0,
                            decisionReason=f"Cat {len(disruptions) - disruption_index - 1} nhanh vi beta <= alpha.",
                            debugData={"role": "PRUNE", "alpha": alpha, "beta": beta, "pruned": len(disruptions) - disruption_index - 1},
                        )
                    )
                break

        branches.append({"route": route, "worstUtility": round(min_utility, 2), "events": event_rows})
        if min_utility > best_utility:
            best_utility = min_utility
            best_route = route
            best_worst_path = worst_path
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
