"""Middleware classes (request/response filters) for crds.server.interactive."""

from . import locks

class ResetLockExpirationMiddleware(object):
    """Manage lock expirations."""
    
    def process_request(self, request):
        """For every request,  if there is an authenticated user,  reset the expiration
        dates on all the locks they own.
        """
        user = getattr(request, "user", None)
        if user and user.is_authenticated():
            instrument = request.session.get("instrument", None)
            if instrument and instrument != "none":
                locks.reset_expiry(type="instrument", name=instrument, user=str(user))
