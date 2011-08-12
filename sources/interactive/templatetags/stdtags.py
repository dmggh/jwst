"""This module maps rendering functions in common.widgets onto
Django template tags so they can be used from HTML.
"""

import sys

from django import template

from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='grey')
@stringfilter
def grey(value):
    return mark_safe("<span class='grey'>" + value + "</span>")
grey.is_safe = True

@register.filter(name='green')
@stringfilter
def green(value):
    return mark_safe("<span class='green'>" + value + "</span>")
green.is_safe = True

@register.filter(name='blue')
@stringfilter
def blue(value):
    return mark_safe("<span class='blue'>" + value + "</span>")
blue.is_safe = True

@register.filter(name='red')
@stringfilter
def red(value):
    return mark_safe("<span class='red'>" + value + "</span>")
red.is_safe = True

