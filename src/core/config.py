"""Source identity and explicit pollutant metadata; never inferred source units."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RESOURCE = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
API_URL = f"https://api.data.gov.in/resource/{RESOURCE}"
SOURCE_URL = "https://www.data.gov.in/catalog/real-time-air-quality-index"
CPCB_URL = "https://cpcb.nic.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvQWJvdXRfQVFJLnBkZg%3D%3D"
TIMEZONE = "Asia/Kolkata"
STALE_HOURS = 3
HORIZONS = (1, 3, 6, 12, 24)
POLLUTANTS = {
    "PM2.5": {"unit": "ug/m3", "hours": 24, "description": "Fine particulate matter"},
    "PM10": {"unit": "ug/m3", "hours": 24, "description": "Respirable particulate matter"},
    "NO2": {"unit": "ug/m3", "hours": 24, "description": "Nitrogen dioxide"},
    "SO2": {"unit": "ug/m3", "hours": 24, "description": "Sulphur dioxide"},
    "O3": {"unit": "ug/m3", "hours": 8, "description": "Ozone"},
    "NH3": {"unit": "ug/m3", "hours": 24, "description": "Ammonia"},
    "CO": {"unit": "mg/m3", "hours": 8, "description": "Carbon monoxide"},
    "Pb": {"unit": "ug/m3", "hours": 24, "description": "Lead"},
}
ALIASES = {"PM25": "PM2.5", "PM2.5": "PM2.5", "PM10": "PM10", "OZONE": "O3", "O3": "O3", "PB": "Pb", **{p: p for p in ("NO2", "SO2", "NH3", "CO")}}


def normalize_pollutant(value: object) -> str:
    """Normalize documented labels without equating different chemical species."""
    key = str(value).strip().upper().replace(" ", "").replace("_", "")
    return ALIASES.get(key, key)
