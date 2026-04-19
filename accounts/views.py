"""Views for the accounts app: signup and per-user preferences.

Login/logout are handled by Django's built-in views wired up in
:mod:`planner_project.urls`.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import PreferencesForm, SignupForm
from .models import Profile


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
    return render(request, 'accounts/settings.html', {'form': form})


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
