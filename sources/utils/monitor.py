"""a program which runs in the background parallel to the web server:

1. periodically verifies that the services are running

2. cleans up stale web file submissions

3. backs up the CRDS Django database

4. assumes ownership of files in the server references and mappings dirs

5. periodically e-mails status

"""
import sys
import os, os.path
import shutil
import datetime
import time

from datetime import datetime, timedelta

from crds import pysh, log, client, utils, timestamp
from crds.server import config
from crds.server.interactive import models, views

# ============================================================================

MONITOR_STATUS_RECIPIENTS = ['jmiller@stsci.edu']
FORCED_STATUS_MAIL_SECONDS = 120*60

# ============================================================================

def check_server_aliveness():
    """Verify that the CRDS server is still up and running"""
    try:
        v = log.get_verbose()
        log.set_verbose(50)
        info = client.get_server_info()
        log.set_verbose(v)
        log.info("Server at", client.get_crds_server(), "is alive.")
        return True
    except Exception, exc:
        log.error("Error getting server_info:", str(exc))
        return False

# ============================================================================

def transfer_ownership():
    """Locate files not owned by CRDS and transfer them to CRDS."""
    try:
        non_crds_files = locate_non_crds_files([config.ref_path_full, 
                                                config.map_path_full])
    except Exception, exc:
        log.error("Failure locating non-crds files:", str(exc))
        return

    for filename in non_crds_files:
        try:
            log.info("Assuming ownership of", repr(filename))
            own_file(filename)
        except Exception, exc:
            log.error("Change in ownership of", repr(filename), 
                      "failed:", str(exc))

def locate_unowned_files(dirs, user="crds", group="crdsoper"):
    paths = " ".join(dirs)
    return pysh.words("find ${paths} !(-user ${user} -a -group ${group})", 
                      raise_on_error=True)

def own_file(filename, mode=0444):
    """Make a copy of a file in order to transfer ownership to crds.
    Remove the original file.   This routine makes specific assumptions about
    the stats of the transferred file:
    1. The file is owned by a cdbsoper user but not crds.
    2. The file is linked into the CRDS references or mappings directory which
       is writable by crds but not crdsoper.
    3. The file is readable by crds.
    All of this is onerous, but it's either this or setuid programs which have
    to be installed by others every time CRDS is set up.
    """
    tempfile = filename + ".assumed"
    shutil.copy2(filename, tempfile)
    os.remove(filename)
    os.rename(tempfile, filename)
    os.chmod(filename, mode)

# ============================================================================

def clean_stale_uploads():
    """Files uploaded to CRDS are in the "uploaded" state prior to being
    confirmed.   This routine handles the case where the user never confirms
    or cancels the file.
    """
    try:
        stale_uploads = find_stale_uploads()
    except Exception, exc:
        log.error("Failure locating stale uploads:", str(exc))
        return
    for filename, blob in stale_uploads.items():
        filedate = blob.delivery_date
        log.info("Removing stale upload", repr(filename),"dated:", filedate)
        try:
            os.remove(blob.filepath)
        except Exception, exc:
            log.error("Failure removing", repr(filename), ":", str(exc))
            
def find_stale_uploads(days=14, seconds=0):
    """Locate files in the "uploaded" state which are more than the specfied
    time old.
    """
    now = datetime.datetime.now()
    stale = {}
    for filename, blob in models.get_fileblob_map().items():
        if not blob.state == "uploaded":
            continue
        blob_datetime = timestamp.parse_date(blob.delivery_date)
        expiration = blob_datetime + timedelta(days,seconds)
        if expiration < now:
            stale[filename] = blob
    return stale

# ============================================================================

def backup_database():
    log.info("Faking database backup.")

# ============================================================================

def mail_results(addresses, results):
    log.info("Faking results e-mail:\n", results)

# ============================================================================

class Task(object):
    def __init__(self, function, period, next_run=None):
        self._function = function
        assert isinstance(period, timedelta)
        self._period = period
        if next_run is None:
            next_run = datetime.now()
        assert isinstance(next_run, datetime)
        self._next_run = next_run

    def __call__(self, *args, **keys):
        if datetime.now() >= self._next_run:
            self._next_run += self._period
            self.call_now(*args, **keys)
    
    def call_now(self, *args, **keys):
        log.info(timestamp.now(), "  Running", self._function.__name__)
        self._function(*args, **keys)

def tomorrow(hour, minute=0, second=0, microsecond=0):
    dt = datetime.now()
    dt = dt + timedelta(1)
    dt = datetime(dt.year, dt.month, dt.day, hour, minute, second)
    return dt

TASKS = [
         Task(check_server_aliveness, period=timedelta(0,10)),
         Task(transfer_ownership, period=timedelta(0, 5*60)),
         Task(clean_stale_uploads, period=timedelta(1, 0), next_run=tomorrow(2,0,0)),
         Task(backup_database, period=timedelta(1, 0), next_run=tomorrow(2,0,0)),
] 
    # transfer_ownership()       # every 5-10 minutes
    # clean_stale_uploads()      # nightly
    # backup_database()          # nightly

@views.capture_output
def _monitor():
    for task in TASKS:
        task()
    time.sleep(1)
    
def monitor():
    mailer = Task(mail_results, timedelta(0, 20))
    while True:
        results = _monitor()[1]
        mailer(MONITOR_STATUS_RECIPIENTS, results)
        if "ERROR" in results or "WARNING" in results:
            mailer.call_now(MONITOR_STATUS_RECIPIENTS, results)
    
if __name__ == "__main__":
    monitor()

