import random
from datetime import datetime, timedelta, timezone
from statistics import mean

from app import db, simulator
from app.config import POLLUTANT_KEYS, STATIONS

END = datetime(2026, 10, 26, tzinfo=timezone.utc)


def local_hour(r: dict) -> int:
    return r["timestamp"].astimezone(simulator.WIB).hour


def test_generate_covers_every_station_and_hour():
    rows = simulator.generate(END - timedelta(hours=23), END, seed=1)
    assert len(rows) == 24 * len(STATIONS)


def test_values_stay_physically_plausible():
    for r in simulator.generate(END - timedelta(days=7), END, seed=2):
        for p in POLLUTANT_KEYS:
            assert r[p] >= 0
        assert r["pm10"] >= r["pm25"] * 0.9
        assert r["pm25"] < 1500 and r["co"] < 150000


def test_rush_hour_raises_no2_at_roadside_station():
    rows = [r for r in simulator.generate(END - timedelta(days=14), END, seed=3)
            if r["station_id"] == "dki1-bundaran-hi"]
    rush = mean(r["no2"] for r in rows if local_hour(r) in (7, 8, 18, 19))
    afternoon = mean(r["no2"] for r in rows if local_hour(r) in (13, 14, 15))
    assert rush > 1.3 * afternoon


def test_ozone_peaks_in_daylight():
    rows = simulator.generate(END - timedelta(days=7), END, seed=4)
    midday = mean(r["o3"] for r in rows if local_hour(r) in (12, 13, 14))
    night = mean(r["o3"] for r in rows if local_hour(r) in (0, 1, 2, 3))
    assert midday > 3 * night


def test_night_inversion_holds_particles_near_the_ground():
    assert simulator.inversion(datetime(2026, 10, 26, 4, tzinfo=simulator.WIB)) > 1.4
    assert simulator.inversion(datetime(2026, 10, 26, 16, tzinfo=simulator.WIB)) < 1.05


def test_haze_episodes_happen_in_the_dry_season():
    hours = [datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(hours=h) for h in range(24 * 60)]
    smoky = [t for t in hours if simulator.haze("pekanbaru", t) > 0.5]
    assert smoky, "expected at least one strong haze episode in August-September"
    station = next(s for s in STATIONS if s["id"] == "pekanbaru")
    peak = simulator.reading(station, smoky[0], random.Random(0))
    assert peak["pm25"] > 100


def test_backfill_stores_readings():
    n = simulator.backfill(hours=6)
    assert n == 7 * len(STATIONS)
    assert db.count() == n
    assert set(db.latest_by_station()) == {s["id"] for s in STATIONS}
