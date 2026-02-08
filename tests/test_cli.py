from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from typer.testing import CliRunner

import bvg_board.cli as cli_module
import bvg_board.config as config_module
from bvg_board.bvg_api import Departure, Location, Stop
from bvg_board.config import AppConfig
from bvg_board.weather import CurrentWeather

runner = CliRunner()
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _strip_ansi(value: str) -> str:
    return ANSI_ESCAPE_RE.sub("", value)


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
        stops = [
            Stop(
                id="900000100003",
                name="Far Stop",
                kind="stop",
                location=Location(latitude=latitude, longitude=longitude),
                distance_m=300 if distance_m is None else min(distance_m, 300),
            ),
            Stop(
                id="900000100001",
                name="Near Station",
                kind="station",
                location=Location(latitude=latitude, longitude=longitude),
                distance_m=100 if distance_m is None else min(distance_m, 100),
            ),
            Stop(
                id="900000100002",
                name="Mid Stop",
                kind="stop",
                location=Location(latitude=latitude, longitude=longitude),
                distance_m=200 if distance_m is None else min(distance_m, 200),
            ),
        ]
        return stops[:results]

    def stop(self, _stop_id: str) -> Stop:
        return Stop(
            id="900000100001",
            name="Alexanderplatz",
            kind="station",
            location=Location(latitude=52.5219, longitude=13.4132),
            distance_m=None,
        )

    def departures(
        self,
        _stop_id: str,
        *,
        duration_minutes: int = 60,
        results: int = 10,
    ) -> list[Departure]:
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


def test_nearby_sorts_by_distance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(
        cli_module,
        "load_config",
        lambda: AppConfig(default_latitude=52.5, default_longitude=13.4),
    )
    result = runner.invoke(cli_module.app, ["nearby"])
    assert result.exit_code == 0
    near_index = result.stdout.index("Near Station")
    mid_index = result.stdout.index("Mid Stop")
    far_index = result.stdout.index("Far Stop")
    assert near_index < mid_index < far_index


def test_nearby_limit_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(
        cli_module,
        "load_config",
        lambda: AppConfig(default_latitude=52.5, default_longitude=13.4),
    )
    result = runner.invoke(cli_module.app, ["nearby", "--limit", "2"])
    assert result.exit_code == 0
    assert "Near Station" in result.stdout
    assert "Mid Stop" in result.stdout
    assert "Far Stop" not in result.stdout


def test_nearby_save_updates_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(cli_module, "load_config", lambda: AppConfig())
    tmp_config_path = tmp_path / "bvg-board" / "config.toml"
    monkeypatch.setattr(config_module, "config_path", lambda: tmp_config_path)

    result = runner.invoke(
        cli_module.app,
        ["nearby", "--latitude", "52.5", "--longitude", "13.4", "--save"],
    )

    assert result.exit_code == 0
    saved = config_module.load_config(tmp_config_path)
    assert saved.default_stop_id == "900000100001"
    assert saved.default_latitude == 52.5
    assert saved.default_longitude == 13.4


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


def test_show_accepts_stop_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(cli_module, "WeatherClient", FakeWeatherClient)
    monkeypatch.setattr(cli_module, "load_config", lambda: AppConfig())
    result = runner.invoke(cli_module.app, ["show", "--stop", "900000100001"])
    assert result.exit_code == 0
    assert "Alexanderplatz" in result.stdout


def test_watch_accepts_stop_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_sleep(_seconds: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_module, "BvgClient", FakeBvgClient)
    monkeypatch.setattr(cli_module, "WeatherClient", FakeWeatherClient)
    monkeypatch.setattr(cli_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(cli_module, "load_config", lambda: AppConfig())
    result = runner.invoke(
        cli_module.app,
        ["watch", "--stop", "900000100001", "--interval", "1"],
    )
    assert result.exit_code == 0
    assert "Stopped watch." in result.stdout


def test_show_help_lists_stop_alias() -> None:
    result = runner.invoke(cli_module.app, ["show", "--help"])
    assert result.exit_code == 0
    help_output = _strip_ansi(result.stdout)
    assert "--stop" in help_output
    assert "-s" in help_output


def test_watch_help_lists_stop_alias() -> None:
    result = runner.invoke(cli_module.app, ["watch", "--help"])
    assert result.exit_code == 0
    help_output = _strip_ansi(result.stdout)
    assert "--stop" in help_output
    assert "-s" in help_output


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
