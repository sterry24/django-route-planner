"""GPX read/write using :mod:`gpxpy`.

GPX is the most common interchange format. Both tracks (GPS-recorded paths)
and routes (planned waypoint chains) are supported on parse; tracks are
preferred because they carry intermediate vertices.
"""
from __future__ import annotations

import gpxpy
import gpxpy.gpx


def parse(data: bytes) -> list[list[float]]:
    """Parse a GPX file into ``[[lng, lat, ele?], ...]`` coordinates.

    Tries track segments first; falls back to ``<rte>`` elements if the file
    contains only a planned route with no trackpoints.
    """
    gpx = gpxpy.parse(data.decode('utf-8', errors='replace'))
    coords: list[list[float]] = []
    for track in gpx.tracks:
        for seg in track.segments:
            for pt in seg.points:
                c = [pt.longitude, pt.latitude]
                if pt.elevation is not None:
                    c.append(pt.elevation)
                coords.append(c)
    if not coords:
        # No tracks — fall back to the <rte> waypoint list.
        for rte in gpx.routes:
            for pt in rte.points:
                c = [pt.longitude, pt.latitude]
                if pt.elevation is not None:
                    c.append(pt.elevation)
                coords.append(c)
    return coords


def serialize(route) -> bytes:
    """Serialize a :class:`routes.models.Route` as a single-track GPX file."""
    gpx = gpxpy.gpx.GPX()
    gpx.creator = 'django-route-planner'
    track = gpxpy.gpx.GPXTrack(name=route.name, description=route.description or None)
    gpx.tracks.append(track)
    seg = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(seg)
    for c in route.coordinates:
        ele = c[2] if len(c) >= 3 else None
        seg.points.append(gpxpy.gpx.GPXTrackPoint(
            latitude=c[1], longitude=c[0], elevation=ele))
    return gpx.to_xml().encode('utf-8')
