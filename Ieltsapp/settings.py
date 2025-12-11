"""
Django settings for Ieltsapp project.
"""
from pathlib import Path
import os
import dj_database_url
from decouple import config

# ----------------------------------------------------
# ASOIY YO'LLAR
# ----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------------------------------------------
# XAVFSIZLIK VA DEBUG
# ----------------------------------------------------
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

# ----------------------------------------------------
# ILOVALAR
# ----------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'Mock.apps.MockAppConfig',

    'widget_tweaks',
    'django_select2',
    'ckeditor',
    'ckeditor_uploader',
    'django.contrib.humanize',
    'django_bleach',
    'crispy_forms',
    'django_bunny_storage',
]

# ----------------------------------------------------
# MIDDLEWARE
# ----------------------------------------------------
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Ieltsapp.urls'
WSGI_APPLICATION = 'Ieltsapp.wsgi.application'

# ----------------------------------------------------
# DATABASE
# ----------------------------------------------------
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True
        )
    }

# ----------------------------------------------------
# KESH
# ----------------------------------------------------
if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# ----------------------------------------------------
# XAVFSIZLIK (Production)
# ----------------------------------------------------
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

    CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ['127.0.0.1', 'localhost']]
    CSRF_TRUSTED_ORIGINS += ['http://127.0.0.1:8000', 'http://localhost:8000', 'https://localhost:8000']
else:
    CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000', 'https://localhost:8000']

# ----------------------------------------------------
# STATIC FILES — HAR DOIM BOʻLSIN! (ENG MUHIM!)
# ----------------------------------------------------
STATIC_URL = '/static/'                                          # ← BU QATOR HAR DOIM BOʻLSIN!
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ----------------------------------------------------
# MEDIA FILES — BUNNY.NET (Production)
# ----------------------------------------------------
if not DEBUG:
    # To'g'ri backend nomi
    DEFAULT_FILE_STORAGE = 'django_bunny_storage.storage.BunnyStorage'

    # Bu paket faqat quyidagi nomlarni o'qiydi:
    BUNNY_USERNAME = config('BUNNY_STORAGE_ZONE_NAME')     # satmakonvideolari
    BUNNY_PASSWORD = config('BUNNY_STORAGE_PASSWORD')      # FTP & API Access → Password !!!
    BUNNY_REGION   = config('BUNNY_REGION', default='de')  # de, ny, la...

    # Fayllar qaysi papkaga tushadi
    BUNNY_BASE_DIR = "uploads/"
    CKEDITOR_UPLOAD_PATH = "uploads/"

else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    CKEDITOR_UPLOAD_PATH = "uploads/"
    
# ----------------------------------------------------
# LOGGING (xatoliklarni koʻrish uchun)
# ----------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'Mock.context_processors.global_context',
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz-UZ'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# CKEditor Sozlamalari 
CKEDITOR_IMAGE_BACKEND = "pillow" # BU YERDA CKEDITOR_UPLOAD_PATH BO'LMASLIGI KERAK!

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa', 'toolbar_Basic': [['Source', '-', 'Bold', 'Italic']],
        'filebrowserUploadUrl': '/ckeditor/upload/', 'filebrowserBrowseUrl': '/ckeditor/browse/',
        'extraPlugins': [['codesnippet,image2,autogrow']], 
        'removePlugins': 'exportpdf,flash',
        'image2_alignClasses': ['image-left', 'image-center', 'image-right'],
        'image2_toolbar': ['|', 'imageTextAlternative', '|', 'imageWidth', 'imageHeight', 'imageStyle', '|', 'imageResize', 'imageResizeWidth', 'imageResizeHeight'],
        'image2_config': {'maxWidth': 800}, 'resize_enabled': True,
        'removeButtons': 'Flash,ExportPdf',
        'toolbar_Full': [
            ['Styles', 'Format', 'Bold', 'Italic', 'Underline', 'Strike', 'SpellChecker', 'Undo', 'Redo'],
            ['Link', 'Unlink', 'Anchor'], ['Image', 'Table', 'HorizontalRule'], 
            ['TextColor', 'BGColor'], ['Smiley', 'SpecialChar'], ['Source', 'Maximize']
        ],
        'toolbar': 'Full', 'height': 300, 'width': '100%',
    }
}

CKEDITOR_ALLOW_NON_STAFF_USERS = True

BLEACH_ALLOWED_TAGS = ['p', 'b', 'i', 'u', 'em', 'strong', 'a', 'ul', 'ol', 'li','img']
BLEACH_ALLOWED_ATTRIBUTES = ['href', 'title','src', 'alt', 'width', 'height', 'style', 'class']
BLEACH_STRIP_TAGS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'Mock.CustomUser'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/redirect/'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CRISPY_TEMPLATE_PACK = "uni_form"
