"""HTTP views for the routes app.

Covers the CRUD for :class:`routes.models.Route`, the browser-facing route
builder (map editor), import/export in five formats, and two JSON endpoints
used by the editor (OSRM proxy and save).

All views require authentication and scope their queryset to
``owner=request.user`` — users can only see and mutate their own routes.
"""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import io as route_io
from .forms import RouteForm, RouteImportForm
from .geometry import compute_bounds, elevation_gain_m, elevation_profile, total_distance_m
from .models import Route
from .services import OSRMError, enrich_with_elevation, snap_route


@login_required
def route_list(request):
    """Render the current user's route library."""
    routes = Route.objects.filter(owner=request.user)
    return render(request, 'routes/list.html', {'routes': routes})


@login_required
def route_detail(request, pk):
    """Show a single route: map, stats, elevation chart, export links."""
    route = get_object_or_404(Route, pk=pk, owner=request.user)
    profile = elevation_profile(route.coordinates)
    max_ele = max((p[1] for p in profile), default=None)
    min_ele = min((p[1] for p in profile), default=None)
    return render(request, 'routes/detail.html', {
        'route': route,
        'profile': profile,
        'max_ele': max_ele,
        'min_ele': min_ele,
    })


@login_required
def route_create(request):
    """Render the blank map-based route builder.

    The builder POSTs waypoints + snapped geometry to :func:`route_save` via
    ``fetch``; this view just serves the editor page.
    """
    return render(request, 'routes/editor.html', {'route': None})


@login_required
def route_edit(request, pk):
    """Open the builder pre-populated with an existing route's geometry."""
    route = get_object_or_404(Route, pk=pk, owner=request.user)
    return render(request, 'routes/editor.html', {'route': route})


@login_required
@require_POST
def route_save(request):
    """Accept a JSON payload from the editor and create/update a Route.

    Request body::

        {"id": <pk or null>, "name": "...", "description": "...",
         "geometry": {"type": "LineString", "coordinates": [[lng, lat], ...]},
         "distance_m": <float>}

    Elevation is fetched server-side after save (best-effort) to keep the
    frontend decoupled from the elevation API.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = (payload.get('name') or '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)

    geometry = payload.get('geometry')
    if not geometry or geometry.get('type') != 'LineString':
        return JsonResponse({'error': 'GeoJSON LineString required'}, status=400)

    coords = geometry.get('coordinates') or []
    if len(coords) < 2:
        return JsonResponse({'error': 'Route needs at least two points'}, status=400)

    route_id = payload.get('id')
    if route_id:
        route = get_object_or_404(Route, pk=route_id, owner=request.user)
    else:
        route = Route(owner=request.user)

    enriched = enrich_with_elevation(coords)
    route.name = name
    route.description = payload.get('description', '')
    route.geometry = {'type': 'LineString', 'coordinates': enriched}
    route.bounds = compute_bounds(enriched)
    route.distance_m = payload.get('distance_m') or total_distance_m(enriched)
    route.elevation_gain_m = elevation_gain_m(enriched)
    route.save()
    return JsonResponse({'id': route.pk, 'url': route.get_absolute_url()})


@login_required
@require_POST
def route_delete(request, pk):
    """Delete a route the user owns."""
    route = get_object_or_404(Route, pk=pk, owner=request.user)
    route.delete()
    messages.success(request, f'Deleted "{route.name}".')
    return redirect('routes:list')


@login_required
@require_POST
def osrm_proxy(request):
    """Snap editor waypoints to cycling-friendly roads via OSRM.

    The proxy keeps the OSRM base URL server-side so it can be swapped (e.g.
    to a self-hosted OSRM container) without changing the frontend, and puts
    response caching in scope for later.

    Request body: ``{"waypoints": [[lng, lat], ...]}``.
    Response: ``{"geometry": <GeoJSON LineString>, "distance_m", "duration_s"}``.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    waypoints = payload.get('waypoints') or []
    try:
        route = snap_route([(float(w[0]), float(w[1])) for w in waypoints])
    except (OSRMError, ValueError, TypeError) as exc:
        return JsonResponse({'error': str(exc)}, status=502)
    return JsonResponse({
        'geometry': route['geometry'],
        'distance_m': route.get('distance', 0),
        'duration_s': route.get('duration', 0),
    })


@login_required
def route_import(request):
    """Upload a GPX/TCX/FIT/KML/KMZ file and create a Route from it."""
    if request.method == 'POST':
        form = RouteImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['file']
            data = f.read()
            try:
                coords = route_io.parse(f.name, data)
            except Exception as exc:
                # Parsers across five formats raise varied exception types
                # (GPXException, XMLSyntaxError, FitParseError, BadZipFile,
                # struct.error, ...). Broad catch is intentional here.
                messages.error(request, f'Could not parse file: {exc}')
                return render(request, 'routes/import.html', {'form': form})
            if len(coords) < 2:
                messages.error(request, 'File contains fewer than 2 track points.')
                return render(request, 'routes/import.html', {'form': form})
            name = form.cleaned_data['name'] or f.name.rsplit('.', 1)[0]
            enriched = enrich_with_elevation(coords)
            route = Route.objects.create(
                owner=request.user,
                name=name,
                geometry={'type': 'LineString', 'coordinates': enriched},
                bounds=compute_bounds(enriched),
                distance_m=total_distance_m(enriched),
                elevation_gain_m=elevation_gain_m(enriched),
            )
            messages.success(request, f'Imported "{route.name}".')
            return redirect(route.get_absolute_url())
    else:
        form = RouteImportForm()
    return render(request, 'routes/import.html', {'form': form})


@login_required
@require_GET
def route_export(request, pk, fmt):
    """Serialize a route to one of the supported file formats and stream it.

    ``fmt`` is the extension (``gpx``, ``tcx``, ``fit``, ``kml``, ``kmz``).
    """
    route = get_object_or_404(Route, pk=pk, owner=request.user)
    try:
        payload, content_type, ext = route_io.serialize(route, fmt)
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)
    resp = HttpResponse(payload, content_type=content_type)
    # Sanitize the filename — route names can contain arbitrary user input.
    safe_name = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_'
                        for ch in route.name) or f'route-{route.pk}'
    resp['Content-Disposition'] = f'attachment; filename="{safe_name}.{ext}"'
    return resp


@login_required
@require_GET
def route_geojson(request, pk):
    """Return a route as JSON (used by embedded maps / future API clients)."""
    route = get_object_or_404(Route, pk=pk, owner=request.user)
    return JsonResponse({
        'id': route.pk,
        'name': route.name,
        'geometry': route.geometry,
        'bounds': route.bounds,
        'distance_m': route.distance_m,
        'elevation_gain_m': route.elevation_gain_m,
    })
