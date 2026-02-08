from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

DEFAULT_TIMEOUT_SECONDS = 10.0


class BvgApiError(RuntimeError):
    """Raised when BVG API calls fail."""


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Stop:
    id: str
    name: str
    kind: str
    location: Location
    distance_m: int | None = None


@dataclass(frozen=True)
class Departure:
    line_name: str
    direction: str
    when: datetime
    delay_seconds: int | None
    platform: str | None
    remarks: tuple[str, ...]


class BvgClient:
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

    def __enter__(self) -> BvgClient:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()

    def nearby(
        self,
        latitude: float,
        longitude: float,
        *,
        results: int = 8,
        distance_m: int | None = None,
    ) -> list[Stop]:
        params: dict[str, object] = {
            "latitude": latitude,
            "longitude": longitude,
            "results": results,
            "stops": "true",
            "poi": "false",
        }
        if distance_m is not None:
            params["distance"] = distance_m
        raw = self._get_json("/locations/nearby", params)
        if not isinstance(raw, list):
            msg = "Unexpected response shape for nearby locations"
            raise BvgApiError(msg)
        return [_parse_stop(item) for item in raw]

    def stop(self, stop_id: str) -> Stop:
        raw = self._get_json(f"/stops/{stop_id}", {})
        if not isinstance(raw, dict):
            msg = "Unexpected response shape for stop details"
            raise BvgApiError(msg)
        return _parse_stop(raw)

    def departures(
        self,
        stop_id: str,
        *,
        duration_minutes: int = 60,
        results: int = 10,
    ) -> list[Departure]:
        raw = self._get_json(
            f"/stops/{stop_id}/departures",
            {"duration": duration_minutes, "results": results},
        )
        if not isinstance(raw, dict):
            msg = "Unexpected response shape for departures"
            raise BvgApiError(msg)
        items = raw.get("departures")
        if not isinstance(items, list):
            msg = "Departures payload is missing the departures list"
            raise BvgApiError(msg)
        return [_parse_departure(item) for item in items]

    def _get_json(self, path: str, params: dict[str, object]) -> Any:
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            msg = f"BVG API request failed: {exc}"
            raise BvgApiError(msg) from exc
        return response.json()


def _parse_stop(data: object) -> Stop:
    if not isinstance(data, dict):
        msg = "Stop entry must be an object"
        raise BvgApiError(msg)

    stop_id = _as_str(data.get("id"), "stop.id")
    name = _as_str(data.get("name"), "stop.name")
    kind = _parse_stop_kind(data.get("locationType") or data.get("type"))
    location = _parse_location(data.get("location"), "stop.location")
    distance_value = data.get("distance")
    distance_m = int(distance_value) if isinstance(distance_value, int | float) else None
    return Stop(id=stop_id, name=name, kind=kind, location=location, distance_m=distance_m)


def _parse_stop_kind(value: object) -> str:
    if not isinstance(value, str):
        return "stop"
    normalized = value.lower()
    if normalized in {"station", "stop"}:
        return normalized
    return "stop"


def _parse_departure(data: object) -> Departure:
    if not isinstance(data, dict):
        msg = "Departure entry must be an object"
        raise BvgApiError(msg)

    line_name = "?"
    line_obj = data.get("line")
    if isinstance(line_obj, dict):
        maybe_line_name = line_obj.get("name")
        if isinstance(maybe_line_name, str):
            line_name = maybe_line_name

    direction = _as_str(data.get("direction"), "departure.direction")
    when_raw = data.get("when") or data.get("plannedWhen")
    when = _parse_datetime(when_raw)
    delay_seconds = _as_optional_int(data.get("delay"), "departure.delay")
    platform = _as_optional_str(data.get("platform"), "departure.platform")
    remarks = _parse_remarks(data.get("remarks"))

    return Departure(
        line_name=line_name,
        direction=direction,
        when=when,
        delay_seconds=delay_seconds,
        platform=platform,
        remarks=remarks,
    )


def _parse_location(data: object, key: str) -> Location:
    if not isinstance(data, dict):
        msg = f"{key} must be an object"
        raise BvgApiError(msg)
    latitude = _as_float(data.get("latitude"), f"{key}.latitude")
    longitude = _as_float(data.get("longitude"), f"{key}.longitude")
    return Location(latitude=latitude, longitude=longitude)


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        msg = "departure.when must be an ISO datetime string"
        raise BvgApiError(msg)
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        msg = f"Invalid datetime in departure: {value}"
        raise BvgApiError(msg) from exc


def _parse_remarks(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    messages: list[str] = []
    for item in value:
        if isinstance(item, dict):
            summary = item.get("summary")
            if isinstance(summary, str):
                messages.append(summary)
    return tuple(messages)


def _as_str(value: object, key: str) -> str:
    if isinstance(value, str):
        return value
    msg = f"{key} must be a string"
    raise BvgApiError(msg)


def _as_optional_str(value: object, key: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    msg = f"{key} must be a string"
    raise BvgApiError(msg)


def _as_float(value: object, key: str) -> float:
    if isinstance(value, int | float):
        return float(value)
    msg = f"{key} must be a number"
    raise BvgApiError(msg)


def _as_optional_int(value: object, key: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    msg = f"{key} must be an integer"
    raise BvgApiError(msg)
