from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Django settings for crds project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Todd Miller', 'jmiller@stsci.edu'),
)

MANAGERS = ADMINS

from crds.server.config import install_dir

DATABASES = {
    'default': {
         # 'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'sql_server.pyodbc', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.

        'NAME': 'crds',
        # 'sqlite3.db',                      # Or path to database file if using sqlite3.

        'USER': 'crds',                      # Not used with sqlite3.
        'PASSWORD': 'CIL',                  # Not used with sqlite3.
        'HOST': '192.168.1.86',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '1433',                      # Set to empty string for default. Not used with sqlite3.
        'OPTIONS': {
            'driver': 'FreeTDS',
            'dsn': 'CrdsDsn', # ODBC DSN name defined in your odbc.ini
            }    
        }
    }

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/Users/jmiller/work/workspace_crds/CRDS_server/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://localhost:8000/media/'

STATIC_URL = '/static/'

#STATICFILE_DIRS = ['/Users/jmiller/work/workspace_crds/CRDS_server/static/',
#                   '/Users/jmiller/work/workspace_crds/CRDS_server/interactive/static/',
#                   '/home/jmiller/work/workspace_crds/CRDS_server/static/',
#                   '/home/jmiller/work/workspace_crds/CRDS_server/interactive/static/',
#                   ]

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'zae_r-rn0arv9c_z*b41_y2qzvqgs+082)ao#6^nxsp*qf(!16'

LOGIN_URL = "/login/"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

FILE_UPLOAD_HANDLERS = ( 
    # submit_file view logic *requires* temporary files, not memory files.
    # "django.core.files.uploadhandler.MemoryFileUploadHandler",
     "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'crds.server.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "./templates",
    "./interactive/templates",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    
    'django.contrib.staticfiles',
    
    "crds.server.interactive",
    "crds.server.jsonapi",

    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)