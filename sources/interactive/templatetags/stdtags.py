"""This module maps rendering functions in common.widgets onto
Django template tags so they can be used from HTML.
"""

import sys

from django import template

import delivery.common as common
import delivery.common.widgets as widgets
import delivery.common.logging as logging
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='grey')
@stringfilter
def grey(value):
    return mark_safe("<span class='grey'>" + value + "</span>")
grey.is_safe = True

# ==========================================================
def context_eval(context, expr):
    """Evaluate a template expression in a context and
    return the string result.
    """
    u = template.Template("{{ " + expr + " }}")
    return u.render(context)

# ==========================================================
# {% form_field <formname>.<fieldname> %}

class FormField(template.Node):
    def __init__(self, formname, fieldname):
        self._form = formname
        self._field = fieldname

    def render(self, context):
        return common.widgets.render_html_field(
            context[self._form], self._field)

def form_field(parser, token):
    """{% form_field <formname>.<fieldname> %}"""
    tag_name, formfield = token.split_contents()
    form, field = formfield.split(".")
    return FormField(form, field)

register.tag("form_field", form_field)

# ==========================================================
# {% select <index_expr> <choices>... %}

class SelectNode(template.Node):
    def __init__(self, tag, selector, *choices):
        self._tag = tag
        self._selector = selector
        self._choices = choices

    def render(self, context):
        selector = context_eval(context, self._selector)
        try:
            which = int(selector)
        except:
            if selector == "False":
                which = 0
            elif selector == "True":
                which = 1
            else:
                raise
        # logging.log("select:",selector,which,self._choices)

        return self._choices[which]

def select(parser, token):
    """{% select <index_var> <choices>... %}"""
    args = token.split_contents()
    return SelectNode(*args)

register.tag("select", select)

# ==========================================================
# {% button_with_help <tag> <name> <url> <help_text> %}

def remove_quotes(s):
    start = s[0] in ["'",'"'] and 1 or 0
    end   = s[-1] in ["'",'"'] and -1 or len(s)
    return s[start:end]

class ButtonWithHelp(template.Node):
    def __init__(self, tag, name, url, help_text):
        self._tag = tag
        self._name = remove_quotes(name)
        self._url = remove_quotes(url)
        self._help_text = remove_quotes(help_text)

    def render(self, context):
        t = template.loader.get_template("help_button.html")
        for var in ["name","url","help_text"]:
            u = template.Template(getattr(self, "_"+var))
            context[var] = u.render(context)
        context["balloon_id"] = widgets.get_balloon_id()
        return t.render(context)  # HTML

def button_with_help(parser, token):
    """{% button_with_help <name> <url> <help_text> %}"""
    return ButtonWithHelp(*token.split_contents())

register.tag("button_with_help", button_with_help)

# ==========================================================
# {% label_with_help <label> <help_text> %}

class LabelWithHelp(template.Node):
    def __init__(self, tag, label, help_text):
        self._tag = tag
        self._label = remove_quotes(label)
        self._help_text = remove_quotes(help_text)

    def render(self, context):
        t = template.loader.get_template("help_label.html")
        for var in ["label","help_text"]:
            u = template.Template(getattr(self, "_"+var))
            context[var] = u.render(context)
        context["balloon_id"] = widgets.get_balloon_id()
        return t.render(context)  # HTML

def label_with_help(parser, token):
    """{% label_with_help <name> <help_text> %}"""
    return LabelWithHelp(*token.split_contents())

register.tag("label_with_help", label_with_help)

# ==========================================================
# {% submit_button <tag> <name> <help_text> %}

def remove_quotes(s):
    start = s[0] in ["'",'"'] and 1 or 0
    end   = s[-1] in ["'",'"'] and -1 or len(s)
    return s[start:end]

class SubmitButtonWithHelp(template.Node):
    def __init__(self, tag, name, help_text):
        self._tag = tag
        self._name = remove_quotes(name)
        self._help_text = remove_quotes(help_text)

    def render(self, context):
        t = template.loader.get_template("submit_button.html")
        for var in ["name","help_text"]:
            u = template.Template(getattr(self, "_"+var))
            context[var] = u.render(context)
        context["balloon_id"] = widgets.get_balloon_id()
        return t.render(context)  # HTML

def submit_button(parser, token):
    """{% submit_button <tag> <name> <help_text> %}"""
    return SubmitButtonWithHelp(*token.split_contents())

register.tag("submit_button", submit_button)

# ==========================================================

def do_button_table(parser, token):
    """
    {% button_table attributes... %}
       {% button_with_help ... %}
       {% button_with_help ... %}
       {% button_with_help ... %}
       ...
    {% endbutton_table %}
    """
    nodelist = parser.parse(('endbutton_table',))
    parser.delete_first_token()
    return ButtonTable(nodelist)

class ButtonTable(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        buttons = []
        for n in self.nodelist:
            rendered = n.render(context)
            if rendered.strip():
                buttons.append(rendered)
        context["buttons"] = buttons
        t = template.loader.get_template("button_table.html")
        return t.render(context)  # HTML

register.tag("button_table", do_button_table)

