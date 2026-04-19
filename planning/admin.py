from django.contrib import admin

from .models import PlannedRide


@admin.register(PlannedRide)
class PlannedRideAdmin(admin.ModelAdmin):
    list_display = ('route', 'owner', 'scheduled_at')
    list_filter = ('owner', 'scheduled_at')
    search_fields = ('route__name', 'notes')
