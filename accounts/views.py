"""Views for the accounts app: signup, preferences, and RideWithGPS OAuth.

Login/logout are handled by Django's built-in views wired up in
:mod:`planner_project.urls`. The RideWithGPS connect/callback/disconnect
views drive the OAuth authorization-code flow against the helpers in
:mod:`accounts.rwgps`.
"""
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import PreferencesForm, SignupForm
from .models import Profile
from .rwgps import RWGPSError, authorize_url, exchange_code_for_token

#: Session key used to round-trip the OAuth ``state`` parameter through the
#: RWGPS redirect — the callback view rejects mismatched values.
RWGPS_STATE_SESSION_KEY = 'rwgps_oauth_state'


@login_required
def settings_view(request):
    """Edit unit system (metric/imperial) on the user's :class:`Profile`.

    Uses ``get_or_create`` so users that pre-date the Profile model can still
    open this page without a 500 — the signal handles new users, this fallback
    handles old ones.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = PreferencesForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Preferences updated.')
            return redirect('accounts:settings')
    else:
        form = PreferencesForm(instance=profile)
    return render(request, 'accounts/settings.html', {'form': form, 'profile': profile})


@login_required
def rwgps_connect(request):
    """Begin the RWGPS OAuth flow — redirect the user to RWGPS to authorize.

    Generates a fresh ``state`` token per request and stashes it in the
    session so :func:`rwgps_callback` can verify the response. Refuses to run
    if the OAuth client isn't configured, so failures are loud rather than
    sending the user to a broken authorize URL.
    """
    if not settings.RWGPS_CLIENT_ID:
        messages.error(request,
                       'RideWithGPS integration is not configured on this server.')
        return redirect('accounts:settings')
    state = secrets.token_urlsafe(32)
    request.session[RWGPS_STATE_SESSION_KEY] = state
    return redirect(authorize_url(state))


@login_required
def rwgps_callback(request):
    """OAuth callback — exchange the ``code`` for an access token and store it.

    Validates the ``state`` round-trip first, then calls the RWGPS token
    endpoint and persists the resulting ``access_token`` (and any ``user.id``
    in the response) on the user's :class:`Profile`.
    """
    expected_state = request.session.pop(RWGPS_STATE_SESSION_KEY, None)
    state = request.GET.get('state')
    if not expected_state or state != expected_state:
        messages.error(request, 'RideWithGPS authorization rejected (state mismatch).')
        return redirect('accounts:settings')

    error = request.GET.get('error')
    if error:
        messages.error(request, f'RideWithGPS authorization failed: {error}')
        return redirect('accounts:settings')

    code = request.GET.get('code')
    if not code:
        messages.error(request, 'RideWithGPS did not return an authorization code.')
        return redirect('accounts:settings')

    try:
        token_data = exchange_code_for_token(code)
    except RWGPSError as exc:
        messages.error(request, f'RideWithGPS token exchange failed: {exc}')
        return redirect('accounts:settings')

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.rwgps_access_token = token_data.get('access_token', '')
    # The token response embeds the user payload under "user" with an "id".
    user_payload = token_data.get('user') or {}
    profile.rwgps_user_id = str(user_payload.get('id', '') or '')
    profile.save(update_fields=['rwgps_access_token', 'rwgps_user_id'])

    messages.success(request, 'RideWithGPS account connected.')
    return redirect('routes:rwgps_import')


@login_required
@require_POST
def rwgps_disconnect(request):
    """Forget the stored RWGPS access token for the current user."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.rwgps_access_token = ''
    profile.rwgps_user_id = ''
    profile.save(update_fields=['rwgps_access_token', 'rwgps_user_id'])
    messages.success(request, 'RideWithGPS account disconnected.')
    return redirect('accounts:settings')


def signup_view(request):
    """Register a new account and log the user in immediately on success.

    Redirects already-authenticated users to the route list to avoid letting a
    logged-in user accidentally create a second account from a stale tab.
    """
    if request.user.is_authenticated:
        return redirect('routes:list')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('routes:list')
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})
