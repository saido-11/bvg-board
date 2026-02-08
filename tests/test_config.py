from __future__ import annotations

from pathlib import Path

import pytest

from bvg_board.config import AppConfig, load_config


def test_load_config_defaults_when_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "does-not-exist.toml")
    assert isinstance(config, AppConfig)
    assert config.watch_interval_seconds == 30
    assert config.default_stop_id is None


def test_load_config_custom_values(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[defaults]
stop_id = "900000100001"
latitude = 52.52
longitude = 13.40
watch_interval_seconds = 45

[api]
bvg_base_url = "https://example-bvg.test"
weather_base_url = "https://example-weather.test"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_file)
    assert config.default_stop_id == "900000100001"
    assert config.default_latitude == 52.52
    assert config.default_longitude == 13.40
    assert config.watch_interval_seconds == 45
    assert config.bvg_base_url == "https://example-bvg.test"
    assert config.weather_base_url == "https://example-weather.test"


def test_load_config_rejects_invalid_interval(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[defaults]\nwatch_interval_seconds = 0", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(config_file)
