"""Auth0 JWT verification as a FastAPI dependency."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import urlopen

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt

from config import settings

_bearer = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] | None = None


def _get_jwks() -> dict[str, Any]:
    """Fetch and cache the Auth0 JSON Web Key Set."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    with urlopen(url, timeout=10) as resp:
        _jwks_cache = json.loads(resp.read())
    return _jwks_cache


def _decode_token(token: str) -> dict:
    """Validate and decode a JWT using Auth0 JWKS."""
    jwks = _get_jwks()
    unverified = jwt.get_unverified_header(token)
    kid = unverified.get("kid")

    rsa_key: dict[str, str] = {}
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find matching signing key.",
        )

    algorithms = [a.strip() for a in settings.auth0_algorithms.split(",")]

    payload = jwt.decode(
        token,
        rsa_key,
        algorithms=algorithms,
        audience=settings.auth0_audience,
        issuer=f"https://{settings.auth0_domain}/",
    )
    return payload


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency — returns the decoded JWT payload or raises 401."""
    if not settings.auth0_domain or not settings.auth0_audience:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth0 is not configured on the server.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return _decode_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """Returns decoded payload if token present and valid, else None."""
    if credentials is None:
        return None
    if not settings.auth0_domain or not settings.auth0_audience:
        return None
    try:
        return _decode_token(credentials.credentials)
    except (JWTError, HTTPException):
        return None
