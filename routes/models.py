"""Database models for the routes app."""
from django.conf import settings
from django.db import models
from django.urls import reverse


class Route(models.Model):
    """A saved cycling route owned by a single user.

    Geometry is stored as a GeoJSON ``LineString`` in a :class:`JSONField` to
    keep SQLite-only setups simple. When migrating to PostGIS, add a
    ``LineStringField`` in a new migration and backfill from :attr:`geometry`
    — the JSONField can then be dropped.

    All distances are stored in metric SI (metres). Display-time conversion
    to imperial units is handled by filters in :mod:`accounts.templatetags.units`.

    Attributes:
        owner: The :class:`~django.contrib.auth.models.User` who created it.
        name: User-visible title.
        description: Freeform notes.
        geometry: ``{"type": "LineString", "coordinates": [[lng, lat, ele?], ...]}``.
            Coordinates follow the GeoJSON convention — longitude first. Elevation
            is optional but populated by the elevation-enrichment step on save.
        bounds: ``[[min_lng, min_lat], [max_lng, max_lat]]`` precomputed on save
            for cheap map-fitting without scanning the line.
        distance_m: Total planar distance along the line, in metres.
        elevation_gain_m: Sum of positive elevation deltas, in metres.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='routes')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    geometry = models.JSONField()
    bounds = models.JSONField(blank=True, null=True)

    distance_m = models.FloatField(default=0)
    elevation_gain_m = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Canonical detail-page URL for this route."""
        return reverse('routes:detail', args=[self.pk])

    @property
    def coordinates(self):
        """Return the raw ``[[lng, lat, ele?], ...]`` list, or ``[]`` if empty."""
        return self.geometry.get('coordinates', []) if self.geometry else []
