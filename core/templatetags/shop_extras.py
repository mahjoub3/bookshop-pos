from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value, currency=""):
    """Format a Decimal as money: 1,234.56"""
    try:
        value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f"{currency}{value:,.2f}" if currency else f"{value:,.2f}"


@register.filter
def mul(a, b):
    try:
        return Decimal(str(a)) * Decimal(str(b))
    except (InvalidOperation, TypeError, ValueError):
        return ""


@register.filter
def sub(a, b):
    try:
        return Decimal(str(a)) - Decimal(str(b))
    except (InvalidOperation, TypeError, ValueError):
        return ""


@register.filter
def get_item(mapping, key):
    """dict lookup by variable key: {{ cart|get_item:product.id }}"""
    if mapping is None:
        return None
    return mapping.get(key) or mapping.get(str(key))


@register.simple_tag
def querystring(request, **kwargs):
    """Current GET params overridden by kwargs — used for pagination links."""
    params = request.GET.copy()
    for key, value in kwargs.items():
        params[key] = value
    return params.urlencode()
