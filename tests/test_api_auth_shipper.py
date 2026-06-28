from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_connection, load_db_path, load_jwt_secret


client = TestClient(app)


def login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["accessToken"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_jwt_secret_is_required_on_vercel():
    with pytest.raises(RuntimeError):
        load_jwt_secret({"VERCEL": "1"})
    assert load_jwt_secret({"VERCEL": "1", "FYP_JWT_SECRET": "test-secret"}) == "test-secret"
    assert load_jwt_secret({}) == "fyp-local-demo-secret"


def test_db_path_defaults_to_tmp_on_vercel_and_allows_override():
    assert load_db_path({}).as_posix().endswith("src/app/data/fyp.sqlite")
    assert load_db_path({"VERCEL": "1"}).as_posix() == "/tmp/fyp.sqlite"
    assert load_db_path({"FYP_DB_PATH": "custom/demo.sqlite"}).as_posix() == "custom/demo.sqlite"


def test_health_endpoint_is_ready():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def clear_shipper_assignments(username: str) -> None:
    with get_connection() as db:
        user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        db.execute(
            """
            UPDATE orders SET status = 'available'
            WHERE id IN (
                SELECT order_id FROM shipper_order_assignments
                WHERE user_id = ? AND delivered_at IS NULL
            )
            """,
            (user["id"],),
        )
        db.execute("DELETE FROM shipper_order_assignments WHERE user_id = ?", (user["id"],))


def test_auth_login_and_me():
    token = login("admin", "admin123")
    response = client.get("/api/auth/me", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_root_serves_python_owned_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "FYP Delivery" in response.text
    assert "flutter_bootstrap.js" in response.text

    bootstrap = client.get("/flutter_bootstrap.js")
    assert bootstrap.status_code == 200


def test_map_route_serves_leaflet_world_map():
    response = client.get("/map?path=W1,A4,D1&start=W1&goal=D1")
    assert response.status_code == 200
    assert "FYP Delivery / Live Map" in response.text
    assert "leaflet@1.9.4" in response.text
    assert "W1" in response.text
    assert "D1" in response.text
    assert "draggable: true" in response.text
    assert "manual-save" in response.text
    assert "manual-delete" in response.text
    assert "toggle-node-place" in response.text
    assert "edge-source" in response.text
    assert "set-edge" in response.text
    assert "copy-graph" in response.text


def test_admin_can_create_update_delete_maps_and_live_map_can_select_one():
    admin = login("admin", "admin123")
    listed = client.get("/api/maps", headers=auth(admin))
    assert listed.status_code == 200
    assert {"uninformed", "informed", "local_search", "complex", "csp", "adversarial", "shipper"} <= {
        item["algorithmGroup"] for item in listed.json()
    }

    created = client.post(
        "/api/maps",
        json={
            "name": "CRUD test map",
            "description": "Created by API test",
            "algorithmGroup": "csp",
            "isDefault": False,
        },
        headers=auth(admin),
    )
    assert created.status_code == 200
    map_id = created.json()["id"]
    assert created.json()["nodeCount"] > 0

    updated = client.patch(
        f"/api/maps/{map_id}",
        json={"name": "CRUD test map updated", "isDefault": True},
        headers=auth(admin),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "CRUD test map updated"
    assert updated.json()["isDefault"] is True

    live = client.get(f"/map?group=csp&mapId={map_id}")
    assert live.status_code == 200
    assert "CRUD test map updated" in live.text

    deleted = client.delete(f"/api/maps/{map_id}", headers=auth(admin))
    assert deleted.status_code == 204
    missing = client.get(f"/api/maps/{map_id}", headers=auth(admin))
    assert missing.status_code == 404


def test_admin_permission_can_block_shipper_algorithm():
    admin = login("admin", "admin123")
    shipper = login("shipper_a", "shipper123")
    patch = {
        "shipperGroup": "standard",
        "algorithmGroup": "informed",
        "algorithmName": "greedy",
        "enabled": False,
    }
    assert client.patch("/api/admin/permissions", json=patch, headers=auth(admin)).status_code == 200
    response = client.post(
        "/api/pathfinding/run",
        json={"algorithm": "greedy", "startId": "D0", "goalId": "G", "debug": True},
        headers=auth(shipper),
    )
    assert response.status_code == 403


def test_order_filter_accept_and_shipper_plan_route():
    token = login("shipper_b", "shipper123")
    clear_shipper_assignments("shipper_b")
    available = client.get("/api/orders/available?urgency=urgent", headers=auth(token))
    assert available.status_code == 200
    assert len(available.json()) >= 7
    order_ids = [order["id"] for order in available.json()[:2]]
    assert order_ids
    accepted = client.post("/api/shipper/orders/accept", json={"orderIds": order_ids}, headers=auth(token))
    assert accepted.status_code == 200
    planned = client.post(
        "/api/shipper/routes/plan",
        json={"algorithm": "sideways_hill_climbing", "debug": True},
        headers=auth(token),
    )
    assert planned.status_code == 200
    body = planned.json()
    assert body["path"]
    assert body["traceSteps"]


def test_shipper_plan_requires_accepted_orders():
    token = login("shipper_a", "shipper123")
    clear_shipper_assignments("shipper_a")
    planned = client.post(
        "/api/shipper/routes/plan",
        json={"algorithm": "simple_hill_climbing", "debug": True},
        headers=auth(token),
    )
    assert planned.status_code == 400
    assert "Chua co don hang" in planned.json()["detail"]


def test_accepting_orders_replenishes_available_pool_to_minimum_seven():
    token = login("shipper_a", "shipper123")
    clear_shipper_assignments("shipper_a")
    before = client.get("/api/orders/available", headers=auth(token))
    assert before.status_code == 200
    assert len(before.json()) >= 7
    accepted_ids = [order["id"] for order in before.json()[:3]]
    accepted = client.post("/api/shipper/orders/accept", json={"orderIds": accepted_ids}, headers=auth(token))
    assert accepted.status_code == 200
    after = client.get("/api/orders/available", headers=auth(token))
    assert after.status_code == 200
    assert len(after.json()) >= 7
    assert not set(accepted_ids).intersection({order["id"] for order in after.json()})


def test_shipper_profiles_filter_orders_and_build_routes_from_the_correct_origin():
    on_demand = login("shipper_a", "shipper123")
    depot_delivery = login("shipper_b", "shipper123")
    clear_shipper_assignments("shipper_a")
    clear_shipper_assignments("shipper_b")

    on_demand_orders = client.get("/api/orders/available", headers=auth(on_demand)).json()
    assert len(on_demand_orders) >= 7
    assert {order["category"] for order in on_demand_orders} <= {"food", "ride"}
    accepted = client.post(
        "/api/shipper/orders/accept",
        json={"orderIds": [on_demand_orders[0]["id"]]},
        headers=auth(on_demand),
    )
    assert accepted.status_code == 200
    on_demand_plan = client.post(
        "/api/shipper/routes/plan",
        json={"startId": "A1", "routingStrategy": "nearest_neighbor", "debug": True},
        headers=auth(on_demand),
    ).json()
    assert on_demand_plan["path"][0] == "A1"
    assert on_demand_plan["metrics"]["operationProfile"] == "on_demand"
    assert [leg["kind"] for leg in on_demand_plan["metrics"]["routeLegs"]][-1] == "serve_order"

    depot_orders = client.get("/api/orders/available", headers=auth(depot_delivery)).json()
    assert len(depot_orders) >= 7
    assert {order["category"] for order in depot_orders} <= {"parcel", "grocery"}
    assert len({order["pickupNodeId"] for order in depot_orders}) == 1
    accepted = client.post(
        "/api/shipper/orders/accept",
        json={"orderIds": [order["id"] for order in depot_orders[:3]]},
        headers=auth(depot_delivery),
    )
    assert accepted.status_code == 200
    nearest = client.post(
        "/api/shipper/routes/plan",
        json={"routingStrategy": "nearest_neighbor", "debug": True},
        headers=auth(depot_delivery),
    ).json()
    global_plan = client.post(
        "/api/shipper/routes/plan",
        json={"routingStrategy": "global_optimization", "debug": True},
        headers=auth(depot_delivery),
    ).json()
    assert nearest["path"][0] == depot_orders[0]["pickupNodeId"]
    assert global_plan["metrics"]["operationProfile"] == "depot_delivery"
    assert global_plan["metrics"]["travelMinutes"] <= nearest["metrics"]["travelMinutes"]
    assert all(leg["kind"] == "warehouse_delivery" for leg in global_plan["metrics"]["routeLegs"])


def test_shipper_plan_keeps_duplicate_dropoff_orders_as_separate_legs():
    token = login("shipper_b", "shipper123")
    clear_shipper_assignments("shipper_b")
    order_ids = ["T_DUP_ROUTE_A", "T_DUP_ROUTE_B"]
    with get_connection() as db:
        db.execute(
            f"DELETE FROM shipper_order_assignments WHERE order_id IN ({','.join('?' for _ in order_ids)})",
            order_ids,
        )
        db.execute(f"DELETE FROM orders WHERE id IN ({','.join('?' for _ in order_ids)})", order_ids)
        db.executemany(
            """
            INSERT INTO orders(id, category, urgency, pickup_node_id, dropoff_node_id, demand_kg, priority, due_min, status)
            VALUES (?, 'parcel', 'urgent', 'W1', 'D3', 1.0, 4, 90, 'available')
            """,
            [(order_id,) for order_id in order_ids],
        )
    accepted = client.post("/api/shipper/orders/accept", json={"orderIds": order_ids}, headers=auth(token))
    assert accepted.status_code == 200

    planned = client.post(
        "/api/shipper/routes/plan",
        json={"algorithm": "simple_hill_climbing", "routingStrategy": "nearest_neighbor", "debug": True},
        headers=auth(token),
    )
    assert planned.status_code == 200
    route_legs = planned.json()["metrics"]["routeLegs"]
    assert [leg["orderId"] for leg in route_legs] == order_ids
    assert route_legs[1]["from"] == "D3"
    assert route_legs[1]["to"] == "D3"
    assert route_legs[1]["path"] == ["D3", "D3"]


def test_shipper_confirms_delivery_after_accepting_order():
    token = login("shipper_a", "shipper123")
    clear_shipper_assignments("shipper_a")
    available = client.get("/api/orders/available", headers=auth(token)).json()
    order_id = available[0]["id"]

    accepted = client.post(
        "/api/shipper/orders/accept",
        json={"orderIds": [order_id]},
        headers=auth(token),
    )
    assert accepted.status_code == 200
    assert accepted.json()[0]["status"] == "accepted"

    completed = client.post(
        "/api/shipper/orders/complete",
        json={"orderId": order_id},
        headers=auth(token),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "delivered"

    with get_connection() as db:
        order = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        assignment = db.execute(
            """
            SELECT delivered_at FROM shipper_order_assignments
            WHERE order_id = ? AND user_id = (SELECT id FROM users WHERE username = 'shipper_a')
            """,
            (order_id,),
        ).fetchone()
    assert order["status"] == "delivered"
    assert assignment["delivered_at"] is not None

    repeated = client.post(
        "/api/shipper/orders/complete",
        json={"orderId": order_id},
        headers=auth(token),
    )
    assert repeated.status_code == 404


def test_debug_trace_for_astar_contains_frontier_and_cost():
    token = login("admin", "admin123")
    response = client.post(
        "/api/pathfinding/run",
        json={"algorithm": "astar", "startId": "D0", "goalId": "G", "debug": True},
        headers=auth(token),
    )
    assert response.status_code == 200
    steps = response.json()["traceSteps"]
    assert steps
    assert {"frontier", "visitedNodes", "costSoFar"}.issubset(steps[0].keys())


def test_dynamic_and_adversarial_endpoints_are_demo_ready():
    token = login("admin", "admin123")
    dynamic = client.post(
        "/api/events/simulate",
        json={"eventType": "accident", "debug": True},
        headers=auth(token),
    )
    assert dynamic.status_code == 200
    assert dynamic.json()["metrics"]["replannedPath"]

    adversarial = client.post(
        "/api/adversarial/run",
        json={"algorithm": "minimax", "debug": True},
        headers=auth(token),
    )
    assert adversarial.status_code == 200
    body = adversarial.json()
    assert body["metrics"]["chosenGoal"]
    assert body["metrics"]["worstCaseCost"] > 0
    assert body["metrics"]["expandedNodes"] > 0
    assert body["traceSteps"]


def test_complex_and_csp_endpoints_return_structured_debug_traces():
    token = login("admin", "admin123")
    complex_response = client.post(
        "/api/complex/run",
        json={
            "algorithm": "online_replan",
            "startId": "W1",
            "goalId": "D1",
            "sensorRadius": 1,
            "hiddenEvent": "accident",
            "debug": True,
        },
        headers=auth(token),
    )
    assert complex_response.status_code == 200
    complex_body = complex_response.json()
    assert complex_body["path"][-1] == "D1"
    assert complex_body["metrics"]["observedEdges"]
    assert any(step["debugData"] for step in complex_body["traceSteps"])

    and_or_response = client.post(
        "/api/complex/run",
        json={
            "algorithm": "and_or",
            "startId": "W1",
            "goalId": "D1",
            "sensorRadius": 1,
            "hiddenEvent": "accident",
            "debug": True,
        },
        headers=auth(token),
    )
    assert and_or_response.status_code == 200
    and_or_body = and_or_response.json()
    assert and_or_body["metrics"]["conditionalPlan"]["complete"] is True
    assert and_or_body["metrics"]["conditionalPlan"]["ifDisrupted"]
    assert any(step["phase"] == "AND_ENV_OUTCOME" for step in and_or_body["traceSteps"])

    csp_response = client.post(
        "/api/csp/solve",
        json={"algorithm": "forward_checking", "orderIds": ["O4"], "capacityKg": 22, "debug": True},
        headers=auth(token),
    )
    assert csp_response.status_code == 200
    csp_body = csp_response.json()
    assert csp_body["metrics"]["valid"] is True
    assert csp_body["metrics"]["assignment"]


def test_permissions_show_six_active_groups_and_no_rl_endpoint():
    token = login("admin", "admin123")
    permissions = client.get("/api/admin/permissions", headers=auth(token))
    assert permissions.status_code == 200
    rows = permissions.json()
    groups = {row["algorithmGroup"] for row in rows}
    algorithm_names = {row["algorithmName"] for row in rows}
    assert groups == {"uninformed", "informed", "local_search", "complex", "csp", "adversarial"}
    assert algorithm_names == {
        "bfs",
        "dfs",
        "astar",
        "greedy",
        "simple_hill_climbing",
        "hill_climbing",
        "steepest_ascent",
        "sideways_hill_climbing",
        "random_restart",
        "local_beam",
        "simulated_annealing",
        "backtracking",
        "forward_checking",
        "online_replan",
        "and_or",
        "minimax",
        "alpha_beta",
    }

    openapi = client.get("/openapi.json")
    assert "/api/rl/train" not in openapi.json()["paths"]
    removed = client.post("/api/rl/train", json={"episodes": 2, "debug": False}, headers=auth(token))
    assert removed.status_code in {404, 405}


def test_osm_cache_loads_default_scenario():
    response = client.get("/api/scenario/default")
    assert response.status_code == 200
    body = response.json()
    assert body["nodes"]
    assert any(order["category"] in {"food", "ride"} for order in body["orders"])
