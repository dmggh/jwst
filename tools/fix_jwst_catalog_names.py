import re
import os

from crds import pysh

from crds_server.interactive import models

CRDS_SERVER_FILES = os.environ["CRDS_SERVER_FILES"]

def fix_files():
    pysh.sh("cd $CRDS_SERVER_FILES/deliveries;  rename opus_ jwst_ opus*.cat;  rename _i.cat .cat jwst_*.cat")
    pysh.sh("cd $CRDS_SERVER_FILES/catalogs;  rename opus_ jwst_ opus*.cat;  rename _i.cat .cat jwst_*.cat")


def fix_file_blobs():
    for (name, blob) in list(models.get_fileblob_map("jwst").items()):
        blob.catalog_link = fix_catalog_name(blob.catalog_link)
        blob.save()

def fix_audit_blobs():
    for blob in models.AuditBlob.objects.all():
        blob.filename = fix_catalog_name(blob.filename)
        blob.details = fix_details(blob.details)
        blob.save()

def fix_details(details_text):
    return fix_catalog_name(details_text)  # works because re.sub does many replacements

def fix_catalog_name(name):
    return re.sub(r"opus_(\d+)_i.cat", r"jwst_\1.cat", name)

def main():
    import django
    django.setup()
    fix_files()
    fix_file_blobs()
    fix_audit_blobs()

if __name__ == "__main__":
    main()

