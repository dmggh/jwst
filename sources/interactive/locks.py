"""This module implements locking to protect critical regions for the CRDS server.

The current implementation is based on the github project django-locking which is
plugged in as crds.server.locking with minimal changes.   The locks are database
based.

Locks can also be released by going to the admin interface and deleting them.
"""

import time
import datetime

from ..locking.models import Lock
from ..locking.exceptions import AlreadyLocked

from crds import CrdsError, log

NEVER=60*60*24*365*1000   # 1000 years in seconds

class ResourceLockedError(CrdsError):
    """The lock for a resource could not be obtained within the timeout period."""

class BrokenLockError(CrdsError):
    """The desired lock no longer exists.   It expired or was killed."""

class CrdsLock(object):
    """Management class to add the notion of a particular user holding a lock 
    without modifying the django-locking package.
    """
    def __init__(self, user, type, name, max_age=NEVER):
        self.user = user
        self.type = type
        self.name = name
        self.max_age = max_age
        self._resource_lock = None
        self._user_lock = None

    def __repr__(self):
        return self.__class__.__name__ + "(user='%s', type='%s', name='%s', max_age=%d)" % \
            (self.user, self.type, self.name, self.max_age)

    @property
    def resource_lock(self):
        return self.type + "_" + self.name if self.type else self.name

    @property
    def user_lock(self):
        return self.resource_lock + "_" + self.user
    
    def _std_info(self, verb, lock_name):
        msg = "%s lock '%s' at %s" % (verb.upper(), lock_name, datetime.datetime.now())
        if self.user:
            msg = "User " + repr(self.user) + " " + msg
        log.info(msg)
        
    def acquire(self, timeout=NEVER):
        self._resource_lock = self._acquire(self.resource_lock, timeout)
        if self.user:
            self._user_lock = self._acquire(self.user_lock, timeout=30)
    
    def _acquire(self, lock_name, timeout=NEVER):
        """Get the `lock_name`.  Return a lock object."""
        start = datetime.datetime.now()
        deadline = start + datetime.timedelta(seconds=timeout)
        naptime = 1.0
        while datetime.datetime.now() < deadline:
            try:
                lock = Lock.objects.acquire_lock(lock_name=lock_name, max_age=self.max_age)
            except AlreadyLocked:
                self._std_info("waiting", lock_name)
                time.sleep(naptime)
            else:
                self._std_info("acquired", lock_name)
                return lock    
        self._std_info("timed out", lock_name)
        raise ResourceLockedError("Can't get lock for '%s'." % lock_name)
        
    def release(self):
        """Release this lock on behalf of self.user."""
        if self.user:
            self._user_lock = self._release(self.user_lock, silent=False)
        self._resource_lock = self._release(self.resource_lock)
            
    def _release(self, lock_name, silent=True):
        """Release the given `lock_kind`,   loading it from the database if it's
        not already loaded.  Set this object's copy to None afterward.
        """
        try:
            lock = self._get_existing(lock_name)
        except BrokenLockError:
            if not silent:
                raise
            self._std_info("broken lock", lock_name)
        else:
            lock.release()
            self._std_info("released", lock_name)
        return None

    def _get_existing(self, lock_name):
        """Fetch the Lock object for `lock_name`,  raising an exception if it
        does not exist and silent is False.
        """
        try:
            lock = Lock.objects.get(locked_object=lock_name)
        except Exception, exc:
            # log.info("_get_existing: " + str(exc))
            lock = None
        if lock is None or lock.is_expired:
            raise BrokenLockError("User " + repr(self.user) + " no longer holds lock " + repr(lock_name))
        else:
            return lock

    def verify_locked(self):
        """Ensure that both components of this lock are still held."""
        self._user_lock = self._get_existing(self.user_lock)
        self._resource_lock = self._get_existing(self.resource_lock)
        return True
            
    
def acquire(name, type="", user="", timeout=NEVER, max_age=NEVER):
    lock = CrdsLock(user=user, type=type, name=name, max_age=max_age)
    lock.acquire(timeout)
    return lock

def release(name, type="", user=""):
    lock = CrdsLock(user=user, type=type, name=name)
    lock.release()
    return lock
    
def verify_locked(name, type="", user=""):
    lock = CrdsLock(user=user, type=type, name=name)
    lock.verify_locked()
    return lock

def release_all():
    """Release all locks of all types."""
    Lock.objects.all().delete()
    log.info("Released all locks at", datetime.datetime.now())
    
def listall():
    """Print out info on all existing locks."""
    locks = Lock.objects.all()
    for lock in locks:
        log.info("Lock ", repr(lock))
