"""SQLite storage for readings (standard library only)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config

COLUMNS = ["station_id", "timestamp", "pm25", "pm10", "so2", "co", "o3", "no2"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    pm25 REAL, pm10 REAL, so2 REAL, co REAL, o3 REAL, no2 REAL
);
CREATE INDEX IF NOT EXISTS idx_readings_station_time ON readings (station_id, timestamp);
"""


def db_path() -> Path:
    return config.DB_PATH


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def to_iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds")


def insert_readings(rows: list[dict]) -> int:
    data = [tuple(to_iso(r[c]) if c == "timestamp" else r.get(c) for c in COLUMNS) for r in rows]
    with connect() as conn:
        conn.executemany(
            f"INSERT INTO readings ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
            data)
    return len(data)


def count() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]


def latest_by_station() -> dict[str, dict]:
    sql = """
        SELECT r.* FROM readings r
        JOIN (SELECT station_id, MAX(timestamp) AS ts FROM readings GROUP BY station_id) m
          ON r.station_id = m.station_id AND r.timestamp = m.ts
    """
    with connect() as conn:
        return {row["station_id"]: dict(row) for row in conn.execute(sql)}


def history(station_id: str | None = None, hours: int = 72, end: datetime | None = None) -> list[dict]:
    """Readings from the `hours` before `end` (default now), oldest first."""
    since = to_iso((end or datetime.now(timezone.utc)) - timedelta(hours=hours))
    sql = "SELECT * FROM readings WHERE timestamp > ?"
    args: list = [since]
    if end is not None:
        sql += " AND timestamp <= ?"
        args.append(to_iso(end))
    if station_id:
        sql += " AND station_id = ?"
        args.append(station_id)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY timestamp, id", args)]
