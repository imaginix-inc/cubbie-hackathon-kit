---
name: weather-before-class
description: Checks the next hours of weather in the student's city and says whether to bring an umbrella or a jacket. Use when the student asks about rain, the weather or what to wear before class.
---

# Weather Before Class

## When to use

- "Do I need an umbrella today?"
- "Is it going to rain before my 2pm lab?"
- "What should I wear to class tomorrow morning?"

Do not use it for forecasts more than 48 hours ahead.

## Setup (first time only)

The script needs `requests` 2.32.3. Install it once into its own virtual environment under HOME, which Cubbie keeps:

```bash
python3 -m venv ~/.local/share/venvs/weather-before-class && ~/.local/share/venvs/weather-before-class/bin/pip install requests==2.32.3
```

If `~/.local/share/venvs/weather-before-class/bin/python` is missing later, run this again.

## Key

This Skill needs the student's own free OpenWeather API key, saved in Cubbie as `OPENWEATHER_API_KEY`
(the student gets one at https://home.openweathermap.org/api_keys). If it is not saved yet, send the student the
secure link to save it. Never ask the student to paste the key into the chat. New OpenWeather keys can take up to
two hours to start working. Commands receive the key only when they name it, as in the run command below.

## Steps

1. Work out the city. Use the city the student just named. Otherwise run the script without `--city`; it uses the saved city.
   If no city is saved, ask the student which city their campus is in.
2. Pick units: `--units imperial` for students in the United States, otherwise `--units metric`.
3. Run from this Skill's folder:

   ```bash
   OPENWEATHER_API_KEY="$OPENWEATHER_API_KEY" ~/.local/share/venvs/weather-before-class/bin/python scripts/forecast.py --city "<City,country code>" --units <units> --hours <hours>
   ```

   Set `--hours` to cover the time the student asked about (default 12, at most 48).
   Add `--remember` the first time a student names their campus city, so later runs can leave out `--city` and `--units`.
4. If the student mentioned a class time, look at the forecast rows around that time.

## Output

Reply in two or three short lines: the recommendation first (umbrella, jacket), then the reason with the time
of the worst weather. Only show the full table when the student asks for details.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | No city given and none saved | Ask which city the student's campus is in |
| 3 | Key missing | Send the secure link to save `OPENWEATHER_API_KEY` |
| 4 | OpenWeather unreachable | Say the weather service is not reachable right now; try once more later |
| 5 | Key rejected | If the key was saved in the last two hours, ask the student to wait; otherwise ask them to save a new key |
| 6 | Unknown city | Ask for the city as "City,country code", for example "Austin,US" |
| 7 | Other OpenWeather error | Say the forecast is unavailable right now; do not retry more than once |

Never guess a forecast when the script fails.
