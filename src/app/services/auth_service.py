from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import random
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping

from fastapi import Depends, Header, HTTPException, status

from app.data.scenario import load_osm_cached_scenario
from app.models.schemas import AvailableOrder, Order, PermissionRow, UserPublic

LOCAL_DEMO_JWT_SECRET = "fyp-local-demo-secret"
PRODUCTION_ENV_FLAGS = ("VERCEL", "FYP_PRODUCTION")
LOCAL_DEMO_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "fyp.sqlite"
VERCEL_DEMO_DB_PATH = Path("/tmp/fyp.sqlite")


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() not in {"", "0", "false", "no", "off"}


def load_jwt_secret(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    configured = source.get("FYP_JWT_SECRET", "").strip()
    if configured:
        return configured
    if any(_truthy(source.get(flag)) for flag in PRODUCTION_ENV_FLAGS):
        raise RuntimeError("FYP_JWT_SECRET must be set before running Find Your Path in production.")
    return LOCAL_DEMO_JWT_SECRET


def load_db_path(env: Mapping[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    configured = source.get("FYP_DB_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    if _truthy(source.get("VERCEL")):
        return VERCEL_DEMO_DB_PATH
    return LOCAL_DEMO_DB_PATH


SECRET = load_jwt_secret()
DB_PATH = load_db_path()
ACTIVE_ALGORITHM_GROUPS = {
    "bfs": "uninformed",
    "dfs": "uninformed",
    "greedy": "informed",
    "astar": "informed",
    "simple_hill_climbing": "local_search",
    "simulated_annealing": "local_search",
    "backtracking": "csp",
    "forward_checking": "csp",
    "online_replan": "complex",
    "and_or": "complex",
    "minimax": "adversarial",
    "alpha_beta": "adversarial",
}
LEGACY_ALGORITHM_GROUPS = {
    "constraint": "csp",
}
ALGORITHM_GROUPS = {**ACTIVE_ALGORITHM_GROUPS, **LEGACY_ALGORITHM_GROUPS}
STANDARD_DEFAULT_ALGORITHMS = {
    "bfs",
    "astar",
    "simple_hill_climbing",
    "constraint",
    "forward_checking",
    "online_replan",
    "and_or",
    "minimax",
}
MIN_AVAILABLE_ORDERS = 7
ORDER_CATEGORIES = ["food", "ride", "parcel", "grocery"]
ORDER_URGENCIES = ["urgent", "normal", "low"]
LEGACY_SHIPPER_GROUPS = {
    "standard": "on_demand",
    "priority": "warehouse",
}
SHIPPER_GROUP_POLICIES = {
    "on_demand": {"profile": "on_demand", "categories": ("food", "ride")},
    "warehouse": {"profile": "warehouse", "categories": ("parcel", "grocery")},
}
SHIPPER_GROUP_DESCRIPTIONS = {
    "on_demand": "Shipper di don/cuoc le",
    "warehouse": "Shipper lay hang tu warehouse W1",
}


def normalize_shipper_group(shipper_group: str | None) -> str | None:
    if shipper_group is None:
        return None
    return LEGACY_SHIPPER_GROUPS.get(shipper_group, shipper_group)


def shipper_operation_profile(user: UserPublic) -> str:
    if user.role == "admin":
        return "warehouse"
    group = normalize_shipper_group(user.shipperGroup)
    return str(SHIPPER_GROUP_POLICIES.get(group or "", {}).get("profile", "on_demand"))


def allowed_order_categories(user: UserPublic) -> tuple[str, ...]:
    if user.role == "admin":
        return ("parcel", "grocery")
    policy = SHIPPER_GROUP_POLICIES.get(normalize_shipper_group(user.shipperGroup) or "")
    return tuple(policy["categories"]) if policy else ()


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS shipper_groups (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'shipper')),
                shipper_group TEXT REFERENCES shipper_groups(name)
            );
            CREATE TABLE IF NOT EXISTS algorithm_permissions (
                shipper_group TEXT NOT NULL,
                algorithm_group TEXT NOT NULL,
                algorithm_name TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                PRIMARY KEY (shipper_group, algorithm_name)
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                urgency TEXT NOT NULL,
                pickup_node_id TEXT NOT NULL,
                dropoff_node_id TEXT NOT NULL,
                demand_kg REAL NOT NULL,
                priority INTEGER NOT NULL,
                due_min INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'available'
            );
            CREATE TABLE IF NOT EXISTS shipper_order_assignments (
                user_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                accepted_at INTEGER NOT NULL,
                delivered_at INTEGER,
                PRIMARY KEY (user_id, order_id)
            );
            CREATE TABLE IF NOT EXISTS maps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                algorithm_group TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                scenario_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """
        )
        assignment_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(shipper_order_assignments)").fetchall()
        }
        if "delivered_at" not in assignment_columns:
            db.execute("ALTER TABLE shipper_order_assignments ADD COLUMN delivered_at INTEGER")
        seed_demo_data(db)
        seed_demo_maps(db)
        db.execute(
            """
            UPDATE orders
            SET status = 'accepted'
            WHERE status = 'available'
            AND id IN (
                SELECT order_id FROM shipper_order_assignments WHERE delivered_at IS NULL
            )
            """
        )


def seed_demo_maps(db: sqlite3.Connection) -> None:
    scenario_json = json.dumps(load_osm_cached_scenario().model_dump(), ensure_ascii=False, separators=(",", ":"))
    now = int(time.time())
    groups = [
        ("uninformed", "Uninformed baseline map", "Graph demo cho BFS va DFS."),
        ("informed", "Informed heuristic map", "Graph demo cho A* va Greedy Best-First."),
        ("local_search", "Local delivery map", "Graph demo cho nhom toi uu lo trinh giao hang."),
        ("complex", "Partial observability map", "Graph demo cho su kien an va re-plan."),
        ("csp", "CSP constraint map", "Graph demo cho rang buoc tai trong va lich giao."),
        ("adversarial", "Adversarial disruption map", "Graph demo cho route robust truoc canh tranh."),
        ("shipper", "Shipper dispatch map", "Graph van hanh live cho shipper."),
    ]
    for group, name, description in groups:
        exists = db.execute("SELECT 1 FROM maps WHERE algorithm_group = ? LIMIT 1", (group,)).fetchone()
        if exists:
            default_exists = db.execute(
                "SELECT 1 FROM maps WHERE algorithm_group = ? AND is_default = 1 LIMIT 1",
                (group,),
            ).fetchone()
            if not default_exists:
                first = db.execute(
                    "SELECT id FROM maps WHERE algorithm_group = ? ORDER BY id LIMIT 1",
                    (group,),
                ).fetchone()
                if first:
                    db.execute("UPDATE maps SET is_default = 1 WHERE id = ?", (first["id"],))
            continue
        db.execute(
            """
            INSERT INTO maps(name, description, algorithm_group, is_default, scenario_json, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (name, description, group, scenario_json, now, now),
        )


def seed_demo_data(db: sqlite3.Connection) -> None:
    db.executemany(
        "INSERT OR IGNORE INTO shipper_groups(name, description) VALUES (?, ?)",
        list(SHIPPER_GROUP_DESCRIPTIONS.items()),
    )
    for legacy, current in LEGACY_SHIPPER_GROUPS.items():
        db.execute("UPDATE users SET shipper_group = ? WHERE shipper_group = ?", (current, legacy))
    db.execute(
        f"DELETE FROM algorithm_permissions WHERE shipper_group IN ({','.join('?' for _ in LEGACY_SHIPPER_GROUPS)})",
        list(LEGACY_SHIPPER_GROUPS),
    )
    db.execute(
        f"DELETE FROM shipper_groups WHERE name IN ({','.join('?' for _ in LEGACY_SHIPPER_GROUPS)})",
        list(LEGACY_SHIPPER_GROUPS),
    )
    for username, password, role, group in [
        ("admin", "admin123", "admin", None),
        ("shipper_a", "shipper123", "shipper", "on_demand"),
        ("shipper_b", "shipper123", "shipper", "warehouse"),
        ("shipper_on_demand", "shipper123", "shipper", "on_demand"),
        ("shipper_warehouse", "shipper123", "shipper", "warehouse"),
    ]:
        db.execute(
            "INSERT OR IGNORE INTO users(username, password_hash, role, shipper_group) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, group),
        )
        db.execute("UPDATE users SET role = ?, shipper_group = ? WHERE username = ?", (role, group, username))
    for group in SHIPPER_GROUP_POLICIES:
        for name, algorithm_group in ALGORITHM_GROUPS.items():
            enabled = 1 if group == "warehouse" or name in STANDARD_DEFAULT_ALGORITHMS else 0
            db.execute(
                """
                INSERT INTO algorithm_permissions(shipper_group, algorithm_group, algorithm_name, enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(shipper_group, algorithm_name)
                DO UPDATE SET algorithm_group = excluded.algorithm_group
                """,
                (group, algorithm_group, name, enabled),
            )
    db.executemany(
        "UPDATE algorithm_permissions SET enabled = 1 WHERE shipper_group = 'on_demand' AND algorithm_name = ?",
        [(name,) for name in STANDARD_DEFAULT_ALGORITHMS],
    )
    scenario = load_osm_cached_scenario()
    for order in scenario.orders:
        db.execute(
            """
            INSERT OR IGNORE INTO orders(id, category, urgency, pickup_node_id, dropoff_node_id, demand_kg, priority, due_min)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.id,
                order.category,
                order.urgency,
                order.pickup_node_id or scenario.depot_id,
                order.dropoff_node_id or order.node_id,
                order.demand_kg,
                order.priority,
                order.due_min,
            ),
        )
    db.execute(
        "UPDATE orders SET pickup_node_id = ? WHERE category IN ('parcel', 'grocery')",
        (scenario.depot_id,),
    )
    ensure_available_pool(db, MIN_AVAILABLE_ORDERS, None, None)


def _order_status_case() -> str:
    return "CASE urgency WHEN 'urgent' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, priority DESC, due_min"


def _row_to_available_order(row: sqlite3.Row) -> AvailableOrder:
    return AvailableOrder(
        id=row["id"],
        category=row["category"],
        urgency=row["urgency"],
        pickupNodeId=row["pickup_node_id"],
        dropoffNodeId=row["dropoff_node_id"],
        demandKg=row["demand_kg"],
        priority=row["priority"],
        dueMin=row["due_min"],
        status=row["status"],
    )


def _count_available_for_user(
    db: sqlite3.Connection,
    user_id: int,
    category: str | None,
    urgency: str | None,
) -> int:
    query = """
        SELECT COUNT(*) AS count FROM orders o
        WHERE o.status = 'available'
        AND NOT EXISTS (
            SELECT 1 FROM shipper_order_assignments a WHERE a.order_id = o.id AND a.user_id = ?
        )
    """
    params: list[Any] = [user_id]
    if category:
        query += " AND o.category = ?"
        params.append(category)
    if urgency:
        query += " AND o.urgency = ?"
        params.append(urgency)
    return int(db.execute(query, params).fetchone()["count"])


def _random_order_payload(category: str | None = None, urgency: str | None = None) -> dict[str, Any]:
    scenario = load_osm_cached_scenario()
    rng = random.Random(time.time_ns())
    pickup_candidates = [scenario.depot_id] + [node.id for node in scenario.nodes if node.type in {"landmark", "intersection"}]
    dropoff_candidates = [node.id for node in scenario.nodes if node.type == "order"]
    if not dropoff_candidates:
        dropoff_candidates = [node.id for node in scenario.nodes if node.id != scenario.depot_id]
    selected_category = category or rng.choices(ORDER_CATEGORIES, weights=[4, 3, 3, 2], k=1)[0]
    selected_urgency = urgency or rng.choices(ORDER_URGENCIES, weights=[3, 5, 2], k=1)[0]
    pickup = scenario.depot_id if selected_category in {"parcel", "grocery"} else rng.choice(
        [node_id for node_id in pickup_candidates if node_id != scenario.depot_id] or pickup_candidates
    )
    dropoff = rng.choice([node for node in dropoff_candidates if node != pickup] or dropoff_candidates)
    category_priority = {"ride": 5, "food": 5, "parcel": 3, "grocery": 2}
    urgency_due = {"urgent": rng.randint(25, 45), "normal": rng.randint(50, 75), "low": rng.randint(80, 105)}
    demand = 1.0 if selected_category == "ride" else round(rng.uniform(1.5, 6.0), 1)
    order_suffix = f"{int(time.time() * 1000)}{rng.randint(100, 999)}"
    return {
        "id": f"R{order_suffix}",
        "category": selected_category,
        "urgency": selected_urgency,
        "pickup_node_id": pickup,
        "dropoff_node_id": dropoff,
        "demand_kg": demand,
        "priority": category_priority[selected_category],
        "due_min": urgency_due[selected_urgency],
    }


def create_random_orders(
    db: sqlite3.Connection,
    count: int,
    category: str | None = None,
    urgency: str | None = None,
) -> list[AvailableOrder]:
    created: list[AvailableOrder] = []
    for _ in range(max(0, count)):
        payload = _random_order_payload(category, urgency)
        while db.execute("SELECT 1 FROM orders WHERE id = ?", (payload["id"],)).fetchone():
            payload = _random_order_payload(category, urgency)
        db.execute(
            """
            INSERT INTO orders(id, category, urgency, pickup_node_id, dropoff_node_id, demand_kg, priority, due_min)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                payload["category"],
                payload["urgency"],
                payload["pickup_node_id"],
                payload["dropoff_node_id"],
                payload["demand_kg"],
                payload["priority"],
                payload["due_min"],
            ),
        )
        row = db.execute("SELECT * FROM orders WHERE id = ?", (payload["id"],)).fetchone()
        created.append(_row_to_available_order(row))
    return created


def ensure_available_pool(
    db: sqlite3.Connection,
    minimum: int,
    category: str | None,
    urgency: str | None,
    user_id: int | None = None,
) -> None:
    if user_id is None:
        query = "SELECT COUNT(*) AS count FROM orders WHERE status = 'available'"
        params: list[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if urgency:
            query += " AND urgency = ?"
            params.append(urgency)
        current = int(db.execute(query, params).fetchone()["count"])
    else:
        current = _count_available_for_user(db, user_id, category, urgency)
    if current < minimum:
        create_random_orders(db, minimum - current, category, urgency)


def _minimum_per_category(categories: tuple[str, ...]) -> int:
    return (MIN_AVAILABLE_ORDERS + len(categories) - 1) // len(categories)


def _ensure_user_pool(
    db: sqlite3.Connection,
    categories: tuple[str, ...],
    urgency: str | None,
    user_id: int,
) -> None:
    minimum = _minimum_per_category(categories)
    for category in categories:
        ensure_available_pool(db, minimum, category, urgency, user_id)


def _accepted_order_rows(user: UserPublic) -> list[sqlite3.Row]:
    with get_connection() as db:
        return db.execute(
            """
            SELECT o.* FROM orders o
            JOIN shipper_order_assignments a ON a.order_id = o.id
            WHERE a.user_id = ? AND a.delivered_at IS NULL AND o.status = 'accepted'
            ORDER BY a.accepted_at, o.priority DESC
            """,
            (user.id,),
        ).fetchall()


def _allowed_accepted_rows(user: UserPublic) -> list[sqlite3.Row]:
    allowed_categories = set(allowed_order_categories(user))
    return [row for row in _accepted_order_rows(user) if row["category"] in allowed_categories]


def _forbidden_order_ids(
    db: sqlite3.Connection,
    order_ids: list[str],
    allowed_categories: tuple[str, ...],
) -> list[str]:
    if not order_ids:
        return []
    placeholders = ",".join("?" for _ in order_ids)
    rows = db.execute(f"SELECT id, category FROM orders WHERE id IN ({placeholders})", order_ids).fetchall()
    return [row["id"] for row in rows if row["category"] not in allowed_categories]


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_text, digest_text = stored.split("$")
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(actual, expected)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def create_token(user: UserPublic, expires_seconds: int = 24 * 60 * 60) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "shipperGroup": user.shipperGroup,
        "exp": int(time.time()) + expires_seconds,
    }
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}.{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header_text, payload_text, signature_text = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token khong hop le") from exc
    signing_input = f"{header_text}.{payload_text}"
    expected = _b64url(hmac.new(SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, signature_text):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chu ky token khong hop le")
    payload = json.loads(_b64url_decode(payload_text))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token da het han")
    return payload


def row_to_user(row: sqlite3.Row) -> UserPublic:
    return UserPublic(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        shipperGroup=normalize_shipper_group(row["shipper_group"]),
    )


def authenticate(username: str, password: str) -> UserPublic:
    with get_connection() as db:
        row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai ten dang nhap hoac mat khau")
    return row_to_user(row)


def get_current_user(authorization: str | None = Header(default=None)) -> UserPublic:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Can dang nhap")
    payload = decode_token(authorization.split(" ", 1)[1])
    with get_connection() as db:
        row = db.execute("SELECT * FROM users WHERE id = ?", (int(payload["sub"]),)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nguoi dung khong ton tai")
    return row_to_user(row)


def require_admin(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chi admin duoc phep thuc hien thao tac nay")
    return user


def assert_algorithm_allowed(user: UserPublic, algorithm_name: str) -> None:
    if user.role == "admin":
        return
    shipper_group = normalize_shipper_group(user.shipperGroup)
    if shipper_group is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Shipper chua duoc gan nhom")
    with get_connection() as db:
        row = db.execute(
            "SELECT enabled FROM algorithm_permissions WHERE shipper_group = ? AND algorithm_name = ?",
            (shipper_group, algorithm_name),
        ).fetchone()
    if row is None or not bool(row["enabled"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Nhom {shipper_group} chua duoc bat thuat toan {algorithm_name}",
        )


def list_permissions() -> list[PermissionRow]:
    active_names = tuple(ACTIVE_ALGORITHM_GROUPS)
    placeholders = ",".join("?" for _ in active_names)
    with get_connection() as db:
        rows = db.execute(
            f"SELECT shipper_group, algorithm_group, algorithm_name, enabled FROM algorithm_permissions "
            f"WHERE algorithm_name IN ({placeholders}) ORDER BY shipper_group, algorithm_group, algorithm_name",
            active_names,
        ).fetchall()
    return [
        PermissionRow(
            shipperGroup=row["shipper_group"],
            algorithmGroup=row["algorithm_group"],
            algorithmName=row["algorithm_name"],
            enabled=bool(row["enabled"]),
        )
        for row in rows
    ]


def update_permission(shipper_group: str, algorithm_group: str, algorithm_name: str, enabled: bool) -> PermissionRow:
    shipper_group = normalize_shipper_group(shipper_group) or shipper_group
    with get_connection() as db:
        db.execute(
            """
            INSERT INTO algorithm_permissions(shipper_group, algorithm_group, algorithm_name, enabled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(shipper_group, algorithm_name)
            DO UPDATE SET algorithm_group = excluded.algorithm_group, enabled = excluded.enabled
            """,
            (shipper_group, algorithm_group, algorithm_name, int(enabled)),
        )
    return PermissionRow(
        shipperGroup=shipper_group,
        algorithmGroup=algorithm_group,
        algorithmName=algorithm_name,
        enabled=enabled,
    )


def list_users() -> list[UserPublic]:
    with get_connection() as db:
        rows = db.execute("SELECT * FROM users ORDER BY role, username").fetchall()
    return [row_to_user(row) for row in rows]


def update_user_group(user_id: int, shipper_group: str) -> UserPublic:
    shipper_group = normalize_shipper_group(shipper_group) or shipper_group
    with get_connection() as db:
        db.execute("UPDATE users SET shipper_group = ? WHERE id = ?", (shipper_group, user_id))
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay user")
    return row_to_user(row)


def register_user(username: str, password: str, role: str, shipper_group: str | None) -> UserPublic:
    shipper_group = normalize_shipper_group(shipper_group)
    try:
        with get_connection() as db:
            cursor = db.execute(
                "INSERT INTO users(username, password_hash, role, shipper_group) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), role, shipper_group),
            )
            row = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username da ton tai") from exc
    return row_to_user(row)


def list_available_orders(category: str | None, urgency: str | None, user: UserPublic) -> list[AvailableOrder]:
    allowed_categories = allowed_order_categories(user)
    if not allowed_categories or (category and category not in allowed_categories):
        return []
    with get_connection() as db:
        if category:
            ensure_available_pool(db, MIN_AVAILABLE_ORDERS, category, urgency, user.id)
        else:
            _ensure_user_pool(db, allowed_categories, urgency, user.id)
    scenario_nodes = {node.id for node in load_osm_cached_scenario().nodes}
    query = """
        SELECT o.* FROM orders o
        WHERE o.status = 'available'
        AND NOT EXISTS (
            SELECT 1 FROM shipper_order_assignments a WHERE a.order_id = o.id AND a.user_id = ?
        )
    """
    params: list[Any] = [user.id]
    if category:
        query += " AND o.category = ?"
        params.append(category)
    else:
        placeholders = ",".join("?" for _ in allowed_categories)
        query += f" AND o.category IN ({placeholders})"
        params.extend(allowed_categories)
    if urgency:
        query += " AND o.urgency = ?"
        params.append(urgency)
    query += f" ORDER BY {_order_status_case()} LIMIT 30"
    with get_connection() as db:
        rows = db.execute(query, params).fetchall()
    orders = [_row_to_available_order(row) for row in rows]
    return [
        order
        for order in orders
        if order.pickupNodeId in scenario_nodes and order.dropoffNodeId in scenario_nodes
    ]


def accept_orders(order_ids: list[str], user: UserPublic) -> list[AvailableOrder]:
    allowed_categories = allowed_order_categories(user)
    if not allowed_categories:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Shipper chua co nhom don hang hop le")
    now = int(time.time())
    accepted_count = 0
    with get_connection() as db:
        forbidden = _forbidden_order_ids(db, order_ids, allowed_categories)
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Don hang khong thuoc nhom van hanh cua shipper: " + ", ".join(forbidden),
            )
        placeholders = ",".join("?" for _ in order_ids)
        rows = (
            db.execute(
                f"SELECT id, status FROM orders WHERE id IN ({placeholders})",
                order_ids,
            ).fetchall()
            if order_ids
            else []
        )
        found_ids = {row["id"] for row in rows}
        missing = [order_id for order_id in order_ids if order_id not in found_ids]
        unavailable = [row["id"] for row in rows if row["status"] != "available"]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khong tim thay don hang: " + ", ".join(missing),
            )
        if unavailable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Don hang da duoc nhan hoac da giao: " + ", ".join(unavailable),
            )
        for order_id in order_ids:
            updated = db.execute(
                "UPDATE orders SET status = 'accepted' WHERE id = ? AND status = 'available'",
                (order_id,),
            )
            if updated.rowcount != 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Don hang {order_id} vua duoc shipper khac nhan",
                )
            db.execute(
                """
                INSERT INTO shipper_order_assignments(user_id, order_id, accepted_at, delivered_at)
                VALUES (?, ?, ?, NULL)
                ON CONFLICT(user_id, order_id)
                DO UPDATE SET accepted_at = excluded.accepted_at, delivered_at = NULL
                """,
                (user.id, order_id, now),
            )
            accepted_count += 1
        if accepted_count:
            for index in range(accepted_count):
                create_random_orders(db, 1, allowed_categories[index % len(allowed_categories)])
        _ensure_user_pool(db, allowed_categories, None, user.id)
    return [_row_to_available_order(row) for row in _allowed_accepted_rows(user)]


def accepted_order_ids(user: UserPublic) -> list[str]:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT order_id FROM shipper_order_assignments
            WHERE user_id = ? AND delivered_at IS NULL
            ORDER BY accepted_at
            """,
            (user.id,),
        ).fetchall()
    return [row["order_id"] for row in rows]


def list_accepted_orders(user: UserPublic) -> list[AvailableOrder]:
    return [_row_to_available_order(row) for row in _allowed_accepted_rows(user)]


def complete_order(order_id: str, user: UserPublic) -> AvailableOrder:
    now = int(time.time())
    with get_connection() as db:
        row = db.execute(
            """
            SELECT o.* FROM orders o
            JOIN shipper_order_assignments a ON a.order_id = o.id
            WHERE a.user_id = ? AND a.order_id = ?
              AND a.delivered_at IS NULL AND o.status = 'accepted'
            """,
            (user.id, order_id),
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Don hang khong con trong danh sach dang giao",
            )
        db.execute(
            """
            UPDATE shipper_order_assignments
            SET delivered_at = ?
            WHERE user_id = ? AND order_id = ? AND delivered_at IS NULL
            """,
            (now, user.id, order_id),
        )
        db.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order_id,))
        delivered = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return _row_to_available_order(delivered)


def accepted_order_models(user: UserPublic) -> list[Order]:
    return [
        Order(
            id=row["id"],
            node_id=row["dropoff_node_id"],
            pickup_node_id=row["pickup_node_id"],
            dropoff_node_id=row["dropoff_node_id"],
            category=row["category"],
            urgency=row["urgency"],
            demand_kg=row["demand_kg"],
            ready_min=0,
            due_min=row["due_min"],
            service_min=2 if row["category"] == "ride" else 4,
            priority=row["priority"],
        )
        for row in _allowed_accepted_rows(user)
    ]
