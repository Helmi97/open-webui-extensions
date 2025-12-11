"""
title: Weather Tool
author: Helmi Chaouachi
repo_url: https://github.com/Helmi97/open-webui-extensions/tree/main/weather_tool
version: 1.0.6
license: MIT
required_open_webui_version: 0.6.34
description: Enhanced weather tool with a stylish widget and comprehensive data from Open-Meteo (free, no API key required).

# Original projects and credit:
# - Keyless Weather by spyci
# - WeatherWeaver by PureGrain at SLA Ops, LLC
#   https://github.com/PureGrain/my-openwebui/tree/main/tools/weatherweaver
"""

import requests
import urllib.parse
import datetime
from pydantic import BaseModel, Field
from typing import Optional

import html
from fastapi.responses import HTMLResponse


def get_city_info(city: str):
    """Get coordinates and timezone for a city."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=en&format=json"
    response = requests.get(url)

    if response.status_code == 200:
        try:
            data = response.json()["results"][0]
            return data["latitude"], data["longitude"], data["timezone"]
        except (KeyError, IndexError):
            print(f"City '{city}' not found")
            return None
    else:
        print(f"Failed to retrieve data for city '{city}': {response.status_code}")
        return None


wmo_weather_codes = {
    "0": "Clear sky",
    "1": "Mainly clear",
    "2": "Partly cloudy",
    "3": "Overcast",
    "45": "Foggy",
    "48": "Depositing rime fog",
    "51": "Light drizzle",
    "53": "Moderate drizzle",
    "55": "Dense drizzle",
    "56": "Light freezing drizzle",
    "57": "Dense freezing drizzle",
    "61": "Slight rain",
    "63": "Moderate rain",
    "65": "Heavy rain",
    "66": "Light freezing rain",
    "67": "Heavy freezing rain",
    "71": "Slight snow",
    "73": "Moderate snow",
    "75": "Heavy snow",
    "77": "Snow grains",
    "80": "Slight rain showers",
    "81": "Moderate rain showers",
    "82": "Violent rain showers",
    "85": "Slight snow showers",
    "86": "Heavy snow showers",
    "95": "Thunderstorm",
    "96": "Thunderstorm with slight hail",
    "99": "Thunderstorm with heavy hail",
}

weather_icon_and_accent = {
    0: ("☀️", "#facc15"),  # Clear sky
    1: ("🌤️", "#fde047"),  # Mainly clear
    2: ("⛅", "#fbbf24"),  # Partly cloudy
    3: ("☁️", "#9ca3af"),  # Overcast
    45: ("🌫️", "#a1a1aa"),  # Fog
    48: ("🌫️", "#a1a1aa"),
    51: ("🌦️", "#38bdf8"),
    53: ("🌦️", "#38bdf8"),
    55: ("🌧️", "#0ea5e9"),
    56: ("🌧️", "#38bdf8"),
    57: ("🌧️", "#0ea5e9"),
    61: ("🌧️", "#38bdf8"),
    63: ("🌧️", "#0ea5e9"),
    65: ("🌧️", "#0284c7"),
    66: ("🌧️", "#38bdf8"),
    67: ("🌧️", "#0ea5e9"),
    71: ("❄️", "#e5e7eb"),
    73: ("❄️", "#e5e7eb"),
    75: ("❄️", "#f9fafb"),
    77: ("❄️", "#e5e7eb"),
    80: ("🌧️", "#38bdf8"),
    81: ("🌧️", "#0ea5e9"),
    82: ("🌧️", "#0284c7"),
    85: ("❄️", "#e5e7eb"),
    86: ("❄️", "#f9fafb"),
    95: ("⛈️", "#a855f7"),
    96: ("⛈️", "#a855f7"),
    99: ("⛈️", "#a855f7"),
}


def get_weather_icon_and_accent(code: int) -> tuple[str, str]:
    try:
        code_int = int(code)
    except (TypeError, ValueError):
        return "❔", "#38bdf8"
    return weather_icon_and_accent.get(code_int, ("❔", "#38bdf8"))


def fetch_weather_data(base_url, params):
    """Fetch data from Open-Meteo API."""
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            return f"Error fetching weather data: {data.get('reason', 'Unknown error')}"
        return data
    except requests.RequestException as e:
        return f"Error fetching weather data: {str(e)}"


def format_date(date_str, date_format="%Y-%m-%dT%H:%M", output_format="%I:%M %p"):
    """Format datetime string."""
    dt = datetime.datetime.strptime(date_str, date_format)
    return dt.strftime(output_format)


def build_weather_widget_html(
    *,
    city: str,
    local_date: str,
    local_time: str,
    tz_abbr: str,
    icon: str,
    weather_desc: str,
    temp: int,
    feels_like: int,
    humidity: int,
    cloud_cover: int,
    pressure: float,
    wind_speed: int,
    wind_gusts: int,
    precip: float,
    temp_symbol: str,
    wind_symbol: str,
    precip_symbol: str,
    unit_system_label: str,
) -> str:
    city_safe = html.escape(city)
    desc_safe = html.escape(weather_desc)

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta
    name="viewport"
    content="width=device-width, initial-scale=1, viewport-fit=cover"
  />
  <title>Weather in {city_safe}</title>
  <style>
    :root {{
      color-scheme: dark;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      padding: 16px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text",
                   "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.28), #020617);
      color: #f9fafb;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .weather-root {{
      width: 100%;
      max-width: 800px;
    }}

    .card {{
      position: relative;
      border-radius: 24px;
      padding: 20px 20px 18px;
      background: linear-gradient(145deg, rgba(15, 23, 42, 0.98), rgba(8, 47, 73, 0.96));
      box-shadow:
        0 22px 60px rgba(15, 23, 42, 0.95),
        0 0 0 1px rgba(148, 163, 184, 0.16);
      overflow: hidden;
      backdrop-filter: blur(18px);
    }}

    .card::before {{
      content: "";
      position: absolute;
      inset: -40%;
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.35), transparent 55%),
        radial-gradient(circle at bottom right, rgba(129, 140, 248, 0.35), transparent 55%);
      opacity: 0.9;
      pointer-events: none;
      z-index: -1;
    }}

    .card::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at top right, rgba(15, 23, 42, 0.72), transparent 55%);
      mix-blend-mode: soft-light;
      pointer-events: none;
      z-index: -1;
    }}

    .card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 12px;
    }}

    .location-block {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .city-name {{
      font-weight: 600;
      font-size: 1.1rem;
      letter-spacing: 0.02em;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .city-dot {{
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: #22c55e;
      box-shadow: 0 0 12px rgba(34, 197, 94, 0.8);
    }}

    .subline {{
      font-size: 0.78rem;
      color: rgba(226, 232, 240, 0.75);
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .tag-pill {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.45);
      font-size: 0.7rem;
      color: rgba(226, 232, 240, 0.8);
      backdrop-filter: blur(12px);
      background: rgba(15, 23, 42, 0.7);
    }}

    .tag-dot {{
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: var(--accent, #38bdf8);
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.9);
    }}

    .card-main {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(0, 1.6fr);
      gap: 10px;
      align-items: stretch;
    }}

    .hero {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      justify-content: center;
    }}

    .hero-top {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .hero-icon {{
      font-size: 3.25rem;
      line-height: 1;
      filter: drop-shadow(0 0 10px rgba(15, 23, 42, 0.4));
      animation: float 4s ease-in-out infinite;
    }}

    .hero-temp-wrapper {{
      display: flex;
      align-items: baseline;
      gap: 4px;
    }}

    .hero-temp {{
      font-size: 3rem;
      font-weight: 600;
      letter-spacing: -0.03em;
    }}

    .hero-unit {{
      font-size: 1.1rem;
      font-weight: 500;
      color: rgba(226, 232, 240, 0.85);
    }}

    .hero-desc {{
      font-size: 0.95rem;
      color: rgba(226, 232, 240, 0.9);
      margin-top: 2px;
    }}

    .hero-feels {{
      font-size: 0.8rem;
      color: rgba(209, 213, 219, 0.85);
    }}

    .side-panel {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      border-radius: 18px;
      padding: 10px 10px 9px;
      background: radial-gradient(circle at top left, rgba(15, 23, 42, 0.7), rgba(15, 23, 42, 0.95));
      box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.3);
    }}

    .side-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.8rem;
      color: rgba(226, 232, 240, 0.78);
    }}

    .side-header span.strong {{
      font-weight: 500;
      color: rgba(248, 250, 252, 0.96);
    }}

    .side-header .chip {{
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.45);
      background: rgba(15, 23, 42, 0.85);
    }}

    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }}

    .metric {{
      border-radius: 14px;
      padding: 7px 8px 6px;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(148, 163, 184, 0.35);
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}

    .metric-label {{
      font-size: 0.72rem;
      color: rgba(148, 163, 184, 0.95);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }}

    .metric-badge {{
      font-size: 0.65rem;
      padding: 1px 6px;
      border-radius: 999px;
      border: 1px solid rgba(51, 65, 85, 0.9);
      color: rgba(148, 163, 184, 0.95);
    }}

    .metric-value {{
      font-size: 0.98rem;
      font-weight: 500;
      color: rgba(248, 250, 252, 0.98);
    }}

    .metric-value.main {{
      color: var(--accent, #38bdf8);
    }}

    .metric-hint {{
      font-size: 0.72rem;
      color: rgba(148, 163, 184, 0.95);
    }}

    .card-footer {{
      margin-top: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-size: 0.74rem;
      color: rgba(148, 163, 184, 0.95);
      flex-wrap: wrap;
    }}

    .footer-left {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .footer-dot {{
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: rgba(148, 163, 184, 1);
    }}

    .footer-right {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .badge {{
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.45);
      background: rgba(15, 23, 42, 0.92);
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}

    .badge span.accent {{
      color: var(--accent, #38bdf8);
      font-weight: 500;
    }}

    .badge .icon {{
      font-size: 0.85rem;
    }}

    @media (max-width: 480px) {{
      .card {{
        padding: 16px 14px 14px;
        border-radius: 20px;
      }}
      .card-main {{
        grid-template-columns: minmax(0, 1fr);
      }}
      .hero {{
        order: -1;
      }}
      .hero-top {{
        justify-content: flex-start;
      }}
      .hero-temp {{
        font-size: 2.6rem;
      }}
      .hero-icon {{
        font-size: 2.7rem;
      }}
    }}

    @keyframes float {{
      0%   {{ transform: translateY(0px); }}
      50%  {{ transform: translateY(-6px); }}
      100% {{ transform: translateY(0px); }}
    }}
  </style>
</head>
<body>
  <div class="weather-root">
    <article class="card" style="--accent: {html.escape('#' + temp_symbol.encode('utf-8').hex()) if False else '#38bdf8'}">
      <header class="card-header">
        <div class="location-block">
          <div class="city-name">
            <span class="city-dot"></span>
            <span>{city_safe}</span>
          </div>
          <div class="subline">
            <span>{local_date}</span>
            <span>·</span>
            <span>{local_time} {tz_abbr}</span>
          </div>
        </div>
        <div class="tag-pill">
          <span class="tag-dot"></span>
          <span>{unit_system_label} units</span>
        </div>
      </header>

      <section class="card-main">
        <div class="hero">
          <div class="hero-top">
            <div class="hero-icon">{icon}</div>
            <div class="hero-temp-wrapper">
              <div class="hero-temp">{temp}</div>
              <div class="hero-unit">{temp_symbol}</div>
            </div>
          </div>
          <div class="hero-desc">{desc_safe}</div>
          <div class="hero-feels">Feels like {feels_like}{temp_symbol}</div>
        </div>

        <aside class="side-panel">
          <div class="side-header">
            <span class="strong">Right now</span>
          </div>
          <div class="metrics-grid">
            <div class="metric">
              <div class="metric-label">
                <span>Humidity</span>
                <span class="metric-badge">Cloud</span>
              </div>
              <div class="metric-value main">{humidity}%</div>
              <div class="metric-hint">Cloud cover {cloud_cover}%</div>
            </div>
            <div class="metric">
              <div class="metric-label">
                <span>Wind</span>
                <span class="metric-badge">Gusts</span>
              </div>
              <div class="metric-value main">{wind_speed} {wind_symbol}</div>
              <div class="metric-hint">Up to {wind_gusts} {wind_symbol}</div>
            </div>
            <div class="metric">
              <div class="metric-label">
                <span>Pressure</span>
                <span class="metric-badge">Sea level</span>
              </div>
              <div class="metric-value">{pressure:.1f} hPa</div>
              <div class="metric-hint">Stable atmosphere</div>
            </div>
            <div class="metric">
              <div class="metric-label">
                <span>Precipitation</span>
                <span class="metric-badge">Last hour</span>
              </div>
              <div class="metric-value">{precip:.2f} {precip_symbol}</div>
              <div class="metric-hint">{'Dry right now' if precip == 0 else 'Active showers'}</div>
            </div>
          </div>
        </aside>
      </section>

      <footer class="card-footer">
        <div class="footer-left">
          <span class="footer-dot"></span>
          <span>Data by Open-Meteo</span>
        </div>
        <div class="footer-right">
          <div class="badge">
            <span class="icon">🌡️</span>
            <span>Real feel {feels_like}{temp_symbol}</span>
          </div>
        </div>
      </footer>
    </article>
  </div>
</body>
</html>
"""
    return html_content


def build_forecast_widget_html(
    *,
    city: str,
    days: int,
    tz_abbr: str,
    unit_system_label: str,
    temp_symbol: str,
    wind_symbol: str,
    precip_symbol: str,
    entries: list[dict],
) -> str:
    """
    Build a responsive multi day forecast widget as HTML.

    entries: list of dicts with keys:
        date_label, day_label, icon, weather_desc,
        temp_max, temp_min, sunrise, sunset,
        uv_index, precip_prob, precip_sum,
        wind_max, wind_gusts
    """
    city_safe = html.escape(city)

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta
    name="viewport"
    content="width=device-width, initial-scale=1, viewport-fit=cover"
  />
  <title>{days}-Day Forecast for {city_safe}</title>
  <style>
    :root {{
      color-scheme: dark;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      padding: 16px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text",
                   "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.28), #020617);
      color: #f9fafb;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .forecast-root {{
      width: 100%;
      max-width: 960px;
    }}

    .forecast-card {{
      position: relative;
      border-radius: 24px;
      padding: 18px 18px 16px;
      background: linear-gradient(145deg, rgba(15, 23, 42, 0.98), rgba(8, 47, 73, 0.96));
      box-shadow:
        0 22px 60px rgba(15, 23, 42, 0.95),
        0 0 0 1px rgba(148, 163, 184, 0.16);
      overflow: hidden;
      backdrop-filter: blur(18px);
    }}

    .forecast-card::before {{
      content: "";
      position: absolute;
      inset: -40%;
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.35), transparent 55%),
        radial-gradient(circle at bottom right, rgba(129, 140, 248, 0.35), transparent 55%);
      opacity: 0.8;
      pointer-events: none;
      z-index: -1;
    }}

    .forecast-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }}

    .forecast-title-block {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .forecast-title-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .forecast-dot {{
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: #22c55e;
      box-shadow: 0 0 12px rgba(34, 197, 94, 0.8);
    }}

    .forecast-title {{
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}

    .forecast-sub {{
      font-size: 0.8rem;
      color: rgba(226, 232, 240, 0.8);
    }}

    .forecast-tag {{
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.45);
      font-size: 0.72rem;
      color: rgba(226, 232, 240, 0.9);
      white-space: nowrap;
      backdrop-filter: blur(12px);
      background: rgba(15, 23, 42, 0.7);
    }}

    .forecast-strip {{
      display: flex;
      gap: 10px;
      overflow-x: auto;
      padding-bottom: 4px;
      margin: 0 -4px;
      padding-left: 4px;
      padding-right: 4px;
      scroll-snap-type: x mandatory;
    }}

    .forecast-strip::-webkit-scrollbar {{
      height: 5px;
    }}

    .forecast-strip::-webkit-scrollbar-track {{
      background: transparent;
    }}

    .forecast-strip::-webkit-scrollbar-thumb {{
      background: rgba(148, 163, 184, 0.5);
      border-radius: 999px;
    }}

    .day-card {{
      flex: 0 0 160px;
      max-width: 180px;
      scroll-snap-align: start;
      border-radius: 18px;
      padding: 10px 10px 9px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(148, 163, 184, 0.35);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .day-header {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}

    .day-label {{
      font-size: 0.82rem;
      font-weight: 500;
      color: rgba(248, 250, 252, 0.96);
    }}

    .day-date {{
      font-size: 0.72rem;
      color: rgba(148, 163, 184, 0.95);
    }}

    .day-main {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
    }}

    .day-icon {{
      font-size: 1.5rem;
      line-height: 1;
    }}

    .day-temp {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 2px;
      font-size: 0.86rem;
    }}

    .temp-high {{
      color: rgba(248, 250, 252, 0.98);
      font-weight: 500;
    }}

    .temp-low {{
      color: rgba(148, 163, 184, 0.95);
    }}

    .day-desc {{
      font-size: 0.78rem;
      color: rgba(226, 232, 240, 0.9);
      min-height: 2.1em;
    }}

    .day-metrics {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 4px;
      font-size: 0.7rem;
      color: rgba(148, 163, 184, 0.95);
    }}

    .metric-item {{
      display: flex;
      flex-direction: column;
      gap: 1px;
    }}

    .metric-label {{
      font-size: 0.7rem;
    }}

    .metric-value {{
      font-size: 0.76rem;
      color: rgba(248, 250, 252, 0.96);
    }}

    .footer-row {{
      margin-top: 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-size: 0.72rem;
      color: rgba(148, 163, 184, 0.95);
      flex-wrap: wrap;
    }}

    @media (max-width: 640px) {{
      body {{
        padding: 12px;
      }}
      .forecast-card {{
        padding: 14px 12px 12px;
        border-radius: 20px;
      }}
      .day-card {{
        flex-basis: 150px;
      }}
    }}
  </style>
</head>
<body>
  <div class="forecast-root">
    <article class="forecast-card">
      <header class="forecast-header">
        <div class="forecast-title-block">
          <div class="forecast-title-row">
            <span class="forecast-dot"></span>
            <span class="forecast-title">{days}-Day Forecast · {city_safe}</span>
          </div>
          <p class="forecast-sub">{tz_abbr} · {unit_system_label} units</p>
        </div>
        <div class="forecast-tag">
          High / Low · UV · Wind · Rain
        </div>
      </header>

      <section class="forecast-strip">
"""
    for entry in entries:
        desc_safe = html.escape(entry["weather_desc"])
        html_content += f"""
        <article class="day-card">
          <header class="day-header">
            <span class="day-label">{html.escape(entry["day_label"])}</span>
            <span class="day-date">{html.escape(entry["date_label"])}</span>
          </header>

          <div class="day-main">
            <div class="day-icon">{entry["icon"]}</div>
            <div class="day-temp">
              <span class="temp-high">{entry["temp_max"]}{temp_symbol}</span>
              <span class="temp-low">{entry["temp_min"]}{temp_symbol}</span>
            </div>
          </div>

          <p class="day-desc">{desc_safe}</p>

          <div class="day-metrics">
            <div class="metric-item">
              <span class="metric-label">Sunrise</span>
              <span class="metric-value">{entry["sunrise"]}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Sunset</span>
              <span class="metric-value">{entry["sunset"]}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">UV max</span>
              <span class="metric-value">{entry["uv_index"]}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Rain</span>
              <span class="metric-value">{entry["precip_prob"]}% · {entry["precip_sum"]} {precip_symbol}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Wind</span>
              <span class="metric-value">{entry["wind_max"]} {wind_symbol}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Gusts</span>
              <span class="metric-value">{entry["wind_gusts"]} {wind_symbol}</span>
            </div>
          </div>
        </article>
"""
    html_content += """
      </section>

      <footer class="footer-row">
        <span>Daily aggregates from Open-Meteo</span>
        <span>Times in local timezone</span>
      </footer>
    </article>
  </div>
</body>
</html>
"""
    return html_content


class Tools:
    class Valves(BaseModel):
        default_location: str = Field(
            default="Berlin",
            description="Default city for weather lookups (e.g., 'Berlin', 'New York', 'Tokyo')",
        )
        unit_system: str = Field(
            default="metric",
            description="Default is: Metric -- Unit system: 'imperial' (°F, mph, inches) or 'metric' (°C, km/h, mm)",
        )

    class UserValves(BaseModel):
        user_location: Optional[str] = Field(
            default=None,
            description="Your preferred city for weather lookups (overrides default)",
        )
        user_unit_system: Optional[str] = Field(
            default=None,
            description="Your preferred units: 'imperial' or 'metric' (overrides default)",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.user_valves = self.UserValves()
        print(f"DEBUG: Initialized user_valves: {self.user_valves}")
        self.citation = True

    def _get_location(self, city: Optional[str] = None) -> str:
        """Get location: provided > user preference > default."""
        print(
            f"DEBUG: city={city}, user_location={self.user_valves.user_location}, default_location={self.valves.default_location}"
        )
        if city:
            return city
        return self.user_valves.user_location or self.valves.default_location

    def _get_units(self) -> dict:
        """Get unit settings based on system preference."""
        system = self.user_valves.user_unit_system or self.valves.unit_system

        if system == "metric":
            return {
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
                "temp_symbol": "°C",
                "wind_symbol": "km/h",
                "precip_symbol": "mm",
            }
        else:  # imperial
            return {
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "temp_symbol": "°F",
                "wind_symbol": "mph",
                "precip_symbol": "in",
            }

    def get_current_weather(self, city: Optional[str] = None) -> HTMLResponse:
        """
        Get comprehensive current weather for a given city and render
        a modern responsive HTML widget that Open WebUI embeds in-chat.
        """
        city = self._get_location(city)
        if not city:
            error_html = "<p style='font-family: system-ui; padding: 12px;'>Please provide a city name or set a default location in settings.</p>"
            return HTMLResponse(
                content=error_html, headers={"Content-Disposition": "inline"}
            )

        city_info = get_city_info(city)
        if not city_info:
            error_html = f"<p style='font-family: system-ui; padding: 12px;'>Could not find city: {html.escape(str(city))}</p>"
            return HTMLResponse(
                content=error_html, headers={"Content-Disposition": "inline"}
            )

        lat, lng, tmzone = city_info

        # Respect user / default unit system
        unit_cfg = self._get_units()

        base_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,rain,showers,snowfall,weather_code,cloud_cover,"
                "pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
            ),
            "timezone": tmzone,
            "temperature_unit": unit_cfg["temperature_unit"],
            "wind_speed_unit": unit_cfg["wind_speed_unit"],
            "precipitation_unit": unit_cfg["precipitation_unit"],
            "forecast_days": 1,
        }

        data = fetch_weather_data(base_url, params)
        if isinstance(data, str):
            # fetch_weather_data already formatted an error string
            error_html = f"<p style='font-family: system-ui; padding: 12px;'>Error fetching weather data: {html.escape(data)}</p>"
            return HTMLResponse(
                content=error_html, headers={"Content-Disposition": "inline"}
            )

        current = data["current"]

        # Time formatting
        try:
            dt = datetime.datetime.strptime(current["time"], "%Y-%m-%dT%H:%M")
        except ValueError:
            # Fallback if format ever changes
            dt = datetime.datetime.fromisoformat(current["time"])

        local_date = dt.strftime("%A, %b %d")
        local_time = dt.strftime("%I:%M %p").lstrip("0")
        tz_abbr = data.get("timezone_abbreviation", "")

        # Weather description and visuals
        weather_code = current.get("weather_code", 0)
        weather_desc = wmo_weather_codes.get(str(weather_code), "Unknown")
        icon, accent = get_weather_icon_and_accent(weather_code)

        # Numbers
        temp = round(current["temperature_2m"])
        feels_like = round(current["apparent_temperature"])
        humidity = round(current["relative_humidity_2m"])
        cloud_cover = round(current["cloud_cover"])
        pressure = float(current["pressure_msl"])
        wind_speed = round(current["wind_speed_10m"])
        wind_gusts = round(current["wind_gusts_10m"])
        precip = float(current.get("precipitation", 0.0))

        temp_sym = unit_cfg["temp_symbol"]
        wind_sym = unit_cfg["wind_symbol"]
        precip_sym = unit_cfg["precip_symbol"]

        unit_system_label = (
            "Metric" if unit_cfg["temperature_unit"] == "celsius" else "Imperial"
        )

        html_content = build_weather_widget_html(
            city=city,
            local_date=local_date,
            local_time=local_time,
            tz_abbr=tz_abbr,
            icon=icon,
            weather_desc=weather_desc,
            temp=temp,
            feels_like=feels_like,
            humidity=humidity,
            cloud_cover=cloud_cover,
            pressure=pressure,
            wind_speed=wind_speed,
            wind_gusts=wind_gusts,
            precip=precip,
            temp_symbol=temp_sym,
            wind_symbol=wind_sym,
            precip_symbol=precip_sym,
            unit_system_label=unit_system_label,
        )

        # Pass accent into CSS if you want per-condition theming
        html_content = html_content.replace(
            "#38bdf8",
            accent,
            1,
        )

        return HTMLResponse(
            content=html_content, headers={"Content-Disposition": "inline"}
        )

    def get_weather_forecast(
        self, city: Optional[str] = None, days: int = 7
    ) -> HTMLResponse:
        """
        Get weather forecast for a city and render a modern responsive
        HTML widget for multi day forecast.
        """
        city = self._get_location(city)
        units = self._get_units()

        if not city:
            error_html = "<p style='font-family: system-ui; padding: 12px;'>Please provide a city name or set a default location in settings.</p>"
            return HTMLResponse(
                content=error_html, headers={"Content-Disposition": "inline"}
            )

        # Clamp days to valid range
        days = max(1, min(16, days))

        city_info = get_city_info(city)
        if not city_info:
            error_html = f"<p style='font-family: system-ui; padding: 12px;'>Could not find city: {html.escape(str(city))}</p>"
            return HTMLResponse(
                content=error_html, headers={"Content-Disposition": "inline"}
            )

        lat, lng, tmzone = city_info

        base_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lng,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "sunrise,sunset,uv_index_max,precipitation_sum,"
                "precipitation_probability_max,wind_speed_10m_max,"
                "wind_gusts_10m_max"
            ),
            "timezone": tmzone,
            "temperature_unit": units["temperature_unit"],
            "wind_speed_unit": units["wind_speed_unit"],
            "precipitation_unit": units["precipitation_unit"],
            "forecast_days": days,
        }

        data = fetch_weather_data(base_url, params)
        if isinstance(data, str):
            error_html = f"<p style='font-family: system-ui; padding: 12px;'>Error fetching weather data: {html.escape(data)}</p>"
            return HTMLResponse(
                content=error_html, headers={"Content-Disposition": "inline"}
            )

        daily = data["daily"]
        tz_abbr = data.get("timezone_abbreviation", "")

        temp_sym = units["temp_symbol"]
        wind_sym = units["wind_symbol"]
        precip_sym = units["precip_symbol"]
        unit_system_label = (
            "Metric" if units["temperature_unit"] == "celsius" else "Imperial"
        )

        entries: list[dict] = []

        for i in range(len(daily["time"])):
            date = daily["time"][i]
            dt = datetime.datetime.fromisoformat(date)

            if i == 0:
                day_label = "Today"
            elif i == 1:
                day_label = "Tomorrow"
            else:
                day_label = dt.strftime("%A")

            date_label = dt.strftime("%b %d")

            w_code = daily["weather_code"][i]
            weather_desc = wmo_weather_codes.get(str(w_code), "Unknown")
            icon, _accent = get_weather_icon_and_accent(w_code)

            temp_max = round(daily["temperature_2m_max"][i])
            temp_min = round(daily["temperature_2m_min"][i])
            sunrise = format_date(daily["sunrise"][i])
            sunset = format_date(daily["sunset"][i])
            uv_index = round(daily["uv_index_max"][i], 1)
            precip_prob = round(daily["precipitation_probability_max"][i])
            precip_sum = round(daily["precipitation_sum"][i], 2)
            wind_max = round(daily["wind_speed_10m_max"][i])
            wind_gusts = round(daily["wind_gusts_10m_max"][i])

            entries.append(
                {
                    "day_label": day_label,
                    "date_label": date_label,
                    "icon": icon,
                    "weather_desc": weather_desc,
                    "temp_max": temp_max,
                    "temp_min": temp_min,
                    "sunrise": sunrise,
                    "sunset": sunset,
                    "uv_index": uv_index,
                    "precip_prob": precip_prob,
                    "precip_sum": precip_sum,
                    "wind_max": wind_max,
                    "wind_gusts": wind_gusts,
                }
            )

        html_content = build_forecast_widget_html(
            city=city,
            days=days,
            tz_abbr=tz_abbr,
            unit_system_label=unit_system_label,
            temp_symbol=temp_sym,
            wind_symbol=wind_sym,
            precip_symbol=precip_sym,
            entries=entries,
        )

        return HTMLResponse(
            content=html_content, headers={"Content-Disposition": "inline"}
        )
