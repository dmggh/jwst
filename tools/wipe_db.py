import crds.server.interactive.models as imodels

def wipe_interactive():
    print "Wiping the database removes all existing objects,  forgetting all CRDS metadata."
    print "Prior to wiping a production database,  make sure it's backed up or you know what you're doing."
    ans = raw_input("Are you sure you want to wipe the database? (y/n) ")
    if ans.lower() != "y":
        print "Aborting..."
        return
    print "wiping files..."
    for obj in imodels.FileBlob.objects.all():
        obj.delete()
    print "wiping audits..."
    for obj in imodels.AuditBlob.objects.all():
        obj.delete()
    print "wiping contexts..."
    for obj in imodels.ContextBlob.objects.all():
        obj.delete()
    print "wiping counters..."
    for obj in imodels.CounterBlob.objects.all():
        obj.delete()
    print "done."

if __name__ == "__main__":
    wipe_interactive()
