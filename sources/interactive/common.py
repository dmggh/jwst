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
import traceback

# ===================================================================

from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

# ===================================================================

from crds.core import log, utils, python23, config
from crds.core.config import complete_re
from crds.core.exceptions import CrdsError
from ..config import crds_server_log_dir

from . import locks, render
from .models import FieldError

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

# ===========================================================================

def set_verbose_log(level=50):
    """Decorate a view with @verbosity to run it with increased debug logging."""
    def decomaker(func):
        """Decorator function maker"""
        def verbose_core(*args, **keys):
            """Runs `func` with verbosity `level`."""
            old_level = log.set_verbose(level)
            try:
                result = func(*args, **keys)
            finally:
                log.set_verbose(old_level)
            return result
        verbose_core.__name__ = func.__name__ + f"[verbosity={level}]"
        return verbose_core
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
    line = re.sub(r"CRDS\s+[\-\:]\s+ERROR", "CRDS - <span class='red'>ERROR</span>", line)
    line = re.sub(r"CRDS\s+[\-\:]\s+WARNING", "CRDS - <span class='orange'>WARNING</span>", line)
    return line

# ===================================================================

def crds_format_html(msg):
    """Similar to Django's format_html but skips string formatting that will crash on {} etc."""
    return mark_safe(conditional_escape(msg))

# ===================================================================

def log_view(func):
    """log() captures view inputs, output, and response to a log file.
    It should be called inside any error_trap() decorator so that it
    executes before error_trap() absorbs many exceptions.
    """
    def dolog(request, *args, **keys):
        """trap() is bound to the func parameter of decorator()."""
        log.info() # start with blank line to make concat logs readable
        log.info("REQUEST:", request.path, request.method, "ajax="+str(request.is_ajax()))
        if request.GET:
            log.info("GET:",   repr(request.GET))
        if request.POST:
            log.info("POST:",  repr(request.POST))
        if request.FILES:
            log.info("FILES:", repr(request.FILES))
        try:
            response = func(request, *args, **keys)
            return response
        except locks.LockingError as exc:  # Skip the traceback for these,  remove manually for debug to log tracebacks
            log.error("Locking error: " + str(exc))
            raise
        except Exception as exc:
            tb_str = get_traceback_str(exc)
            log.info(tb_str)
            raise
        finally:
            pass
    dolog.__name__ = func.__name__
    return dolog

def get_traceback_str(exc):
    """Return the traceback string associated with Exception `exc`."""
    info = sys.exc_info()
    tb_list = traceback.extract_tb(info[2])
    tb_str = ""
    tb_str += "EXCEPTION REPR: " + repr(exc) + "\n"
    tb_str += "EXCEPTION STR: " + str(exc) + "\n"
    tb_str += "EXCEPTION TRACEBACK:" + "\n"
    for line in traceback.format_list(tb_list):
        tb_str += line.strip() + "\n"
    return tb_str

def error_trap(template):
    """error_trap() is a 'decorator maker' which returns a decorator which
    traps exceptions in views and re-issues the input `template` with an
    appropriate error message so the user can try again.
    """
    def decorator(func):
        """decorator is bound to the template parameter of error_trap()."""
        def trap(request, *args, **keys):
            """trap() is bound to the func parameter of decorator()."""
            try:
                return func(request, *args, **keys)
            except (AssertionError, CrdsError, FieldError) as exc:
                msg = crds_format_html("ERROR: " + str(exc))
            # Generic exception handler,  undescriptive,  to prevent server probing via errors
            except Exception as exc:
                msg = crds_format_html("ERROR: internal server error")
            pars = dict(list(keys.items()) + [("error_message", msg)])
            return render.crds_render(request, template, pars, requires_pmaps=True)
        trap.__name__ = func.__name__
        return trap
    return decorator

# ===================================================================

def check_value(value, pattern, msg):
    """Ensure that `value` satisifies the conditions implied by `pattern`,
    otherwise raise a FieldError containing `msg`.

    If pattern is a function,  call it and trap for assertions, adjust value.
    If pattern is a list,  `value` must be in it.
    If pattern is a string, it is a regex which `value` must match.

    Return `value` if it checks out OK.
    """
    value = str(value)
    if isinstance(pattern, type(check_value)):
        try:
            return pattern(value)
        except Exception as exc:
            raise FieldError(msg)
    elif isinstance(pattern, list):
        for choice in pattern:
            assert "|" not in choice, "Found | in choice " + srepr(choice) + " seen as regex special char"
        pattern = config.complete_re("|".join(pattern))
    if not re.match(pattern, value):
        raise FieldError(msg)
    return value


def validate(request, variable, pattern, default=None):
    """Check a `variable` from `request`,  ensuring that it meets the
    check_value() conditions specified by `pattern`.  Use GET or POST
    depending on request type.
    """
    variables = request.GET if request.method == "GET" else request.POST
    try:
        value = str(variables[variable] if default is None 
                    else variables.get(variable, default)
                    ).strip()
    except:
        raise FieldError("Undefined parameter " + repr(variable))
    return check_value(value, pattern, "Invalid value " + srepr(value) + " for " + srepr(variable))

