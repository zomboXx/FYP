from __future__ import annotations

from copy import deepcopy

from app.algorithms.delivery import selected_orders
from app.algorithms.graph import edge_key
from app.algorithms.search import astar
from app.models.schemas import Scenario


def simulate_event(scenario: Scenario, event_type: str, affected_edge: tuple[str, str] | None) -> tuple[Scenario, str]:
    updated = deepcopy(scenario)
    if event_type == "accident":
        edge = _pick_edge(updated, affected_edge)
        edge.blocked = True
        edge.traffic = "heavy"
        return updated, f"Tai nan lam chan duong {edge.source}-{edge.target}; he thong can tim duong thay the."
    if event_type == "peak_hour":
        for edge in updated.edges:
            if edge.traffic != "light":
                edge.traffic = "heavy"
        return updated, "Gio cao diem bien nhieu truc duong thanh ket xe nang."
    for edge in updated.edges:
        if edge.traffic == "light":
            edge.traffic = "normal"
        elif edge.traffic == "normal":
            edge.traffic = "heavy"
    return updated, "Mua lon lam tang thoi gian di chuyen tren toan mang duong."


def _pick_edge(scenario: Scenario, affected_edge: tuple[str, str] | None):
    if affected_edge:
        wanted = edge_key(*affected_edge)
        for edge in scenario.edges:
            if edge_key(edge.source, edge.target) == wanted:
                return edge
    return scenario.edges[6]


def expectimax_event_choice(scenario: Scenario) -> dict:
    orders = selected_orders(scenario, None)
    goal = orders[-1].dropoff_node_id or orders[-1].node_id
    start = scenario.depot_id
    candidates = [
        ("no_event", scenario, 0.5),
        ("rain", simulate_event(scenario, "rain", None)[0], 0.3),
        ("accident", simulate_event(scenario, "accident", ("C", "D"))[0], 0.2),
    ]
    expected_cost = 0.0
    branch_details = []
    best_path: list[str] = []
    best_minutes = float("inf")
    visited: list[str] = []
    for name, branch, probability in candidates:
        result = astar(branch, start, goal)
        expected_cost += probability * result.total_minutes
        branch_details.append({"event": name, "probability": probability, "minutes": result.total_minutes})
        if result.total_minutes < best_minutes:
            best_minutes = result.total_minutes
            best_path = result.path
            visited = result.visited_nodes
    return {
        "path": best_path,
        "visited": visited,
        "expectedMinutes": round(expected_cost, 2),
        "branches": branch_details,
    }


def replan_after_event(scenario: Scenario, event_type: str, affected_edge: tuple[str, str] | None) -> dict:
    orders = selected_orders(scenario, None)
    goal = orders[-1].dropoff_node_id or orders[-1].node_id
    start = scenario.depot_id
    original = astar(scenario, start, goal)
    updated, event_message = simulate_event(scenario, event_type, affected_edge)
    replanned = astar(updated, start, goal)
    original_edges = {edge_key(a, b) for a, b in zip(original.path, original.path[1:])}
    replanned_edges = {edge_key(a, b) for a, b in zip(replanned.path, replanned.path[1:])}
    changed_edges = sorted("-".join(edge) for edge in replanned_edges.symmetric_difference(original_edges))
    return {
        "updatedScenario": updated,
        "eventMessage": event_message,
        "start": start,
        "goal": goal,
        "originalPath": original.path,
        "originalMinutes": original.total_minutes,
        "replannedPath": replanned.path,
        "replannedMinutes": replanned.total_minutes,
        "changedEdges": changed_edges,
        "visited": list(dict.fromkeys(original.visited_nodes + replanned.visited_nodes)),
    }
