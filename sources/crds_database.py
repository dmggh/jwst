import os

SECRETS = os.environ["CRDS_SECRETS"]

with open(os.environ["CRDS_DJANGO_DB_PASSWORD_FILE"]) as db_file:
    DB_WORD = db_file.read().strip()

DATABASES = {
    'default': {
        'ENGINE': os.environ["CRDS_DJANGO_DB_ENGINE"],
        'NAME': os.environ["CRDS_DJANGO_DB_NAME"],
        'USER': os.environ["CRDS_DJANGO_DB_USER"],                      # Not used with sqlite3.
        'PASSWORD': DB_WORD,                                           # Not used with sqlite3.
        'HOST': os.environ["CRDS_DJANGO_DB_HOST"],                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': os.environ["CRDS_DJANGO_DB_PORT"],                      # Set to empty string for default. Not used with sqlite3.

        "OPTIONS": {
            'init_command': os.environ["CRDS_DJANGO_DB_OPTIONS_INIT"],
        },
    }
}
