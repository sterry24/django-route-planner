"""Django forms used by the routes app.

The map-based builder does not use a Django form — it POSTs JSON directly
to :func:`routes.views.route_save`. These forms cover the plain HTML paths
(metadata-only edits via the admin, file uploads for import).
"""
from django import forms

from .models import Route


class RouteForm(forms.ModelForm):
    """Edit a Route's name and description.

    Geometry is not exposed here — that goes through the map editor.
    """

    class Meta:
        model = Route
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class RouteImportForm(forms.Form):
    """Upload a track file in one of the supported formats."""

    #: Tuple of accepted file extensions, including the leading dot.
    SUPPORTED = ('.gpx', '.tcx', '.fit', '.kml', '.kmz')

    name = forms.CharField(max_length=200, required=False,
                           help_text='Leave blank to use the file name.')
    file = forms.FileField(help_text='GPX, TCX, FIT, KML or KMZ')

    def clean_file(self):
        """Validate extension only — the actual parse happens in the view."""
        f = self.cleaned_data['file']
        lower = f.name.lower()
        if not any(lower.endswith(ext) for ext in self.SUPPORTED):
            raise forms.ValidationError(
                f'Unsupported file type. Supported: {", ".join(self.SUPPORTED)}')
        return f
