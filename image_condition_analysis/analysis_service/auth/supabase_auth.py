from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

import jwt
from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication, exceptions


@dataclass
class SupabaseUser:
    sub: str
    email: Optional[str]
    role: Optional[str]

    @property
    def is_authenticated(self) -> bool:  # DRF expects this attribute
        return True


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication backend that validates Supabase GoTrue JWTs using HS256.

    Requirements:
    - SUPABASE_JWT_SECRET: HMAC secret used by Supabase.
    - Optional: SUPABASE_JWT_AUD to validate the `aud` claim.

    Usage: add to REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] before others.
    """

    def authenticate(self, request) -> Optional[Tuple[SupabaseUser, None]]:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]
        secret = os.getenv("SUPABASE_JWT_SECRET")
        if not secret:
            # If not configured, skip and let other backends try
            return None

        try:
            payload = jwt.decode(
                token,
                key=secret,
                algorithms=["HS256"],
                options={"verify_aud": bool(os.getenv("SUPABASE_JWT_AUD"))},
                audience=os.getenv("SUPABASE_JWT_AUD"),
            )
        except jwt.ExpiredSignatureError as e:
            raise exceptions.AuthenticationFailed("Token expired") from e
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed("Invalid token") from e

        user = SupabaseUser(
            sub=str(payload.get("sub")),
            email=payload.get("email"),
            role=payload.get("role"),
        )
        return (user, None)


class OptionalAuthentication(authentication.BaseAuthentication):
    """
    A no-op backend that always returns AnonymousUser.
    Useful if you want endpoints to be open but still run the auth chain.
    """

    def authenticate(self, request):
        return (AnonymousUser(), None)
