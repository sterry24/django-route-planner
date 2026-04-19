"""Pure-python geometry helpers for operating on GeoJSON polylines.

These functions intentionally avoid any GIS dependency (no GeoDjango, no
Shapely, no PostGIS) so the app runs on a vanilla SQLite install. When the
project migrates to PostGIS, replace these with GIS-native queries — the
call sites are small and the function names are stable.

All distances are metres; inputs use GeoJSON coordinate order (longitude
first, then latitude, optionally elevation).
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

#: One coordinate tuple. ``[lng, lat]`` or ``[lng, lat, elevation_m]``.
Coord = Sequence[float]

# Mean Earth radius in metres (WGS-84 authalic radius rounded to 4 sig figs).
_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(a: Coord, b: Coord) -> float:
    """Great-circle distance in metres between two ``[lng, lat, ...]`` points.

    Uses the haversine formula — accurate to <0.5% across any distance on
    Earth, which is well below the GPS error in the inputs.
    """
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def total_distance_m(coords: Iterable[Coord]) -> float:
    """Sum the great-circle distance between consecutive points."""
    coords = list(coords)
    return sum(haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def elevation_gain_m(coords: Iterable[Coord]) -> float:
    """Total positive elevation delta (climb only, descents ignored).

    Returns ``0`` if any coordinate lacks elevation — elevation is either
    present for every point or ignored entirely.
    """
    gain = 0.0
    prev_ele = None
    for c in coords:
        if len(c) < 3:
            return 0.0
        ele = c[2]
        if prev_ele is not None and ele > prev_ele:
            gain += ele - prev_ele
        prev_ele = ele
    return gain


def compute_bounds(coords: Sequence[Coord]) -> list[list[float]] | None:
    """Axis-aligned bounding box for a polyline.

    Returns ``[[min_lng, min_lat], [max_lng, max_lat]]`` or ``None`` for empty
    input. Stored on the model so map-fit at render time is O(1).
    """
    if not coords:
        return None
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [[min(lngs), min(lats)], [max(lngs), max(lats)]]


def elevation_profile(coords: Sequence[Coord], max_points: int = 200) -> list[list[float]]:
    """Build a downsampled ``[[distance_km, elevation_m, lng, lat], ...]`` series.

    Each sample carries its own geographic coordinates so the route detail
    page can cross-link chart hovers to map positions and vice versa.

    If the input has more than ``max_points`` coordinates it is sampled
    uniformly by index. Returns ``[]`` when any point lacks elevation so
    callers can suppress the chart entirely rather than render a half-empty
    one.
    """
    coords = list(coords)
    if len(coords) < 2 or any(len(c) < 3 for c in coords):
        return []

    cumulative = [0.0]
    for i in range(len(coords) - 1):
        cumulative.append(cumulative[-1] + haversine_m(coords[i], coords[i + 1]))

    def _sample(i: int) -> list[float]:
        c = coords[i]
        return [round(cumulative[i] / 1000.0, 3), round(c[2], 1),
                round(c[0], 6), round(c[1], 6)]

    if len(coords) <= max_points:
        return [_sample(i) for i in range(len(coords))]

    step = (len(coords) - 1) / (max_points - 1)
    return [_sample(min(int(round(k * step)), len(coords) - 1))
            for k in range(max_points)]


def sample_along(coords: Sequence[Coord], n_samples: int) -> list[tuple[float, Coord]]:
    """Return ``n_samples`` evenly-spaced points along the polyline.

    Each output item is ``(distance_from_start_m, [lng, lat, ele?])``. Used
    by the wind overlay to pick forecast query points spread across the route
    instead of densely clustered around every GPS vertex.
    """
    if not coords or n_samples <= 0:
        return []
    if len(coords) == 1 or n_samples == 1:
        return [(0.0, coords[0])]

    seg_lengths = [haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    total = sum(seg_lengths)
    if total == 0:
        # Degenerate polyline (all points identical) — return the first point N times.
        return [(0.0, coords[0])] * n_samples

    step = total / (n_samples - 1)
    result: list[tuple[float, Coord]] = []
    target = 0.0
    cumulative = 0.0
    seg_i = 0
    for _ in range(n_samples):
        # Advance the segment pointer until the target distance falls inside it.
        while seg_i < len(seg_lengths) - 1 and cumulative + seg_lengths[seg_i] < target:
            cumulative += seg_lengths[seg_i]
            seg_i += 1
        seg_len = seg_lengths[seg_i] if seg_lengths[seg_i] > 0 else 1.0
        t = (target - cumulative) / seg_len
        t = max(0.0, min(1.0, t))
        a, b = coords[seg_i], coords[seg_i + 1]
        lng = a[0] + (b[0] - a[0]) * t
        lat = a[1] + (b[1] - a[1]) * t
        point: Coord = [lng, lat]
        if len(a) >= 3 and len(b) >= 3:
            point = [lng, lat, a[2] + (b[2] - a[2]) * t]
        result.append((target, point))
        target += step
    return result
