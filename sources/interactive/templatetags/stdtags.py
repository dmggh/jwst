"""This module maps rendering functions in common.widgets onto
Django template tags so they can be used from HTML.
"""

import sys
import os.path

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

@register.filter(name='yellow')
@stringfilter
def yellow(value):
    return mark_safe("<span class='yellow'>" + value + "</span>")
yellow.is_safe = True

@register.filter(name='orange')
@stringfilter
def orange(value):
    return mark_safe("<span class='orange'>" + value + "</span>")
orange.is_safe = True

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

@register.filter
@stringfilter
def exists_color(name):  # handle str(datetime.datetime.now())
    color = "green" if os.path.exists(name) else "red"
    return mark_safe("<span class='%s'>%s</span>" % (color, name))
exists_color.is_safe = True

@register.filter
@stringfilter
def color_status(status):
    if status.lower().startswith(("ok",)):
        return green(status)
    elif status.lower().startswith(("warnings",)):
        return orange(status)
    elif status.lower().startswith(("failed","errors")):
        return red(status)
    else:
        return status

# ===========================================================================

# Because of multiple projects this is uncomfortably complicated.  Sorry.
#  1. Both client and server observatory "personality" live in a single package.
#  2. The core library knows how to transform observatory -> personality.
#  3. This code knows how to convert a filter expression to an anchor.

@register.filter
def download_url(filename):
    """Return the URL for downloading `filename`.

        {{"hst.pmap"|download_url}} --> 
            http://localhost:8000/static/mappings/hst/hst.pmap
    """
    try:
        return jviews.create_url(config.observatory, filename)
    except Exception:
        return filename

#     return mark_safe(url)
# download.is_safe = True

# Filter for accessing dictionary using variable
@register.filter
def lookup(d, key):
    if not isinstance(d, dict):
        d = dict(tuple(d))
    return d[key]

@register.simple_tag
def alpha():
    return red("alpha")

@register.simple_tag
def beta():
    return red("beta")

# do accordion

@register.tag
def accordion(parser, token):
    tag_name, title = token.split_contents()
    nodelist = parser.parse(('endaccordion',))
    parser.delete_first_token()
    # title = parser.compile_filter(title)
    if title.startswith(('"',"'")) and title.endswith(('"',"'")):
        title = title[1:-1]
    return AccordionNode(title, nodelist)

accordion_template = """
<div class="accordion">
<h3><a href="#">%s</a></h3>
<div>
"""

class AccordionNode(template.Node):
    def __init__(self, title, nodelist):
        self.title = title
        self.nodelist = nodelist
        
    def render(self, context):
        output = accordion_template % self.title
        output += self.nodelist.render(context)
        output += "</div>\n"
        output += "</div>\n"
        return output
