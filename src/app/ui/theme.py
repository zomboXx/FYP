from __future__ import annotations

from typing import Any

BG = "#05080D"
PANEL = "#0B1016"
PANEL_2 = "#101720"
INK = "#030507"
LINE = "#23303C"
LINE_LIGHT = "#344250"
TEXT = "#F7FAFC"
MUTED = "#8EA0B7"
GREEN = "#23D179"
GREEN_DARK = "#10291D"
CYAN = "#24C8E8"
YELLOW = "#FACC15"
RED = "#FF4D57"
PAPER = PANEL
PAPER_2 = BG


ALGORITHM_GROUPS: dict[str, dict[str, Any]] = {
    "uninformed": {
        "label": "Uninformed Search",
        "short": "UNINFORMED",
        "mode": "pathfinding",
        "algorithms": [("bfs", "BFS"), ("dfs", "DFS"), ("ucs", "UCS")],
    },
    "informed": {
        "label": "Informed Search",
        "short": "INFORMED",
        "mode": "pathfinding",
        "algorithms": [("astar", "A*"), ("greedy", "Greedy Best-First")],
    },
    "local_search": {
        "label": "Local Search",
        "short": "LOCAL SEARCH",
        "mode": "delivery",
        "algorithms": [
            ("hill_climbing", "Hill Climbing"),
            ("simulated_annealing", "Simulated Annealing"),
            ("local_beam", "Local Beam Search"),
            ("genetic", "Genetic Algorithm"),
        ],
    },
    "complex": {
        "label": "Complex / Partial Observability",
        "short": "COMPLEX ENV",
        "mode": "complex",
        "algorithms": [
            ("belief_state", "Belief-State Search"),
            ("online_replan", "Online Replanning"),
            ("expectimax", "Expectimax Evaluator"),
        ],
    },
    "csp": {
        "label": "CSP",
        "short": "CSP",
        "mode": "csp",
        "algorithms": [("backtracking", "Backtracking + MRV"), ("forward_checking", "Forward Checking")],
    },
    "adversarial": {
        "label": "Adversarial Search",
        "short": "ADVERSARIAL",
        "mode": "adversarial",
        "algorithms": [("minimax", "Minimax"), ("alpha_beta", "Alpha-Beta")],
    },
}


WORKSPACE_COPY = {
    "shipper": (
        "SHIPPER DISPATCH",
        "Nhan don, lap lo trinh va theo doi graph giao hang trong mot man hinh lam viec.",
    ),
    "defense": (
        "DEFENSE LAB",
        "Mo phong thuat toan, xem frontier/visited/cost va ke cau chuyen debug cho buoi bao ve.",
    ),
    "admin": (
        "ADMIN PERMISSIONS",
        "Bat tat nhom thuat toan theo nhom shipper va giu luong demo trong tam kiem soat.",
    ),
    "map": (
        "LIVE MAP",
        "Ban do OpenStreetMap/Leaflet co zoom, pan, nodes, edges va click de lay toa do.",
    ),
}
