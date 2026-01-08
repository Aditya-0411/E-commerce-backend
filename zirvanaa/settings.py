import os
from datetime import timedelta
from pathlib import Path
from decouple import config
import dj_database_url
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY SETTINGS
# ---------------------------------------------------------
# 🔵 Use environment variable for secret key
SECRET_KEY = config('SECRET_KEY', default='unsafe-secret-key-for-dev')
DEBUG = config('DEBUG', default=True, cast=bool)

# 🔵 Allow hosts for local + Render
ALLOWED_HOSTS = ['api.zirvanaa.com', 'zirvanaa.com', 'www.zirvanaa.com','localhost','127.0.0.1','172.31.7.98','16.16.159.184']

    # Application definition

INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    "rest_framework",
    "rest_framework_simplejwt",  # ✅ FIXED: Added the missing JWT app
    "django_filters",
    "corsheaders",
    # Your Apps
    "accounts",
    "catalog",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',


    # 🔵 For serving static files on Render
    'whitenoise.middleware.WhiteNoiseMiddleware',
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]

# ✅ CORS settings
CORS_ALLOWED_ORIGINS = [
    'https://zirvanaa.com',
    'https://www.zirvanaa.com',
]

CORS_ALLOW_CREDENTIALS = True

# ✅ CSRF sett
CSRF_TRUSTED_ORIGINS = [
    "https://api.zirvanaa.com",
    "https://zirvanaa.com",
    "http://api.zirvanaa.com",
    "http://zirvanaa.com",
]
# ✅ Secure cookies (important for HTTPS)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
# ✅ Set cookie domain so frontend and backend share session
SESSION_COOKIE_DOMAIN = ".zirvanaa.com"   # note the dot prefix
CSRF_COOKIE_DOMAIN = ".zirvanaa.com"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),   # Short-lived, secure
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),      # Refresh every 7 days
    "ROTATE_REFRESH_TOKENS": True,                    # Issue new refresh on use
    "BLACKLIST_AFTER_ROTATION": True,                 # Blacklist old refresh
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,                        # Keep secret in env
    "AUTH_HEADER_TYPES": ("Bearer",),                 # Authorization: Bearer <token>
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

ROOT_URLCONF = 'zirvanaa.urls'

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
                ],
            },
        },
    ]

WSGI_APPLICATION = 'zirvanaa.wsgi.application'


    # Database
    # https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'zirvanaadb',
        'USER': 'zirvanaauser',
        'PASSWORD': 'Zirvanaa@Star25',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]

	
    # Internationalization
    # https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "accounts.User"
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

