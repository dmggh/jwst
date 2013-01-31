"""Utility routines used by more than one server module."""

import sys
import cStringIO

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

# ===================================================================

def srepr(string):
    """A string repr which suppresses u'' notation."""
    return repr(str(string))
        
