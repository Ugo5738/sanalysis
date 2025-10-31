import json
import os
import secrets
from datetime import timedelta
from pathlib import Path
from typing import List

import dj_database_url
from corsheaders.defaults import default_headers
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")

# Application definition
DEFAULT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "channels",
    "django_countries",
    "django_extensions",
    "django_filters",
    # "django_rest_passwordreset",
    "drf_yasg",
    "drf_spectacular",
    "storages",
    "django.contrib.sites",
    "rest_framework",
    # "rest_framework.authtoken",
    # "rest_framework_simplejwt",
    # "rest_framework_simplejwt.token_blacklist",
    # "allauth",
    # "allauth.account",
    # "allauth.socialaccount",
    # "allauth.socialaccount.providers.google",
    # 'allauth.socialaccount.providers.facebook',
    # "dj_rest_auth",
    # "dj_rest_auth.registration",
]

LOCAL_APPS = ["image_condition_analysis"]

OTHER_APPS = [
    # "debug_toolbar",
]

INSTALLED_APPS = DEFAULT_APPS + LOCAL_APPS + THIRD_PARTY_APPS + OTHER_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Custom added
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 'accounts.middleware.PaymentMiddleware',
]

ROOT_URLCONF = "analysis_service.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "analysis_service.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ================================ CUSTOM CONFIGS =======================================
AUTH_USER_MODEL = "auth.User"
ASGI_APPLICATION = "analysis_service.asgi.application"

LOGIN_URL = "login"
LOGOUT_URL = "logout"
LOGIN_REDIRECT_URL = "index"  # "dashboard"
LOGOUT_REDIRECT_URL = "login"


def get_origin_list(env_variable: str, default: str = "") -> List[str]:
    origins: str = config(env_variable, default)
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


# ==> CORS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = get_origin_list("CORS_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-csrftoken",
]

# ==> CSRF
CSRF_TRUSTED_ORIGINS = get_origin_list("CSRF_TRUSTED_ORIGINS")
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # False to allow JavaScript to access the cookie
SESSION_COOKIE_HTTPONLY = True

# ==> SUPABASE M2M JWT
SHARED_M2M_JWT_SECRET_KEY = config("SHARED_M2M_JWT_SECRET_KEY", default=None)
M2M_JWT_SECRET_KEY = config("M2M_JWT_SECRET_KEY", default=SHARED_M2M_JWT_SECRET_KEY)
M2M_JWT_AUDIENCE = config("M2M_JWT_AUDIENCE", default="paservices_microservices")
AUTH_SERVICE_JWT_ALGORITHM = config("AUTH_SERVICE_JWT_ALGORITHM", default="RS256")
AUTH_SERVICE_URL = config("AUTH_SERVICE_URL", default="http://auth_service:8000/api/v1")
AUTH_SERVICE_JWKS_URL = config("AUTH_SERVICE_JWKS_URL", default="")
AUTH_SERVICE_ISSUER = config("AUTH_SERVICE_ISSUER", default="paservices_auth_service")

# ==> CONSTANTS
CART_SESSION_ID = secrets.token_urlsafe(16)

SITE_ID = 1

# ==> AUTHENTICATION
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    # "allauth.account.auth_backends.AuthenticationBackend",
]

# ==> DJ-REST-Auth settings
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "my-app-auth",
    "JWT_AUTH_REFRESH_COOKIE": "my-refresh-token",
}

# ==> REST FRAMEWORK
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # USE YOUR NEW M2M AUTHENTICATOR HERE
        "image_condition_analysis.analysis_service.auth.m2m_auth.M2MJWTAuthentication",
        # Keep SessionAuthentication for the Django Admin interface
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=15),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Notification Service API",
    "DESCRIPTION": "Notification Service description",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": True,
}

# ================================ CUSTOM VARIABLES =======================================
# ==> SUPERUSER
ADMIN_USERNAME = config("ADMIN_USERNAME")
ADMIN_EMAIL = config("ADMIN_EMAIL")
ADMIN_PASSWORD = config("ADMIN_PASSWORD")

# ==> OPENAI
OPENAI_API_KEY = config("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# ==> Status notification configuration (S3 snapshots + webhook callbacks)
STATUS_S3_BUCKET_NAME = (
    config("IMAGE_CONDITION_STATUS_S3_BUCKET_NAME", default=None, cast=str) or None
)
STATUS_S3_REGION = (
    config("IMAGE_CONDITION_STATUS_S3_REGION", default=None, cast=str) or None
)
STATUS_S3_PREFIX = config(
    "IMAGE_CONDITION_STATUS_S3_PREFIX", default="image-condition/status", cast=str
)
STATUS_S3_PUBLIC_BASE_URL = (
    config("IMAGE_CONDITION_STATUS_S3_PUBLIC_BASE_URL", default=None, cast=str) or None
)
STATUS_S3_ENDPOINT_URL = (
    config("IMAGE_CONDITION_STATUS_S3_ENDPOINT_URL", default=None, cast=str) or None
)
STATUS_WEBHOOK_URL = (
    config("IMAGE_CONDITION_STATUS_WEBHOOK_URL", default=None, cast=str) or None
)
_STATUS_WEBHOOK_HEADERS_RAW = (
    config("IMAGE_CONDITION_STATUS_WEBHOOK_HEADERS", default=None, cast=str) or None
)
if _STATUS_WEBHOOK_HEADERS_RAW:
    try:
        STATUS_WEBHOOK_HEADERS = json.loads(_STATUS_WEBHOOK_HEADERS_RAW)
    except json.JSONDecodeError:
        STATUS_WEBHOOK_HEADERS = None
else:
    STATUS_WEBHOOK_HEADERS = None

STATUS_NOTIFICATIONS_ENABLED = bool(STATUS_S3_BUCKET_NAME)
# ================================ CUSTOM VARIABLES =======================================
