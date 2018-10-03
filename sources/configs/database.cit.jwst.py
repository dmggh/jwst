DBWORD = open("/crds/data1/database/production_django_jwst.dat").read().strip()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_jwst_cit',
        'USER': 'jwstcrds',                      # Not used with sqlite3.
        'PASSWORD': DBWORD,              # Not used with sqlite3.
        'HOST': 'iljwdmsccrdsdb.stsci.edu',             # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '3306',                      # Set to empty string for default. Not used with sqlite3.
        "OPTIONS": {
           'init_command': 'SET default_storage_engine=INNODB;',
        },
    }
}
