from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_TIMEOUT_SECONDS = 10.0


class WeatherApiError(RuntimeError):
    """Raised when Open-Meteo API calls fail."""


@dataclass(frozen=True)
class CurrentWeather:
    temperature_c: float
    apparent_temperature_c: float | None
    wind_speed_kmh: float | None
    weather_code: int | None
    is_day: bool | None


class WeatherClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"User-Agent": "bvg-board/0.1.0"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> WeatherClient:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()

    def current_weather(self, latitude: float, longitude: float) -> CurrentWeather:
        payload = self._get_json(
            "/v1/forecast",
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,apparent_temperature,wind_speed_10m,weather_code,is_day",
                "timezone": "Europe/Berlin",
            },
        )
        if not isinstance(payload, dict):
            msg = "Unexpected weather response shape"
            raise WeatherApiError(msg)
        current = payload.get("current")
        if not isinstance(current, dict):
            msg = "Weather payload is missing current weather data"
            raise WeatherApiError(msg)
        return CurrentWeather(
            temperature_c=_as_float(current.get("temperature_2m"), "current.temperature_2m"),
            apparent_temperature_c=_as_optional_float(
                current.get("apparent_temperature"), "current.apparent_temperature"
            ),
            wind_speed_kmh=_as_optional_float(current.get("wind_speed_10m"), "current.wind_speed_10m"),
            weather_code=_as_optional_int(current.get("weather_code"), "current.weather_code"),
            is_day=_as_optional_bool(current.get("is_day"), "current.is_day"),
        )

    def _get_json(self, path: str, params: dict[str, object]) -> Any:
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            msg = f"Open-Meteo request failed: {exc}"
            raise WeatherApiError(msg) from exc
        return response.json()


def _as_float(value: object, key: str) -> float:
    if isinstance(value, int | float):
        return float(value)
    msg = f"{key} must be a number"
    raise WeatherApiError(msg)


def _as_optional_float(value: object, key: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    msg = f"{key} must be a number"
    raise WeatherApiError(msg)


def _as_optional_int(value: object, key: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    msg = f"{key} must be an integer"
    raise WeatherApiError(msg)


def _as_optional_bool(value: object, key: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    msg = f"{key} must be a boolean"
    raise WeatherApiError(msg)
