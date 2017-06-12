from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_jwst_test',
        'USER': 'jwstcrds',                      # Not used with sqlite3.
        'PASSWORD': 'uj297rWzaNyk',                  # Not used with sqlite3.
        'HOST': 'goldtst.stsci.edu',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '23306',                      # Set to empty string for default. Not used with sqlite3.

        "OPTIONS": {
           'init_command': 'SET default_storage_engine=INNODB;',
        },
    }
}
