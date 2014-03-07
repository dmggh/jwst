#! /usr/bin/env python
#-*-python-*-

import crds
from crds.server.interactive import models

def reset_counters():
    models.CounterModel.objects.all().delete()
    for blob in models.get_fileblob_map().values():
        path = crds.locate_file(blob.name, models.OBSERVATORY)
        models.mirror_filename_counters(models.OBSERVATORY, path)

if __name__ == "__main__":
    reset_counters()
