from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from bvg_board.bvg_api import BvgApiError, BvgClient


def test_nearby_parses_stops(httpx_mock: HTTPXMock, sample_stop_payload: dict[str, object]) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^https://example\.test/locations/nearby(\?.*)?$"),
        json=[sample_stop_payload],
    )

    with BvgClient(base_url="https://example.test") as client:
        stops = client.nearby(52.52, 13.4, results=1)

    assert len(stops) == 1
    assert stops[0].id == "900000100001"
    assert stops[0].name == "Alexanderplatz"
    assert stops[0].distance_m == 120


def test_departures_parses_data(httpx_mock: HTTPXMock, sample_departure_payload: dict[str, object]) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^https://example\.test/stops/900000100001/departures(\?.*)?$"),
        json=sample_departure_payload,
    )

    with BvgClient(base_url="https://example.test") as client:
        departures = client.departures("900000100001", duration_minutes=60, results=1)

    assert len(departures) == 1
    assert departures[0].line_name == "U2"
    assert departures[0].direction == "Ruhleben"
    assert departures[0].delay_seconds == 60


def test_stop_http_error_raises(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="GET", url="https://example.test/stops/nope", status_code=404)

    with BvgClient(base_url="https://example.test") as client:
        with pytest.raises(BvgApiError):
            client.stop("nope")
