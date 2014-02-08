"""Utility routines used by more than one server module."""

import sys
import cStringIO
import cProfile
import re
import os.path

from crds import log, utils
from crds.config import complete_re
from crds.server.config import crds_server_log_dir

# ===================================================================

DESCRIPTION_RE = re.compile(complete_re(r"[A-Za-z0-9._ ,\-\+\*]+"))
PERSON_RE = re.compile(complete_re(r"[A-Za-z_0-9\.@ ]*"))

DATASET_ID_RE = re.compile(complete_re(r"[A-Za-z0-9_]+"))

FITS_KEY_RE = re.compile(complete_re(r"[A-Z0-9_\-]+"))
FITS_VAL_RE = re.compile(complete_re(r"[A-Za-z0-9_\- :\.]*"))

FILE_RE_STR = r"[A-Za-z0-9_]+(\.fits|\.pmap|\.imap|\.rmap|\.r\d[hd])"   # partial
FILE_RE = re.compile(complete_re(FILE_RE_STR))

LIST_GLOB_RE = re.compile(complete_re(r"[A-Za-z0-9_\.\*\+\(\)\-\[\]]+"))

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
        out = cStringIO.StringIO()
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
        filename = os.path.join(crds_server_log_dir, filename)
    def decomaker(func):
        """Decorator function maker
        """
        def profile_core(*args, **keys):
            """profile_request runs the runit() hack under the profiler and
            extracts the function result from a global.
            """
            def runit():
                """executes a function and stores the result globally."""
                profile_core.result = func(*args, **keys)
            utils.ensure_dir_exists(filename)
            cProfile.runctx("runit()", locals(), locals(), filename=filename)
            return profile_core.result
        return profile_core
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
    line = re.sub(": ERROR", ": <span class='red'>ERROR</span>", line)
    line = re.sub(": WARNING", ": <span class='orange'>WARNING</span>", line)
    return line

