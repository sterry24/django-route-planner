"""Models for the planning app.

A :class:`PlannedRide` ties a saved :class:`routes.models.Route` to a moment in
time. The wind overlay on the ride detail page is computed from the route
geometry and ``scheduled_at`` together.
"""
from django.conf import settings
from django.db import models
from django.urls import reverse


class PlannedRide(models.Model):
    """A scheduled attempt at a Route on a specific date/time.

    Attributes:
        owner: The user who scheduled the ride. Cascade delete with the user.
        route: Foreign key to the planned route. Cascade delete: removing a
            route also removes its scheduled rides.
        scheduled_at: Timezone-aware UTC datetime. Stored in UTC because
            ``USE_TZ = True``; rendered in the user's local timezone in
            templates.
        notes: Optional free-form notes (gear, group, weather caveats).
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='planned_rides')
    route = models.ForeignKey(
        'routes.Route', on_delete=models.CASCADE, related_name='planned_rides')
    scheduled_at = models.DateTimeField()
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        # Composite index supports the calendar view's per-user date-range
        # query and the chronological ordering used everywhere else.
        indexes = [models.Index(fields=['owner', 'scheduled_at'])]

    def __str__(self):
        return f'{self.route.name} @ {self.scheduled_at:%Y-%m-%d %H:%M}'

    def get_absolute_url(self):
        return reverse('planning:detail', args=[self.pk])
