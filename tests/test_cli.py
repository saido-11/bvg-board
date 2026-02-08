from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from typer.testing import CliRunner

import bvg_board.cli as cli_module
from bvg_board.bvg_api import Departure, Location, Stop
from bvg_board.config import AppConfig
from bvg_board.weather import CurrentWeather

runner = CliRunner()


class FakeBvgClient:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def __enter__(self) -> FakeBvgClient:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def nearby(
        self, latitude: float, longitude: float, *, results: int = 8, distance_m: int | None = None
    ) -> list[Stop]:
        return [
            Stop(
                id="900000100001",
                name=f"Test Stop ({latitude:.2f},{longitude:.2f})",
                location=Location(latitude=latitude, longitude=longitude),
                distance_m=distance_m or 100,
            )
        ][:results]

    def stop(self, _stop_id: str) -> Stop:
        return Stop(
            id="900000100001",
            name="Alexanderplatz",
            location=Location(latitude=52.5219, longitude=13.4132),
            distance_m=None,
        )

    def departures(self, _stop_id: str, *, duration_minutes: int = 60, results: int = 10) -> list[Departure]:
        departure_time = datetime(2026, 2, 8, 20, 30, tzinfo=ZoneInfo("Europe/Berlin"))
        departures = [
            Departure(
                line_name="U2",
                direction="Ruhleben",
                when=departure_time,
                delay_seconds=60,
                platform="2",
                remarks=(),
            )
        ]
        return departures[:results]


class FakeWeatherClient:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def __enter__(self) -> FakeWeatherClient:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def current_weather(self, _latitude: float, _longitude: float) -> CurrentWeather:
        return CurrentWeather(
            temperature_c=4.2,
            apparent_temperature_c=2.8,
            wind_speed_kmh=12.5,
            weather_code=2,
            is_day=True,
        )


def test_nearby_command_uses_config_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(
        cli_module,
        "load_config",
        lambda: AppConfig(default_latitude=52.5, default_longitude=13.4),
    )
    result = runner.invoke(cli_module.app, ["nearby"])
    assert result.exit_code == 0
    assert "Test Stop" in result.stdout


def test_show_command_uses_config_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(cli_module, "WeatherClient", FakeWeatherClient)
    monkeypatch.setattr(
        cli_module,
        "load_config",
        lambda: AppConfig(
            default_stop_id="900000100001",
            default_latitude=52.5,
            default_longitude=13.4,
        ),
    )
    result = runner.invoke(cli_module.app, ["show"])
    assert result.exit_code == 0
    assert "Alexanderplatz" in result.stdout
    assert "Weather:" in result.stdout


def test_watch_command_handles_ctrl_c(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_sleep(_seconds: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(cli_module, "WeatherClient", FakeWeatherClient)
    monkeypatch.setattr(cli_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(
        cli_module,
        "load_config",
        lambda: AppConfig(
            default_stop_id="900000100001",
            default_latitude=52.5,
            default_longitude=13.4,
        ),
    )
    result = runner.invoke(cli_module.app, ["watch", "--interval", "1"])
    assert result.exit_code == 0
    assert "Stopped watch." in result.stdout
