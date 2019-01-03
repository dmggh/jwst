"""This module supports integration of CRDS rules update functions with web
functionality and results presentation.
"""

from crds.core import exceptions
from crds.refactoring import refactor

from crds_server.interactive import common

def rmap_insert_references(*args, **keys):
    """Run refactor.insert_references and capture the output.

    If an ERROR appears in the output,  raise an exception.

    Otherwise,  return the rmap insertion output.
    """
    _result, output = captured_insert_references(*args, **keys)
    if "CRDS - ERROR" in output:
        raise exceptions.MappingInsertionError(output)
    return output

@common.capture_output
def captured_insert_references(*args, **keys):
    """Decorate refactor.insert_references to capture the log output."""
    return refactor.rmap_insert_references(*args, **keys)


