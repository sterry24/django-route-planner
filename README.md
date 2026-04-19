# django-route-planner

A Django web app for planning cycling routes and scheduling rides, with a
wind-forecast overlay on the route for the scheduled time. Models the core
RideWithGPS flow (draw routes, save a library, import/export) plus a calendar
with per-ride wind data.

## Features

- **Map-based route builder** — click to drop waypoints; the app snaps them to
  cycling-friendly roads via OSRM and renders the resulting polyline. Drag to
  move points, undo, clear.
- **Elevation profile** — every saved route is enriched with elevation data
  from Open-Meteo and rendered as a Chart.js graph on the route detail page.
- **Route library** — per-user list of saved routes with name, description,
  distance, and elevation gain.
- **Import / export** — round-trip GPX, TCX, FIT, KML, and KMZ files. FIT
  export is hand-rolled to produce a valid Garmin Course file.
- **Ride calendar** — schedule a saved route for a date and time; rides are
  grouped by day in a month-grid calendar.
- **Wind overlay** — on the ride detail page, hourly wind speed and direction
  are sampled along the route from Open-Meteo and drawn as rotated arrow
  markers at the time of the ride.
- **Unit preferences** — each user picks metric or imperial; the choice flows
  through templates and the JS map editor.
- **Auth** — Django's built-in signup/login/logout, with per-user route
  ownership enforced on every view.

## Tech stack

- Python 3.11+, Django 6
- SQLite (data model is GeoJSON in a `JSONField` — see "PostGIS migration"
  below)
- Leaflet 1.9 + CartoDB tiles (no build step)
- Chart.js 4 for the elevation profile
- HTMX 1.9 (loaded; used lightly)
- Third-party libs: `gpxpy`, `fitparse`, `lxml`, `requests`

## External services

Both default to free, keyless public endpoints — no signup required:

- **OSRM** at `routing.openstreetmap.de/routed-bike` for bike routing.
  Rate-limited; for heavy use run a local OSRM container and override
  `OSRM_BASE_URL` in settings.
- **Open-Meteo** at `api.open-meteo.com` for hourly wind and elevation.
  Forecast horizon is ~16 days, so rides scheduled further out return null
  wind values.

## Quick start

On Windows (bash). The project assumes a virtualenv at `.venv/django_env`.

```bash
VENV="./.venv/django_env/Scripts"
$VENV/pip.exe install -r requirements.txt
$VENV/python.exe manage.py migrate
$VENV/python.exe manage.py createsuperuser
$VENV/python.exe manage.py runserver
```

Then open <http://127.0.0.1:8000>.

## Project layout

```
planner_project/    # settings, root URLs, auth wiring
routes/             # Route model, CRUD, import/export, OSRM proxy
  io/               # one module per file format (gpx, tcx, fit, kml)
  geometry.py       # pure-python distance/bounds/sampling
  services.py       # OSRM + Open-Meteo elevation
planning/           # PlannedRide model, calendar, ride detail, wind overlay
  services.py       # Open-Meteo wind sampler
accounts/           # Profile (units), signup, signals
templates/          # base templates and auth pages
static/js/          # editor.js (route builder)
docs/               # Sphinx documentation source
```

## Conventions

- Geometry is stored as a GeoJSON `LineString`:
  `{"type": "LineString", "coordinates": [[lng, lat, ele?], ...]}`.
  Coordinates are `[lng, lat]` (GeoJSON convention) — Leaflet uses
  `[lat, lng]`, so flip at the rendering boundary.
- Geometry math and file I/O live in `routes/geometry.py` and `routes/io/`,
  not in views. Views orchestrate; modules compute.
- Every user-facing view requires `@login_required` and filters by
  `owner=request.user`.

## Testing

```bash
$VENV/python.exe manage.py test
```

## Documentation

Full docs (architecture, API reference, user guide) live under `docs/` and are
built with Sphinx:

```bash
$VENV/pip.exe install sphinx sphinx-rtd-theme
cd docs && ../$VENV/sphinx-build.exe -b html . _build/html
```

Then open `docs/_build/html/index.html`.

## PostGIS migration

The current data model uses a JSONField rather than a GeoDjango
`LineStringField` so the app runs on plain SQLite. The migration path:

1. Install GeoDjango / set up PostGIS.
2. Add a `LineStringField` (e.g. `geom`) in a new migration.
3. Backfill `geom` from `geometry['coordinates']`.
4. Replace usages in `routes/geometry.py` with PostGIS-native calls and drop
   the JSONField in a follow-up migration.
