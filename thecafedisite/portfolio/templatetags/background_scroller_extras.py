from django import template

register = template.Library()


@register.filter
def zip_lists(a, b):
    """Zips two lists together for iteration in templates"""
    return zip(a, b)
