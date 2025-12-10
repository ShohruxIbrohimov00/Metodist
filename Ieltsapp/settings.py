"""
Django settings for Ieltsapp project.
"""

from pathlib import Path
import os
import dj_database_url
from decouple import config  # Atrof-muhit o'zgaruvchilarini (.env/Render Env) o'qish uchun

# ----------------------------------------------------
# ASOIY YO'LLAR
# ----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------------------------------------------
# XAVFSIZLIK VA DEBUG
# ----------------------------------------------------
# Maxfiy kalitni .env faylidan olish (Renderda env variables'dan olinadi)
SECRET_KEY = config('SECRET_KEY')

# Debug holatini .env faylidan olish. Serverda HAR DOIM False bo'lishi kerak.
DEBUG = config('DEBUG', default=False, cast=bool)

# Ruxsat etilgan domenlar ro'yxati
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

ALLOWED_TELEGRAM_IDS = []

# ----------------------------------------------------
# ILOVALAR
# ----------------------------------------------------
INSTALLED_APPS = [
    # 1. Asosiy Django ilovalari
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'Mock.apps.MockAppConfig', 
    
    # 3. Boshqa uchinchi tomon ilovalari
    'widget_tweaks',
    'django_select2',
    'ckeditor',
    'ckeditor_uploader',
    'django.contrib.humanize', 
    'django_bleach',
    'crispy_forms',
    'storages',
]

# ----------------------------------------------------
# MIDDLEWARE
# ----------------------------------------------------
MIDDLEWARE = [
    # Whitenoise eng tepada bo'lishi shart
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
# DATABASE (PostgreSQL Sozlamalari)
# ----------------------------------------------------
if DEBUG:
    # Lokal rivojlanish uchun (SQLite)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Server (Render) uchun: DATABASE_URL (PostgreSQL) orqali sozlanadi
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL'),
            conn_max_age=600  # Ulanish vaqtini cheklash
        )
    }

# ----------------------------------------------------
# KESH (DUMMY/LOCMEM CACHING - RESURSLARNI TEJASH UCHUN)
# ----------------------------------------------------
if DEBUG:
    # Lokal rivojlanish uchun LocMemCache (eng sodda va tez)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
else:
    # ⭐️ Server (Production) uchun DUMMY kesh. Bu kesh chaqiriqlarini e'tiborsiz qoldiradi.
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# CELERY BROKER URL SIZNING SO'ROVINGIZGA KO'RA BUTUNLAY O'CHIRILDI.
# ----------------------------------------------------

# ----------------------------------------------------
# XAVFSIZLIKNI KUCHAYTIRISH (DEBUG=False bo'lganda)
# ----------------------------------------------------
if not DEBUG:
    # Render HTTPS ishlatganligi uchun
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    
    # HTTP Strict Transport Security (HSTS)
    SECURE_HSTS_SECONDS = 31536000 # 1 yil
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Boshqa xavfsizlik sozlamalari
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ----------------------------------------------------
# CSRF VA DOMENLAR
# ----------------------------------------------------
# ALLOWED_HOSTS asosida avtomatik HTTPS manbalarni qo'shadi
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ['127.0.0.1', 'localhost']]
CSRF_TRUSTED_ORIGINS += ['http://127.0.0.1:8000', 'http://localhost:8000', 'https://localhost:8000'] 


# ----------------------------------------------------
# STATIC VA MEDIA FILES (Render/Whitenoise)
# ----------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 

# Whitenoise statik fayllarni serverda ishlatish uchun
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ⭐️ MEDIA/FAYL SOZLAMALARI (BUNNY.NET UCHUN)
if not DEBUG:
    # Production uchun (Fayllarni Bunny Storage'ga yo'naltiramiz)
    
    # S3 protokoli bilan ishlash uchun
    AWS_S3_REGION_NAME = config('BUNNY_REGION') # Masalan, 'ny' yoki 'sg'
    AWS_S3_ENDPOINT_URL = config('BUNNY_ENDPOINT_URL') # Masalan, 'https://ny.storage.bunnycdn.com'
    
    # API Kalitlari (Bunny Storage API kalitlari)
    AWS_ACCESS_KEY_ID = config('BUNNY_ACCESS_KEY')
    AWS_SECRET_ACCESS_KEY = config('BUNNY_SECRET_KEY') # Aslida S3'da talab qilinmasa ham, ko'pincha qo'shiladi
    
    AWS_STORAGE_BUCKET_NAME = config('BUNNY_STORAGE_ZONE_NAME') # Bunny'da yaratilgan Storage Zone nomi
    
    # Fayl Saqlash Manzilini Belgilash
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Fayllarning Internetdagi URL Manzili (CDN Pull Zone orqali)
    # Masalan: https://cdn.bunny.net/sizning-pull-zone-ingiz/
    AWS_S3_CUSTOM_DOMAIN = config('BUNNY_CDN_PULL_ZONE_HOST')
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
    
    # Fayl nomlariga regionni qo'shishni o'chirish
    AWS_S3_FILE_OVERWRITE = False
    
    # CKEditor Yuklash Yo'li (Avtomatik Bunny ga yuklanadi)
    CKEDITOR_UPLOAD_PATH = 'media/uploads/' # Bunny ichidagi papka
    
else:
    # Lokal rivojlanish uchun
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    CKEDITOR_UPLOAD_PATH = "uploads/"
# ----------------------------------------------------
# BOSHQA SOZLAMALAR
# ----------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler',}},
    # DEBUG holatiga qarab log levelini sozlash
    'loggers': {'': {'handlers': ['console'], 'level': 'INFO' if not DEBUG else 'DEBUG',}},
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

# CKEditor Sozlamalari (o'zgarishsiz qoldirildi)
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"

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
