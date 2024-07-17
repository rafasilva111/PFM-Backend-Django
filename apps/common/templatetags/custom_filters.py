from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    A custom template tag that generates a query string based on the provided context and keyword arguments.
    Returns the encoded query string.
    """
    request = context['request']
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value
    return updated.urlencode()