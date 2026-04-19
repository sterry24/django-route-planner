from django.contrib import admin

from .models import Route


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'distance_m', 'elevation_gain_m', 'updated_at')
    list_filter = ('owner',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
