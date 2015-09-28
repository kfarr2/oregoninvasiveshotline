import os
from fnmatch import fnmatch

import pkg_resources
from django.contrib.messages import constants as messages
from django.core.urlresolvers import reverse_lazy
from local_settings import LocalSetting, SecretSetting, load_and_check_settings
from mommy_spatial_generators import MOMMY_SPATIAL_FIELDS

#
# Package Stuff
#
CWD = os.getcwd()
PACKAGE = os.path.basename(os.path.dirname(__file__))
PACKAGE_DIR = pkg_resources.resource_filename(PACKAGE, '')

#
# Path constructors
#

DJANGO_DIR = lambda *path: os.path.normpath(os.path.join(os.path.dirname(__file__), *path))
BASE_DIR = lambda *path: DJANGO_DIR("../", *path)

#
# System and Debugging
#

# SECURITY WARNING: don't run with debug turned on in production!
# make this True in dev
DEBUG = LocalSetting(default=False)
DEFAULT_FROM_EMAIL = SERVER_EMAIL = 'no-reply@pdx.edu'


# allow the use of wildcards in the INTERAL_IPS setting
class IPList(list):
    # do a unix-like glob match
    # E.g. '192.168.1.100' would match '192.*'
    def __contains__(self, ip):
        return any(fnmatch(ip, ip_pattern) for ip_pattern in self)
INTERNAL_IPS = IPList(['10.*', '192.168.*'])
ADMINS = LocalSetting(default=[("Konstantin", "foo@example.com")])

#
# Host info
#

# This hostname is used to construct URLs. It would be something like
# "example.com" in production. This is used to construct the
# SESSION_COOKIE_DOMAIN and ALLOWED_HOSTS, so make sure it is correct
HOSTNAME = LocalSetting(default="10.0.0.10.xip.io:8000")
# we construct the SESSION_COOKIE_DOMAIN based on the hostname. We prepend a
# dot so the cookie is set for all subdomains
# SESSION_COOKIE_DOMAIN = "." + HOSTNAME.split(":")[0]
ALLOWED_HOSTS = ["*"]

#
# Test Stuff
#

# we use a custom test runner to set some custom settings
TEST_RUNNER = 'hotline.testrunner.TestRunner'
# are we in test mode? This gets overridden in the test runnner
TEST = LocalSetting(default=False)

#
# Auth Stuff
#

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = reverse_lazy("login")
LOGIN_REDIRECT_URL = reverse_lazy("users-home")
# uncomment to use CAS. You need to update requirements.txt too
# CAS_SERVER_URL = 'https://sso.pdx.edu/cas/'
# AUTHENTICATION_BACKENDS += ('djangocas.backends.CASBackend',)

#
# Celery
#

# CELERY_ACKS_LATE = True
# CELERY_RESULT_BACKEND = 'amqp'
# The celery broker URL 'amqp://guest:guest@localhost//'
# BROKER_URL = variable("BROKER_URL", default='amqp://guest:guest@localhost//')


#
# Email
#

# In production, use something like 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = LocalSetting(default='django.core.mail.backends.console.EmailBackend')

#
# DB
#

DATABASES = {
    'default': {
        'NAME': LocalSetting(PACKAGE),
        # the default is fine for dev
        'USER': LocalSetting(''),
        # the default is fine for dev
        'PASSWORD': SecretSetting(),
        # the default is fine for dev
        'HOST': LocalSetting(''),
        'ATOMIC_REQUESTS': True,
    },
}

LOGGING_CONFIG = 'arcutils.logging.basic'

#
# Flatpages
#
SITE_ID = 1

#
# Elaticsearch
#

ELASTICSEARCH_CONNECTIONS = {
    'default': {
        'hosts': [LocalSetting(default='http://localhost:9200')],
        'index_name': 'hotline',
    }
}

#
# UI
#

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

ITEMS_PER_PAGE = 100


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    # auth doesn't have to be installed to use the django auth stuff. It adds a
    # bunch of annoying group and permission tables
    # 'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'django.contrib.gis',
    'permissions',
    'arcutils',
    'elasticmodels',
    'hotline.pages',
    'hotline.users',
    'hotline.species',
    'hotline.reports',
    'hotline.images',
    'hotline.notifications',
    'hotline.comments',
    'hotline.counties',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cloak.middleware.CloakMiddleware',
    # 'djangocas.middleware.CASMiddleware',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'hotline.utils.RubyPasswordHasher',
)

ROOT_URLCONF = 'hotline.urls'

WSGI_APPLICATION = 'hotline.wsgi.application'

#
# I18n and Time
#

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = False
USE_L10N = False
USE_TZ = True


#
# Static files and media
#

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    DJANGO_DIR("static"),
)
STATIC_ROOT = BASE_DIR("static")

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR("media")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SecretSetting(doc="The secret key")

#
# Templates
#

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [DJANGO_DIR("templates")],
    'APP_DIRS': True,
    'OPTIONS': {
        'debug': DEBUG,
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.media',
            'django.template.context_processors.static',
            'django.template.context_processors.tz',
        ],
    },
}]

#
# Test specific stuff
#

MOMMY_CUSTOM_FIELDS_GEN = MOMMY_SPATIAL_FIELDS


#
# Need this for Wyatt's deployment tool
#
_settings = load_and_check_settings(globals())
globals().update(_settings)

if _settings.get('TEST'):
    import logging
    logging.disable(logging.ERROR)
