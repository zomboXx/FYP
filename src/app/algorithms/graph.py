from __future__ import annotations

import math

from app.models.schemas import Edge, Scenario

TRAFFIC_MULTIPLIER = {"light": 0.8, "normal": 1.0, "heavy": 1.6}
BLOCKED_COST = 1_000_000.0


def edge_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def edge_time(edge: Edge) -> float:
    if edge.blocked:
        return BLOCKED_COST
    return edge.base_minutes * TRAFFIC_MULTIPLIER[edge.traffic]


def build_adjacency(scenario: Scenario) -> dict[str, list[tuple[str, Edge]]]:
    adjacency: dict[str, list[tuple[str, Edge]]] = {node.id: [] for node in scenario.nodes}
    for edge in scenario.edges:
        adjacency.setdefault(edge.source, []).append((edge.target, edge))
        adjacency.setdefault(edge.target, []).append((edge.source, edge))
    for neighbors in adjacency.values():
        neighbors.sort(key=lambda item: item[0])
    return adjacency


def find_edge(scenario: Scenario, a: str, b: str) -> Edge | None:
    wanted = edge_key(a, b)
    for edge in scenario.edges:
        if edge_key(edge.source, edge.target) == wanted:
            return edge
    return None


def node_lookup(scenario: Scenario):
    return {node.id: node for node in scenario.nodes}


def heuristic_minutes(scenario: Scenario, a: str, b: str) -> float:
    nodes = node_lookup(scenario)
    start = nodes[a]
    goal = nodes[b]
    pixel_distance = math.hypot(start.x - goal.x, start.y - goal.y)
    return pixel_distance / 55


def path_distance(scenario: Scenario, path: list[str]) -> float:
    total = 0.0
    for a, b in zip(path, path[1:]):
        edge = find_edge(scenario, a, b)
        if edge is None:
            return BLOCKED_COST
        total += edge.distance_km
    return round(total, 2)


def path_time(scenario: Scenario, path: list[str]) -> float:
    total = 0.0
    for a, b in zip(path, path[1:]):
        edge = find_edge(scenario, a, b)
        if edge is None:
            return BLOCKED_COST
        total += edge_time(edge)
    return round(total, 2)
