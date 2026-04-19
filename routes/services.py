"""External service clients: OSRM (bike routing) and Open-Meteo (elevation).

Both services are used server-side only so URLs, keys (if any), and caching
policy live in one place and the frontend stays decoupled from the provider.
"""
from __future__ import annotations

from typing import Iterable, Sequence

import requests
from django.conf import settings


class OSRMError(RuntimeError):
    """Raised when OSRM returns a non-Ok response or is unreachable."""


class ElevationError(RuntimeError):
    """Raised when the Open-Meteo elevation API fails or returns junk."""


OPEN_METEO_ELEVATION_URL = 'https://api.open-meteo.com/v1/elevation'
ELEVATION_BATCH_SIZE = 100  # Open-Meteo's per-request limit
ELEVATION_MAX_POINTS = 1500  # safety cap to bound save latency


def snap_route(waypoints: Iterable[tuple[float, float]]) -> dict:
    """Given ``[(lng, lat), ...]`` waypoints, return the OSRM response as a dict.

    Uses the public OSRM bike profile by default (configured in settings).
    Returns the ``routes[0]`` object which includes a ``geometry`` GeoJSON
    LineString and ``distance``, ``duration`` scalars.
    """
    pts = list(waypoints)
    if len(pts) < 2:
        raise OSRMError('Need at least two waypoints.')
    coord_str = ';'.join(f'{lng},{lat}' for lng, lat in pts)
    url = f'{settings.OSRM_BASE_URL}/route/v1/{settings.OSRM_PROFILE}/{coord_str}'
    params = {
        'overview': 'full',
        'geometries': 'geojson',
        'steps': 'false',
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise OSRMError(str(exc)) from exc
    data = resp.json()
    if data.get('code') != 'Ok' or not data.get('routes'):
        raise OSRMError(data.get('message') or 'OSRM returned no route')
    return data['routes'][0]


def fetch_elevations(coords: Sequence[Sequence[float]]) -> list[float]:
    """Return elevations (metres) for each ``[lng, lat, ...]`` in ``coords``.

    Calls Open-Meteo's free elevation API in batches of 100. Raises
    :class:`ElevationError` on network / parse failure.
    """
    if len(coords) > ELEVATION_MAX_POINTS:
        raise ElevationError(
            f'Too many points for elevation lookup ({len(coords)} > {ELEVATION_MAX_POINTS})')

    elevations: list[float] = []
    for i in range(0, len(coords), ELEVATION_BATCH_SIZE):
        batch = coords[i:i + ELEVATION_BATCH_SIZE]
        lats = ','.join(f'{c[1]:.5f}' for c in batch)
        lngs = ','.join(f'{c[0]:.5f}' for c in batch)
        try:
            resp = requests.get(
                OPEN_METEO_ELEVATION_URL,
                params={'latitude': lats, 'longitude': lngs},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise ElevationError(str(exc)) from exc
        batch_elev = data.get('elevation')
        if not isinstance(batch_elev, list) or len(batch_elev) != len(batch):
            raise ElevationError('Unexpected response from elevation API')
        elevations.extend(float(e) for e in batch_elev)
    return elevations


def enrich_with_elevation(coords: Sequence[Sequence[float]]) -> list[list[float]]:
    """Return ``coords`` with elevation filled in; fall back to input on failure.

    Callers should treat this as best-effort — a save must succeed even if
    the elevation service is unreachable. Coordinates that already have
    elevation (3rd component present) are returned unchanged without a
    network call.
    """
    # Short-circuit: if every point already has elevation, skip the API entirely.
    # This also covers imports from formats that carry elevation (GPX, FIT, TCX).
    if all(len(c) >= 3 for c in coords):
        return [list(c) for c in coords]
    try:
        elevs = fetch_elevations(coords)
    except ElevationError:
        return [list(c) for c in coords]
    return [[c[0], c[1], e] for c, e in zip(coords, elevs)]
