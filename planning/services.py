"""Wrap Open-Meteo's forecast API for use as a wind overlay along a route.

Open-Meteo is free and keyless. We sample ``N`` points along the route and
request wind speed + direction for the forecast hour closest to the ride's
scheduled time. The response is zipped back onto the sample points so the
frontend can draw an arrow at each.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

import requests
from django.conf import settings

from routes.geometry import sample_along

DEFAULT_SAMPLES = 12


class OpenMeteoError(RuntimeError):
    pass


def wind_along_route(
    coords: Sequence[Sequence[float]],
    when: datetime,
    n_samples: int = DEFAULT_SAMPLES,
) -> list[dict]:
    """Return a list of ``{lng, lat, distance_m, wind_speed_ms, wind_dir_deg}``."""
    samples = sample_along(coords, n_samples)
    if not samples:
        return []

    # Open-Meteo's forecast horizon is ~16 days; it doesn't accept a single
    # timestamp directly, but returns hourly values and we pick the closest.
    start = when.date()
    end = (when + timedelta(hours=1)).date()

    results: list[dict] = []
    for dist, point in samples:
        lng, lat = point[0], point[1]
        params = {
            'latitude': f'{lat:.5f}',
            'longitude': f'{lng:.5f}',
            'hourly': 'wind_speed_10m,wind_direction_10m',
            'wind_speed_unit': 'ms',
            'timezone': 'UTC',
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
        }
        try:
            resp = requests.get(settings.OPEN_METEO_BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise OpenMeteoError(str(exc)) from exc

        hourly = data.get('hourly') or {}
        times = hourly.get('time') or []
        speeds = hourly.get('wind_speed_10m') or []
        dirs = hourly.get('wind_direction_10m') or []
        idx = _closest_hour_index(times, when)
        results.append({
            'lng': lng,
            'lat': lat,
            'distance_m': dist,
            'wind_speed_ms': speeds[idx] if idx is not None and idx < len(speeds) else None,
            'wind_dir_deg': dirs[idx] if idx is not None and idx < len(dirs) else None,
            'time': times[idx] if idx is not None and idx < len(times) else None,
        })
    return results


def _closest_hour_index(times: list[str], target: datetime) -> int | None:
    if not times:
        return None
    target_utc = target.astimezone(tz=target.tzinfo).replace(tzinfo=None)
    best = None
    best_delta = None
    for i, t in enumerate(times):
        try:
            parsed = datetime.fromisoformat(t)
        except ValueError:
            continue
        delta = abs((parsed - target_utc).total_seconds())
        if best_delta is None or delta < best_delta:
            best = i
            best_delta = delta
    return best
