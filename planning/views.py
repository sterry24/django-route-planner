"""Views for the planning app.

The calendar view groups a user's rides by day for a month grid. The detail
view renders the route geometry plus a wind overlay fetched from
:func:`planning.services.wind_along_route` via the JSON ``ride_wind`` endpoint.
All views require authentication and filter by ``owner=request.user``.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET

from .forms import PlannedRideForm
from .models import PlannedRide
from .services import OpenMeteoError, wind_along_route


@login_required
def calendar_view(request):
    """Render a month-grid calendar of the user's planned rides.

    Reads ``year`` and ``month`` from the query string (defaulting to today)
    and groups :class:`PlannedRide` rows that fall in that month into a
    ``date -> [ride, ...]`` map. ``prev_*`` / ``next_*`` context values drive
    the navigation arrows on the calendar template.
    """
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    first = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    last = date(year, month, last_day)

    rides = PlannedRide.objects.filter(
        owner=request.user,
        scheduled_at__date__gte=first,
        scheduled_at__date__lte=last,
    ).select_related('route')

    rides_by_day: dict[date, list[PlannedRide]] = {}
    for r in rides:
        rides_by_day.setdefault(r.scheduled_at.date(), []).append(r)

    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)

    prev_month = first - timedelta(days=1)
    next_month = last + timedelta(days=1)

    return render(request, 'planning/calendar.html', {
        'weeks': weeks,
        'rides_by_day': rides_by_day,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'today': today,
        'prev_year': prev_month.year,
        'prev_month': prev_month.month,
        'next_year': next_month.year,
        'next_month_num': next_month.month,
    })


@login_required
def ride_create(request):
    """Schedule a new ride.

    Pre-populates the form from ``?route=<id>`` and ``?when=<iso>`` query
    parameters so the calendar's "Add ride" links can prefill the date and
    route. The form's route choices are restricted to routes owned by the
    current user (see :class:`PlannedRideForm`).
    """
    initial = {}
    if 'route' in request.GET:
        initial['route'] = request.GET['route']
    if 'when' in request.GET:
        parsed = parse_datetime(request.GET['when'])
        if parsed:
            initial['scheduled_at'] = parsed.strftime('%Y-%m-%dT%H:%M')

    if request.method == 'POST':
        form = PlannedRideForm(request.POST, user=request.user)
        if form.is_valid():
            ride = form.save(commit=False)
            ride.owner = request.user
            ride.save()
            messages.success(request, 'Ride scheduled.')
            return redirect(ride.get_absolute_url())
    else:
        form = PlannedRideForm(user=request.user, initial=initial)
    return render(request, 'planning/ride_form.html', {'form': form, 'ride': None})


@login_required
def ride_detail(request, pk):
    """Render a ride with map, route polyline, and wind overlay markers.

    The wind data is fetched asynchronously by the template's inline JS via
    the :func:`ride_wind` endpoint to keep this page fast even when the
    Open-Meteo round-trip is slow.
    """
    ride = get_object_or_404(PlannedRide, pk=pk, owner=request.user)
    return render(request, 'planning/ride_detail.html', {'ride': ride})


@login_required
def ride_edit(request, pk):
    """Edit a previously scheduled ride.

    Pre-formats ``scheduled_at`` to the ``datetime-local`` widget format
    because the browser input type rejects timezone suffixes.
    """
    ride = get_object_or_404(PlannedRide, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = PlannedRideForm(request.POST, instance=ride, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ride updated.')
            return redirect(ride.get_absolute_url())
    else:
        form = PlannedRideForm(instance=ride, user=request.user, initial={
            'scheduled_at': ride.scheduled_at.strftime('%Y-%m-%dT%H:%M')})
    return render(request, 'planning/ride_form.html', {'form': form, 'ride': ride})


@login_required
def ride_delete(request, pk):
    """Confirm-and-delete a planned ride. GET shows the confirm page."""
    ride = get_object_or_404(PlannedRide, pk=pk, owner=request.user)
    if request.method == 'POST':
        ride.delete()
        messages.success(request, 'Ride deleted.')
        return redirect('planning:calendar')
    return render(request, 'planning/ride_confirm_delete.html', {'ride': ride})


@login_required
@require_GET
def ride_wind(request, pk):
    """Return wind samples along the ride's route at ``scheduled_at`` as JSON.

    Returns 400 if the route has fewer than two vertices and 502 if the
    Open-Meteo upstream errors out — both surfaced to the user via the
    template's inline JS as a non-blocking message.
    """
    ride = get_object_or_404(PlannedRide, pk=pk, owner=request.user)
    coords = ride.route.coordinates
    if len(coords) < 2:
        return JsonResponse({'error': 'Route has too few points'}, status=400)
    try:
        samples = wind_along_route(coords, ride.scheduled_at)
    except OpenMeteoError as exc:
        return JsonResponse({'error': str(exc)}, status=502)
    return JsonResponse({'samples': samples})
