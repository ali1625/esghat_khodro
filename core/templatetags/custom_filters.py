from django import template

register = template.Library()

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def second(value):
    return value[1] if len(value) > 1 else ''

@register.filter
def third(value):
    return value[2] if len(value) > 2 else ''

@register.filter
def last(value):
    return value[-1] if value else ''

@register.filter
def first_part(value):
    return value.split(' ')[0] if value else ''