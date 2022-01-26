import locale
from numbers import Number
from django import template

register = template.Library()

locale.setlocale(locale.LC_ALL, '')

@register.filter
def as_currency(value: Number) -> str:
    return locale.currency(value, grouping=True, symbol='$')
