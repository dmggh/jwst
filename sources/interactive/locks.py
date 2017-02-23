"""This module implements locking to protect critical regions for the CRDS server.

The current implementation is based on the github project django-locking which is
plugged in as crds.server.locking with no changes.   The locks are database
based.

Locks can also be released by going to the admin interface and deleting them.

This module customizes django-locking to CRDS by layering additional concepts
onto the basic locks:

1. Users who own locks (locks persisting across HTTP requests.)
2. Types of locks (different namespaces for lock names.)
3. Acquisition timeouts  (Retry acquires every second until a deadline has passed, then raise)

Both users and types are supported by adding them to the lock name separated by "$".
Hence "$" may not appear in a lock name, type, or username.

Locks which persist by user are supported by using paired locks, one for the resource,
and one for the resource owned by a particular user.  First a user obtains the resource,
next they leave behind a breadcrumb lock proving they are the one that owns it.

The expiration dates of resource,user lock pairs are set to approximately the same thing.
In practice this should be good enough.

These locks are relatively slow but should still be fast enough for their
intended purpose of coordinating file submissions between different users.   This
module encapsulates django-locking so that it can be replaced if something improved
comes along.   The key feature of django-locking is atomic get-and-set:  two processes
cannot get-and-set the same lock at the same time.

A solid alternative to django-locking would be to use file locks on a local file system.
"""

import time
import datetime

from ..locking.models import Lock
from ..locking.exceptions import AlreadyLocked

from crds import CrdsError, log, utils
from crds.server import settings

NEVER = 60 * 60 * 24 * 365 * 1000   # 1000 years in seconds

class LockingError(CrdsError):
    """A routine locking error occurred which shouldn't generate a traceback
    int the CRDS log.
    """

class ResourceLockedError(LockingError):
    """The lock for a resource could not be obtained within the timeout period."""

class BrokenLockError(LockingError):
    """The desired lock no longer exists.  It expired or was released."""

class CrdsLock(object):
    """Management class to add the notion of a particular user holding a lock 
    without modifying the django-locking package.
    """
    def __init__(self, user, type, name, max_age=settings.CRDS_MAX_LOCK_AGE):
        assert "$" not in user, "Illegal lock user name '%s'" % user
        assert "$" not in type, "Illegal lock type name '%s'" % type
        assert "$" not in name, "Illegal lock name '%s'" % name
        self.user = user
        self.type = type
        self.name = name
        self.max_age = max_age
        self._resource_lock = None
        self._user_lock = None
    
    @property    
    def created_on(self):
        self._get_locks()
        return self._resource_lock.created_on
    
    @property
    def expires_on(self):
        self._get_locks()
        return self._resource_lock.created_on + datetime.timedelta(seconds=self._resource_lock.max_age)
    
    @property
    def is_expired(self):
        self._get_locks(return_expired=True)
        return self._resource_lock.is_expired
    
    @property
    def time_remaining(self):
        self._get_locks()
        return self.expires_on - datetime.datetime.now()

    def __repr__(self):
        return self.__class__.__name__ + "(user='%s', type='%s', name='%s', max_age=%d)" % \
            (self.user, self.type, self.name, self.max_age)

    @property
    def resource_lock(self):
        """The name of the generic resource being locked."""
        return self.type + "$" + self.name if self.type else self.name

    @property
    def user_lock(self):
        """The name of a generic resource combined with the name of the user that locked it."""
        return self.resource_lock + "$" + self.user
    
    def _std_info(self, verb, lock_name):
        """Log a locking info() message in a standard style."""
        msg = "%s lock '%s' at %s" % (verb.upper(), lock_name, datetime.datetime.now())
        if self.user:
            msg = "User " + repr(self.user) + " " + msg
        log.info(msg)
        
    def acquire(self, timeout=NEVER):
        """Acquire both halves of a CrdsLock, timing out after `timeout` seconds."""
        self._resource_lock = self._acquire(self.resource_lock, timeout)
        if self.user:
            self._user_lock = self._acquire(self.user_lock, timeout)
    
    def _acquire(self, lock_name, timeout=NEVER):
        """Get the locking.Lock `lock_name`.  Return a lock object.   Raise ResourceLockedError
        exception if `lock_name` cannot be acquired within `timeout` seconds.
        """
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
        self._resource_lock = self._release(self.resource_lock, silent=False)
            
    def _release(self, lock_name, silent=True):
        """Release the given `lock_kind`,   loading it from the database if it's
        not already loaded.  Set this object's copy to None afterward.
        """
        try:
            lock = self._get_existing(lock_name, return_expired=True)
        except BrokenLockError:
            if not silent:
                raise
            self._std_info("broken lock", lock_name)
        else:
            lock.release()
            self._std_info("released", lock_name)
        return None

    def _get_existing(self, lock_name, return_expired=False):
        """Fetch the Lock object for `lock_name`,  raising an exception if it
        does not exist and silent is False.
        """
        try:
            lock = Lock.objects.get(locked_object=lock_name)
        except Exception, _exc:
            log.info("_get_existing: " + str(_exc))
            lock = None
        broken = BrokenLockError("User " + repr(self.user) + " no longer holds lock " + repr(lock_name))
        if lock is None or (not return_expired and lock.is_expired):
            raise broken
        else:
            return lock
    
    def _get_locks(self, return_expired=False):
        self._resource_lock = self._get_existing(self.resource_lock, return_expired)
        if self.user:
            self._user_lock = self._get_existing(self.user_lock, return_expired)
        
    def _check_unbroken(self, lock_name, lock, datestr=None):
        if datestr:
            datestr = str(datestr)
        if (datestr and datestr != lock.created_on and datestr != str(self.created_on)):
            log.error("User " + repr(self.user) + " lost and re-acquired lock " + repr(lock_name), 
                      "datestr", datestr, "lock datestr", lock.created_on)
            raise BrokenLockError("User " + repr(self.user) + " lost and re-acquired lock " + repr(lock_name))            
 
    def verify_locked(self, datestr=None):
        """Ensure that both components of this lock are still held."""
        self._get_locks()
        self._check_unbroken(self.resource_lock, self._resource_lock, datestr)
        if self.user:
            self._check_unbroken(self.user_lock, self._user_lock, datestr)
        return True
    
    def reset_expiry(self):
        """Verify this lock is still locked and reset the expiry dates of both halves."""
        self.verify_locked()
        now = datetime.datetime.now()
        self._set_max_age(self._resource_lock, now)
        if self._user_lock:
            self._set_max_age(self._user_lock, now)
    
    def _set_max_age(self, lock, now):
        """Set the created_on field of a primitive locking.Lock `lock`."""
        delta = now - lock.created_on
        delta += datetime.timedelta(seconds=self.max_age)
        lock.max_age = int(delta.total_seconds())
        lock.save()
        new_expire = lock.created_on + datetime.timedelta(seconds=lock.max_age)
        # log.info("New lock duration", new_expire-now)
        # self._std_info("reset expiry", lock.locked_object)

    def delete(self):
        """Remove supporting lock objects from database.  NOTE:  this is not __del__
        since CrdsLock objects go out of scope all the time.   This is for supporting
        database maintenance.
        """
        with log.error_on_exception("Failed deleting resource lock for", repr(self)):
            self._resource_lock.delete()
        with log.error_on_exception("Failed deleting user lock for", repr(self)):
            if self._user_lock is not None:
                self._user_lock.delete()
    
def acquire(name, type="", user="", timeout=NEVER, max_age=settings.CRDS_MAX_LOCK_AGE):
    """Acquire the locks associated with `name` and `type` on behalf of `user`.   Fail after `timeout` seconds
    if the lock is already locked, defaulting to waiting forever.  The acquired lock will expire
    after `max_age` seconds even if it is not released.
    """
    lock = CrdsLock(user=user, type=type, name=name, max_age=max_age)
    lock.acquire(timeout)
    return lock

def release(name, type="", user=""):
    """Release the lock for the specified `name`, `type`, and `user`."""
    lock = CrdsLock(user=user, type=type, name=name)
    lock.release()
    return lock
    
def verify_locked(name, type="", user="", datestr=None):
    """Ensure that `user` owns the locks associated with `name` and `type`."""
    lock = CrdsLock(user=user, type=type, name=name)
    lock.verify_locked(datestr)
    return lock

def get_lock_datestr(name, type="", user=""):
    """Get the creation date string of the specified lock."""
    if name is None or name == "none":
        return ""
    lock = verify_locked(name, type=type, user=user)
    return str(lock.created_on)

def reset_expiry(name, type="", user=""):
    """Reset the expiration timer on locks associated with `name`, `type`, and `user`."""
    lock = CrdsLock(user=user, type=type, name=name)
    lock.reset_expiry()
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
        
def filter_locks(name=None, type=None, user=None):
    """Return the primitive locks which match name, user, and/or type."""
    filtered = []
    for lock in Lock.objects.all():
        lock_name = str(lock.locked_object)
        parts = lock_name.split("$")
        if len(parts) == 2:
            continue
        elif len(parts) == 3:
            l_type, l_name, l_user = parts
        else:
            raise CrdsError("Lock name error: '%s'." % lock_name)
        if name is not None and name != l_name:
            continue
        if type is not None and type != l_type:
            continue
        if user is not None and l_user is not None and user != l_user:
            continue
        c_lock = CrdsLock(name=l_name, user=l_user, type=l_type, max_age=lock.max_age)
        filtered.append(c_lock)
    return filtered

def release_locks(name=None, user=None, type=None):
    """Release all CRDS locks matching the specified parameters."""
    for lock in filter_locks(name=name, type=type, user=user):
        lock.release()
        
def owner_of(name, type=None):
    """Return the owner of the first CrdsLock found with the specified `name` and `type`, or 'unknown'."""
    for lock in filter_locks(name=name, type=type):
        if not lock.is_expired:
            return lock.user
    return "unknown"

def instrument_of(user):
    """Return the instrument name associated with any lock associated with `user`."""
    locks = filter_locks(user=user, type="instrument")
    if not locks:
        return None
    assert len(locks) == 1, "User {} has mode than one instrument lock.".format(user)
    lock = locks[0]
    if lock.is_expired:
        return None
    else:
        return lock.name

def get_lock_status(user, name=None, type=None):
    """Return a status dictionary about this lock."""
    locks = filter_locks(user=user, type=type, name=name)
    if locks:
        try:
            assert len(locks) == 1, "More than one lock owned by user."
            lock = locks[0]
            return { "name" : lock.name, "user": user, "type":type, "status" : "ok",
                    "created_on" : str(lock.created_on).split(".")[0],
                    "is_expired": lock.is_expired, 
                    "time_remaining": str(lock.time_remaining).split(".")[0],                
                    }
        except Exception as exc:
            try:
                name = lock.name
            except:
                name = "unknown"
            return { "name" : name, "user": user, "type":type, "status" : "error",
                    "exception": str(exc)
                    }
    else:
        return { "name": "", "user": user, "type": type, "status" : "error", 
                "exception": "no lock found."}

def get_expired_locks():
    """Return a list of expired CrdsLocks."""
    return [ lock for lock in filter_locks() if lock.is_expired ]

def clear_expired_locks():
    """Examine all locks and remove the expired locks."""
    log.info("Clearing expired locks.")
    for lock in get_expired_locks():
        log.info("Clearing expired lock", lock)
        lock.delete()

# -----------------------------------------------------------------------------

def verify_instrument_locked_files(user, locked_instrument, filepaths, observatory):
    """Ensure that all the submitted files correspond to the locked instrument and
    that the instrument is still locked.
    
    user                   username or Django User
    locked_instrument      name of instrument
    filepaths              paths of submitted files
    observatory            name of observatory, 'hst' or 'jwst'
    """
    if locked_instrument is None:
        log.info("Operating in unlocked mode.")
        return
    verify_locked(user=str(user), type="instrument", name=locked_instrument)
    for path in filepaths:
        instrument, _filekind = utils.get_file_properties(observatory, path)
        assert instrument == locked_instrument, \
            "Instrument Mismatch:  Logged in for '%s'. Submitted files for '%s'." % (locked_instrument, instrument)
     

        
