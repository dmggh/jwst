import os

from crds import log
from crds.server.interactive import models as imodels
from crds.server import crds_database

def wipe_interactive():
    print "Wiping the database removes all existing objects,  forgetting all CRDS metadata."
    print "Prior to wiping a production database,  make sure it's backed up or you know what you're doing."
    
    print crds_database.DATABASES
   
    for var in os.environ:
        if var.upper().startswith("CRDS"):
            log.verbose(var, "=", repr(os.environ[var]))


    ans = raw_input("Are you sure you want to wipe the database? (y/n) ")
    if ans.lower() != "y":
        print "Aborting..."
        return

    print "wiping files..."
    imodels.FileBlob.objects.all().delete()

    print "wiping audits..."
    imodels.AuditBlob.objects.all().delete()

    print "wiping contexts..."
    imodels.ContextBlob.objects.all().delete()

    print "wiping counters..."
    imodels.CounterBlob.objects.all().delete()

    print "done."

if __name__ == "__main__":
    wipe_interactive()
