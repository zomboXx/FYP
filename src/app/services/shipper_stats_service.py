from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from app.algorithms.search import astar
from app.data.scenario import load_osm_cached_scenario
from app.models.schemas import FatigueWarning, ShipperStats, UserPublic
from app.services.auth_service import get_connection


def _period_starts(now: int) -> tuple[int, int]:
    current = datetime.fromtimestamp(now)
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(day_start.timestamp()), int(month_start.timestamp())


def _percent(part: int, total: int) -> float:
    return round((part / total) * 100, 1) if total else 0.0


def _delivery_route_metrics(pickup_node_id: str, dropoff_node_id: str) -> tuple[float, int]:
    scenario = load_osm_cached_scenario()
    if pickup_node_id == dropoff_node_id:
        return 0.0, 0
    result = astar(scenario, pickup_node_id, dropoff_node_id)
    if not result.path:
        return 0.0, 0
    return float(result.distance_km), int(round(float(result.total_minutes) * 60))


def _finished_rows(user_id: int, since: int) -> list[dict[str, Any]]:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT
                a.accepted_at,
                a.delivery_started_at,
                a.delivered_at,
                a.failed_at,
                a.finished_at,
                a.outcome,
                o.pickup_node_id,
                o.dropoff_node_id,
                o.due_min
            FROM shipper_order_assignments a
            JOIN orders o ON o.id = a.order_id
            WHERE a.user_id = ? AND a.finished_at IS NOT NULL AND a.finished_at >= ?
            """,
            (user_id, since),
        ).fetchall()
    return [dict(row) for row in rows]


def _session_seconds(user_id: int, since: int, now: int) -> int:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT opened_at, closed_at FROM app_sessions
            WHERE user_id = ? AND COALESCE(closed_at, ?) > ?
            """,
            (user_id, now, since),
        ).fetchall()
    total = 0
    for row in rows:
        opened = max(int(row["opened_at"]), since)
        closed = min(int(row["closed_at"] or now), now)
        total += max(0, closed - opened)
    return total


def _summarize_finished(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = 0
    failed = 0
    late = 0
    delivery_seconds = 0
    estimated_delivery_seconds = 0
    distance_km = 0.0
    for row in rows:
        finished_at = int(row["finished_at"])
        started_at = int(row["delivery_started_at"] or row["accepted_at"])
        duration = max(0, finished_at - started_at)
        delivery_seconds += duration
        if row["outcome"] == "delivered" or row["delivered_at"]:
            completed += 1
        else:
            failed += 1
        if duration > int(row["due_min"]) * 60:
            late += 1
        order_distance_km, order_estimated_seconds = _delivery_route_metrics(row["pickup_node_id"], row["dropoff_node_id"])
        distance_km += order_distance_km
        estimated_delivery_seconds += order_estimated_seconds
    total = completed + failed
    return {
        "completed": completed,
        "failed": failed,
        "finished": total,
        "late": late,
        "delivery_seconds": delivery_seconds,
        "estimated_delivery_seconds": estimated_delivery_seconds,
        "distance_km": round(distance_km, 2),
    }


def _fatigue_warning(app_open_seconds: int, delivery_seconds: int) -> FatigueWarning:
    delivery_hours = delivery_seconds / 3600
    app_hours = app_open_seconds / 3600
    if delivery_hours >= 10 or app_hours >= 12:
        return FatigueWarning(
            level="danger",
            message="Bạn đã làm việc rất lâu hôm nay. Nên dừng nhận đơn và nghỉ ngơi để đảm bảo an toàn.",
        )
    if delivery_hours >= 8 or app_hours >= 10:
        return FatigueWarning(
            level="warning",
            message="Thời gian làm việc hôm nay đang cao. Hãy cân nhắc nghỉ ngắn trước khi nhận thêm đơn.",
        )
    if delivery_hours >= 4:
        return FatigueWarning(
            level="info",
            message="Bạn đã giao hàng liên tục khá lâu. Uống nước và nghỉ vài phút nếu thấy mệt.",
        )
    return FatigueWarning(level="ok", message="Thời gian làm việc hiện tại vẫn ổn định.")


def shipper_stats(user: UserPublic) -> ShipperStats:
    now = int(time.time())
    day_start, month_start = _period_starts(now)
    today = _summarize_finished(_finished_rows(user.id, day_start))
    month = _summarize_finished(_finished_rows(user.id, month_start))
    app_open_today = _session_seconds(user.id, day_start, now)
    app_open_month = _session_seconds(user.id, month_start, now)
    return ShipperStats(
        appOpenSecondsToday=app_open_today,
        appOpenSecondsMonth=app_open_month,
        deliverySecondsToday=today["delivery_seconds"],
        deliverySecondsMonth=month["delivery_seconds"],
        estimatedDeliverySecondsToday=today["estimated_delivery_seconds"],
        estimatedDeliverySecondsMonth=month["estimated_delivery_seconds"],
        completedOrdersToday=today["completed"],
        completedOrdersMonth=month["completed"],
        failedOrdersToday=today["failed"],
        failedOrdersMonth=month["failed"],
        finishedOrdersToday=today["finished"],
        finishedOrdersMonth=month["finished"],
        lateOrdersToday=today["late"],
        lateOrdersMonth=month["late"],
        distanceKmToday=today["distance_km"],
        distanceKmMonth=month["distance_km"],
        successRate=_percent(today["completed"], today["finished"]),
        lateOrderRate=_percent(today["late"], today["finished"]),
        fatigueWarning=_fatigue_warning(app_open_today, max(today["delivery_seconds"], today["estimated_delivery_seconds"])),
    )
