from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from fastapi import HTTPException, status

from app.data.scenario import load_osm_cached_scenario
from app.models.schemas import MapCreateRequest, MapDetail, MapPatchRequest, MapSummary, Scenario
from app.services.auth_service import get_connection


def _scenario_json(scenario: Scenario) -> str:
    return json.dumps(scenario.model_dump(), ensure_ascii=False, separators=(",", ":"))


def _scenario_from_row(row: sqlite3.Row) -> Scenario:
    return Scenario(**json.loads(row["scenario_json"]))


def _summary_from_row(row: sqlite3.Row) -> MapSummary:
    scenario = _scenario_from_row(row)
    return MapSummary(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        algorithmGroup=row["algorithm_group"],
        isDefault=bool(row["is_default"]),
        nodeCount=len(scenario.nodes),
        edgeCount=len(scenario.edges),
        updatedAt=row["updated_at"],
    )


def _detail_from_row(row: sqlite3.Row) -> MapDetail:
    summary = _summary_from_row(row)
    return MapDetail(**summary.model_dump(), scenario=_scenario_from_row(row))


def _fetch_map(db: sqlite3.Connection, map_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM maps WHERE id = ?", (map_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay map")
    return row


def _clear_group_default(db: sqlite3.Connection, algorithm_group: str) -> None:
    db.execute("UPDATE maps SET is_default = 0 WHERE algorithm_group = ?", (algorithm_group,))


def _ensure_group_default(db: sqlite3.Connection, algorithm_group: str) -> None:
    default_exists = db.execute(
        "SELECT 1 FROM maps WHERE algorithm_group = ? AND is_default = 1 LIMIT 1",
        (algorithm_group,),
    ).fetchone()
    if default_exists:
        return
    first = db.execute(
        "SELECT id FROM maps WHERE algorithm_group = ? ORDER BY id LIMIT 1",
        (algorithm_group,),
    ).fetchone()
    if first:
        db.execute("UPDATE maps SET is_default = 1 WHERE id = ?", (first["id"],))


def list_maps() -> list[MapSummary]:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT * FROM maps
            ORDER BY algorithm_group, is_default DESC, name COLLATE NOCASE, id
            """
        ).fetchall()
    return [_summary_from_row(row) for row in rows]


def get_map(map_id: int) -> MapDetail:
    with get_connection() as db:
        return _detail_from_row(_fetch_map(db, map_id))


def default_map_for_group(algorithm_group: str) -> MapDetail:
    with get_connection() as db:
        row = db.execute(
            """
            SELECT * FROM maps
            WHERE algorithm_group = ?
            ORDER BY is_default DESC, id
            LIMIT 1
            """,
            (algorithm_group,),
        ).fetchone()
        if row is None:
            row = db.execute(
                """
                SELECT * FROM maps
                ORDER BY is_default DESC, id
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            scenario = load_osm_cached_scenario()
            return MapDetail(
                id=0,
                name="OSM fallback map",
                description="Map mac dinh khi database chua co ban ghi.",
                algorithmGroup=algorithm_group,
                isDefault=True,
                nodeCount=len(scenario.nodes),
                edgeCount=len(scenario.edges),
                updatedAt=int(time.time()),
                scenario=scenario,
            )
        return _detail_from_row(row)


def selected_map_for_group(algorithm_group: str, map_id: int | None) -> MapDetail:
    if map_id:
        return get_map(map_id)
    return default_map_for_group(algorithm_group)


def create_map(request: MapCreateRequest) -> MapDetail:
    scenario = request.scenario or load_osm_cached_scenario()
    now = int(time.time())
    with get_connection() as db:
        has_group_map = db.execute(
            "SELECT 1 FROM maps WHERE algorithm_group = ? LIMIT 1",
            (request.algorithmGroup,),
        ).fetchone()
        is_default = request.isDefault or has_group_map is None
        if is_default:
            _clear_group_default(db, request.algorithmGroup)
        cursor = db.execute(
            """
            INSERT INTO maps(name, description, algorithm_group, is_default, scenario_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.name.strip(),
                request.description.strip(),
                request.algorithmGroup,
                int(is_default),
                _scenario_json(scenario),
                now,
                now,
            ),
        )
        row = _fetch_map(db, int(cursor.lastrowid))
    return _detail_from_row(row)


def update_map(map_id: int, request: MapPatchRequest) -> MapDetail:
    changes: dict[str, Any] = {}
    if request.name is not None:
        changes["name"] = request.name.strip()
    if request.description is not None:
        changes["description"] = request.description.strip()
    if request.algorithmGroup is not None:
        changes["algorithm_group"] = request.algorithmGroup
    if request.scenario is not None:
        changes["scenario_json"] = _scenario_json(request.scenario)
    if request.isDefault is not None:
        changes["is_default"] = int(request.isDefault)
    if not changes:
        return get_map(map_id)

    with get_connection() as db:
        current = _fetch_map(db, map_id)
        next_group = str(changes.get("algorithm_group", current["algorithm_group"]))
        if changes.get("is_default") == 1:
            _clear_group_default(db, next_group)
        changes["updated_at"] = int(time.time())
        assignments = ", ".join(f"{column} = ?" for column in changes)
        db.execute(
            f"UPDATE maps SET {assignments} WHERE id = ?",
            [*changes.values(), map_id],
        )
        if request.algorithmGroup is not None:
            _ensure_group_default(db, current["algorithm_group"])
        _ensure_group_default(db, next_group)
        row = _fetch_map(db, map_id)
    return _detail_from_row(row)


def delete_map(map_id: int) -> None:
    with get_connection() as db:
        row = _fetch_map(db, map_id)
        group = row["algorithm_group"]
        db.execute("DELETE FROM maps WHERE id = ?", (map_id,))
        _ensure_group_default(db, group)
