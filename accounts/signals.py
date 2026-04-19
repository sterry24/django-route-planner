"""Signal handlers for the accounts app.

These are connected in :meth:`AccountsConfig.ready`. Keeping them in their
own module avoids the circular-import trap that comes from defining signals
inline in ``models.py``.
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a :class:`Profile` whenever a new :class:`User` is saved.

    ``get_or_create`` rather than ``create`` defends against the rare case of
    a duplicate signal (e.g. fixtures replayed during tests).
    """
    if created:
        Profile.objects.get_or_create(user=instance)
