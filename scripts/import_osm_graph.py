from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a small HCMC OSM drive graph into the FYP Scenario JSON format.")
    parser.add_argument("--output", default="src/app/data/osm_hcm_q1.json")
    parser.add_argument("--north", type=float, default=10.7895)
    parser.add_argument("--south", type=float, default=10.7605)
    parser.add_argument("--east", type=float, default=106.7105)
    parser.add_argument("--west", type=float, default=106.6825)
    parser.add_argument("--max-nodes", type=int, default=24)
    args = parser.parse_args()

    try:
        import osmnx as ox
    except ImportError as exc:
        raise SystemExit("Install osmnx first: python -m pip install osmnx") from exc

    graph = ox.graph_from_bbox(
        (args.north, args.south, args.east, args.west),
        network_type="drive",
        simplify=True,
    )
    graph = ox.project_graph(graph)
    nodes = list(graph.nodes(data=True))[: args.max_nodes]
    node_ids = {raw_id: f"N{index}" for index, (raw_id, _) in enumerate(nodes)}
    xs = [data["x"] for _, data in nodes]
    ys = [data["y"] for _, data in nodes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def scale(value: float, low: float, high: float, target_low: float, target_high: float) -> float:
        if math.isclose(low, high):
            return (target_low + target_high) / 2
        return target_low + ((value - low) / (high - low)) * (target_high - target_low)

    scenario_nodes = []
    for index, (raw_id, data) in enumerate(nodes):
        node_id = node_ids[raw_id]
        node_type = "depot" if index == 0 else "order" if index in {5, 9, 13, 17, 21} else "intersection"
        scenario_nodes.append(
            {
                "id": "D0" if index == 0 else node_id,
                "name": f"OSM node {raw_id}",
                "x": round(scale(data["x"], min_x, max_x, 80, 720), 2),
                "y": round(scale(data["y"], min_y, max_y, 380, 80), 2),
                "type": node_type,
            }
        )

    normalized_ids = {raw_id: ("D0" if index == 0 else node_ids[raw_id]) for index, (raw_id, _) in enumerate(nodes)}
    scenario_edges = []
    seen_edges = set()
    for source, target, data in graph.edges(data=True):
        if source not in normalized_ids or target not in normalized_ids:
            continue
        a, b = normalized_ids[source], normalized_ids[target]
        key = tuple(sorted((a, b)))
        if a == b or key in seen_edges:
            continue
        seen_edges.add(key)
        distance_km = round(float(data.get("length", 500)) / 1000, 2)
        base_minutes = max(2.0, round(distance_km / 22 * 60, 2))
        scenario_edges.append(
            {
                "source": a,
                "target": b,
                "distance_km": distance_km,
                "base_minutes": base_minutes,
                "traffic": "normal",
                "blocked": False,
            }
        )

    order_nodes = [node for node in scenario_nodes if node["type"] == "order"][:5]
    scenario = {
        "depot_id": "D0",
        "capacity_kg": 18,
        "nodes": scenario_nodes,
        "edges": scenario_edges,
        "orders": [
            {
                "id": f"O{index + 1}",
                "node_id": node["id"],
                "pickup_node_id": "D0",
                "dropoff_node_id": node["id"],
                "category": ["food", "ride", "parcel", "grocery", "food"][index],
                "urgency": ["urgent", "urgent", "normal", "low", "normal"][index],
                "demand_kg": [3, 1, 5, 4, 3][index],
                "ready_min": [0, 5, 0, 0, 10][index],
                "due_min": [30, 55, 70, 90, 65][index],
                "service_min": [4, 2, 5, 4, 3][index],
                "priority": [5, 5, 3, 2, 4][index],
            }
            for index, node in enumerate(order_nodes)
        ],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    print(f"Wrote {output} with {len(scenario_nodes)} nodes and {len(scenario_edges)} edges.")


if __name__ == "__main__":
    main()
