DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_hst_dev',
        'USER': 'hstcrds',                      # Not used with sqlite3.
        'PASSWORD': 'WqEynF9te2PM',                  # Not used with sqlite3.
        'HOST': 'goldtst.stsci.edu',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '23306',                      # Set to empty string for default. Not used with sqlite3.

        "OPTIONS": {
           'init_command': 'SET storage_engine=INNODB;',
        },
    }
}
