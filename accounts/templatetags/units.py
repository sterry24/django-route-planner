"""Display-only unit conversion filters.

Storage is always metric SI; these filters run at render time to convert to
the user's preference. Pass ``units`` (from the context processor) as the
filter argument::

    {{ route.distance_m|dist_long:units }}
    {{ route.elevation_gain_m|elev:units }}
    {{ ms|windspeed:units }}
"""
from django import template

register = template.Library()

_M_TO_MI = 0.000621371
_M_TO_KM = 0.001
_M_TO_FT = 3.28084
_MS_TO_MPH = 2.23694
_MS_TO_KMH = 3.6


@register.filter
def dist_long(metres, units='metric'):
    """Metres to a human-friendly distance in km or miles."""
    if metres is None:
        return ''
    if units == 'imperial':
        return f'{metres * _M_TO_MI:.1f} mi'
    return f'{metres * _M_TO_KM:.1f} km'


@register.filter
def elev(metres, units='metric'):
    """Metres to m or ft."""
    if metres is None:
        return ''
    if units == 'imperial':
        return f'{metres * _M_TO_FT:.0f} ft'
    return f'{metres:.0f} m'


@register.filter
def windspeed(ms, units='metric'):
    """m/s to km/h or mph."""
    if ms is None:
        return ''
    if units == 'imperial':
        return f'{ms * _MS_TO_MPH:.1f} mph'
    return f'{ms * _MS_TO_KMH:.1f} km/h'


@register.filter
def dist_unit_label(units):
    return 'mi' if units == 'imperial' else 'km'


@register.filter
def elev_unit_label(units):
    return 'ft' if units == 'imperial' else 'm'


@register.filter
def speed_unit_label(units):
    return 'mph' if units == 'imperial' else 'km/h'
