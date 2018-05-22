"""Utility routines used by more than one server module."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# from builtins import str

# ===================================================================

import sys
import cProfile
import re
import os.path

# ===================================================================

from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

# ===================================================================

from crds.core import log, utils, python23
from crds.core.config import complete_re
from crds.server.config import crds_server_log_dir

# ===================================================================

DESCRIPTION_RE = re.compile(complete_re(r"[A-Za-z0-9._\s/,=\-\+]{1,2000}")) 
PERSON_RE = re.compile(complete_re(r"[A-Za-z_0-9\.@, \-]{0,128}"))

DATASET_ID_PART = r"[A-Za-z0-9_\.\+\-]{1,128}"
DATASET_ID_RE = re.compile(complete_re(DATASET_ID_PART + "(:" + DATASET_ID_PART+")?"))

FITS_KEY_RE_STR = r"[A-Za-z0-9_\-\.]{1,256}"
FITS_KEY_RE = re.compile(complete_re(FITS_KEY_RE_STR))
FITS_VAL_RE = re.compile(complete_re(r".{0,256}"))

LIST_GLOB_RE = re.compile(complete_re(r"[A-Za-z0-9_\.\*\+\(\)\-\[\]]{1,128}"))

INSTRUMENT_RE = re.compile(complete_re(r"[A-Za-z0-9_]{1,64}"))
FIELD_RE = re.compile(complete_re(r"[A-Za-z0-9_]{1,64}"))

UUID_RE_STR = r"[A-Za-z0-9]{8}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{12}"
UUID_RE = re.compile(complete_re(UUID_RE_STR))

# ===================================================================

def capture_output(func):
    """Decorate a function with @capture_output to make it capture and return
    stdout/stderr as part of it's result.   Returns (original_result, outlines)
    """
    def captured(*args, **keys):
        """Temorarily re-assign stdout/stderr to a StringIO, run func,
        return captured output.
        """
        oldout, olderr = sys.stdout, sys.stderr
        out = python23.StringIO()
        sys.stdout, sys.stderr = out, out
        handler = log.add_stream_handler(out)
        try:
            result = func(*args, **keys)
        finally:
            out.flush()
            log.remove_stream_handler(handler)
            sys.stdout, sys.stderr = oldout, olderr
        out.seek(0)
        return result, out.read()
    return captured

# ===========================================================================

def profile(filename=None):
    """Decorate a view with @profile to run cProfile when the function is called.
    """
    if not os.path.dirname(filename):
        filename = os.path.join(crds_server_log_dir, "..", "profiles", filename)
    def decomaker(func):
        """Decorator function maker
        """
        # @utils.elapsed_time,  name must be established first
        def profile_core(*args, **keys):
            """profile_request runs the runit() hack under the profiler and
            extracts the function result from a global.
            """
            def runit():
                """executes a function and stores the result globally."""
                profile_core.result = func(*args, **keys)
            runit.__name__ = func.__name__ + " [profile]"
            utils.ensure_dir_exists(filename)
            cProfile.runctx("runit()", locals(), locals(), filename=filename)
            return profile_core.result
        profile_core.__name__ = func.__name__ + "[profile]"
        return utils.elapsed_time(profile_core)
    return decomaker

# ===================================================================

def srepr(string):
    """A string repr which suppresses u'' notation."""
    return repr(str(string))


# ===================================================================

class Struct(dict):
    """A dictionary which supports dotted access to members."""
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, val):
        self[name] = val

# ===================================================================

def html_colorize_log(output):
    """Format CRDS log output as colorized HTML paragraphs."""
    html = []
    for line in output.splitlines():
        html.append("<p>" + colorize_line(line) + "</p>")
    return "\n".join(html)

def colorize_line(line):
    """Add color to one CRDS log line."""
    line = re.sub("CRDS\s+[\-\:]\s+ERROR", "CRDS - <span class='red'>ERROR</span>", line)
    line = re.sub("CRDS\s+[\-\:]\s+WARNING", "CRDS - <span class='orange'>WARNING</span>", line)
    return line

# ===================================================================

def crds_format_html(msg):
    """Similar to Django's format_html but skips string formatting that will crash on {} etc."""
    return mark_safe(conditional_escape(msg))
