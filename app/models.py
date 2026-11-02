"""Data model for air quality readings."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import POLLUTANT_KEYS, STATION_IDS


class ReadingIn(BaseModel):
    """One hourly set of concentrations from a station, in µg/m³.

    Not every station measures every pollutant: leave out what is not measured,
    but send at least one.
    """

    station_id: str
    timestamp: datetime | None = Field(None, description="End of the measured hour; defaults to now (UTC)")
    pm25: float | None = Field(None, ge=0, le=1500, description="Fine particles PM2.5, µg/m³")
    pm10: float | None = Field(None, ge=0, le=2500, description="Particles PM10, µg/m³")
    so2: float | None = Field(None, ge=0, le=5000, description="Sulphur dioxide, µg/m³")
    co: float | None = Field(None, ge=0, le=150000, description="Carbon monoxide, µg/m³")
    o3: float | None = Field(None, ge=0, le=3000, description="Ozone, µg/m³")
    no2: float | None = Field(None, ge=0, le=6000, description="Nitrogen dioxide, µg/m³")

    @field_validator("station_id")
    @classmethod
    def known_station(cls, v: str) -> str:
        if v not in STATION_IDS:
            raise ValueError(f"unknown station '{v}'")
        return v

    @model_validator(mode="after")
    def at_least_one_pollutant(self) -> "ReadingIn":
        if all(getattr(self, p) is None for p in POLLUTANT_KEYS):
            raise ValueError("send at least one pollutant")
        return self


class Reading(ReadingIn):
    timestamp: datetime
