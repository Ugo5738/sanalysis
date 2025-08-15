"""
Supabase Postgres connection helper for Django settings.

Usage in settings.py:

from analysis_service.config.supabase_db import build_databases_from_env
DATABASES = build_databases_from_env() or DATABASES

Environment variables supported:
- SUPABASE_DB_URL (preferred) e.g. postgres://user:pass@host:5432/db
- DATABASE_URL (fallback)
- SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD
- SUPABASE_DB_SSLMODE (default: require)
- DB_CONN_MAX_AGE (default: 60)
"""
from __future__ import annotations

from typing import Dict, Optional
from urllib.parse import urlparse, unquote
from decouple import config as dconfig


def _build_from_url(url: str) -> Dict[str, dict]:
    parsed = urlparse(url)
    sslmode = dconfig("SUPABASE_DB_SSLMODE", default="require")
    conn_max_age = dconfig("DB_CONN_MAX_AGE", cast=int, default=60)
    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": (parsed.path or "/").lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname,
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": conn_max_age,
            "OPTIONS": {"sslmode": sslmode},
        }
    }


def _build_from_parts() -> Optional[Dict[str, dict]]:
    host = dconfig("SUPABASE_DB_HOST", default=None)
    if not host:
        return None
    name = dconfig("SUPABASE_DB_NAME", default="postgres")
    user = dconfig("SUPABASE_DB_USER", default="postgres")
    password = dconfig("SUPABASE_DB_PASSWORD", default="")
    port = dconfig("SUPABASE_DB_PORT", cast=int, default=5432)
    sslmode = dconfig("SUPABASE_DB_SSLMODE", default="require")
    conn_max_age = dconfig("DB_CONN_MAX_AGE", cast=int, default=60)
    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": name,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": port,
            "CONN_MAX_AGE": conn_max_age,
            "OPTIONS": {"sslmode": sslmode},
        }
    }


def build_databases_from_env() -> Optional[Dict[str, dict]]:
    """Return a Django DATABASES dict built from Supabase env vars.

    Priority:
      1) SUPABASE_DB_URL
      2) DATABASE_URL
      3) SUPABASE_DB_HOST + parts
    """
    url = dconfig("SUPABASE_DB_URL", default=None) or dconfig("DATABASE_URL", default=None)
    if url:
        return _build_from_url(url)
    return _build_from_parts()
