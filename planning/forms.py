"""Forms for the planning app."""
from django import forms

from routes.models import Route

from .models import PlannedRide


class PlannedRideForm(forms.ModelForm):
    """Schedule or edit a :class:`PlannedRide`.

    The form constrains the route dropdown to routes owned by ``user`` so a
    user can never schedule a ride on someone else's route. The browser's
    native ``datetime-local`` widget is used for ``scheduled_at``; it requires
    the ``YYYY-MM-DDTHH:MM`` format with no timezone suffix.
    """

    scheduled_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
    )

    class Meta:
        model = PlannedRide
        fields = ['route', 'scheduled_at', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, user=None, **kwargs):
        """Restrict route choices to ``user``'s own routes when ``user`` given."""
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['route'].queryset = Route.objects.filter(owner=user)
