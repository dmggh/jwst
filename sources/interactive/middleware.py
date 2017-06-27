"""Middleware classes (request/response filters) for crds.server.interactive."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import str
from builtins import object

from crds import log
from . import locks, views

class ResetLockExpirationMiddleware(object):
    """Manage lock expirations."""
    
    def process_request(self, request):
        """For every request,  if there is an authenticated user,  reset the expiration
        dates on all the locks they own.
        """
        # Don't reset lock expiry for (1) lock status poll or (2) log message polling
        # Other interactive views clear lock timeout
        if "lock_status" not in request.path and "jpoll" not in request.path:
            user = getattr(request, "user", None)
            if user and user.is_authenticated:
                instrument = views.get_locked_instrument(request)
                if instrument:
                    with log.info_on_exception("failed resetting lock expiration"):
                        locks.reset_expiry(type="instrument", name=instrument, user=str(user))
