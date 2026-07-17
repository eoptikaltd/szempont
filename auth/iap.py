"""R6 — IAP JWT verification (perimeter identity = the TERMINAL).

Google's guidance (research annex §4, verified 2026-07-17): the app must
validate `x-goog-iap-jwt-assertion` on every request; the plain
X-Goog-Authenticated-User-Email header is forgeable if IAP is ever
bypassed and MUST NOT be used for authorization. ES256, issuer
https://cloud.google.com/iap, keys from the Google JWK endpoint (the
google-auth library caches/rotates them).

Audience (R9a): direct-on-Cloud-Run format
  /projects/PROJECT_NUMBER/locations/REGION/services/SERVICE_NAME
— comes from the SZEMPONT_IAP_AUDIENCE env var at the W4-end infra step.
Unset audience = verification off (dev/tests); staging/prod set it.
"""

from __future__ import annotations

import os

_IAP_ISSUER = "https://cloud.google.com/iap"
_IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key-jwk"


class IapError(Exception):
    """Missing or invalid IAP assertion."""


def iap_audience() -> str | None:
    return os.environ.get("SZEMPONT_IAP_AUDIENCE") or None


def verify_iap_jwt(assertion: str | None,
                   audience: str) -> str:  # pragma: no cover — needs network
    """Return the verified terminal identity (email claim) or raise.

    Uses google-auth's id_token verifier with the IAP JWK endpoint —
    signature, expiry, issuer and audience are all checked. Exercised on
    staging (R9a session experiment); unit tests cover only the wiring
    (off by default), not Google's crypto.
    """
    if not assertion:
        raise IapError("missing x-goog-iap-jwt-assertion")
    from google.auth.transport import requests as ga_requests
    from google.oauth2 import id_token
    try:
        claims = id_token.verify_token(
            assertion, ga_requests.Request(), audience=audience,
            certs_url=_IAP_CERTS_URL)
    except Exception as e:
        raise IapError(f"IAP JWT verification failed: {e}") from e
    if claims.get("iss") != _IAP_ISSUER:
        raise IapError(f"unexpected issuer {claims.get('iss')!r}")
    return claims.get("email") or claims.get("sub") or "unknown-terminal"
