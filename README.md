# Air Quality Monitoring System

**Sistem Pemantauan Kualitas Udara** for Indonesian cities.

Tracks PM2.5, PM10, ozone, NO2, SO2 and CO at stations in Jakarta and other Indonesian cities,
converts them to the national air quality index (*Indeks Standar Pencemar Udara*, ISPU) of
PermenLHK P.14/2020, gives health advice for each category and warns sensitive groups when the
air becomes unhealthy.

> Week 2 of Nusantara Intel: one new open-source
> information system for Indonesia every week, built in public one step per day.

## Features

- **12 stations**: five in Jakarta at the locations of the city's ISPU stations (Bundaran HI,
  Kelapa Gading, Jagakarsa, Lubang Buaya, Kebon Jeruk), Bandung, Surabaya and Medan, and the
  haze-prone cities of Palembang, Pekanbaru, Pontianak and Palangka Raya.
- **ISPU index** per PermenLHK P.14/2020 for PM2.5, PM10, SO2, CO, O3 and NO2, each averaged over
  its own period, with the dominant pollutant and five categories from *Baik* to *Berbahaya*.
- **Health advice** in English and Indonesian for every category, for sensitive groups and for
  everyone.
- **Alerts** when a station reaches *Tidak Sehat* (Unhealthy) or worse, grouped into episodes
  with their peak and duration.
- **Bilingual dashboard** (English / Bahasa Indonesia): summary, station table, health advice,
  72-hour charts, map and alerts.
- **REST API** with interactive docs at `/docs`, including an endpoint for real stations.
- **Simulator** that produces realistic hourly readings (rush hours, night inversions, ozone in
  the afternoon sun, rubbish burning, dry-season haze) so the system runs out of the box.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the dashboard and http://localhost:8000/docs for the API.
On first start the database is filled with 96 hours of simulated readings (72 to show plus the
24 the averages need), and a new reading per station is added every hour.

With Docker:

```bash
docker build -t air-quality-monitor .
docker run -p 8000:8000 -v aq-data:/data air-quality-monitor
```

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `AQ_DB` | `data/air.db` | SQLite database file |
| `AQ_SIMULATE` | `1` | `0` turns the simulator off (use with real stations) |
| `AQ_SIM_INTERVAL` | `3600` | Seconds between simulated readings |
| `AQ_API_KEY` | not set | If set, `POST /api/readings` needs the header `X-API-Key` |

## API

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/stations` | All stations with their latest ISPU, averages and health advice |
| GET | `/api/stations/{id}/readings?hours=72` | Scored hourly history for one station |
| GET | `/api/summary` | Counts per category, dominant pollutants, average ISPU, worst station |
| GET | `/api/alerts?hours=24&min_category=unhealthy` | Episodes at or above a category |
| GET | `/api/meta` | Pollutants, breakpoints, categories and health advice |
| POST | `/api/readings` | Store an hourly reading from a station; returns its ISPU |

Send an hourly reading from a real station (leave out pollutants it does not measure):

```bash
curl -X POST http://localhost:8000/api/readings \
  -H "Content-Type: application/json" \
  -d '{"station_id": "dki1-bundaran-hi", "pm25": 48.2, "pm10": 71.5, "o3": 64, "no2": 58, "so2": 21, "co": 1900}'
```

## How the ISPU is calculated

Each pollutant is averaged over the period the regulation sets for it, then converted to a
sub-index by linear interpolation between the breakpoints around it:

```
I = (Ia - Ib) / (Xa - Xb) × (Xx - Xb) + Ib
```

`Xx` is the averaged concentration, `Xa` and `Xb` the upper and lower breakpoints, `Ia` and `Ib`
the ISPU values at those breakpoints. The station's ISPU is the highest sub-index, and that
pollutant is reported as dominant. Concentrations above the last breakpoint are reported as 500.

| Pollutant | Averaging | ISPU 50 | ISPU 100 | ISPU 200 | ISPU 300 | ISPU 500 |
|-----------|-----------|---------|----------|----------|----------|----------|
| PM2.5 | 24 h | 15.5 | 55.4 | 150.4 | 250.4 | 500 |
| PM10 | 24 h | 50 | 150 | 350 | 420 | 500 |
| SO₂ | 24 h | 52 | 180 | 400 | 800 | 1200 |
| CO | 8 h | 4000 | 8000 | 15000 | 30000 | 45000 |
| O₃ | 1 h | 120 | 235 | 400 | 800 | 1000 |
| NO₂ | 1 h | 80 | 200 | 1130 | 2260 | 3000 |

Concentrations in µg/m³.

| ISPU | Category | Advice (short) |
|------|----------|----------------|
| 0 to 50 | Good (*Baik*) | Fine for outdoor activities |
| 51 to 100 | Moderate (*Sedang*) | Sensitive groups cut down on long or strenuous outdoor exercise |
| 101 to 200 | Unhealthy (*Tidak Sehat*) | Sensitive groups limit time outdoors and wear a mask; everyone reduces strenuous activity |
| 201 to 300 | Very unhealthy (*Sangat Tidak Sehat*) | Sensitive groups stay indoors; everyone avoids outdoor exercise |
| 301 and above | Hazardous (*Berbahaya*) | Everyone stays indoors with windows closed |

Sensitive groups are children, older people, pregnant women and people with heart or lung
disease. Hydrocarbons (HC), also in the regulation, are not measured.

## Tests

```bash
pytest -q
```

## Notes

The demo data is simulated: station locations are real, readings are not. The breakpoints were
transcribed from PermenLHK P.14/2020 for this project; verify them against the regulation before
official use. For real air quality in Indonesia see the official ISPU publications of KLHK and
the provincial environment agencies.

## Roadmap this week

- [x] Mon: scaffold, stations and data model
- [x] Tue: sensor data simulator and storage
- [x] Wed: REST API, ISPU index and alerts
- [x] Thu: dashboard
- [x] Fri: map and alerts panel
- [x] Sat: Docker, tests and documentation
- [ ] Sun: live demo and v1.0 release

## License

MIT
