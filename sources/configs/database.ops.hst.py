from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
DB_WORD = open("/crds/data1/database/production_django_hst.dat").read().strip()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_hst',
        'USER': 'hstcrds',                      # Not used with sqlite3.
        'PASSWORD': DB_WORD,                  # Not used with sqlite3.
        'HOST': 'tanops.stsci.edu',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '33306',                      # Set to empty string for default. Not used with sqlite3.

        "OPTIONS": {
           'init_command': 'SET default_storage_engine=INNODB; SET sql_mode=STRICT_TRANS_TABLES',
        },
    }
}
