# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Django web app for planning cycling routes and scheduling rides, with a wind-forecast overlay on the route for the scheduled time. Models the core ridewithgps flow (draw routes, save a library, import/export) plus a calendar with per-ride wind data.

## Commands

All commands assume the project's virtualenv Python. On Windows (bash):

```bash
VENV="./.venv/django_env/Scripts"
$VENV/python.exe manage.py runserver          # http://127.0.0.1:8000
$VENV/python.exe manage.py migrate
$VENV/python.exe manage.py makemigrations
$VENV/python.exe manage.py createsuperuser
$VENV/python.exe manage.py check              # system checks
$VENV/python.exe manage.py test               # run tests (none yet)
$VENV/python.exe manage.py test routes.tests.TestClassName.test_method  # single test
$VENV/python.exe manage.py shell
```

Dependencies are pinned loosely in `requirements.txt`; install with `$VENV/pip.exe install -r requirements.txt`.

## Architecture

Two Django apps plus one project package:

- **`routes/`** — Route model + CRUD + import/export. Geometry is stored as a GeoJSON `LineString` in a `JSONField` (`Route.geometry`). This is intentional so SQLite works without SpatiaLite; the migration path to PostGIS is to add a `LineStringField` in a new migration and backfill from the JSON, then drop it.
- **`planning/`** — `PlannedRide` FKs a `Route` and a `scheduled_at` datetime. Calendar view groups rides by day. Wind overlay is fetched per-ride via `services.wind_along_route()`.
- **`planner_project/`** — settings, root URLs, auth wiring.

Key cross-cutting modules:

- `routes/geometry.py` — pure-Python distance/bounds/sampling helpers. No GeoDjango dependency. Replace with GIS-native calls after the PostGIS migration.
- `routes/io/` — one module per file format (`gpx`, `tcx`, `fit`, `kml`). KMZ piggybacks on KML via zip. `routes/io/__init__.py::parse()` / `serialize()` dispatch by extension/format name.
- `routes/services.py` — OSRM bike-routing proxy. Frontend posts waypoints to `routes:osrm` which calls the public `routing.openstreetmap.de/routed-bike` service and returns the snapped GeoJSON.
- `planning/services.py` — Open-Meteo wrapper. Samples N points along the route (default 12) and fetches hourly wind at each, picking the hour closest to `scheduled_at`.

### Frontend

Server-rendered templates + Leaflet 1.9 for maps + HTMX (loaded, not yet heavily used). No build step. Two pieces of custom JS:

- `static/js/editor.js` — route builder. Click to add waypoints → POST to `routes:osrm` → draw snapped polyline → save via `routes:save`. Supports drag-to-move, undo, clear.
- Inline script in `planning/templates/planning/ride_detail.html` — loads the route + fetches `planning:wind` and draws rotated arrow markers (meteorological direction is *from*; the arrow is rotated 180° to point where the wind is going).

All map tiles come from `tile.openstreetmap.org`.

### Data model quick reference

- `Route.geometry` — `{"type": "LineString", "coordinates": [[lng, lat, ele?], ...]}`. Coordinates are `[lng, lat]` order (GeoJSON convention), **not** `[lat, lng]`. Leaflet uses `[lat, lng]` — flip at the rendering boundary.
- `Route.bounds` — `[[min_lng, min_lat], [max_lng, max_lat]]`, recomputed on save.
- `PlannedRide.scheduled_at` — timezone-aware UTC. `USE_TZ = True`.

## External services

Configured in `planner_project/settings.py`:

- `OSRM_BASE_URL` — defaults to the public `routing.openstreetmap.de/routed-bike`. Rate-limited; for heavy use run a local OSRM container.
- `OPEN_METEO_BASE_URL` — `api.open-meteo.com/v1/forecast`. Free, keyless. Forecast horizon is ~16 days, so scheduling rides further out returns nulls.

Neither service requires credentials.

## Conventions

- Geometry I/O and geometry math belong in `routes/geometry.py` and `routes/io/`, not in views. Views orchestrate; modules compute.
- When adding a new file format, add a submodule under `routes/io/`, update the `parse` / `serialize` dispatchers in `routes/io/__init__.py`, and add a button in `routes/templates/routes/detail.html`.
- Third-party parser exceptions are varied (`gpxpy.GPXException`, `lxml.etree.XMLSyntaxError`, `fitparse.FitParseError`, `struct.error`, `zipfile.BadZipFile`, etc.). The import view catches broad `Exception` by design — narrow only if you have a reason.
- Auth is Django's built-in. Every user-facing view requires `@login_required` and filters by `owner=request.user`. Do not skip the ownership filter.
