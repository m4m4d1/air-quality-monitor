"""Monitoring stations, pollutants and the ISPU air quality index.

The index is Indonesia's Indeks Standar Pencemar Udara (ISPU) as defined in
Peraturan Menteri LHK No. P.14/MENLHK/SETJEN/KUM.1/7/2020. For each pollutant
the regulation gives concentration breakpoints for ISPU 50, 100, 200, 300 and
500; the index of a pollutant is interpolated linearly between them and the
station's ISPU is the highest of those sub-indices. Hydrocarbons (HC) are part
of the regulation but are not measured here.

The breakpoints and averaging periods below were transcribed for this project.
Verify them against the regulation before using the results for official purposes.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("AQ_DB", ROOT / "data" / "air.db"))

# Station profiles drive the simulator:
#   traffic     roadside in a city centre (rush-hour peaks of NO2, CO and fine dust)
#   industrial  near industrial estates and the port (more SO2 and coarse dust)
#   suburban    residential edge of the city (less traffic, more ozone downwind)
#   city        other large cities, mixed sources
#   haze        cities in the peatland provinces of Sumatra and Kalimantan, usually
#               clean but hit by smoke from land and forest fires in the dry season
# The five Jakarta stations sit at the locations of the city's own ISPU stations
# (DKI1 to DKI5); readings in this project are simulated, not theirs.
STATIONS = [
    {"id": "dki1-bundaran-hi", "name": "Bundaran HI", "city": "Jakarta Pusat", "province": "DKI Jakarta",
     "lat": -6.1950, "lon": 106.8230, "profile": "traffic"},
    {"id": "dki2-kelapa-gading", "name": "Kelapa Gading", "city": "Jakarta Utara", "province": "DKI Jakarta",
     "lat": -6.1540, "lon": 106.9100, "profile": "industrial"},
    {"id": "dki3-jagakarsa", "name": "Jagakarsa", "city": "Jakarta Selatan", "province": "DKI Jakarta",
     "lat": -6.3350, "lon": 106.8230, "profile": "suburban"},
    {"id": "dki4-lubang-buaya", "name": "Lubang Buaya", "city": "Jakarta Timur", "province": "DKI Jakarta",
     "lat": -6.2900, "lon": 106.9050, "profile": "suburban"},
    {"id": "dki5-kebon-jeruk", "name": "Kebon Jeruk", "city": "Jakarta Barat", "province": "DKI Jakarta",
     "lat": -6.1950, "lon": 106.7700, "profile": "traffic"},
    {"id": "bandung", "name": "Dago", "city": "Bandung", "province": "Jawa Barat",
     "lat": -6.8900, "lon": 107.6130, "profile": "city"},
    {"id": "surabaya", "name": "Wonorejo", "city": "Surabaya", "province": "Jawa Timur",
     "lat": -7.3100, "lon": 112.7850, "profile": "industrial"},
    {"id": "medan", "name": "Medan Kota", "city": "Medan", "province": "Sumatera Utara",
     "lat": 3.5850, "lon": 98.6750, "profile": "city"},
    {"id": "palembang", "name": "Jakabaring", "city": "Palembang", "province": "Sumatera Selatan",
     "lat": -3.0150, "lon": 104.7900, "profile": "haze"},
    {"id": "pekanbaru", "name": "Sukajadi", "city": "Pekanbaru", "province": "Riau",
     "lat": 0.5150, "lon": 101.4400, "profile": "haze"},
    {"id": "pontianak", "name": "Pontianak Kota", "city": "Pontianak", "province": "Kalimantan Barat",
     "lat": -0.0300, "lon": 109.3300, "profile": "haze"},
    {"id": "palangka-raya", "name": "Palangka Raya", "city": "Palangka Raya", "province": "Kalimantan Tengah",
     "lat": -2.2100, "lon": 113.9200, "profile": "haze"},
]
STATION_IDS = {s["id"] for s in STATIONS}

# ISPU values at the breakpoints. A concentration at breakpoint k gives ISPU_BREAKS[k + 1];
# zero concentration gives zero.
ISPU_BREAKS = [0, 50, 100, 200, 300, 500]

# Concentrations in µg/m³ (CO too). `hours` is the averaging period the regulation
# applies before comparing with the breakpoints.
POLLUTANTS = {
    "pm25": {"en": "PM2.5", "id": "PM2.5", "unit": "µg/m³", "hours": 24,
             "breakpoints": [15.5, 55.4, 150.4, 250.4, 500.0]},
    "pm10": {"en": "PM10", "id": "PM10", "unit": "µg/m³", "hours": 24,
             "breakpoints": [50.0, 150.0, 350.0, 420.0, 500.0]},
    "so2": {"en": "Sulphur dioxide (SO₂)", "id": "Sulfur dioksida (SO₂)", "unit": "µg/m³", "hours": 24,
            "breakpoints": [52.0, 180.0, 400.0, 800.0, 1200.0]},
    "co": {"en": "Carbon monoxide (CO)", "id": "Karbon monoksida (CO)", "unit": "µg/m³", "hours": 8,
           "breakpoints": [4000.0, 8000.0, 15000.0, 30000.0, 45000.0]},
    "o3": {"en": "Ozone (O₃)", "id": "Ozon (O₃)", "unit": "µg/m³", "hours": 1,
           "breakpoints": [120.0, 235.0, 400.0, 800.0, 1000.0]},
    "no2": {"en": "Nitrogen dioxide (NO₂)", "id": "Nitrogen dioksida (NO₂)", "unit": "µg/m³", "hours": 1,
            "breakpoints": [80.0, 200.0, 1130.0, 2260.0, 3000.0]},
}
POLLUTANT_KEYS = list(POLLUTANTS)

# ISPU categories with the colours used by the regulation (green, blue, yellow, red, black)
# and health advice paraphrased from its annex. "Sensitive groups" are children, older
# people, pregnant women and people with heart or lung disease such as asthma.
CATEGORIES = [
    {"key": "good", "max": 50, "en": "Good", "id": "Baik", "color": "#2e9e44",
     "advice": {
         "en": "Air quality is good. A fine day for outdoor activities.",
         "id": "Kualitas udara baik. Waktu yang tepat untuk beraktivitas di luar ruangan."}},
    {"key": "moderate", "max": 100, "en": "Moderate", "id": "Sedang", "color": "#1f6fd1",
     "advice": {
         "en": "Acceptable for most people. Sensitive groups should cut down on long or strenuous outdoor exercise.",
         "id": "Masih dapat diterima. Kelompok sensitif sebaiknya mengurangi olahraga berat atau lama di luar ruangan."}},
    {"key": "unhealthy", "max": 200, "en": "Unhealthy", "id": "Tidak Sehat", "color": "#e0a800",
     "advice": {
         "en": "Sensitive groups should limit time outdoors and wear a mask outside. Everyone else should reduce strenuous outdoor activity.",
         "id": "Kelompok sensitif sebaiknya membatasi waktu di luar ruangan dan memakai masker. Masyarakat umum sebaiknya mengurangi aktivitas berat di luar ruangan."}},
    {"key": "very_unhealthy", "max": 300, "en": "Very unhealthy", "id": "Sangat Tidak Sehat", "color": "#d7262b",
     "advice": {
         "en": "Sensitive groups should stay indoors. Everyone should avoid outdoor exercise and wear a well-fitting mask (N95/KN95) outside.",
         "id": "Kelompok sensitif sebaiknya tetap di dalam ruangan. Semua orang sebaiknya menghindari olahraga di luar dan memakai masker yang rapat (N95/KN95)."}},
    {"key": "hazardous", "max": float("inf"), "en": "Hazardous", "id": "Berbahaya", "color": "#1d1d1f",
     "advice": {
         "en": "Everyone should stay indoors with doors and windows closed, use an air purifier if available, and seek medical help for breathing problems.",
         "id": "Semua orang sebaiknya tetap di dalam ruangan dengan pintu dan jendela tertutup, memakai penjernih udara bila ada, dan segera ke fasilitas kesehatan bila sesak napas."}},
]
CATEGORY_KEYS = [c["key"] for c in CATEGORIES]

# Alerts are raised from this category upwards.
ALERT_CATEGORY = "unhealthy"
