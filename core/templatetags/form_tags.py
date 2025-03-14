
from django import template
from django.http import QueryDict

register = template.Library()

@register.filter
def getattribute(obj, attr):
    return getattr(obj, attr, None)

@register.filter
def attribute_exists(obj, attr):
    return hasattr(obj, attr)



@register.simple_tag
def query_transform(request, **kwargs):
    query = request.GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return query.urlencode()