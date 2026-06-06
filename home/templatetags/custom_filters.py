from django import template

register = template.Library()


@register.filter
def split(value, arg):
    """Split a string by arg and return a list."""
    return value.split(arg)
