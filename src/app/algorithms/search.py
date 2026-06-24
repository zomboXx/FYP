from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import heapq
from itertools import count

from app.algorithms.graph import BLOCKED_COST, build_adjacency, edge_time, heuristic_minutes, path_distance, path_time
from app.models.schemas import Scenario, TraceStep


@dataclass
class SearchResult:
    path: list[str]
    visited_nodes: list[str]
    cost: float
    distance_km: float
    total_minutes: float
    trace_steps: list[TraceStep]


def _result(scenario: Scenario, path: list[str], visited: list[str], trace: list[TraceStep] | None = None) -> SearchResult:
    minutes = path_time(scenario, path) if path else BLOCKED_COST
    return SearchResult(
        path=path,
        visited_nodes=visited,
        cost=minutes,
        distance_km=path_distance(scenario, path) if path else 0,
        total_minutes=minutes,
        trace_steps=trace or [],
    )


def _trace(
    trace_steps: list[TraceStep],
    phase: str,
    current: str | None,
    frontier: list[str],
    visited: list[str],
    path: list[str],
    cost: float,
    heuristic: float,
    reason: str,
    previous: str | None = None,
    preview_path: list[str] | None = None,
    debug_data: dict | None = None,
) -> None:
    trace_steps.append(
        TraceStep(
            stepIndex=len(trace_steps),
            phase=phase,
            currentNode=current,
            previousNode=previous,
            frontier=frontier[:],
            visitedNodes=visited[:],
            candidatePath=path[:],
            previewPath=(preview_path or path)[:],
            costSoFar=round(cost, 2),
            heuristic=round(heuristic, 2),
            decisionReason=reason,
            debugData=debug_data or {},
        )
    )


def _parent_path(parent: dict[str, str | None], node: str | None) -> list[str]:
    if node is None or node not in parent:
        return []
    path: list[str] = []
    current: str | None = node
    while current is not None:
        path.append(current)
        current = parent.get(current)
    return list(reversed(path))


def _parent_debug(parent: dict[str, str | None]) -> dict[str, str | None]:
    return {node: previous for node, previous in parent.items() if previous is not None}


def bfs(scenario: Scenario, start: str, goal: str, debug: bool = False) -> SearchResult:
    adjacency = build_adjacency(scenario)
    queue = deque([start])
    seen = {start}
    parent: dict[str, str | None] = {start: None}
    visited: list[str] = []
    trace: list[TraceStep] = []
    if debug:
        _trace(
            trace,
            "initialize",
            None,
            [start],
            [],
            [],
            0,
            0,
            "Khoi tao BFS: node/edge tren ban do giu mau nen cho den khi bat dau xet frontier.",
            debug_data={"root": start, "parentMap": {}, "suppressHighlights": True},
        )
    while queue:
        node = queue.popleft()
        path = _parent_path(parent, node)
        visited.append(node)
        if debug:
            _trace(
                trace,
                "pop_frontier",
                node,
                list(queue),
                visited,
                path,
                len(path) - 1,
                0,
                "BFS lay nut cu nhat trong hang doi FIFO.",
                previous=parent.get(node),
                preview_path=path,
                debug_data={"root": start, "parentMap": _parent_debug(parent)},
            )
        if node == goal:
            if debug:
                _trace(
                    trace,
                    "goal_found",
                    node,
                    [],
                    visited,
                    path,
                    path_time(scenario, path),
                    0,
                    "Da gap dich nen dung tim kiem.",
                    previous=parent.get(node),
                    preview_path=path,
                    debug_data={"root": start, "parentMap": _parent_debug(parent)},
                )
            return _result(scenario, path, visited, trace)
        for neighbor, edge in adjacency[node]:
            if neighbor not in seen and edge_time(edge) < BLOCKED_COST:
                seen.add(neighbor)
                parent[neighbor] = node
                queue.append(neighbor)
                neighbor_path = _parent_path(parent, neighbor)
                if debug:
                    _trace(
                        trace,
                        "push_neighbor",
                        node,
                        list(queue),
                        visited,
                        path,
                        len(path),
                        0,
                        f"Them {neighbor} vao frontier voi node truoc do la {node}.",
                        previous=parent.get(node),
                        preview_path=path,
                        debug_data={
                            "root": start,
                            "parentMap": _parent_debug(parent),
                            "generatedNode": neighbor,
                            "generatedFrom": node,
                            "generatedPath": neighbor_path,
                        },
                    )
    return _result(scenario, [], visited, trace)


def dfs(scenario: Scenario, start: str, goal: str, debug: bool = False) -> SearchResult:
    adjacency = build_adjacency(scenario)
    stack = [start]
    scheduled = {start}
    parent: dict[str, str | None] = {start: None}
    seen: set[str] = set()
    visited: list[str] = []
    trace: list[TraceStep] = []
    if debug:
        _trace(
            trace,
            "initialize",
            None,
            [start],
            [],
            [],
            0,
            0,
            "Khoi tao DFS: ban do bat dau tu trang thai nen truoc khi pop stack.",
            debug_data={"root": start, "parentMap": {}, "suppressHighlights": True},
        )
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        path = _parent_path(parent, node)
        seen.add(node)
        visited.append(node)
        if debug:
            _trace(
                trace,
                "pop_frontier",
                node,
                stack[:],
                visited,
                path,
                len(path) - 1,
                0,
                "DFS lay nut moi nhat trong stack LIFO.",
                previous=parent.get(node),
                preview_path=path,
                debug_data={"root": start, "parentMap": _parent_debug(parent)},
            )
        if node == goal:
            if debug:
                _trace(
                    trace,
                    "goal_found",
                    node,
                    [],
                    visited,
                    path,
                    path_time(scenario, path),
                    0,
                    "Da gap dich nen dung tim kiem.",
                    previous=parent.get(node),
                    preview_path=path,
                    debug_data={"root": start, "parentMap": _parent_debug(parent)},
                )
            return _result(scenario, path, visited, trace)
        for neighbor, edge in reversed(adjacency[node]):
            if neighbor not in seen and neighbor not in scheduled and edge_time(edge) < BLOCKED_COST:
                scheduled.add(neighbor)
                parent[neighbor] = node
                stack.append(neighbor)
                neighbor_path = _parent_path(parent, neighbor)
                if debug:
                    _trace(
                        trace,
                        "push_neighbor",
                        node,
                        stack[:],
                        visited,
                        path,
                        len(path),
                        0,
                        f"Day {neighbor} vao stack voi node truoc do la {node}.",
                        previous=parent.get(node),
                        preview_path=path,
                        debug_data={
                            "root": start,
                            "parentMap": _parent_debug(parent),
                            "generatedNode": neighbor,
                            "generatedFrom": node,
                            "generatedPath": neighbor_path,
                        },
                    )
    return _result(scenario, [], visited, trace)


def _priority_search(scenario: Scenario, start: str, goal: str, mode: str, debug: bool = False) -> SearchResult:
    adjacency = build_adjacency(scenario)
    order = count()
    initial_priority = heuristic_minutes(scenario, start, goal) if mode in {"greedy", "astar"} else 0
    frontier: list[tuple[float, int, str, list[str], float]] = [(initial_priority, next(order), start, [start], 0)]
    best_cost = {start: 0.0}
    parent: dict[str, str | None] = {start: None}
    visited: list[str] = []
    trace: list[TraceStep] = []
    if debug:
        _trace(
            trace,
            "initialize",
            None,
            [start],
            [],
            [],
            0,
            initial_priority,
            f"Khoi tao {mode.upper()}: chua highlight node/edge nao tren ban do.",
            debug_data={
                "root": start,
                "parentMap": {},
                "suppressHighlights": True,
                "evaluation": mode,
                "g": 0,
                "h": round(heuristic_minutes(scenario, start, goal), 2),
                "f": round(initial_priority, 2),
            },
        )
    while frontier:
        priority, _, node, path, cost_so_far = heapq.heappop(frontier)
        if node in visited:
            continue
        visited.append(node)
        if debug:
            _trace(
                trace,
                "pop_frontier",
                node,
                [item[2] for item in sorted(frontier)],
                visited,
                path,
                cost_so_far,
                heuristic_minutes(scenario, node, goal),
                f"{mode.upper()} chon {node} vi priority hien tai la {priority:.2f}.",
                previous=parent.get(node),
                preview_path=_parent_path(parent, node),
                debug_data={
                    "evaluation": mode,
                    "g": round(cost_so_far, 2),
                    "h": round(heuristic_minutes(scenario, node, goal), 2),
                    "f": round(priority, 2),
                    "parentMap": _parent_debug(parent),
                },
            )
        if node == goal:
            if debug:
                _trace(
                    trace,
                    "goal_found",
                    node,
                    [],
                    visited,
                    path,
                    cost_so_far,
                    0,
                    "Da gap dich, duong di hien tai duoc tra ve.",
                    previous=parent.get(node),
                    preview_path=_parent_path(parent, node),
                    debug_data={"evaluation": mode, "parentMap": _parent_debug(parent)},
                )
            return _result(scenario, path, visited, trace)
        for neighbor, edge in adjacency[node]:
            travel = edge_time(edge)
            if travel >= BLOCKED_COST:
                continue
            new_cost = cost_so_far + travel
            if new_cost >= best_cost.get(neighbor, BLOCKED_COST):
                continue
            best_cost[neighbor] = new_cost
            parent[neighbor] = node
            if mode == "ucs":
                priority = new_cost
            elif mode == "greedy":
                priority = heuristic_minutes(scenario, neighbor, goal)
            else:
                priority = new_cost + heuristic_minutes(scenario, neighbor, goal)
            neighbor_path = _parent_path(parent, neighbor)
            heapq.heappush(frontier, (priority, next(order), neighbor, neighbor_path, new_cost))
            if debug:
                _trace(
                    trace,
                    "push_neighbor",
                    node,
                    [item[2] for item in sorted(frontier)],
                    visited,
                    path,
                    new_cost,
                    heuristic_minutes(scenario, neighbor, goal),
                    f"Cap nhat {neighbor} qua node truoc do {node}: g={new_cost:.2f}, priority={priority:.2f}.",
                    previous=parent.get(node),
                    preview_path=path,
                    debug_data={
                        "evaluation": mode,
                        "g": round(new_cost, 2),
                        "h": round(heuristic_minutes(scenario, neighbor, goal), 2),
                        "f": round(priority, 2),
                        "parentMap": _parent_debug(parent),
                        "generatedNode": neighbor,
                        "generatedFrom": node,
                        "generatedPath": neighbor_path,
                    },
                )
    return _result(scenario, [], visited, trace)


def ucs(scenario: Scenario, start: str, goal: str, debug: bool = False) -> SearchResult:
    return _priority_search(scenario, start, goal, "ucs", debug)


def greedy(scenario: Scenario, start: str, goal: str, debug: bool = False) -> SearchResult:
    return _priority_search(scenario, start, goal, "greedy", debug)


def astar(scenario: Scenario, start: str, goal: str, debug: bool = False) -> SearchResult:
    return _priority_search(scenario, start, goal, "astar", debug)


SEARCH_ALGORITHMS = {
    "bfs": bfs,
    "dfs": dfs,
    "ucs": ucs,
    "greedy": greedy,
    "astar": astar,
}
