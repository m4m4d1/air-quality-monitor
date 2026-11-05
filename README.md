# Air Quality Monitoring System

**Sistem Pemantauan Kualitas Udara** for Indonesian cities.

Tracks PM2.5, PM10, ozone, NO2, SO2 and CO at stations in Jakarta and other Indonesian cities,
converts them to the national air quality index (*Indeks Standar Pencemar Udara*, ISPU) of
PermenLHK P.14/2020, gives health advice for each category and warns sensitive groups when the
air becomes unhealthy.

> Week 2 of Nusantara Intel: one new open-source
> information system for Indonesia every week, built in public one step per day.

## Monitored stations

12 stations: five in Jakarta at the locations of the city's ISPU stations (Bundaran HI,
Kelapa Gading, Jagakarsa, Lubang Buaya, Kebon Jeruk), Bandung, Surabaya and Medan, and four cities
that suffer from haze from land and forest fires in the dry season: Palembang, Pekanbaru,
Pontianak and Palangka Raya.

## Pollutants and index

ISPU breakpoints from PermenLHK No. P.14/MENLHK/SETJEN/KUM.1/7/2020:

| Pollutant | Averaging | ISPU 50 | ISPU 100 | ISPU 200 | ISPU 300 | ISPU 500 |
|-----------|-----------|---------|----------|----------|----------|----------|
| PM2.5 | 24 h | 15.5 | 55.4 | 150.4 | 250.4 | 500 |
| PM10 | 24 h | 50 | 150 | 350 | 420 | 500 |
| SO₂ | 24 h | 52 | 180 | 400 | 800 | 1200 |
| CO | 8 h | 4000 | 8000 | 15000 | 30000 | 45000 |
| O₃ | 1 h | 120 | 235 | 400 | 800 | 1000 |
| NO₂ | 1 h | 80 | 200 | 1130 | 2260 | 3000 |

Concentrations in µg/m³.

| ISPU | Category |
|------|----------|
| 0 to 50 | Good (*Baik*) |
| 51 to 100 | Moderate (*Sedang*) |
| 101 to 200 | Unhealthy (*Tidak Sehat*) |
| 201 to 300 | Very unhealthy (*Sangat Tidak Sehat*) |
| 301 and above | Hazardous (*Berbahaya*) |

Verify the breakpoints against the regulation before official use.

## Roadmap this week

- [x] Mon: scaffold, stations and data model
- [x] Tue: sensor data simulator and storage
- [x] Wed: REST API, ISPU index and alerts
- [x] Thu: dashboard
- [ ] Fri: map and alerts panel
- [ ] Sat: Docker, tests and documentation
- [ ] Sun: live demo and v1.0 release

## License

MIT
