from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from bvg_board.bvg_api import BvgApiError, BvgClient, Departure, Stop
from bvg_board.config import AppConfig, load_config, save_defaults
from bvg_board.format import format_departures_table, format_nearby_table, format_weather_line
from bvg_board.weather import CurrentWeather, WeatherApiError, WeatherClient

BERLIN_TZ = ZoneInfo("Europe/Berlin")
app = typer.Typer(help="BVG departures board with weather.", no_args_is_help=True)
console = Console()


@dataclass(frozen=True)
class ShowSnapshot:
    stop: Stop
    departures: list[Departure]
    weather: CurrentWeather
    now_berlin: datetime


@app.command()
def nearby(
    latitude: float | None = typer.Option(
        None,
        "--latitude",
        "-a",
        help="Latitude in decimal degrees.",
    ),
    longitude: float | None = typer.Option(
        None, "--longitude", "-o", help="Longitude in decimal degrees."
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        min=1,
        help="Maximum number of rows to display.",
    ),
    distance: int | None = typer.Option(
        None, "--distance", "-d", min=1, help="Maximum distance in meters."
    ),
    save: bool = typer.Option(
        False,
        "--save/--no-save",
        help="Save nearest stop id and coordinates into your user config file.",
    ),
) -> None:
    """List nearby stops for coordinates."""
    cfg = _load_config_safe()
    lat, lon = _resolve_coordinates(latitude, longitude, cfg)
    query_results = max(limit, 20)
    with BvgClient(base_url=cfg.bvg_base_url) as bvg_client:
        try:
            stops = bvg_client.nearby(lat, lon, results=query_results, distance_m=distance)
        except BvgApiError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
    sorted_stops = _sort_stops_by_distance(stops)
    visible_stops = sorted_stops[:limit]
    console.print(format_nearby_table(visible_stops))

    if save and visible_stops:
        nearest = visible_stops[0]
        saved_path = save_defaults(
            stop_id=nearest.id,
            latitude=nearest.location.latitude,
            longitude=nearest.location.longitude,
        )
        console.print(f"[green]Saved defaults to[/green] {saved_path}")


@app.command()
def show(
    stop_id: str | None = typer.Option(None, "--stop-id", "-s", help="BVG stop ID."),
    latitude: float | None = typer.Option(
        None, "--latitude", "-a", help="Latitude override for weather lookups."
    ),
    longitude: float | None = typer.Option(
        None, "--longitude", "-o", help="Longitude override for weather lookups."
    ),
    results: int = typer.Option(
        10,
        "--results",
        "-r",
        min=1,
        max=30,
        help="Number of departures to show.",
    ),
    duration: int = typer.Option(
        60, "--duration", "-d", min=1, help="Look-ahead window for departures in minutes."
    ),
) -> None:
    """Show departures, Berlin time, and current weather."""
    cfg = _load_config_safe()
    effective_stop_id = _resolve_stop_id(stop_id, cfg)
    snapshot = _fetch_snapshot(
        stop_id=effective_stop_id,
        latitude=latitude,
        longitude=longitude,
        results=results,
        duration=duration,
        cfg=cfg,
    )
    console.print(_render_snapshot(snapshot))


@app.command()
def watch(
    stop_id: str | None = typer.Option(None, "--stop-id", "-s", help="BVG stop ID."),
    latitude: float | None = typer.Option(
        None, "--latitude", "-a", help="Latitude override for weather lookups."
    ),
    longitude: float | None = typer.Option(
        None, "--longitude", "-o", help="Longitude override for weather lookups."
    ),
    results: int = typer.Option(
        10,
        "--results",
        "-r",
        min=1,
        max=30,
        help="Number of departures to show.",
    ),
    duration: int = typer.Option(
        60, "--duration", "-d", min=1, help="Look-ahead window for departures in minutes."
    ),
    interval: int | None = typer.Option(
        None,
        "--interval",
        "-i",
        min=1,
        help="Refresh interval in seconds. Defaults to config value or 30 seconds.",
    ),
) -> None:
    """Live view that refreshes departures and weather."""
    cfg = _load_config_safe()
    effective_stop_id = _resolve_stop_id(stop_id, cfg)
    refresh_seconds = interval if interval is not None else cfg.watch_interval_seconds
    if refresh_seconds <= 0:
        raise typer.BadParameter("Interval must be greater than 0.")

    with Live(console=console, auto_refresh=False) as live:
        try:
            while True:
                snapshot = _fetch_snapshot(
                    stop_id=effective_stop_id,
                    latitude=latitude,
                    longitude=longitude,
                    results=results,
                    duration=duration,
                    cfg=cfg,
                )
                live.update(
                    _render_snapshot(snapshot, refresh_seconds=refresh_seconds),
                    refresh=True,
                )
                time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            console.print("\nStopped watch.")


def _render_snapshot(snapshot: ShowSnapshot, refresh_seconds: int | None = None) -> Panel:
    header = Text(f"Stop: {snapshot.stop.name} ({snapshot.stop.id})", style="bold")
    clock = Text(f"Berlin time: {snapshot.now_berlin.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    weather = format_weather_line(snapshot.weather)
    refresh = (
        Text(f"Auto refresh: every {refresh_seconds} seconds", style="dim")
        if refresh_seconds is not None
        else Text("")
    )
    table = format_departures_table(snapshot.departures, snapshot.now_berlin)
    return Panel(Group(header, clock, weather, refresh, table), border_style="blue")


def _fetch_snapshot(
    *,
    stop_id: str,
    latitude: float | None,
    longitude: float | None,
    results: int,
    duration: int,
    cfg: AppConfig,
) -> ShowSnapshot:
    try:
        with BvgClient(base_url=cfg.bvg_base_url) as bvg_client:
            stop = bvg_client.stop(stop_id)
            departures = bvg_client.departures(stop_id, duration_minutes=duration, results=results)

        weather_lat, weather_lon = _resolve_weather_coordinates(latitude, longitude, cfg, stop)
        with WeatherClient(base_url=cfg.weather_base_url) as weather_client:
            weather = weather_client.current_weather(weather_lat, weather_lon)
    except (BvgApiError, WeatherApiError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    now_berlin = datetime.now(BERLIN_TZ)
    return ShowSnapshot(stop=stop, departures=departures, weather=weather, now_berlin=now_berlin)


def _resolve_weather_coordinates(
    latitude: float | None,
    longitude: float | None,
    cfg: AppConfig,
    stop: Stop,
) -> tuple[float, float]:
    explicit = latitude is not None and longitude is not None
    if explicit:
        return latitude, longitude
    if latitude is not None or longitude is not None:
        raise typer.BadParameter("Provide both --latitude and --longitude or neither.")

    if cfg.default_latitude is not None and cfg.default_longitude is not None:
        return cfg.default_latitude, cfg.default_longitude
    return stop.location.latitude, stop.location.longitude


def _resolve_coordinates(
    latitude: float | None,
    longitude: float | None,
    cfg: AppConfig,
) -> tuple[float, float]:
    lat = latitude if latitude is not None else cfg.default_latitude
    lon = longitude if longitude is not None else cfg.default_longitude
    if lat is None or lon is None:
        raise typer.BadParameter(
            "Latitude/longitude are required. Provide flags or defaults in config.toml."
        )
    return lat, lon


def _resolve_stop_id(stop_id: str | None, cfg: AppConfig) -> str:
    resolved = stop_id or cfg.default_stop_id
    if not resolved:
        raise typer.BadParameter(
            "Stop ID is required. Use --stop-id or defaults.stop_id in config.toml."
        )
    return resolved


def _load_config_safe() -> AppConfig:
    try:
        return load_config()
    except ValueError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


def _sort_stops_by_distance(stops: list[Stop]) -> list[Stop]:
    return sorted(stops, key=lambda stop: stop.distance_m if stop.distance_m is not None else 10**9)


if __name__ == "__main__":
    app()
