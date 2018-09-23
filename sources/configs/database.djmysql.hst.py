import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'crds_hst_django',
        'USER': 'jmiller',                      # Not used with sqlite3.
        'PASSWORD': 'ThisIsATest',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '3306',                      # Set to empty string for default. Not used with sqlite3.
        "OPTIONS": {
           'init_command': 'SET default_storage_engine=INNODB;',
        },
    }
}
