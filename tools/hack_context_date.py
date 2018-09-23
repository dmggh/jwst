"""Update the context history date created for the specified contexts to the specified date.
Assumes each context appears in the history only once,  this is a hack for setting up dev installations.
"""
import sys

from crds import timestamp, log

from crds_server.interactive import models

import django

def main(context, datestr):
    
    django.setup()

    date = timestamp.parse_date(datestr)
    for hist in  models.ContextHistoryModel.objects.filter(context=context):
        hist.start_date = date
        hist.save()
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: ", sys.argv[0], "<context> <YYYY-MM-DDTHH:MM:SS>") 
        sys.exit(-1)
    main(sys.argv[1], sys.argv[2])

