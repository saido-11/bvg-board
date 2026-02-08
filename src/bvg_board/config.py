from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from platformdirs import user_config_dir

APP_NAME = "bvg-board"
DEFAULT_BVG_BASE_URL = "https://v6.bvg.transport.rest"
DEFAULT_WEATHER_BASE_URL = "https://api.open-meteo.com"
DEFAULT_WATCH_INTERVAL_SECONDS = 30


@dataclass(frozen=True)
class AppConfig:
    default_stop_id: str | None = None
    default_latitude: float | None = None
    default_longitude: float | None = None
    watch_interval_seconds: int = DEFAULT_WATCH_INTERVAL_SECONDS
    bvg_base_url: str = DEFAULT_BVG_BASE_URL
    weather_base_url: str = DEFAULT_WEATHER_BASE_URL


def config_path() -> Path:
    directory = Path(user_config_dir(APP_NAME, appauthor=False))
    return directory / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    effective_path = path or config_path()
    if not effective_path.exists():
        return AppConfig()

    content = tomllib.loads(effective_path.read_text(encoding="utf-8"))
    defaults = _as_dict(content.get("defaults"))
    api = _as_dict(content.get("api"))

    watch_interval = _as_int(defaults.get("watch_interval_seconds"), "defaults.watch_interval_seconds")
    if watch_interval is None:
        watch_interval = DEFAULT_WATCH_INTERVAL_SECONDS
    if watch_interval <= 0:
        msg = "defaults.watch_interval_seconds must be greater than 0"
        raise ValueError(msg)

    return AppConfig(
        default_stop_id=_as_optional_str(defaults.get("stop_id"), "defaults.stop_id"),
        default_latitude=_as_optional_float(defaults.get("latitude"), "defaults.latitude"),
        default_longitude=_as_optional_float(defaults.get("longitude"), "defaults.longitude"),
        watch_interval_seconds=watch_interval,
        bvg_base_url=_as_optional_str(api.get("bvg_base_url"), "api.bvg_base_url")
        or DEFAULT_BVG_BASE_URL,
        weather_base_url=_as_optional_str(api.get("weather_base_url"), "api.weather_base_url")
        or DEFAULT_WEATHER_BASE_URL,
    )


def _as_dict(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    msg = "Expected a TOML table"
    raise ValueError(msg)


def _as_optional_str(value: object, key: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    msg = f"{key} must be a string"
    raise ValueError(msg)


def _as_optional_float(value: object, key: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    msg = f"{key} must be a number"
    raise ValueError(msg)


def _as_int(value: object, key: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    msg = f"{key} must be an integer"
    raise ValueError(msg)
