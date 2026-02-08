# bvg-board

`bvg-board` is a Python CLI that shows:
- upcoming departures for a BVG stop (via `https://v6.bvg.transport.rest`)
- current Berlin time (`Europe/Berlin`)
- current weather from Open-Meteo

## Features

- `nearby`: find nearby BVG stops from coordinates
- `show`: render one snapshot of departures + time + weather
- `watch`: live-refreshing board view (default refresh: 30 seconds)

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

## Configuration

The app reads a TOML config file from your user config directory:

- macOS: `~/Library/Application Support/bvg-board/config.toml`
- Linux: `~/.config/bvg-board/config.toml`
- Windows: `%APPDATA%\\bvg-board\\config.toml`

Example:

```toml
[defaults]
stop_id = "900000100001"
latitude = 52.5200
longitude = 13.4050
watch_interval_seconds = 30

[api]
bvg_base_url = "https://v6.bvg.transport.rest"
weather_base_url = "https://api.open-meteo.com"
```

No personal coordinates or stop IDs are hardcoded in the project. Provide them via CLI flags and/or config.

## Usage

```bash
# Find nearby stops for coordinates
bvg-board nearby --latitude 52.5200 --longitude 13.4050 --limit 5

# Save nearest stop and coordinates into config
bvg-board nearby --latitude 52.5200 --longitude 13.4050 --save

# Show one board snapshot for a stop
bvg-board show --stop-id 900000100001

# Live board with refresh every 30s (default)
bvg-board watch --stop-id 900000100001

# Override refresh interval
bvg-board watch --stop-id 900000100001 --interval 15
```

## Development

```bash
ruff check .
pytest
```
