# Changelog

## Unreleased

- Bilingual (EN/ID) dashboard: summary, station table, station detail with health advice and
  72-hour chart.
- REST API: stations, history, summary, alerts and a sensor ingest endpoint (`/docs` for details).
- ISPU index: rolling averages, breakpoint interpolation, dominant pollutant, health advice and
  alert episodes from Tidak Sehat upwards.
- Sensor data simulator with rush hours, night inversions, rubbish burning and dry-season haze,
  and SQLite storage (`python -m app.simulator --hours 72`).
- Project scaffold, 12 monitoring stations and the air quality data model (ISPU breakpoints,
  PermenLHK P.14/2020).
