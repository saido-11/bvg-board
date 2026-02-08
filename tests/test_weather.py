from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from bvg_board.weather import WeatherApiError, WeatherClient


def test_current_weather_parses_payload(
    httpx_mock: HTTPXMock, sample_weather_payload: dict[str, object]
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^https://weather\.test/v1/forecast(\?.*)?$"),
        json=sample_weather_payload,
    )

    with WeatherClient(base_url="https://weather.test") as client:
        weather = client.current_weather(52.52, 13.4)

    assert weather.temperature_c == 3.8
    assert weather.apparent_temperature_c == 1.2
    assert weather.wind_speed_kmh == 11.4
    assert weather.weather_code == 3
    assert weather.is_day is False


def test_current_weather_missing_current_raises(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^https://weather\.test/v1/forecast(\?.*)?$"),
        json={},
    )

    with WeatherClient(base_url="https://weather.test") as client, pytest.raises(WeatherApiError):
        client.current_weather(52.52, 13.4)
