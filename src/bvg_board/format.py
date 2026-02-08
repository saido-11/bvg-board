from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from rich.table import Table
from rich.text import Text

from bvg_board.bvg_api import Departure, Stop
from bvg_board.weather import CurrentWeather

WEATHER_LABELS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Heavy rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


def format_nearby_table(stops: Sequence[Stop]) -> Table:
    table = Table(title="Nearby BVG Stops", expand=True)
    table.add_column("name", style="bold")
    table.add_column("type", justify="center", no_wrap=True)
    table.add_column("distance_m", justify="right", no_wrap=True)
    table.add_column("id", style="cyan", no_wrap=True)

    for stop in stops:
        distance = str(stop.distance_m) if stop.distance_m is not None else "-"
        table.add_row(stop.name, stop.kind, distance, stop.id)
    return table


def format_departures_table(departures: Sequence[Departure], now: datetime) -> Table:
    table = Table(title="Next Departures", expand=True)
    table.add_column("Line", style="cyan", no_wrap=True)
    table.add_column("Direction", style="bold")
    table.add_column("When", no_wrap=True)
    table.add_column("In", justify="right")
    table.add_column("Platform", justify="center", no_wrap=True)
    table.add_column("Delay", justify="right", no_wrap=True)

    for departure in departures:
        delay = _format_delay(departure.delay_seconds)
        eta = _minutes_until(departure.when, now)
        when_display = departure.when.strftime("%H:%M:%S")
        table.add_row(
            departure.line_name,
            departure.direction,
            when_display,
            eta,
            departure.platform or "-",
            delay,
        )

    if not departures:
        table.add_row("-", "No departures found", "-", "-", "-", "-")
    return table


def format_weather_line(weather: CurrentWeather) -> Text:
    code_label = weather_code_label(weather.weather_code)
    temp = f"{weather.temperature_c:.1f}°C"
    apparent = (
        f", feels like {weather.apparent_temperature_c:.1f}°C"
        if weather.apparent_temperature_c is not None
        else ""
    )
    wind = f", wind {weather.wind_speed_kmh:.1f} km/h" if weather.wind_speed_kmh is not None else ""
    day_night = "" if weather.is_day is None else ", daytime" if weather.is_day else ", nighttime"
    return Text(f"Weather: {code_label}, {temp}{apparent}{wind}{day_night}")


def weather_code_label(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WEATHER_LABELS.get(code, f"Code {code}")


def _minutes_until(when: datetime, now: datetime) -> str:
    delta_seconds = int((when - now).total_seconds())
    if delta_seconds <= 60:
        return "now"
    minutes = round(delta_seconds / 60)
    return f"{minutes} min"


def _format_delay(delay_seconds: int | None) -> str:
    if delay_seconds is None:
        return "-"
    if delay_seconds <= 0:
        return "on time"
    minutes = round(delay_seconds / 60)
    return f"+{minutes} min"
