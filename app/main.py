"""REST API (and, once the web/ folder exists, the dashboard).

    uvicorn app.main:app --reload      # then open http://localhost:8000 and /docs

Environment variables:
    AQ_DB             SQLite file (default data/air.db)
    AQ_SIMULATE       1 (default) to add simulated readings every AQ_SIM_INTERVAL seconds
    AQ_SIM_INTERVAL   seconds between simulated readings (default 3600: stations report hourly)
    AQ_API_KEY        if set, POST /api/readings requires the header X-API-Key
"""
import asyncio
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import __version__, db, ispu, simulator
from .config import ALERT_CATEGORY, CATEGORIES, ISPU_BREAKS, POLLUTANTS, STATION_IDS, STATIONS
from .models import ReadingIn

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
ADVICE = {c["key"]: c["advice"] for c in CATEGORIES}


async def simulate_forever(interval: int) -> None:
    rng = random.Random()
    while True:
        await asyncio.sleep(interval)
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        db.insert_readings([simulator.reading(s, now, rng) for s in STATIONS])


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    task = None
    if os.environ.get("AQ_SIMULATE", "1") == "1":
        if db.count() == 0:
            simulator.backfill(hours=72 + ispu.MAX_HOURS)
        task = asyncio.create_task(simulate_forever(int(os.environ.get("AQ_SIM_INTERVAL", "3600"))))
    yield
    if task:
        task.cancel()


app = FastAPI(
    title="Air Quality Monitoring System",
    description="Air quality for Indonesian cities: pollutant readings, the ISPU index "
                "(PermenLHK P.14/2020), health advice and alerts.",
    version=__version__,
    lifespan=lifespan,
)


def latest_scored(station_id: str, latest: dict | None = None) -> dict | None:
    """The newest reading of a station, scored against the history before it."""
    latest = latest or db.latest_by_station().get(station_id)
    if not latest:
        return None
    rows = db.history(station_id, ispu.MAX_HOURS, end=ispu.parse(latest["timestamp"]))
    scored = ispu.score_series(rows)[-1]
    return {**scored, "advice": ADVICE[scored["category"]]}


def scored_history(station_id: str | None, hours: int) -> list[dict]:
    """Scored readings of the last `hours`, using the extra history the averages need."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    scored = ispu.score_series(db.history(station_id, hours + ispu.MAX_HOURS))
    return [r for r in scored if ispu.parse(r["timestamp"]) > since]


def station_view(station: dict, latest: dict | None) -> dict:
    return {**station, "latest": latest_scored(station["id"], latest) if latest else None}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "readings": db.count()}


@app.get("/api/meta")
def meta() -> dict:
    """Pollutants, ISPU breakpoints, categories and health advice, for building a UI."""
    return {
        "regulation": "PermenLHK No. P.14/MENLHK/SETJEN/KUM.1/7/2020",
        "ispu_breaks": ISPU_BREAKS,
        "pollutants": POLLUTANTS,
        "categories": [{**c, "max": None if c["max"] == float("inf") else c["max"]} for c in CATEGORIES],
        "alert_category": ALERT_CATEGORY,
    }


@app.get("/api/stations")
def stations() -> list[dict]:
    latest = db.latest_by_station()
    return [station_view(s, latest.get(s["id"])) for s in STATIONS]


@app.get("/api/stations/{station_id}")
def station(station_id: str) -> dict:
    if station_id not in STATION_IDS:
        raise HTTPException(404, f"unknown station '{station_id}'")
    s = next(s for s in STATIONS if s["id"] == station_id)
    return station_view(s, db.latest_by_station().get(station_id))


@app.get("/api/stations/{station_id}/readings")
def station_readings(station_id: str, hours: int = Query(72, ge=1, le=24 * 30)) -> list[dict]:
    if station_id not in STATION_IDS:
        raise HTTPException(404, f"unknown station '{station_id}'")
    return scored_history(station_id, hours)


@app.get("/api/summary")
def summary() -> dict:
    latest = [latest_scored(sid, r) for sid, r in db.latest_by_station().items()]
    counts = {c["key"]: 0 for c in CATEGORIES}
    dominant: dict[str, int] = {}
    for r in latest:
        counts[r["category"]] += 1
        dominant[r["dominant"]] = dominant.get(r["dominant"], 0) + 1
    worst = max(latest, key=lambda r: r["index"], default=None)
    return {
        "stations": len(STATIONS),
        "reporting": len(latest),
        "category_counts": counts,
        "dominant_counts": dominant,
        "average_index": round(sum(r["index"] for r in latest) / len(latest)) if latest else None,
        "worst": {"station_id": worst["station_id"], "index": worst["index"],
                  "category": worst["category"]} if worst else None,
        "alerts_24h": len(ispu.alerts(scored_history(None, 24))),
    }


@app.get("/api/alerts")
def alerts(hours: int = Query(24, ge=1, le=24 * 30),
           min_category: str = Query(ALERT_CATEGORY,
                                     pattern="^(moderate|unhealthy|very_unhealthy|hazardous)$")) -> list[dict]:
    """Episodes when a station was at or above `min_category` (default: unhealthy)."""
    return ispu.alerts(scored_history(None, hours), min_category)[:200]


@app.post("/api/readings", status_code=201)
def ingest(reading: ReadingIn, x_api_key: str | None = Header(None)) -> dict:
    """Store an hourly reading from a real station and return its ISPU."""
    key = os.environ.get("AQ_API_KEY")
    if key and x_api_key != key:
        raise HTTPException(401, "invalid or missing X-API-Key")
    row = reading.model_dump()
    row["timestamp"] = row["timestamp"] or datetime.now(timezone.utc)
    db.insert_readings([row])
    rows = db.history(row["station_id"], ispu.MAX_HOURS, end=row["timestamp"])
    stored = db.to_iso(row["timestamp"])
    scored = [r for r in ispu.score_series(rows) if r["timestamp"] == stored][-1]
    return {**scored, "advice": ADVICE[scored["category"]]}


if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
