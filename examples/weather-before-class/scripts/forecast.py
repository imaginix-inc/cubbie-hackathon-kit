#!/usr/bin/env python3
"""Say whether the student needs an umbrella or a jacket in the next few hours.

Calls the free OpenWeather 5 day / 3 hour forecast API with the student's own key, which Cubbie
injects as OPENWEATHER_API_KEY. The student's city and units are remembered in $SKILL_DATA_DIR,
which survives sandbox restarts and Skill updates.

Exit codes: 0 ok, 2 bad arguments or no city, 3 key missing, 4 network error, 5 key rejected,
6 unknown city, 7 other API error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.openweathermap.org/data/2.5/forecast"
SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample_forecast.json"
WET = {"Rain", "Drizzle", "Thunderstorm"}
COLD = {"metric": 15, "imperial": 59}
SYMBOL = {"metric": "°C", "imperial": "°F"}


def fail(message: str, code: int):
    print(message, file=sys.stderr)
    sys.exit(code)


def settings_file() -> Path | None:
    data_dir = os.environ.get("SKILL_DATA_DIR")
    return Path(data_dir) / "settings.json" if data_dir else None


def load_settings() -> dict:
    path = settings_file()
    try:
        return json.loads(path.read_text()) if path else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    path = settings_file()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings))


def fetch(city: str, units: str, steps: int) -> dict:
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        fail("OPENWEATHER_API_KEY is not set. Ask the student to save their OpenWeather API key.", 3)
    import requests  # installed by Cubbie from cubbie.yaml

    try:
        response = requests.get(API, params={"q": city, "appid": key, "units": units, "cnt": steps}, timeout=15)
    except requests.RequestException as exc:
        # Never print the exception text: it can contain the request URL, which includes the key.
        fail(f"Could not reach OpenWeather ({type(exc).__name__}). Try again later.", 4)
    if response.status_code == 401:
        fail("OpenWeather rejected the API key. New keys can take up to 2 hours to start working.", 5)
    if response.status_code == 404:
        fail(f"OpenWeather does not know the city {city!r}. Ask for 'City,country code', for example 'Austin,US'.", 6)
    if response.status_code != 200:
        fail(f"OpenWeather returned HTTP {response.status_code}. Try again later.", 7)
    return response.json()


def summarize(data: dict, units: str) -> str:
    city = data.get("city") or {}
    offset = timezone(timedelta(seconds=int(city.get("timezone") or 0)))
    symbol = SYMBOL[units]
    rows, wettest, coldest = [], None, None
    for slot in data.get("list") or []:
        when = datetime.fromtimestamp(slot["dt"], offset)
        weather = (slot.get("weather") or [{}])[0]
        chance = round(100 * float(slot.get("pop") or 0))
        wet = chance >= 40 or weather.get("main") in WET or bool(slot.get("rain"))
        feels = round(slot["main"]["feels_like"])
        rows.append(f"{when:%a %H:%M}  {round(slot['main']['temp'])}{symbol} (feels {feels}{symbol})  "
                    f"{weather.get('description', 'unknown')}  rain chance {chance}%")
        if wet and (wettest is None or chance > wettest[1]):
            wettest = (when, chance)
        if coldest is None or feels < coldest[1]:
            coldest = (when, feels)
    if not rows:
        return "OpenWeather returned no forecast for this city."
    umbrella = (f"Umbrella: yes, {wettest[1]}% chance of rain around {wettest[0]:%H:%M}." if wettest
                else "Umbrella: no rain expected.")
    jacket = (f"Jacket: yes, it feels like {coldest[1]}{symbol} around {coldest[0]:%H:%M}." if coldest[1] < COLD[units]
              else f"Jacket: not needed, the coldest it feels is {coldest[1]}{symbol}.")
    place = ", ".join(part for part in (city.get("name"), city.get("country")) if part)
    return "\n".join([f"{place or 'Forecast'} (local time)", *rows, umbrella, jacket])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", help="'City,country code', for example 'Austin,US'; defaults to the saved city")
    parser.add_argument("--units", choices=["metric", "imperial"], help="defaults to the saved units, else metric")
    parser.add_argument("--hours", type=int, default=12, help="how far ahead to look, 3 to 48 (default 12)")
    parser.add_argument("--remember", action="store_true", help="save the city and units for later runs")
    parser.add_argument("--sample", action="store_true", help="offline demo with the metric data in assets/sample_forecast.json")
    args = parser.parse_args(argv)

    settings = load_settings()
    city = ",".join(part.strip() for part in (args.city or settings.get("city") or "").split(",") if part.strip())
    units = args.units or settings.get("units") or "metric"
    if not city and not args.sample:
        fail("No city given and none saved. Ask the student which city their campus is in.", 2)
    if args.remember and city:
        save_settings({"city": city, "units": units})
    steps = max(1, min(16, -(-args.hours // 3)))
    if args.sample:
        data, units = json.loads(SAMPLE.read_text()), "metric"
        data["list"] = data["list"][:steps]
    else:
        data = fetch(city, units, steps)
    print(summarize(data, units))
    return 0


if __name__ == "__main__":
    sys.exit(main())
