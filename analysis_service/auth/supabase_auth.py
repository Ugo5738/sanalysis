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
    def is_authenticated(self) -> bool:
        return True


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication backend that validates Supabase GoTrue JWTs.
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
            return None  # If not configured, skip auth

        try:
            payload = jwt.decode(
                token,
                key=secret,
                algorithms=["HS256"],
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
