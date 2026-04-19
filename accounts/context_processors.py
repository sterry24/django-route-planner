"""Template context processors for the accounts app.

Registered in ``TEMPLATES[0]['OPTIONS']['context_processors']`` in
:mod:`planner_project.settings`.
"""
from .models import Profile


def user_units(request):
    """Expose ``units`` ('metric' | 'imperial') to every template.

    Falls back to metric for anonymous users and for legacy users whose
    Profile row hasn't been created yet (the signal handles new signups; this
    fallback covers the gap for accounts that pre-date the model).
    """
    units = Profile.METRIC
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile is not None:
            units = profile.units
    return {'units': units}
