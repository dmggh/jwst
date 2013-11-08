# Django settings for crds project.
import os.path

from crds.server.config import install_dir, DEBUG, DEBUG_EXTRAS, FILE_UPLOAD_TEMP_DIR, crds_server_dir
from crds.server.crds_database import DATABASES

TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Todd Miller', 'jmiller@stsci.edu'),
)

MANAGERS = ADMINS

ALLOWED_HOSTS = ['*']

USE_X_FORWARDED_HOST = True

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
DBBACKUP_STORAGE = 'dbbackup.storage.filesystem_storage'
DBBACKUP_FILESYSTEM_DIRECTORY = install_dir + "/server/db_backups"
    
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
# STATICFILES_DIRS = open(HERE + "/" + "static_dirs.txt").read().splitlines()
# STATICFILES_DIRS = [ os.path.abspath(sdir) for sdir in STATICFILES_DIRS]
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
SECRET_KEY = 'zae_r-rn0arv9c_z*b41_y2qzvqgs+082)ao#6^nxsp*qf(!16'

LOGIN_URL = "/login/"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

#TEMPLATE_CONTEXT_PROCESSORS = [
#    'django.contrib.messages.context_processors.messages',
#]

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
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'unix:/tmp/memcached.sock',
        }
}

# Session management, logins and expiration

SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60*60*24*365*1000   # 1000 years
CRDS_MAX_LOCK_AGE = 60*60*4  # 4 hours,  refreshed every request
CRDS_LOCK_ACQUIRE_TIMEOUT = 2 # seconds

MIDDLEWARE_CLASSES = (
    # must precede middleware which assumes CSRF already dealt with
    'django.middleware.csrf.CsrfViewMiddleware',
    
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    
    # 'crds.server.stats.middleware.LogMiddleware',
    'crds.server.interactive.middleware.ResetLockExpirationMiddleware',
)

if DEBUG_EXTRAS:
    MIDDLEWARE_CLASSES += (  
    'sugar.middleware.speedtracer.SpeedTracerMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

ROOT_URLCONF = 'crds.server.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    crds_server_dir + "/templates",
    crds_server_dir + "/interactive/templates",
    crds_server_dir + "/fileupload/templates",
    crds_server_dir + "/jsonapi/templates",
    crds_server_dir + "/jpoll/templates",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    
    'django.contrib.staticfiles',
    
    "crds.server.interactive",
    "crds.server.jpoll",
    "crds.server.jsonapi",
    # "crds.server.stats",    # CRDS Django request logging
    
    "crds.server.fileupload",
    "crds.server.locking",     # from git-hub django-locking

    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'dbbackup',
)

if DEBUG_EXTRAS:
    INSTALLED_APPS += (
        'sugar',           # for django speedtrace   requires django-sugar, chrome speedtracer extension
        "debug_toolbar",   # requires django-debug-toolbar
    )

    # XXX Deferred import
    from crds.server.config import CRDS_SERVER_IP
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
