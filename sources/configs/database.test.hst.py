from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

DBWORD = open("/crds/data1/database/dev_test_django_hst.dat").read().strip()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_hst_test',
        'USER': 'hstcrds',                      # Not used with sqlite3.
        'PASSWORD': DBWORD,                  # Not used with sqlite3.
        'HOST': 'goldtst.stsci.edu',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '23306',                      # Set to empty string for default. Not used with sqlite3.

        "OPTIONS": {
           'init_command': 'SET default_storage_engine=INNODB; SET sql_mode=STRICT_TRANS_TABLES',
        },
    }
}
