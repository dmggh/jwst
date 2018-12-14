# Django settings for crds project.
import os.path

# ===========================================================================

import sys
from crds import log
log.add_stream_handler(sys.stderr)
log.remove_console_handler()

# ===========================================================================

from crds_server.config import install_dir, DEBUG, DEBUG_EXTRAS, FILE_UPLOAD_TEMP_DIR, crds_server_dir
from crds_server.crds_database import DATABASES

ALLOWED_HOSTS = ['*']

USE_X_FORWARDED_HOST = True

LOGIN_REDIRECT_URL = '/'   # default page redirected to after login,  fix for "/account/profile not found"

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

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

# Django dbbackup settings
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': install_dir + "/server/db_backups"}

# DBBACKUP_FILESYSTEM_DIRECTORY = install_dir + "/server/db_backups"
    
# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = install_dir + '/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_URL = '/static/'

STATIC_ROOT = install_dir + "/static"

HERE = os.path.dirname(__file__) or "."

# Used by STATICFILES_FINDERS
STATICFILES_DIRS = [os.path.abspath("static")]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/'

# Make this unique, and don't share it with anybody.
with open open("/crds/data1/database/session_key") as secret_file:
    SECRET_KEY = secret_file.read().strip()


# XXX move SECRET_KEY to files.

LOGIN_URL = "/login/"

FILE_UPLOAD_HANDLERS = ( 
    # submit_file view logic *requires* temporary files, not memory files.
    # "django.core.files.uploadhandler.MemoryFileUploadHandler",
     "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

CACHES = {
    'default' : {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    'crds_cache': {  # non-standard cache for CRDS optimizations,  
                     # "default" interacts with sessions so make a custom cache.
        'BACKEND' : 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION' : 'unix:/tmp/memcached.sock',
        "TIMEOUT" : 24 * 3600,
        }
}

# Session management, logins and expiration
# With the removal of automatic submission cancellation and "forced" confirmation,  less critical.
CRDS_MAX_LOCK_AGE = 60*60*4  # 4 hours,  refreshed every request, dropped lock enables other team members to force confirmation.
CRDS_LOCK_ACQUIRE_TIMEOUT = 2 # seconds

SESSION_EXPIRE_AT_BROWSER_CLOSE = False    # closing browser will *not* kill submission,  problem with JPOLL
SESSION_COOKIE_AGE = 60*60*18              # 18 hours,  deterministic logout,  intended as 1 killer business day.
SESSION_SAVE_EVERY_REQUEST = False         # don't reset expiry every view,  JPOLL would keep session open indefinitely

# SESSION_COOKIE_SECURE = True             # XXXX Force https: for session related communication.  Defaults False,  set True and test.

#
# Clickjacking:
#
# Disable nesting withing <IFRAME> to prevent deceptive/invisible overlay buttons
#
X_FRAME_OPTIONS = 'DENY'

MIDDLEWARE = (
    # must precede middleware which assumes CSRF already dealt with
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    
    'crds_server.interactive.middleware.ResetLockExpirationMiddleware',
)

if DEBUG_EXTRAS:
    MIDDLEWARE += (  
    # 'sugar.middleware.speedtracer.SpeedTracerMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

ROOT_URLCONF = 'crds_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            crds_server_dir + "/templates",
            crds_server_dir + "/interactive/templates",
            crds_server_dir + "/interactive/templates/registration",
            crds_server_dir + "/fileupload/templates",
            crds_server_dir + "/jsonapi/templates",
            crds_server_dir + "/jpoll/templates",
            # crds_server_dir + "/forms/templates",
            ],
        'OPTIONS': {
             'debug': DEBUG,
             'context_processors' : [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                ]
             }
    },
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    
    'django.contrib.staticfiles',
    
    "crds_server.interactive.apps.InteractiveConfig",
    "crds_server.jpoll",
    "crds_server.jsonapi",
    
    "crds_server.fileupload",
    "crds_server.locking",     # from git-hub django-locking

    # "crds_server.forms.apps.FormsConfig",

    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'dbbackup',
    'smuggler',
)

if DEBUG_EXTRAS:
    INSTALLED_APPS += (
        'sugar',           # for django speedtrace   requires django-sugar, chrome speedtracer extension
        "debug_toolbar",   # requires django-debug-toolbar
    )

    # XXX Deferred import
    from crds_server.config import CRDS_SERVER_IP
    INTERNAL_IPS = (CRDS_SERVER_IP,)  # for django-debug-toolbar
    
    DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    )

    def custom_show_toolbar(request):
        return True  # Always show toolbar, for example purposes only.

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
        'EXTRA_SIGNALS': [],  # 'myproject.signals.MySignal'],
        'HIDE_DJANGO_SQL': False,
        'TAG': 'div',
        'ENABLE_STACKTRACES' : True,
        }
