DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_jwst_dev',
        'USER': 'jwstcrds',                      # Not used with sqlite3.
        'PASSWORD': 'uj297rWzaNyk',                  # Not used with sqlite3.
        'HOST': 'goldtst.stsci.edu',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '23306',                      # Set to empty string for default. Not used with sqlite3.

        "OPTIONS": {
           'init_command': 'SET storage_engine=INNODB;',
        },
    }
}
