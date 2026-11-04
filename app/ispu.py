"""ISPU air quality index (PermenLHK No. P.14/MENLHK/SETJEN/KUM.1/7/2020) and alerts.

Each pollutant is first averaged over the period the regulation uses for it
(24 hours for PM2.5, PM10 and SO2, 8 hours for CO, 1 hour for O3 and NO2).
The average is converted to a sub-index by linear interpolation between the
two breakpoints around it:

    I = (Ia - Ib) / (Xa - Xb) · (Xx - Xb) + Ib

where Xx is the concentration, Xa and Xb the upper and lower concentration
breakpoints and Ia and Ib the ISPU values at those breakpoints. The station's
ISPU is the highest sub-index, and that pollutant is the dominant one.
Concentrations above the last breakpoint are reported as 500.

With less history than the averaging period (a new station, a gap) the
average is taken over the readings that are there.
"""
from bisect import bisect_right
from datetime import datetime, timedelta

from .config import ALERT_CATEGORY, CATEGORIES, CATEGORY_KEYS, ISPU_BREAKS, POLLUTANT_KEYS, POLLUTANTS

MAX_HOURS = max(p["hours"] for p in POLLUTANTS.values())


def parse(ts) -> datetime:
    return datetime.fromisoformat(ts) if isinstance(ts, str) else ts


def sub_index(pollutant: str, concentration: float) -> int:
    """ISPU of one pollutant from its averaged concentration (µg/m³)."""
    if concentration <= 0:
        return 0
    low_c, low_i = 0.0, ISPU_BREAKS[0]
    for high_c, high_i in zip(POLLUTANTS[pollutant]["breakpoints"], ISPU_BREAKS[1:]):
        if concentration <= high_c:
            value = (high_i - low_i) / (high_c - low_c) * (concentration - low_c) + low_i
            return int(value + 0.5)
        low_c, low_i = high_c, high_i
    return ISPU_BREAKS[-1]


def category(index: int) -> dict:
    return next(c for c in CATEGORIES if index <= c["max"])


def averages(rows: list[dict]) -> list[dict]:
    """Rolling averages for each reading of ONE station (rows sorted oldest first).

    For each pollutant, the mean of the readings in its averaging period ending at
    that reading; None when the pollutant was not measured in that period.
    """
    times = [parse(r["timestamp"]) for r in rows]
    out: list[dict] = [{} for _ in rows]
    for p in POLLUTANT_KEYS:
        window = timedelta(hours=POLLUTANTS[p]["hours"])
        total, n = [0.0], [0]
        for r in rows:
            v = r.get(p)
            total.append(total[-1] + (v or 0.0))
            n.append(n[-1] + (v is not None))
        for k, t in enumerate(times):
            start = bisect_right(times, t - window)
            count = n[k + 1] - n[start]
            out[k][p] = round((total[k + 1] - total[start]) / count, 1) if count else None
    return out


def score(reading: dict, avg: dict) -> dict:
    """A reading with its averages, sub-indices, ISPU, category and dominant pollutant."""
    subs = {p: sub_index(p, v) for p, v in avg.items() if v is not None}
    dominant = max(subs, key=lambda p: subs[p]) if subs else None
    index = subs[dominant] if dominant else 0
    cat = category(index)
    return {**reading, "averages": avg, "sub_indices": subs, "index": index, "dominant": dominant,
            "category": cat["key"], "category_label": {"en": cat["en"], "id": cat["id"]}}


def score_series(rows: list[dict]) -> list[dict]:
    """Score readings of one or more stations, each against its own history in `rows`."""
    by_station: dict[str, list[dict]] = {}
    for r in rows:
        by_station.setdefault(r["station_id"], []).append(r)
    out = []
    for series in by_station.values():
        series.sort(key=lambda r: parse(r["timestamp"]))
        out.extend(score(r, a) for r, a in zip(series, averages(series)))
    return out


def ispu(concentrations: dict) -> dict:
    """ISPU straight from already-averaged concentrations, e.g. {"pm25": 60, "o3": 140}."""
    avg = {p: concentrations.get(p) for p in POLLUTANT_KEYS}
    s = score({}, avg)
    return {k: s[k] for k in ("sub_indices", "index", "dominant", "category", "category_label")}


def alerts(scored: list[dict], min_category: str = ALERT_CATEGORY, gap_hours: float = 2) -> list[dict]:
    """Episodes of consecutive readings at or above `min_category`, latest first.

    A reading below the threshold, or a gap of more than `gap_hours`, ends an episode.
    """
    threshold = CATEGORY_KEYS.index(min_category)
    by_station: dict[str, list[dict]] = {}
    for r in sorted(scored, key=lambda r: parse(r["timestamp"])):
        by_station.setdefault(r["station_id"], []).append(r)
    episodes = []
    for station_id, rows in by_station.items():
        current = None
        for r in rows:
            if CATEGORY_KEYS.index(r["category"]) < threshold:
                current = None
                continue
            t = parse(r["timestamp"])
            if current and t - parse(current["end"]) <= timedelta(hours=gap_hours):
                current["end"] = r["timestamp"]
                current["readings"] += 1
            else:
                current = {"station_id": station_id, "start": r["timestamp"], "end": r["timestamp"],
                           "readings": 1, "peak_index": -1}
                episodes.append(current)
            if r["index"] > current["peak_index"]:
                current.update(peak_index=r["index"], peak_time=r["timestamp"], dominant=r["dominant"],
                               category=r["category"], category_label=r["category_label"])
        if current and rows and current["end"] == rows[-1]["timestamp"]:
            current["ongoing"] = True
    for e in episodes:
        e.setdefault("ongoing", False)
        e["hours"] = round((parse(e["end"]) - parse(e["start"])).total_seconds() / 3600 + 1, 1)
    return sorted(episodes, key=lambda e: (parse(e["end"]), e["peak_index"]), reverse=True)
