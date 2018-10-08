#! /usr/bin/env python
#-*-python-*-
import os
import glob

import crds
from crds_server.interactive import models

CRDS_SERVER_FILES = os.environ["CRDS_SERVER_FILES"]

def reset_counters():
    models.CounterModel.objects.all().delete()
    reset_fileblob_counters()
    reset_delivery_counters()
    
def reset_fileblob_counters():
    for blob in list(models.get_fileblob_map().values()):
        path = crds.locate_file(blob.name, models.OBSERVATORY)
        models.mirror_filename_counters(models.OBSERVATORY, path)

def reset_delivery_counters():
    for path in glob.glob(CRDS_SERVER_FILES + "/catalogs/*.cat"):
        models.mirror_filename_counters(models.OBSERVATORY, path)

if __name__ == "__main__":
    reset_counters()
