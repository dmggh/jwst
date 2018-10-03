import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.

        'NAME': config.install_dir + '/python/lib/python/crds_server/sqlite3.db',
    }
}
