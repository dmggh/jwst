"""Middleware classes (request/response filters) for crds.server.interactive."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# from builtins import str
# from builtins import object

from crds.core import log
from . import locks

class ResetLockExpirationMiddleware(object):
    """Manage instrument lock timeouts for all views except lock polling and
    JSONRPC services.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # Don't reset lock expiry for (1) lock status poll or (2) log message polling
        # via JSONRPC for command line tools.  Other interactive views clear lock timeout.
        if "lock_status" not in request.path and "jpoll" not in request.path:
            user = getattr(request, "user", None)
            if user and user.is_authenticated:
                instrument = locks.get_locked_instrument(request)
                if instrument:
                    with log.info_on_exception("failed resetting lock expiration"):
                        locks.reset_expiry(type="instrument", name=instrument, user=str(user))

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

