#!/usr/bin/env python
import sys
import os
import pdb

import django

if "--pdb" in sys.argv:
    PDB = True
    sys.argv.remove("--pdb")
else:
    PDB = False


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crds_server.settings")

    django.setup()
    from django.core.management import execute_from_command_line

    if PDB:
        pdb.runctx("execute_from_command_line(sys.argv)", locals(), globals())
    else:
        execute_from_command_line(sys.argv)

