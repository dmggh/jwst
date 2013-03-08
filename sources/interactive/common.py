"""Utility routines used by more than one server module."""

import sys
import cStringIO
import cProfile

from crds import log

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

