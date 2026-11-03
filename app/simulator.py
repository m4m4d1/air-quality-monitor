"""Realistic simulated hourly readings for every station.

Each station profile has typical concentrations. On top of that the simulator adds:

- rush hours: traffic peaks around 07:30 and 18:00 WIB (weaker at weekends), which
  drives NO2, CO and fine particles;
- night inversions: the air near the ground mixes poorly at night and before
  sunrise, so pollution builds up until the morning sun breaks the inversion;
- ozone, which is made by sunlight and peaks in the early afternoon;
- day-to-day weather: some days are stagnant and hazy, rainy days wash the air;
- open burning of rubbish near city stations, a few hours at a time;
- haze from land and forest fires at the Sumatra and Kalimantan stations, lasting
  days, mostly in the dry season (July to October).

Weather, burning and haze are derived from a hash of (station, hour or day), so the
same time always gives the same answer, whichever order readings are generated in.

    python -m app.simulator --hours 72      # fill the database with 3 days of readings
"""
import argparse
import math
import random
from datetime import datetime, timedelta, timezone

from . import db
from .config import STATIONS

WIB = timezone(timedelta(hours=7))

PROFILES = {
    #             pm25  pm10/pm25  so2    co   o3 peak  no2
    "traffic":    (34.0, 1.55, 16.0, 1500.0, 95.0, 48.0),
    "industrial": (38.0, 1.80, 34.0, 1300.0, 85.0, 42.0),
    "suburban":   (27.0, 1.60, 11.0, 900.0, 125.0, 26.0),
    "city":       (24.0, 1.70, 14.0, 1000.0, 95.0, 30.0),
    "haze":       (15.0, 1.60, 8.0, 650.0, 70.0, 16.0),
}
BURN_CHANCE = 0.006                # per station-hour, cities only
BURN_HOURS = (2, 5)
HAZE_CHANCE = {"dry": 0.10, "wet": 0.03}   # chance per station-day that a fire episode starts
HAZE_HOURS = (36, 120)


def traffic(local: datetime) -> float:
    """Relative traffic, about 0.3 at night to 1.4 at the morning peak."""
    h = local.hour + local.minute / 60
    level = (0.3 + 0.9 * math.exp(-((h - 7.5) / 1.4) ** 2) + 0.8 * math.exp(-((h - 18.0) / 1.8) ** 2)
             + (0.25 if 6 <= h <= 21 else 0.0))
    return level * {5: 0.85, 6: 0.65}.get(local.weekday(), 1.0)


def inversion(local: datetime) -> float:
    """Build-up under the night inversion: 1.45 before dawn, 1.0 in the afternoon."""
    h = local.hour + local.minute / 60
    return 1 + 0.45 * (1 + math.cos(2 * math.pi * (h - 4) / 24)) / 2


def sunlight(local: datetime) -> float:
    h = local.hour + local.minute / 60
    return max(0.0, math.sin(math.pi * (h - 6.5) / 12))


def weather(province: str, local: datetime) -> float:
    """Day-to-day dispersion, 0.65 (rainy, windy) to 1.45 (stagnant), smooth across midnight."""
    def day_factor(day) -> float:
        return random.Random(f"wx:{province}:{day.isoformat()}").uniform(0.65, 1.45)
    frac = (local.hour + local.minute / 60) / 24
    today = local.date()
    return day_factor(today) * (1 - frac) + day_factor(today + timedelta(days=1)) * frac


def burning(station_id: str, ts: datetime) -> float:
    """0 when no rubbish is burning nearby, up to ~1 at the peak."""
    strength = 0.0
    for back in range(BURN_HOURS[1]):
        hour = (ts - timedelta(hours=back)).replace(minute=0, second=0, microsecond=0)
        rng = random.Random(f"burn:{station_id}:{hour.isoformat()}")
        if rng.random() < BURN_CHANCE:
            length = rng.randint(*BURN_HOURS)
            if back < length:
                strength = max(strength, math.sin(math.pi * (back + 0.5) / length) * rng.uniform(0.5, 1.0))
    return strength


def haze(station_id: str, ts: datetime) -> float:
    """0 without smoke, up to ~1 at the peak of a multi-day haze episode."""
    local = ts.astimezone(WIB)
    strength = 0.0
    for back in range(7):
        day = local.date() - timedelta(days=back)
        rng = random.Random(f"haze:{station_id}:{day.isoformat()}")
        season = "dry" if 7 <= day.month <= 10 else "wet"
        if rng.random() < HAZE_CHANCE[season]:
            start = datetime(day.year, day.month, day.day, rng.randint(0, 23), tzinfo=WIB)
            length = rng.randint(*HAZE_HOURS)
            elapsed = (local - start).total_seconds() / 3600
            if 0 <= elapsed < length:
                strength = max(strength, math.sin(math.pi * elapsed / length) * rng.uniform(0.5, 1.0))
    return strength


def reading(station: dict, ts: datetime, rng: random.Random) -> dict:
    pm25, coarse, so2, co, o3, no2 = PROFILES[station["profile"]]
    local = ts.astimezone(WIB) if ts.tzinfo else ts.replace(tzinfo=timezone.utc).astimezone(WIB)
    tr, inv, wx = traffic(local), inversion(local), weather(station["province"], local)
    smoke = haze(station["id"], ts) if station["profile"] == "haze" else 0.0
    fire = burning(station["id"], ts) if station["profile"] != "haze" else 0.0

    # Smoke is mostly fine particles and builds up under the night inversion too.
    base = pm25 * wx * inv * (0.55 + 0.45 * tr) * rng.lognormvariate(0, 0.12)
    smoke_fine = smoke * 320 * (0.75 + 0.25 * inv)
    return {
        "station_id": station["id"],
        "timestamp": ts,
        "pm25": round(base + smoke_fine + fire * 70, 1),
        "pm10": round(base * coarse * rng.lognormvariate(0, 0.08) + smoke_fine * 1.25 + fire * 95, 1),
        "so2": round(so2 * wx * inv ** 0.6 * rng.lognormvariate(0, 0.25), 1),
        "co": round(co * wx * inv * (0.3 + 0.7 * tr) * rng.lognormvariate(0, 0.15) + smoke * 4000 + fire * 1500),
        "o3": round(o3 * (0.12 + 0.88 * sunlight(local) ** 1.3) * (0.8 + 0.2 * wx) * rng.lognormvariate(0, 0.12), 1),
        "no2": round(no2 * wx ** 0.5 * inv ** 0.8 * (0.25 + 0.75 * tr) * rng.lognormvariate(0, 0.15), 1),
    }


def generate(start: datetime, end: datetime, step_minutes: int = 60, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    ts = start.replace(second=0, microsecond=0)
    while ts <= end:
        rows.extend(reading(s, ts, rng) for s in STATIONS)
        ts += timedelta(minutes=step_minutes)
    return rows


def backfill(hours: int = 72, step_minutes: int = 60, seed: int | None = 42) -> int:
    """Store `hours` of history ending now."""
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    db.init_db()
    return db.insert_readings(generate(end - timedelta(hours=hours), end, step_minutes, seed))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill the database with simulated readings.")
    parser.add_argument("--hours", type=int, default=72)
    parser.add_argument("--step", type=int, default=60, help="minutes between readings")
    args = parser.parse_args()
    n = backfill(args.hours, args.step)
    print(f"stored {n} readings in {db.db_path()}")


if __name__ == "__main__":
    main()
