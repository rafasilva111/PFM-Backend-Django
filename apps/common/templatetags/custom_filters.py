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

@register.simple_tag(takes_context=True)
def active(context, *url_names):
    """
    Usage:
        {% active 'url_name1' 'url_name2' %}
    Returns 'active' if the current url_name is in url_names.
    """
    request = context.get("request")
    if request and request.resolver_match and request.resolver_match.url_name in url_names:
        return "active"
    return ""