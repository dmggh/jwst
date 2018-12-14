with open("/crds/data1/database/production_django_jwst.dat") as db_file:
    DB_WORD = db_file.read().strip()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_jwst_bit',
        'USER': 'jwstcrds',                      # Not used with sqlite3.
        'PASSWORD': DB_WORD,              # Not used with sqlite3.
        'HOST': 'iljwdmsbcrdsdb.stsci.edu',             # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '3306',                      # Set to empty string for default. Not used with sqlite3.
        "OPTIONS": {
           'init_command': 'SET default_storage_engine=INNODB;',
        },
    }
}
