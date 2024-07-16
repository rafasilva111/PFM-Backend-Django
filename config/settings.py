"""
Django settings for web_project project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
import random
import string
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv

from .template import  THEME_LAYOUT_DIR, THEME_VARIABLES

load_dotenv()  # take environment variables from .env.

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
ETL_LOG_DIR = BASE_DIR / "apps/etl_app/recipe/logs"





# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# Update secret key in .env file and .env.prod file
# SECRET_KEY = os.environ.get("SECRET_KEY", default='')

# SECURITY WARNING: keep the secret key used in production secret!
# If using the .env file for SECRET_KEY then comment below random SECRET_KEY generation code.
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = "".join(random.choice(string.ascii_lowercase) for i in range(32))


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", 'True').lower() in ['true', 'yes', '1']


# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

# Current DJANGO_ENVIRONMENT
ENVIRONMENT = os.environ.get("DJANGO_ENVIRONMENT", default="local")


# Application definition

INSTALLED_APPS = [
    'daphne',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django_celery_beat',
    'django_extensions',
    "apps.home",
    "apps.layouts",
    "apps.pages",
    "apps.authentication",
    "apps.cards",
    "apps.ui",
    "apps.extended_ui",
    "apps.icons",
    "apps.forms",
    "apps.form_layouts",
    'apps.common',
    'apps.user_app',
    'apps.recipe_app',
    'apps.calendar_app',
    'apps.shopping_app',
    'apps.dispensery_app',
    'apps.notification_app',
    'apps.api',
    'apps.etl_app',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.my_setting",
                "config.context_processors.environment",
            ],
            "libraries": {
                "theme": "web_project.template_tags.theme",
            },
            "builtins": [
                "django.templatetags.static",
                "web_project.template_tags.theme",
            ],
        },
    },
]



REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),  # Adjust the duration as needed
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': 'your-signing-key',
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
ASGI_APPLICATION = 'config.asgi.application'
#WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DB_NAME = os.environ.get('DB_NAME', 'goodbites')
DB_USERNAME = os.environ.get('DB_USERNAME', 'postgres')
DB_PASS = os.environ.get('DB_PASS', 'password')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')


DATABASES = { 
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME'    : DB_NAME,
            'USER'    : DB_USERNAME,
            'PASSWORD': DB_PASS,
            'HOST'    : DB_HOST,
            'PORT'    : DB_PORT,
        },

    }


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = 'Europe/Lisbon'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


STATICFILES_DIRS = [
    BASE_DIR / "src" / "assets",
]

# Default URL on which Django application runs for specific environment
BASE_URL = os.environ.get("BASE_URL", default="http://127.0.0.1:8000")


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Template Settings
# ------------------------------------------------------------------------------

THEME_LAYOUT_DIR = THEME_LAYOUT_DIR
THEME_VARIABLES = THEME_VARIABLES



# Your stuff...
# ------------------------------------------------------------------------------


LOGIN_URL = 'login'

LOGIN_REDIRECT_URL = "home"  
LOGOUT_REDIRECT_URL = "login" 
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


AUTH_USER_MODEL = 'user_app.User'

# 0.0.0.0
CELERY_BROKER_HOST = os.environ.get('APP_BROKER_URI', '0.0.0.0')


CELERY_BROKER_URL = f'pyamqp://{CELERY_BROKER_HOST}:5672'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

from celery.schedules import crontab


CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'


"""CELERY_BEAT_SCHEDULE = {
    'run-etl-every-night': {
        'task': 'etl_app.tasks.run_etl',
        'schedule': crontab(hour=0, minute=0),  # Runs every night at midnight
    },
}"""