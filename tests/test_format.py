from __future__ import annotations

from datetime import datetime

from bvg_board.bvg_api import Departure, Stop
from bvg_board.format import format_departures_table, format_nearby_table, weather_code_label


def test_format_nearby_table_has_rows(sample_stop: Stop) -> None:
    table = format_nearby_table([sample_stop])
    assert table.row_count == 1


def test_format_departures_table_has_rows(sample_departure: Departure) -> None:
    now = datetime(2026, 2, 8, 20, 0, tzinfo=sample_departure.when.tzinfo)
    table = format_departures_table([sample_departure], now)
    assert table.row_count == 1


def test_weather_code_label_fallback() -> None:
    assert weather_code_label(999) == "Code 999"
