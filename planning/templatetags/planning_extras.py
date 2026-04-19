from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Look up ``key`` in a dict from a template."""
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return None
