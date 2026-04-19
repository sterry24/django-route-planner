Architecture
============

The app is a server-rendered Django site with two domain apps and one
project package. Maps are drawn with Leaflet from a CDN, with HTMX loaded
for incremental enhancement. There is no frontend build step.

Apps
----

``routes``
    Owns the :class:`routes.models.Route` model, CRUD, the OSRM proxy, and
    file import/export. Geometry is stored as a GeoJSON ``LineString`` in a
    Django ``JSONField`` so the app runs on plain SQLite. The
    :mod:`routes.io` package contains one submodule per file format
    (``gpx``, ``tcx``, ``fit``, ``kml``); the package's ``__init__`` exposes
    a ``parse``/``serialize`` dispatcher keyed on extension.

``planning``
    Owns :class:`planning.models.PlannedRide` (a route + a datetime), the
    month-grid calendar view, and the wind-overlay endpoint. Wind data is
    fetched per-ride from Open-Meteo in :func:`planning.services.wind_along_route`.

``accounts``
    Owns the :class:`accounts.models.Profile` model (per-user unit
    preference), the signup view, the settings view, and a context
    processor that exposes the user's chosen units to every template.

``planner_project``
    Settings, root URLs, auth wiring. Login/logout use Django's built-in
    views.

Cross-cutting modules
---------------------

:mod:`routes.geometry`
    Pure-Python distance / bounds / sampling helpers — no GeoDjango
    dependency. Replace with PostGIS-native calls after a migration.

:mod:`routes.services`
    OSRM bike-routing proxy and Open-Meteo elevation enrichment. The
    frontend POSTs waypoints to the OSRM proxy view, which forwards to the
    public OSRM instance and returns the snapped GeoJSON.

:mod:`planning.services`
    Open-Meteo wind sampler. Samples N points along a route (default 12)
    and queries hourly wind at each, picking the hour closest to
    ``scheduled_at``.

Data model
----------

``Route.geometry`` is a GeoJSON object::

    {
        "type": "LineString",
        "coordinates": [[lng, lat, ele?], ...]
    }

Coordinates are ``[lng, lat]`` order — GeoJSON convention. Leaflet uses
``[lat, lng]``, so flip at the rendering boundary.

``Route.bounds`` is ``[[min_lng, min_lat], [max_lng, max_lat]]``, recomputed
on save.

``PlannedRide.scheduled_at`` is a timezone-aware UTC datetime. ``USE_TZ``
is set to ``True``.

Frontend
--------

* ``static/js/editor.js`` — the route builder. Handles waypoint adds,
  drags, undo, clear; POSTs to the OSRM proxy and the route-save
  endpoints.
* ``planning/templates/planning/ride_detail.html`` — inline JS that loads
  the route geometry, fetches the wind JSON, and renders rotated arrow
  markers. Wind direction is converted from "from" (meteorological
  convention) to "toward" by adding 180° before rotating the arrow.

The map tile source is CartoDB Voyager
(``basemaps.cartocdn.com/rastertiles/voyager``) — the public OSM tile
server returns 403 for non-attributed dev usage.

PostGIS migration path
----------------------

The current SQLite-friendly model (GeoJSON in a JSONField) is intentional.
To migrate to PostGIS:

#. Install GeoDjango and configure PostGIS.
#. Add a ``LineStringField`` (e.g. ``geom``) in a new migration.
#. Backfill ``geom`` from ``geometry['coordinates']``.
#. Replace the pure-Python helpers in :mod:`routes.geometry` with
   PostGIS-native calls.
#. Drop the JSONField in a follow-up migration.

External services
-----------------

Configured in :mod:`planner_project.settings`:

* ``OSRM_BASE_URL`` — defaults to ``https://routing.openstreetmap.de/routed-bike``.
* ``OSRM_PROFILE`` — ``bike``.
* ``OPEN_METEO_BASE_URL`` — ``https://api.open-meteo.com/v1/forecast``.

Neither service requires credentials.
