from __future__ import annotations

from collections import deque
from copy import deepcopy

from app.algorithms.events import simulate_event
from app.algorithms.graph import BLOCKED_COST, build_adjacency, edge_key, find_edge, path_time
from app.algorithms.search import astar
from app.models.schemas import Scenario, TraceStep


def _hidden_event_scenario(scenario: Scenario, event_type: str, start: str, goal: str) -> tuple[Scenario, str]:
    if event_type == "accident":
        initial = astar(scenario, start, goal).path
        # The hidden accident should force a visible re-plan, but the demo still needs a solvable map.
        edge_indices = sorted(range(max(0, len(initial) - 1)), key=lambda index: abs(index - (len(initial) - 2) / 2))
        for index in edge_indices:
            affected_edge = (initial[index], initial[index + 1])
            candidate, message = simulate_event(scenario, event_type, affected_edge)
            if astar(candidate, start, goal).path:
                return candidate, message
    return simulate_event(scenario, event_type, None)


def _changed_edges(before: Scenario, after: Scenario) -> set[tuple[str, str]]:
    changed: set[tuple[str, str]] = set()
    for edge in before.edges:
        updated = find_edge(after, edge.source, edge.target)
        if updated and (edge.blocked != updated.blocked or edge.traffic != updated.traffic):
            changed.add(edge_key(edge.source, edge.target))
    return changed


def _nodes_within_radius(scenario: Scenario, start: str, radius: int) -> set[str]:
    adjacency = build_adjacency(scenario)
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= radius:
            continue
        for neighbor, _ in adjacency.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, depth + 1))
    return seen


def _reveal_nearby_edges(
    believed: Scenario,
    actual: Scenario,
    current: str,
    radius: int,
    hidden: set[tuple[str, str]],
) -> list[str]:
    visible_nodes = _nodes_within_radius(actual, current, radius)
    revealed: list[str] = []
    for key in sorted(hidden):
        if not set(key).intersection(visible_nodes):
            continue
        actual_edge = find_edge(actual, *key)
        believed_edge = find_edge(believed, *key)
        if actual_edge and believed_edge:
            believed_edge.blocked = actual_edge.blocked
            believed_edge.traffic = actual_edge.traffic
            revealed.append("-".join(key))
    return revealed


def _candidate_paths(base: Scenario, actual: Scenario, start: str, goal: str) -> list[list[str]]:
    candidates: list[list[str]] = []
    for world in (base, actual):
        path = astar(world, start, goal).path
        if path and path not in candidates:
            candidates.append(path)
    return candidates


def _belief_plan(
    scenario: Scenario,
    actual: Scenario,
    start: str,
    goal: str,
    algorithm: str,
    debug: bool,
) -> dict:
    candidates = _candidate_paths(scenario, actual, start, goal)
    traces: list[TraceStep] = []
    scored: list[dict] = []
    for path in candidates:
        clear_cost = path_time(scenario, path)
        event_cost = path_time(actual, path)
        value = 0.65 * clear_cost + 0.35 * event_cost if algorithm == "expectimax" else max(clear_cost, event_cost)
        row = {
            "path": path,
            "clearCost": round(clear_cost, 2),
            "eventCost": round(event_cost, 2),
            "value": round(value, 2),
        }
        scored.append(row)
        if debug:
            traces.append(
                TraceStep(
                    stepIndex=len(traces),
                    phase="evaluate_belief_candidate",
                    currentNode=start,
                    frontier=[candidate[-1] for candidate in candidates],
                    visitedNodes=list(dict.fromkeys(path)),
                    candidatePath=path,
                    costSoFar=round(value, 2),
                    heuristic=round(event_cost - clear_cost, 2),
                    decisionReason=(
                        f"Danh gia route trong hai world clear/event; "
                        f"{'expected' if algorithm == 'expectimax' else 'worst-case'} cost={value:.2f}."
                    ),
                    debugData={"possibleWorlds": ["clear", "hidden_event"], **row},
                )
            )
    best = min(scored, key=lambda item: item["value"], default={"path": [], "value": BLOCKED_COST})
    return {
        "path": best["path"],
        "visited": list(dict.fromkeys(node for item in scored for node in item["path"])),
        "traceSteps": traces,
        "candidateWorlds": scored,
        "beliefMode": "expected_cost" if algorithm == "expectimax" else "worst_case",
        "replans": 0,
        "observedEdges": [],
    }


def _online_replan(
    scenario: Scenario,
    actual: Scenario,
    start: str,
    goal: str,
    sensor_radius: int,
    hidden: set[tuple[str, str]],
    debug: bool,
) -> dict:
    believed = deepcopy(scenario)
    initial = astar(believed, start, goal, debug=False)
    current = start
    travelled = [start]
    visited: list[str] = []
    observed_edges: list[str] = []
    traces: list[TraceStep] = []
    replans = 0
    remaining_hidden = set(hidden)

    if debug:
        traces.append(
            TraceStep(
                stepIndex=0,
                phase="belief_init",
                currentNode=current,
                frontier=[],
                visitedNodes=[],
                candidatePath=initial.path,
                costSoFar=0,
                heuristic=float(len(remaining_hidden)),
                decisionReason="Khoi tao belief state: cac thay doi ngoai sensor range chua duoc quan sat.",
                debugData={"hiddenEdges": sorted("-".join(key) for key in remaining_hidden), "sensorRadius": sensor_radius},
            )
        )

    safety_limit = max(8, len(scenario.nodes) * 3)
    for _ in range(safety_limit):
        revealed = _reveal_nearby_edges(believed, actual, current, sensor_radius, remaining_hidden)
        if revealed:
            observed_edges.extend(revealed)
            remaining_hidden = {key for key in remaining_hidden if "-".join(key) not in revealed}
        plan = astar(believed, current, goal, debug=False)
        visited.extend(plan.visited_nodes)
        replans += 1
        if debug:
            traces.append(
                TraceStep(
                    stepIndex=len(traces),
                    phase="observe_and_replan",
                    currentNode=current,
                    frontier=plan.visited_nodes,
                    visitedNodes=list(dict.fromkeys(visited)),
                    candidatePath=plan.path,
                    costSoFar=plan.total_minutes,
                    heuristic=float(len(remaining_hidden)),
                    decisionReason=(
                        f"Sensor thay {len(revealed)} thay doi; cap nhat belief va lap route tu {current}."
                        if revealed
                        else f"Khong co observation moi; tiep tuc policy tu {current}."
                    ),
                    debugData={
                        "observation": revealed,
                        "observedEdges": observed_edges[:],
                        "remainingHiddenEdges": sorted("-".join(key) for key in remaining_hidden),
                        "beliefPath": plan.path,
                    },
                )
            )
        if current == goal:
            break
        if len(plan.path) < 2:
            break
        next_node = plan.path[1]
        actual_edge = find_edge(actual, current, next_node)
        if not actual_edge or actual_edge.blocked:
            key = edge_key(current, next_node)
            believed_edge = find_edge(believed, *key)
            if believed_edge and actual_edge:
                believed_edge.blocked = actual_edge.blocked
                believed_edge.traffic = actual_edge.traffic
                remaining_hidden.discard(key)
            continue
        current = next_node
        travelled.append(current)
        if current == goal:
            break

    final_plan = astar(believed, current, goal, debug=False)
    completed_path = travelled + (final_plan.path[1:] if final_plan.path and final_plan.path[0] == current else [])
    return {
        "path": completed_path if completed_path[-1:] == [goal] else travelled,
        "visited": list(dict.fromkeys(visited)),
        "traceSteps": traces,
        "initialPath": initial.path,
        "finalPath": completed_path,
        "beliefMode": "observe_update_replan",
        "replans": replans,
        "observedEdges": observed_edges,
        "remainingHiddenEdges": sorted("-".join(key) for key in remaining_hidden),
        "updatedScenario": believed.model_dump(),
    }


def complex_search(
    scenario: Scenario,
    algorithm: str,
    start: str,
    goal: str,
    sensor_radius: int,
    hidden_event: str,
    debug: bool = False,
) -> dict:
    actual, event_message = _hidden_event_scenario(scenario, hidden_event, start, goal)
    hidden = _changed_edges(scenario, actual)
    if algorithm in {"belief_state", "expectimax"}:
        result = _belief_plan(scenario, actual, start, goal, algorithm, debug)
    else:
        result = _online_replan(scenario, actual, start, goal, sensor_radius, hidden, debug)
    result.update(
        {
            "algorithm": algorithm,
            "hiddenEvent": hidden_event,
            "eventMessage": event_message,
            "hiddenEdges": sorted("-".join(key) for key in hidden),
            "sensorRadius": sensor_radius,
            "actualScenario": actual.model_dump(),
        }
    )
    return result
