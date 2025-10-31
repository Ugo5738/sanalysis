# ./analysis_service/auth/m2m_auth.py
import json
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import jwt
import requests
from django.conf import settings
from jwt.algorithms import RSAAlgorithm
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

    _jwks_cache: Optional[Dict[str, dict]] = None
    _jwks_cache_expiry: float = 0.0

    @staticmethod
    def _auth_error(detail: str) -> exceptions.AuthenticationFailed:
        return exceptions.AuthenticationFailed(detail)

    @classmethod
    def _resolve_jwks_url(cls) -> str:
        explicit = getattr(settings, "AUTH_SERVICE_JWKS_URL", None)
        if explicit:
            return explicit.rstrip("/")

        base_url = getattr(settings, "AUTH_SERVICE_URL", "").rstrip("/")
        if not base_url:
            raise cls._auth_error("Auth service JWKS URL is not configured.")
        if not base_url.endswith("/auth"):
            base_url = f"{base_url}/auth"
        return f"{base_url}/.well-known/jwks.json"

    @classmethod
    def _fetch_jwks(cls) -> Dict[str, dict]:
        now = time.time()
        if cls._jwks_cache and now < cls._jwks_cache_expiry:
            return cls._jwks_cache

        url = cls._resolve_jwks_url()
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise cls._auth_error("Unable to retrieve JWKS from auth service.") from exc

        jwks = response.json()
        cls._jwks_cache = jwks
        cls._jwks_cache_expiry = now + 300  # cache for 5 minutes
        return jwks

    @classmethod
    def _get_jwk(cls, kid: Optional[str]) -> dict:
        if not kid:
            raise cls._auth_error("Invalid token: missing key identifier.")

        jwks = cls._fetch_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        raise cls._auth_error("Invalid token: unknown signing key.")

    @classmethod
    def _decode_hs_token(cls, token: str, audience: str) -> dict:
        secret = getattr(settings, "SHARED_M2M_JWT_SECRET_KEY", None) or getattr(
            settings, "M2M_JWT_SECRET_KEY", None
        )
        if not secret:
            raise cls._auth_error("Shared secret key is not configured.")

        issuer = getattr(settings, "AUTH_SERVICE_ISSUER", None)
        decode_kwargs = {
            "key": secret,
            "algorithms": ["HS256"],
            "audience": audience,
        }
        if issuer:
            decode_kwargs["issuer"] = issuer
        try:
            return jwt.decode(
                token,
                **decode_kwargs,
            )
        except jwt.ExpiredSignatureError as exc:
            raise cls._auth_error("Token has expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise cls._auth_error(f"Invalid token: {exc}") from exc

    @classmethod
    def _decode_rs_token(cls, token: str, audience: str, algorithm: str, kid: str) -> dict:
        jwk = cls._get_jwk(kid)
        try:
            public_key = RSAAlgorithm.from_jwk(json.dumps(jwk))
        except Exception as exc:  # pragma: no cover
            raise cls._auth_error("Failed to construct verification key.") from exc

        issuer = getattr(settings, "AUTH_SERVICE_ISSUER", None)
        decode_kwargs = {
            "key": public_key,
            "algorithms": [algorithm],
            "audience": audience,
        }
        if issuer:
            decode_kwargs["issuer"] = issuer
        try:
            return jwt.decode(
                token,
                **decode_kwargs,
            )
        except jwt.ExpiredSignatureError as exc:
            raise cls._auth_error("Token has expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise cls._auth_error(f"Invalid token: {exc}") from exc

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
        audience = getattr(settings, "M2M_JWT_AUDIENCE", None)
        if not audience:
            return None

        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise self._auth_error(f"Invalid token header: {exc}") from exc

        algorithm = header.get("alg")

        if algorithm == "HS256":
            payload = self._decode_hs_token(token, audience)
        else:
            expected_alg = getattr(settings, "AUTH_SERVICE_JWT_ALGORITHM", "RS256")
            if algorithm != expected_alg:
                raise self._auth_error("Invalid token: unsupported algorithm.")
            kid = header.get("kid")
            payload = self._decode_rs_token(token, audience, algorithm, kid)

        client_id = payload.get("sub")
        if not client_id:
            raise self._auth_error("Invalid token: missing 'sub' (client_id) claim.")

        user = ServiceClient(client_id=client_id)
        return (user, None)
