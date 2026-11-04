from fastapi.testclient import TestClient

from app import simulator
from app.config import CATEGORY_KEYS, STATIONS
from app.main import app


def client() -> TestClient:
    simulator.backfill(hours=48)
    return TestClient(app)


def test_health():
    with client() as c:
        body = c.get("/api/health").json()
        assert body["status"] == "ok"
        assert body["readings"] == 49 * len(STATIONS)


def test_meta_lists_breakpoints_and_categories():
    with client() as c:
        body = c.get("/api/meta").json()
        assert body["pollutants"]["pm25"]["breakpoints"][0] == 15.5
        assert [k["key"] for k in body["categories"]] == CATEGORY_KEYS
        assert body["categories"][-1]["max"] is None


def test_stations_have_scored_latest_reading_with_advice():
    with client() as c:
        stations = c.get("/api/stations").json()
        assert len(stations) == len(STATIONS)
        for s in stations:
            latest = s["latest"]
            assert latest["category"] in CATEGORY_KEYS
            assert 0 <= latest["index"] <= 500
            assert latest["dominant"] in latest["sub_indices"]
            assert latest["advice"]["en"] and latest["advice"]["id"]


def test_station_history_and_unknown_station():
    with client() as c:
        rows = c.get("/api/stations/dki1-bundaran-hi/readings?hours=12").json()
        assert 12 <= len(rows) <= 13
        assert all(r["station_id"] == "dki1-bundaran-hi" for r in rows)
        # the first hour of the window is still averaged over the full 24 hours before it
        assert rows[0]["averages"]["pm25"] is not None
        assert c.get("/api/stations/nowhere/readings").status_code == 404
        assert c.get("/api/stations/nowhere").status_code == 404


def test_summary_counts_every_reporting_station():
    with client() as c:
        body = c.get("/api/summary").json()
        assert body["reporting"] == len(STATIONS)
        assert sum(body["category_counts"].values()) == len(STATIONS)
        assert sum(body["dominant_counts"].values()) == len(STATIONS)
        assert body["worst"]["index"] >= body["average_index"]


def test_alerts_endpoint():
    with client() as c:
        alerts = c.get("/api/alerts?hours=24&min_category=moderate").json()
        assert all(CATEGORY_KEYS.index(a["category"]) >= 1 for a in alerts)
        assert all(a["start"] <= a["end"] for a in alerts)
        assert c.get("/api/alerts?min_category=bogus").status_code == 422
