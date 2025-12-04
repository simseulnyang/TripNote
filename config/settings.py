from datetime import timedelta
from pathlib import Path

import os
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env.str('SECRET_KEY', default='test')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # third-party
    'django.contrib.sites',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.kakao',
    'allauth.socialaccount.providers.google',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'environ',
    
    #apps,
    'users',
    'trips',
]

SITE_ID = 1

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

LANGUAGE_CODE = 'ko-kr'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':(
        'rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DeFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.AllowAny',
    ],
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'TripNote API',
    'DESCRIPTION': '',
    'VERSION': '1.0.0',
}

JWT_AUTH = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    
    'ALGORITHM': 'HS256',
    'TOKEN_USER_CLASS': 'accounts.User',
    
    'AUTH_COOKIE': 'access',  # Access 토큰의 쿠키 이름
    'AUTH_COOKIE_REFRESH': 'refresh',  # Refresh 토큰의 쿠키 이름
    'AUTH_COOKIE_SECURE': True,  # HTTPS에서만 쿠키 전송
    'AUTH_COOKIE_HTTPONLY': True,  # HttpOnly 설정
    'AUTH_COOKIE_SAMESITE': 'Lax',  # SameSite 설정
    'AUTH_HEADER_TYPES': ('Bearer',),
}

KAKAO_REST_API_KEY = env.str('KAKAO_REST_API_KEY')
KAKAO_CLIENT_SECRET = env.str('KAKAO_CLIENT_SECRET')
KAKAO_REDIRECT_URI = env.str('KAKAO_REDIRECT_URI')
KAKAO_ADMIN_KEY = env.str('KAKAO_ADMIN_KEY')

GOOGLE_CLIENT_ID = env.str('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = env.str('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = env.str('GOOGLE_REDIRECT_URI')