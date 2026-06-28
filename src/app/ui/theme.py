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

MAP_STATUS_COLORS: dict[str, str] = {
    "route": CYAN,
    "preview": "#9BE7F6",
    "visited": GREEN,
    "frontier": YELLOW,
    "current": RED,
    "goal": RED,
}

ALGORITHM_GROUPS: dict[str, dict[str, Any]] = {
    "uninformed": {
        "label": "Uninformed Search",
        "short": "UNINFORMED",
        "mode": "pathfinding",
        "algorithms": [("bfs", "BFS"), ("dfs", "DFS")],
    },
    "informed": {
        "label": "Informed Search",
        "short": "INFORMED",
        "mode": "pathfinding",
        "algorithms": [("greedy", "Greedy Best-First Search"), ("astar", "A*")],
    },
    "local_search": {
        "label": "Local Search",
        "short": "LOCAL SEARCH",
        "mode": "delivery",
        "algorithms": [
            ("simple_hill_climbing", "Simple Hill Climbing"),
            ("simulated_annealing", "Simulated Annealing"),
        ],
    },
    "complex": {
        "label": "Complex Environment Search",
        "short": "COMPLEX ENV",
        "mode": "complex",
        "algorithms": [
            ("online_replan", "Online Re-planning"),
            ("and_or", "AND-OR Search"),
        ],
    },
    "csp": {
        "label": "Constraint Satisfaction Problem (CSP)",
        "short": "CSP",
        "mode": "csp",
        "algorithms": [
            ("backtracking", "Backtracking"),
            ("forward_checking", "Forward Checking"),
        ],
    },
    "adversarial": {
        "label": "Adversarial Search",
        "short": "ADVERSARIAL",
        "mode": "adversarial",
        "algorithms": [("minimax", "Minimax"), ("alpha_beta", "Alpha-Beta Pruning")],
    },
}

ALGORITHM_MAP_STYLES: dict[str, dict[str, str]] = {
    "uninformed": {
        **MAP_STATUS_COLORS,
        "badge": "UNINFORMED MAP",
    },
    "informed": {
        **MAP_STATUS_COLORS,
        "badge": "INFORMED MAP",
    },
    "local_search": {
        **MAP_STATUS_COLORS,
        "badge": "LOCAL MAP",
    },
    "complex": {
        **MAP_STATUS_COLORS,
        "badge": "COMPLEX MAP",
    },
    "csp": {
        **MAP_STATUS_COLORS,
        "badge": "CSP MAP",
    },
    "adversarial": {
        **MAP_STATUS_COLORS,
        "badge": "GAME MAP",
    },
    "shipper": {
        **MAP_STATUS_COLORS,
        "badge": "SHIPPER MAP",
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
