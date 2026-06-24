from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB = Path(__file__).resolve().parents[1] / "src" / "app" / "data" / "fyp.sqlite"


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"Không tìm thấy database: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def table_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(row["name"]) for row in rows]


def table_summary(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    summary = []
    for table in table_names(connection):
        count = connection.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()["count"]
        summary.append({"table": table, "rows": count})
    return summary


def table_rows(connection: sqlite3.Connection, table: str, limit: int) -> list[dict[str, Any]]:
    available = table_names(connection)
    if table not in available:
        raise SystemExit(f"Bảng không tồn tại: {table}. Các bảng hiện có: {', '.join(available)}")
    rows = connection.execute(f'SELECT * FROM "{table}" LIMIT ?', (limit,)).fetchall()
    return [dict(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Xem dữ liệu SQLite của Find Your Path.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Đường dẫn tới file SQLite.")
    parser.add_argument("--table", help="Tên bảng cần xem. Bỏ trống để xem danh sách bảng.")
    parser.add_argument("--limit", type=int, default=20, help="Số dòng tối đa cần hiển thị.")
    args = parser.parse_args()

    with connect(args.db) as connection:
        data = table_rows(connection, args.table, max(1, args.limit)) if args.table else table_summary(connection)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
