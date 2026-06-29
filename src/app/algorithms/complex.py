from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Literal

from app.algorithms.events import simulate_event
from app.algorithms.graph import BLOCKED_COST, build_adjacency, edge_key, find_edge, path_time, heuristic_minutes, edge_time
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


def _select_uncertain_edge(path: list[str], hidden: set[tuple[str, str]]) -> tuple[str, str] | None:
    for source, target in zip(path, path[1:]):
        key = edge_key(source, target)
        if key in hidden:
            return key
    return sorted(hidden)[0] if hidden else None


def _scenario_with_actual_edges(base: Scenario, actual: Scenario, edges: set[tuple[str, str]]) -> Scenario:
    branch = deepcopy(base)
    for key in edges:
        actual_edge = find_edge(actual, *key)
        branch_edge = find_edge(branch, *key)
        if actual_edge and branch_edge:
            branch_edge.blocked = actual_edge.blocked
            branch_edge.traffic = actual_edge.traffic
    return branch


def _and_or_plan(
    scenario: Scenario,
    actual: Scenario,
    start: str,
    goal: str,
    hidden: set[tuple[str, str]],
    debug: bool,
) -> dict:
    traces: list[TraceStep] = []
    
    def add_trace(
        phase: str,
        current: str,
        frontier: list[str],
        candidate: list[str],
        cost: float,
        reason: str,
        data: dict,
    ) -> None:
        if not debug:
            return
        traces.append(
            TraceStep(
                stepIndex=len(traces),
                phase=phase,
                currentNode=current,
                frontier=frontier,
                visitedNodes=list(dict.fromkeys(candidate)),
                candidatePath=candidate,
                costSoFar=round(cost, 2),
                heuristic=float(len(frontier)),
                decisionReason=reason,
                debugData={
                    "traceType": "and_or_search",
                    **data,
                },
            )
        )

    MAX_DEPTH = 30
    
    adjacency = build_adjacency(scenario)
    
    def or_search(state: tuple[str, frozenset[tuple[str, str]]], path: list[tuple[str, frozenset[tuple[str, str]]]]) -> list | Literal["failure"]:
        node, blocked = state
        
        if node == goal:
            add_trace(
                "OR_GOAL", node, [], [s[0] for s in path] + [node], 0,
                f"Dat muc tieu tai {node}", {"nodeType": "OR", "result": "GOAL"}
            )
            return []
            
        if state in path:
            add_trace(
                "OR_CYCLE", node, [], [s[0] for s in path] + [node], 0,
                f"Phat hien chu trinh tai {node}", {"nodeType": "OR", "result": "FAILURE_CYCLE"}
            )
            return "failure"
            
        if len(path) > MAX_DEPTH:
            return "failure"
            
        neighbors = []
        for v, edge in adjacency.get(node, []):
            if edge_time(edge) >= BLOCKED_COST: continue
            if (node, v) in blocked or (v, node) in blocked: continue
            neighbors.append(v)
            
        neighbors.sort(key=lambda v: heuristic_minutes(scenario, v, goal))
        
        add_trace(
            "OR_VISIT", node, neighbors, [s[0] for s in path] + [node], 0,
            f"OR Node: Dang o {node}, co {len(neighbors)} hanh dong kha di.",
            {"nodeType": "OR", "possibleActions": neighbors, "result": "EVALUATING"}
        )
        
        for action in neighbors:
            is_hidden = (node, action) in hidden or (action, node) in hidden
            if is_hidden:
                s1 = (action, blocked)
                new_blocked = frozenset(blocked | {(node, action), (action, node)})
                s2 = (node, new_blocked)
                result_states = [s1, s2]
                
                add_trace(
                    "AND_SPLIT", node, [action, node], [s[0] for s in path] + [node], 0,
                    f"AND Node: Canh toi {action} co the bi ket. Can ke hoach cho ca 2 ket qua.",
                    {"nodeType": "AND", "uncertainEdge": f"{node}-{action}", "outcomes": ["open", "blocked"]}
                )
            else:
                result_states = [(action, blocked)]
                
            plan = and_search(result_states, path + [state])
            if plan != "failure":
                add_trace(
                    "OR_SUCCESS", node, [action], [s[0] for s in path] + [node], 0,
                    f"Action di toi {action} thanh cong.",
                    {"nodeType": "OR", "action": action, "result": "SUCCESS"}
                )
                return [action, plan]
                
        add_trace(
            "OR_FAIL", node, [], [s[0] for s in path] + [node], 0,
            f"Khong hanh dong nao tu {node} thanh cong.",
            {"nodeType": "OR", "result": "FAILURE_ALL_ACTIONS"}
        )
        return "failure"
        
    def and_search(states: list[tuple[str, frozenset[tuple[str, str]]]], path: list[tuple[str, frozenset[tuple[str, str]]]]) -> dict | Literal["failure"]:
        plans = {}
        for s in states:
            node, blocked = s
            outcome_name = "open" if len(blocked) == len(path[-1][1]) else "blocked"
            add_trace(
                "AND_EVAL_OUTCOME", node, [], [p[0] for p in path] + [node], 0,
                f"Danh gia kich ban {outcome_name} tai {node}.",
                {"nodeType": "AND", "outcome": outcome_name, "evaluatingState": node}
            )
            plan_s = or_search(s, path)
            if plan_s == "failure":
                add_trace(
                    "AND_FAIL", node, [], [p[0] for p in path] + [node], 0,
                    f"Kich ban {outcome_name} that bai. Huy bo hanh dong nay.",
                    {"nodeType": "AND", "failedOutcome": outcome_name, "result": "FAILURE"}
                )
                return "failure"
            plans[s] = plan_s
        return plans

    initial_state = (start, frozenset())
    result_tree = or_search(initial_state, [])
    
    open_path = []
    disrupted_path = []
    uncertain_edge = None
    complete = False
    
    if result_tree != "failure":
        complete = True
        
        def extract_paths(tree, current_node, is_disrupted=False):
            if not tree:
                if is_disrupted:
                    disrupted_path.append(current_node)
                else:
                    open_path.append(current_node)
                return
            
            action = tree[0]
            plans = tree[1]
            
            if is_disrupted:
                disrupted_path.append(current_node)
            else:
                open_path.append(current_node)
                
            states = list(plans.keys())
            if len(states) == 1:
                extract_paths(plans[states[0]], action, is_disrupted)
            else:
                nonlocal uncertain_edge
                uncertain_edge = (current_node, action)
                for s in states:
                    s_node, s_blocked = s
                    if s_node == action:
                        extract_paths(plans[s], action, is_disrupted)
                    else:
                        disrupted_path.clear()
                        disrupted_path.extend(open_path)
                        extract_paths(plans[s], current_node, True)

        extract_paths(result_tree, start, False)
        if not uncertain_edge:
            disrupted_path = open_path.copy()
            
    def clean_path(p):
        res = []
        for n in p:
            if not res or res[-1] != n:
                res.append(n)
        return res
        
    open_path = clean_path(open_path)
    disrupted_path = clean_path(disrupted_path)
    
    selected_path = open_path if open_path else []
    edge_label = "-".join(uncertain_edge) if uncertain_edge else "none"

    if complete:
        add_trace(
            "RETURN_CONDITIONAL_PLAN", start, [], selected_path, path_time(scenario, selected_path),
            "Tim thay ke hoach AND-OR hoan thien.",
            {"nodeType": "RETURN", "complete": True, "result": "SOLUTION"}
        )
    else:
        add_trace(
            "FAIL_CONDITIONAL_PLAN", start, [], [], BLOCKED_COST,
            "Khong the tim duoc ke hoach AND-OR hoan thien.",
            {"nodeType": "RETURN", "complete": False, "result": "FAILURE"}
        )

    return {
        "path": selected_path,
        "visited": list(dict.fromkeys(open_path + disrupted_path)),
        "traceSteps": traces,
        "initialPath": open_path,
        "finalPath": selected_path,
        "beliefMode": "conditional_plan",
        "replans": 0,
        "observedEdges": [],
        "conditionalPlan": {
            "uncertainEdge": edge_label,
            "ifOpen": open_path,
            "ifDisrupted": disrupted_path,
            "complete": complete,
        },
        "andOrTree": {
            "root": "OR",
            "action": "recursive_search",
            "andOutcomes": [
                {"outcome": "open", "path": open_path, "solved": complete},
                {"outcome": "disrupted", "path": disrupted_path, "solved": complete},
            ],
        },
        "expandedAndOrNodes": len(traces) if debug else 1,
        "complete": complete,
        "completenessCondition": "Complete theo chuan de quy AND-OR Graph Search cua AI textbook.",
    }


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
    if debug:
        traces.append(
            TraceStep(
                stepIndex=0,
                phase="BELIEF_INIT",
                currentNode=start,
                frontier=["clear_world", "hidden_event_world"],
                visitedNodes=[],
                candidatePath=[],
                costSoFar=0,
                heuristic=float(2),
                decisionReason=(
                    "Khoi tao belief state gom cac world kha di; agent chua biet world nao la that."
                ),
                debugData={
                    "traceType": "belief_state" if algorithm == "belief_state" else "expectimax",
                    "courseConcept": "Belief State = tap cac trang thai/world kha di khi thieu thong tin.",
                    "beliefStateSize": 2,
                    "possibleWorlds": ["clear_world", "hidden_event_world"],
                    "observation": None,
                    "filtering": "Khong co observation moi nen chua loai world nao.",
                    "result": "INIT_BELIEF",
                },
            )
        )
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
            phase = "CHANCE_EXPECTED_VALUE" if algorithm == "expectimax" else "BELIEF_ACTION_EVALUATE"
            aggregation = "sum(P(world) * cost(world))" if algorithm == "expectimax" else "worst-case over possible worlds"
            traces.append(
                TraceStep(
                    stepIndex=len(traces),
                    phase=phase,
                    currentNode=start,
                    frontier=[" -> ".join(candidate) for candidate in candidates],
                    visitedNodes=list(dict.fromkeys(path)),
                    candidatePath=path,
                    costSoFar=round(value, 2),
                    heuristic=round(event_cost - clear_cost, 2),
                    decisionReason=(
                        f"Danh gia mot action/route tren belief state: clear={clear_cost:.2f}, "
                        f"hidden_event={event_cost:.2f}, value={value:.2f} theo {aggregation}."
                    ),
                    debugData={
                        "traceType": "belief_state" if algorithm == "belief_state" else "expectimax",
                        "courseConcept": (
                            "Expectimax dung chance node va expected value."
                            if algorithm == "expectimax"
                            else "Sensorless/Belief search phai chon action tot cho toan bo tap world kha di."
                        ),
                        "beliefStateSize": 2,
                        "possibleWorlds": ["clear_world", "hidden_event_world"],
                        "probabilities": {"clear_world": 0.65, "hidden_event_world": 0.35} if algorithm == "expectimax" else {},
                        "aggregation": aggregation,
                        "action": " -> ".join(path),
                        "result": "EVALUATE_ACTION",
                        **row,
                    },
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
                phase="PARTIAL_OBSERVATION_INIT",
                currentNode=current,
                frontier=[],
                visitedNodes=[],
                candidatePath=initial.path,
                costSoFar=0,
                heuristic=float(len(remaining_hidden)),
                decisionReason=(
                    "Khoi tao partial-observable state: agent co map believed, hidden event nam ngoai sensor range."
                ),
                debugData={
                    "traceType": "partial_observation",
                    "courseConcept": "Partial Observation: predict -> observe percept -> filter belief state -> replan.",
                    "hiddenEdges": sorted("-".join(key) for key in remaining_hidden),
                    "sensorRadius": sensor_radius,
                    "beliefStateSize": 1 + len(remaining_hidden),
                    "observation": [],
                    "filtering": "Chua co percept nen believed map giu nguyen.",
                    "result": "INIT_BELIEF",
                },
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
            before_size = 1 + len(remaining_hidden) + len(revealed)
            after_size = 1 + len(remaining_hidden)
            traces.append(
                TraceStep(
                    stepIndex=len(traces),
                    phase="OBSERVE_FILTER_REPLAN",
                    currentNode=current,
                    frontier=plan.visited_nodes,
                    visitedNodes=list(dict.fromkeys(visited)),
                    candidatePath=plan.path,
                    costSoFar=plan.total_minutes,
                    heuristic=float(len(remaining_hidden)),
                    decisionReason=(
                        f"Nhan percept co {len(revealed)} thay doi; filter belief state roi re-plan tu {current}."
                        if revealed
                        else f"Khong co percept moi; belief state khong doi va tiep tuc policy tu {current}."
                    ),
                    debugData={
                        "traceType": "partial_observation",
                        "courseConcept": "Observation dung de loai cac world khong phu hop, sau do lap ke hoach lai.",
                        "observation": revealed,
                        "observedEdges": observed_edges[:],
                        "remainingHiddenEdges": sorted("-".join(key) for key in remaining_hidden),
                        "beliefStateSizeBefore": before_size,
                        "beliefStateSizeAfter": after_size,
                        "filtering": (
                            "Loai cac edge hidden da duoc sensor xac nhan."
                            if revealed
                            else "Khong loai world nao vi percept rong."
                        ),
                        "beliefPath": plan.path,
                        "result": "FILTER_AND_REPLAN",
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
    if algorithm == "and_or":
        result = _and_or_plan(scenario, actual, start, goal, hidden, debug)
    elif algorithm in {"belief_state", "expectimax"}:
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
