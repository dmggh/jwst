"""This module implements locking to protect critical regions for the CRDS server.

The current implementation is based on the github project django-locking which is
plugged in minimally in settings.py.

Locks can be released by going to the admin interface and deleting them.
"""

import time
import datetime

import locking.models
from locking.exceptions import AlreadyLocked

from crds import CrdsError, log

NEVER=60*60*24*365*1000   # 1000 years in seconds

class ResourceLockedError(CrdsError):
    """The lock for a resource could not be obtained within the timeout period."""

def _lname(name, type):
    return "_".join([type, name])

def _std_info(verb, user, name,  type):
    log.info("User '%s' %s '%s' lock '%s' at %s" % (user, verb.upper(), type, name, datetime.datetime.now()))

def acquire(name, type="", user="unknown", timeout=NEVER, max_age=0):
    """Get the lock `name` of the specified `type`.  Return a lock object."""
    lock_name = _lname(name, type)
    start = datetime.datetime.now()
    deadline = start + datetime.timedelta(seconds=timeout)
    naptime = 1.0
    while datetime.datetime.now() < deadline:
        try:
            lock = locking.models.Lock.objects.acquire_lock(lock_name=lock_name, max_age=max_age)
        except AlreadyLocked:
            _std_info("waiting", user, name, type)
            time.sleep(naptime)
        else:
            _std_info("acquired", user, name, type)
            return lock    
    _std_info("timed out", user, name, type)
    raise ResourceLockedError("Can't get lock for '%s'." % lock_name)
        
def release(name, type="", user="unknown"):
    """Release the given lock. `name` can be a name (with type) or a Lock from acquire()."""
    if isinstance(name, locking.models.Lock):
        lock = name
        lock_name = lock.locked_object
    else:
        lock_name = _lname(name, type)
        try:
            lock = locking.models.Lock.objects.get(locked_object=lock_name)
        except Exception, exc:
            _std_info("failed releasing", user, name, type)
            log.info(str(exc))
            return
    lock.release()
    type, name = lock_name.split("_")
    _std_info("released", user, name, type)

def release_all():
    """Release all locks of all types."""
    locking.models.Lock.objects.all().delete()
    log.info("Released all locks at", datetime.datetime.now())
    
def listall():
    """Print out info on all existing locks."""
    locks = locking.models.Lock.objects.all()
    for lock in locks:
        log.info("Lock ", repr(lock))
        
