# ./analysis_service/auth/m2m_auth.py
import os
from dataclasses import dataclass
from typing import Optional, Tuple

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions


@dataclass
class ServiceClient:
    """A simple, non-persistent object to represent an authenticated service."""

    client_id: str

    @property
    def is_authenticated(self) -> bool:
        return True


class M2MJWTAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication backend that validates M2M JWTs issued by the auth_service.
    """

    def authenticate(self, request) -> Optional[Tuple[ServiceClient, None]]:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            # Invalid header format
            return None

        token = parts[1]

        # These must be set in your Django settings (.env file)
        secret = getattr(settings, "SHARED_M2M_JWT_SECRET_KEY", None)
        audience = getattr(settings, "M2M_JWT_AUDIENCE", None)

        if not secret or not audience:
            # If not configured, this backend cannot authenticate.
            # Returning None allows other backends (like SessionAuthentication for the admin) to try.
            return None

        try:
            payload = jwt.decode(
                token,
                key=secret,
                algorithms=["HS256"],
                audience=audience,
            )

            client_id = payload.get("sub")
            if not client_id:
                raise exceptions.AuthenticationFailed(
                    "Invalid token: Missing 'sub' (client_id) claim."
                )

            # On successful validation, return a ServiceClient object.
            # This object will be available as `request.user`.
            user = ServiceClient(client_id=client_id)
            return (user, None)

        except jwt.ExpiredSignatureError as e:
            raise exceptions.AuthenticationFailed("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f"Invalid token: {e}") from e
