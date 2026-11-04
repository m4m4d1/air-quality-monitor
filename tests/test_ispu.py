from datetime import datetime, timedelta, timezone

import pytest

from app import ispu

T0 = datetime(2026, 10, 26, tzinfo=timezone.utc)


def series(station_id: str, values: list[dict], start: datetime = T0) -> list[dict]:
    return [{"station_id": station_id, "timestamp": (start + timedelta(hours=k)).isoformat(), **v}
            for k, v in enumerate(values)]


@pytest.mark.parametrize("pollutant,concentration,expected", [
    ("pm25", 0, 0),
    ("pm25", 15.5, 50),
    ("pm25", 55.4, 100),
    ("pm25", 35.45, 75),        # halfway between 15.5 and 55.4
    ("pm25", 150.4, 200),
    ("pm25", 900, 500),         # beyond the scale
    ("pm10", 100, 75),
    ("pm10", 420, 300),
    ("co", 8000, 100),
    ("o3", 120, 50),
    ("no2", 665, 150),          # halfway between 200 and 1130
    ("so2", 26, 25),
])
def test_sub_index_interpolates_between_breakpoints(pollutant, concentration, expected):
    assert ispu.sub_index(pollutant, concentration) == expected


@pytest.mark.parametrize("index,key", [(0, "good"), (50, "good"), (51, "moderate"), (100, "moderate"),
                                       (101, "unhealthy"), (200, "unhealthy"), (201, "very_unhealthy"),
                                       (300, "very_unhealthy"), (301, "hazardous"), (500, "hazardous")])
def test_categories(index, key):
    assert ispu.category(index)["key"] == key


def test_highest_sub_index_wins_and_names_the_dominant_pollutant():
    result = ispu.ispu({"pm25": 60, "pm10": 80, "o3": 140, "no2": 40})
    assert result["dominant"] == "pm25"
    assert result["index"] == result["sub_indices"]["pm25"] > result["sub_indices"]["o3"]
    assert result["category"] == "unhealthy"
    assert result["category_label"] == {"en": "Unhealthy", "id": "Tidak Sehat"}


def test_averaging_periods_differ_per_pollutant():
    # 23 clean hours, then one very dirty hour
    values = [{"pm25": 10.0, "o3": 20.0}] * 23 + [{"pm25": 250.0, "o3": 260.0}]
    last = ispu.averages(series("x", values))[-1]
    assert last["pm25"] == pytest.approx((23 * 10 + 250) / 24, abs=0.05)   # 24-hour mean
    assert last["o3"] == 260.0                                            # 1-hour value
    assert last["co"] is None                                             # not measured


def test_average_window_drops_old_readings():
    values = [{"pm25": 500.0}] + [{"pm25": 20.0}] * 24
    assert ispu.averages(series("x", values))[-1]["pm25"] == 20.0


def test_score_series_keeps_stations_apart():
    rows = series("a", [{"pm25": 10.0}] * 3) + series("b", [{"pm25": 200.0}] * 3)
    scored = ispu.score_series(rows)
    assert {r["category"] for r in scored if r["station_id"] == "a"} == {"good"}
    assert {r["category"] for r in scored if r["station_id"] == "b"} == {"very_unhealthy"}


def test_alerts_group_consecutive_hours_into_episodes():
    clean, smoky = {"pm25": 10.0, "o3": 30.0}, {"pm25": 10.0, "o3": 300.0}
    rows = series("pekanbaru", [clean, smoky, smoky, smoky, clean, smoky]) + \
        series("bandung", [clean] * 6)
    episodes = ispu.alerts(ispu.score_series(rows))
    assert len(episodes) == 2
    latest, first = episodes
    assert latest["ongoing"] and latest["readings"] == 1
    assert first["hours"] == 3 and not first["ongoing"]
    assert first["dominant"] == "o3" and first["category"] == "unhealthy"


def test_alert_threshold_can_be_raised():
    rows = series("palembang", [{"pm25": 10.0, "o3": 300.0}] * 2)   # unhealthy, not very unhealthy
    scored = ispu.score_series(rows)
    assert ispu.alerts(scored, "unhealthy")
    assert ispu.alerts(scored, "very_unhealthy") == []
