from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

CLEAN = {"station_id": "bandung", "pm25": 12.0, "pm10": 25.0, "so2": 8.0, "co": 600, "o3": 40.0, "no2": 20.0}


def test_ingest_scores_and_stores_a_reading():
    with TestClient(app) as c:
        res = c.post("/api/readings", json=CLEAN)
        assert res.status_code == 201
        body = res.json()
        assert body["category"] == "good"
        assert body["index"] == 39            # PM2.5 12 µg/m³ dominates
        assert body["advice"]["id"]
        latest = c.get("/api/stations/bandung").json()["latest"]
        assert latest["pm25"] == 12.0


def test_ingest_uses_the_24_hour_average_for_particles():
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
    with TestClient(app) as c:
        for h in range(23):
            ts = (start + timedelta(hours=h)).isoformat()
            assert c.post("/api/readings", json={**CLEAN, "station_id": "pekanbaru", "timestamp": ts,
                                                 "pm25": 200.0}).status_code == 201
        # one clean hour does not clear a day of smoke
        body = c.post("/api/readings", json={**CLEAN, "station_id": "pekanbaru",
                                             "timestamp": (start + timedelta(hours=23)).isoformat()}).json()
        assert body["averages"]["pm25"] > 150
        assert body["category"] == "very_unhealthy"
        assert body["dominant"] == "pm25"
        alerts = c.get("/api/alerts?hours=48").json()
        assert alerts and alerts[0]["station_id"] == "pekanbaru" and alerts[0]["ongoing"]


def test_ingest_accepts_partial_readings():
    with TestClient(app) as c:
        res = c.post("/api/readings", json={"station_id": "medan", "pm25": 70.0})
        assert res.status_code == 201
        body = res.json()
        assert set(body["sub_indices"]) == {"pm25"}
        assert body["category"] == "unhealthy"


def test_ingest_validates_input():
    with TestClient(app) as c:
        assert c.post("/api/readings", json={**CLEAN, "station_id": "nowhere"}).status_code == 422
        assert c.post("/api/readings", json={**CLEAN, "pm25": -1}).status_code == 422
        assert c.post("/api/readings", json={"station_id": "bandung"}).status_code == 422


def test_api_key_is_enforced_when_set(monkeypatch):
    monkeypatch.setenv("AQ_API_KEY", "secret")
    with TestClient(app) as c:
        assert c.post("/api/readings", json=CLEAN).status_code == 401
        assert c.post("/api/readings", json=CLEAN, headers={"X-API-Key": "secret"}).status_code == 201
