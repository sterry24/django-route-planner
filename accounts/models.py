"""Models for the accounts app.

Holds per-user preferences that don't belong on the built-in :class:`User`
model. Currently just a unit-system choice that drives display formatting in
templates and the JS map editor.
"""
from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Per-user preferences (extends :class:`django.contrib.auth.models.User`).

    Created automatically by the ``create_user_profile`` signal in
    :mod:`accounts.signals`. The :func:`accounts.context_processors.user_units`
    context processor exposes the chosen unit system to every template, and
    ``base.html`` mirrors it to the JS global ``window.USER_UNITS`` so the
    Leaflet editor can display distances consistently.
    """

    METRIC = 'metric'
    IMPERIAL = 'imperial'
    UNITS_CHOICES = [
        (METRIC, 'Metric (km, m, km/h)'),
        (IMPERIAL, 'Imperial (mi, ft, mph)'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    units = models.CharField(max_length=10, choices=UNITS_CHOICES, default=METRIC)

    # RideWithGPS OAuth — populated by the connect/callback flow in
    # :mod:`accounts.rwgps`. Empty string means "not connected".
    rwgps_access_token = models.CharField(max_length=255, blank=True, default='')
    rwgps_user_id = models.CharField(max_length=64, blank=True, default='')

    def __str__(self):
        return f'Profile({self.user.username})'

    @property
    def rwgps_connected(self) -> bool:
        """True when this profile has a stored RideWithGPS access token."""
        return bool(self.rwgps_access_token)
