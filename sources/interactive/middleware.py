"""Middleware classes (request/response filters) for crds.server.interactive."""

from crds import log
from . import locks, views

class ResetLockExpirationMiddleware(object):
    """Manage lock expirations."""
    
    def process_request(self, request):
        """For every request,  if there is an authenticated user,  reset the expiration
        dates on all the locks they own.
        """
        user = getattr(request, "user", None)
        if user and user.is_authenticated():
            instrument = views.get_locked_instrument(request)
            if instrument and instrument != "none":
                with log.info_on_exception("failed resetting lock expiration"):
                    locks.reset_expiry(type="instrument", name=instrument, user=str(user))
