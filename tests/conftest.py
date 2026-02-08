from __future__ import annotations

from datetime import datetime
import socket
from zoneinfo import ZoneInfo

import pytest

from bvg_board.bvg_api import Departure, Location, Stop
from bvg_board.weather import CurrentWeather


@pytest.fixture
def berlin_tz() -> ZoneInfo:
    return ZoneInfo("Europe/Berlin")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def guard(*_args: object, **_kwargs: object) -> None:
        msg = "Tests must not perform network I/O."
        raise AssertionError(msg)

    monkeypatch.setattr(socket, "create_connection", guard)


@pytest.fixture
def sample_stop_payload() -> dict[str, object]:
    return {
        "id": "900000100001",
        "name": "Alexanderplatz",
        "location": {"latitude": 52.5219, "longitude": 13.4132},
        "distance": 120,
    }


@pytest.fixture
def sample_departure_payload() -> dict[str, object]:
    return {
        "departures": [
            {
                "line": {"name": "U2"},
                "direction": "Ruhleben",
                "when": "2026-02-08T20:30:00+01:00",
                "delay": 60,
                "platform": "2",
                "remarks": [{"summary": "Minor delays"}],
            }
        ]
    }


@pytest.fixture
def sample_weather_payload() -> dict[str, object]:
    return {
        "current": {
            "temperature_2m": 3.8,
            "apparent_temperature": 1.2,
            "wind_speed_10m": 11.4,
            "weather_code": 3,
            "is_day": 0,
        }
    }


@pytest.fixture
def sample_stop() -> Stop:
    return Stop(
        id="900000100001",
        name="Alexanderplatz",
        location=Location(latitude=52.5219, longitude=13.4132),
        distance_m=120,
    )


@pytest.fixture
def sample_departure(berlin_tz: ZoneInfo) -> Departure:
    return Departure(
        line_name="U2",
        direction="Ruhleben",
        when=datetime(2026, 2, 8, 20, 30, tzinfo=berlin_tz),
        delay_seconds=120,
        platform="2",
        remarks=("Minor delays",),
    )


@pytest.fixture
def sample_weather() -> CurrentWeather:
    return CurrentWeather(
        temperature_c=3.8,
        apparent_temperature_c=1.2,
        wind_speed_kmh=11.4,
        weather_code=3,
        is_day=False,
    )
