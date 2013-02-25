from . import locks

class ResetLockExpirationMiddleware(object):
    
    def process_request(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated():
            instrument = request.session.get("instrument", None)
            if instrument and instrument != "none":
                locks.reset_expiry(type="instrument", name=instrument, user=str(user))
