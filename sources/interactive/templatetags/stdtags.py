"""This module maps rendering functions in common.widgets onto
Django template tags so they can be used from HTML.
"""

import sys

from django import template

from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from crds import (rmap, utils)
from crds.server import (config)
import crds.server.jsonapi.views as jviews

register = template.Library()

# ===========================================================================

# Inline styles might be better than classes.   At least these filters isolate
# that...

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

# ===========================================================================

@register.filter
@stringfilter
def minutes(value):  # handle str(datetime.datetime.now())
    """Return date & time formatted to minutes."""
    parts = value.split(":")
    return ":".join(parts[:-1])

@register.filter
@stringfilter
def seconds(value):  # handle str(datetime.datetime.now())
    """Return date & time formatted to seconds."""
    parts = value.split(".")
    return ".".join(parts[:-1])

# ===========================================================================

@register.filter
@stringfilter
def browse(name):  # handle str(datetime.datetime.now())
    return mark_safe("<a href='/browse/%s'>%s</a>" % (name, name))
browse.is_safe = True

# ===========================================================================

# Because of multiple projects this is uncomfortably complicated.  Sorry.
#  1. Both client and server observatory "personality" live in a single package.
#  2. The core library knows how to transform observatory -> personality.
#  3. This code knows how to convert a filter expression to an anchor.

@register.filter
def download_url(filename, observatory):
    """Return the URL for downloading `file` of `observatory`,  optionally
    using `text` as the visible portion of the link.
    
        {{file|download_url:observatory}}
    
        {{"hst.pmap"|download_url:"hst"}} --> 
            http://localhost:8000/static/mappings/hst/hst.pmap
    """
    parts = observatory.split()
    observatory = parts[0]
    text = " ".join(parts[1:])
    if not text:
        text = filename
    return jviews.get_url(observatory, filename)

#     return mark_safe(url)
# download.is_safe = True

