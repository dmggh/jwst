"""This module maps rendering functions in common.widgets onto
Django template tags so they can be used from HTML.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import sys
import os.path
import re

from django import template

from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import format_html, format_html_join, conditional_escape 
from django.shortcuts import render as django_render
import django.utils.encoding

import crds
from crds import rmap, utils, log, data_file
from crds.server import config
from crds.server.jsonapi import views as jviews
from crds.server.interactive import models as imodels

register = template.Library()

# ===========================================================================

# Inline styles might be better than classes.   At least these filters isolate
# that...

@register.filter(name='gray', is_safe=True)
@stringfilter
def gray(value):
    return format_html(u"<span class='{0}'>{1}</span>", "gray", value)

@register.filter(name='green', is_safe=True)
@stringfilter
def green(value):
    return format_html(u"<span class='{0}'>{1}</span>", "green", value)

@register.filter(name='darkgreen', is_safe=True)
@stringfilter
def darkgreen(value):
    return format_html(u"<span class='{0}'>{1}</span>", "darkgreen", value)

@register.filter(name='blue', is_safe=True)
@stringfilter
def blue(value):
    return format_html(u"<span class='{0}'>{1}</span>", "blue", value)

@register.filter(name='darkblue', is_safe=True)
@stringfilter
def darkblue(value):
    return format_html(u"<span class='{0}'>{1}</span>", "darkblue", value)

@register.filter(name='red', is_safe=True)
@stringfilter
def red(value):
    return format_html(u"<span class='{0}'>{1}</span>", "red", value)

@register.filter(name='yellow', is_safe=True)
@stringfilter
def yellow(value):
    return format_html(u"<span class='{0}'>{1}</span>", "yellow", value)

@register.filter(name='orange', is_safe=True)
@stringfilter
def orange(value):
    return format_html(u"<span class='{0}'>{1}</span>", "orange", value)

# ===========================================================================

@register.filter
@stringfilter
def minutes(value):  # handle str(datetime.datetime.now())
    """Return date & time formatted to minutes."""
    if value == "N/A":
        return value
    else:
        parts = value.split(":")
        return format_html_join(":", "{0}", ((part,) for part in parts[:-1]))

@register.filter
@stringfilter
def seconds(value):  # handle str(datetime.datetime.now())
    """Return date & time formatted to seconds."""
    parts = value.split(".")
    if len(parts) > 1:
        return conditional_escape(".".join(parts[:-1]))
    else:
        return conditional_escape(parts[0])

@register.filter
@stringfilter
def days(value):  # handle str(datetime.datetime.now())
    """Return only the date/day portion of a CRDS time."""
    parts = value.split(" ")
    return conditional_escape(parts[0])

@register.filter
@stringfilter
def file_exists(filename):
    if filename.lower() in ["undefined", "n/a", "no match found."]:
        return False
    with log.error_on_exception("Failed determining file existence for", repr(filename)):
        return (not rmap.is_special_value(filename)) and os.path.exists(crds.locate_file(filename, config.observatory))
    return False

@register.filter
@stringfilter
def split(string, delimiter="\n"):
    return string.split(delimiter)

@register.filter
def human_format_number(number):
    return utils.human_format_number(number)

# ===========================================================================

@register.filter(is_safe=True)
@stringfilter
def browse(name):
    return format_html("<a href='/browse/{0}'>{1}</a>", name, name)


@register.filter(is_safe=True)
@stringfilter
def context_table(pmap):
    return format_html('<a href="/context_table/{0}">{0}</a>', pmap, pmap)

@register.filter(is_safe=True)
@stringfilter
def browsify(string, fileblobs):
    try:
        return re.sub(r"\[?'([A-Za-z0-9\._]+)'[\,\]]", 
                      lambda x: _browse(x,fileblobs), string)
    except Exception:
        return string

def _browse(match, fileblobs):
    quoted_name = match.group(0)
    parts = quoted_name.split("'")
    crds_name = parts[1]
    quoted_name = crds_name # XXX hack
    if crds_name.endswith(".cat"):
        return "<tr><td>{0}</td><td></td></tr>".format(quoted_name)
    else:
        crds_name = parts[1]
        try:
            uploaded_as = fileblobs[crds_name].uploaded_as
            if uploaded_as == crds_name and crds_name.endswith(".rmap"):
                uploaded_as = fileblobs[crds_name].derived_from
            return (format_html("<tr><td>{0}</td>", uploaded_as ) + 
                    format_html("<td><a href='/browse/{0}'>{1}</a></td></tr>", crds_name, quoted_name))
        except Exception:
            format_html("<tr><td><a href='/browse/{0}'>{1}</a></td><td></td></tr>", crds_name, quoted_name)

# ===========================================================================

@register.filter(is_safe=True)
@stringfilter
def format_history(history):
    if "\n" not in history and len(history) >= 80:
        return format_html(history)
    else:
        return format_html("<pre class='simple_white'>{0}</p>", history)

# ===========================================================================

@register.filter
@stringfilter
def exists_color(name):  # handle str(datetime.datetime.now())
    color = "green" if os.path.exists(name) else "red"
    return format_html("<span class='{0}'>{1}</span>",color, name)
exists_color.is_safe = True

@register.filter
@stringfilter
def color_status(status):
    if status.lower().startswith(("ok",)):
        return green(status)
    elif status.lower().startswith(("warnings",)):
        return orange(status)
    elif status.lower().startswith(("failed","error","blacklisted","rejected","bad")):
        return red(status)
    else:
        return format_html(status)

# ===========================================================================

@register.filter
def download_url(filename):
    """Return the URL for downloading `filename`.
    """
    try:
        # return jviews.create_url(config.observatory, filename)
        return conditional_escape("/get/" + filename)
    except Exception:
        return conditional_escape(filename)


@register.filter
def download_link(filename):
    """Return the URL for downloading `filename`.
    """
    try:
        # return jviews.create_url(config.observatory, filename)
        if data_file.is_geis(filename):
            return "download <a href='{}'>header</a>&nbsp<a href='{}'>data</a>".format(
                jviews.create_unchecked_url(imodels.OBSERVATORY, filename[:-1]+"h"), 
                jviews.create_unchecked_url(imodels.OBSERVATORY, filename[:-1]+"d"))
        else:
            return "<a href='{}'>download</a>".format(
                jviews.create_unchecked_url(imodels.OBSERVATORY, filename))
    except Exception:
        return conditional_escape("[no download link]")

@register.filter
def comma_or_patterns(pattern):
    """Replace pattern values that contain or-bars with the comma seperated list
    of discrete values.
    """
    if "|" in pattern:
        return ", ".join(pattern.replace(" "*2, " ").split("|"))
    else:
        return pattern

@register.filter
def colorize_diff(pattern):
    """Replace pattern values that contain or-bars with the comma seperated list
    of discrete values.
    """
    pattern = re.sub(r"(replaced)",r"<span class='orange'>\1</span>", pattern)
    pattern = re.sub(r"(added)",r"<span class='green'>\1</span>", pattern)
    pattern = re.sub(r"(deleted)",r"<span class='red'>\1</span>", pattern)
    pattern = re.sub(r"(equal weight special case)",r"<span class='red'>\1</span>", pattern)
    pattern = re.sub(r"(requiring dynamic merging)",r"<span class='red'>\1</span>", pattern)
    return pattern

# Filter for accessing dictionary using variable
@register.filter
def lookup(d, key):
    if not isinstance(d, dict):
        try:
            d = dict(tuple(d))     # original approach
        except:
            return getattr(d, key)  # last ditch for incompatible objects 
    return d[key]

@register.simple_tag
def alpha():
    return red("alpha")

@register.simple_tag
def beta():
    return red("beta")

# ===========================================================================
# do accordion

@register.tag
def accordion(parser, token):
    pars = token.split_contents()
    tag_name = pars[0]
    title_words = pars[1:]
    nodelist = parser.parse(('endaccordion',))
    parser.delete_first_token()
    return AccordionNode(title_words, nodelist)

accordion_template = """
<div class="accordion">
    <h3>{0}</h3>
    <div>
    {1}
    </div>
</div>
"""

class AccordionNode(template.Node):
    def __init__(self, title_words, nodelist):
        self.title_words = title_words
        self.nodelist = nodelist
        
    def render(self, context):
        title_words = []
        for word in self.title_words:
            if word.startswith(('"',"'")) and word.endswith(('"',"'")):
                resolved = word[1:-1]
            elif word.startswith("{{") and word.endswith("}}"):
                t = template.Template("{% load stdtags %} " + word)
                resolved = t.render(context)
            else:
                try:
                    resolved = template.Variable(word).resolve(context)
                except Exception as exc:
                    log.info("Accordion tag failed resolving: ", repr(word), "under context", repr(context))
                    raise
            title_words.append(resolved)
        title = " ".join(title_words)
        content = self.nodelist.render(context)
        return accordion_template.format(title, content)
    
# ===========================================================================
# do jquery-ui tooltip

@register.tag
def tip(parser, token):
    pars = token.split_contents()
    tag_name = pars[0]
    title_words = pars[1:]
    nodelist = parser.parse(('endtip',))
    parser.delete_first_token()
    return TipNode(title_words, nodelist)

TIP_TEMPLATE = """
<script class="tip">
    $(function() {
        $("%s").attr("title", "%s");
    });
</script>
"""

TIP_TRAILER = """
<script>
    $( document ).tooltip();
</script>
"""

class TipNode(template.Node):
    def __init__(self, title_words, nodelist):
        self.title_words = title_words
        self.nodelist = nodelist
        
    def render(self, context):
        title_words = []
        for word in self.title_words:
            if word.startswith(('"',"'")) and word.endswith(('"',"'")):
                resolved = word[1:-1]
            elif word.startswith("{{") and word.endswith("}}"):
                t = template.Template("{% load stdtags %} " + word)
                resolved = t.render(context)
            else:
                try:
                    resolved = template.Variable(word).resolve(context)
                except Exception as exc:
                    log.info("Accordion tag failed resolving: ", 
                             repr(word), "under context", repr(context))
                    raise
            title_words.append(resolved)
        title = " ".join(title_words).strip()
        content = self.nodelist.render(context).strip()
        return TIP_TEMPLATE % (title, content)
    
# ===========================================================================
# copied from https://djangosnippets.org/snippets/847/

@register.filter
def in_group(user, groups):
    """Returns a boolean if the user is in the given group, or comma-separated
    list of groups.

    Usage::

        {% if user|in_group:"Friends" %}
        ...
        {% endif %}

    or::

        {% if user|in_group:"Friends,Enemies" %}
        ...
        {% endif %}

    """
    group_list = django.utils.encoding.force_text(groups).split(',')
    return bool(user.groups.filter(name__in=group_list).values('name'))


@register.filter
def endswith(string, suffix):
    """Exexcute string .endswith method on

    Usage::

        {% if mapping|endswith:".pmap" %}
        ...
        {% endif %}
    """
    suffix = django.utils.encoding.force_text(suffix)
    return string.endswith(suffix)
