"""Forms for the accounts app."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile


class PreferencesForm(forms.ModelForm):
    """Edit a :class:`Profile`'s unit system as a radio choice."""

    class Meta:
        model = Profile
        fields = ['units']
        widgets = {'units': forms.RadioSelect}


class SignupForm(UserCreationForm):
    """Extends Django's :class:`UserCreationForm` to require an email address.

    Django's default form makes email optional; we require it so password
    reset works without an extra collection step later.
    """

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email', 'password1', 'password2')
