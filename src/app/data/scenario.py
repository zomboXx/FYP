from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import Edge, Node, Order, Scenario

DATA_DIR = Path(__file__).resolve().parent
OSM_CACHE_PATH = DATA_DIR / "osm_hcm_q1.json"


def load_osm_cached_scenario() -> Scenario:
    if not OSM_CACHE_PATH.exists():
        return default_scenario()
    with OSM_CACHE_PATH.open("r", encoding="utf-8") as file:
        return Scenario.model_validate(json.load(file))


def default_scenario() -> Scenario:
    return Scenario(
        depot_id="D0",
        capacity_kg=18,
        nodes=[
            Node(id="D0", name="Kho Quan 1", x=80, y=220, type="depot"),
            Node(id="A", name="Cho Ben Thanh", x=190, y=145, type="landmark"),
            Node(id="B", name="Nga sau Phu Dong", x=295, y=105, type="intersection"),
            Node(id="C", name="Cau Ong Lanh", x=240, y=245, type="intersection"),
            Node(id="D", name="Tran Hung Dao", x=380, y=230, type="order"),
            Node(id="E", name="Nguyen Trai", x=500, y=145, type="order"),
            Node(id="F", name="Cach Mang Thang 8", x=460, y=330, type="intersection"),
            Node(id="G", name="Kho Binh Thanh", x=625, y=250, type="order"),
            Node(id="H", name="Thu Thiem", x=690, y=120, type="order"),
            Node(id="I", name="Tan Dinh", x=345, y=370, type="order"),
        ],
        edges=[
            Edge(source="D0", target="A", distance_km=1.2, base_minutes=5, traffic="normal"),
            Edge(source="D0", target="C", distance_km=1.4, base_minutes=6, traffic="light"),
            Edge(source="A", target="B", distance_km=1.1, base_minutes=5, traffic="heavy"),
            Edge(source="A", target="C", distance_km=1.0, base_minutes=4, traffic="normal"),
            Edge(source="B", target="D", distance_km=1.5, base_minutes=7, traffic="normal"),
            Edge(source="B", target="E", distance_km=2.0, base_minutes=9, traffic="heavy"),
            Edge(source="C", target="D", distance_km=1.3, base_minutes=6, traffic="light"),
            Edge(source="C", target="I", distance_km=1.7, base_minutes=8, traffic="normal"),
            Edge(source="D", target="E", distance_km=1.4, base_minutes=6, traffic="normal"),
            Edge(source="D", target="F", distance_km=1.2, base_minutes=5, traffic="heavy"),
            Edge(source="E", target="G", distance_km=1.8, base_minutes=8, traffic="normal"),
            Edge(source="E", target="H", distance_km=2.2, base_minutes=10, traffic="light"),
            Edge(source="F", target="G", distance_km=1.9, base_minutes=8, traffic="normal"),
            Edge(source="F", target="I", distance_km=1.0, base_minutes=4, traffic="light"),
            Edge(source="G", target="H", distance_km=1.5, base_minutes=7, traffic="normal"),
            Edge(source="I", target="D", distance_km=1.1, base_minutes=5, traffic="normal"),
        ],
        orders=[
            Order(
                id="O1",
                node_id="D",
                pickup_node_id="D0",
                dropoff_node_id="D",
                category="food",
                urgency="urgent",
                demand_kg=4,
                ready_min=0,
                due_min=35,
                service_min=4,
                priority=5,
            ),
            Order(
                id="O2",
                node_id="E",
                pickup_node_id="A",
                dropoff_node_id="E",
                category="parcel",
                urgency="normal",
                demand_kg=5,
                ready_min=0,
                due_min=55,
                service_min=5,
                priority=3,
            ),
            Order(
                id="O3",
                node_id="G",
                pickup_node_id="D0",
                dropoff_node_id="G",
                category="ride",
                urgency="urgent",
                demand_kg=1,
                ready_min=10,
                due_min=75,
                service_min=2,
                priority=5,
            ),
            Order(
                id="O4",
                node_id="H",
                pickup_node_id="E",
                dropoff_node_id="H",
                category="grocery",
                urgency="low",
                demand_kg=3,
                ready_min=0,
                due_min=70,
                service_min=4,
                priority=2,
            ),
            Order(
                id="O5",
                node_id="I",
                pickup_node_id="C",
                dropoff_node_id="I",
                category="food",
                urgency="normal",
                demand_kg=4,
                ready_min=5,
                due_min=50,
                service_min=3,
                priority=4,
            ),
        ],
    )
