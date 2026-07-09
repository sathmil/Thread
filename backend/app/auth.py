import os

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal  # noqa: F401  (import ensures .env is loaded before os.getenv below)
from app.deps import get_db
from app.models import User

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")

_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        if not CLERK_JWKS_URL:
            raise HTTPException(
                status_code=500,
                detail="Auth is not configured (CLERK_JWKS_URL is unset) — set up Clerk to enable sign-in.",
            )
        _jwk_client = PyJWKClient(CLERK_JWKS_URL)
    return _jwk_client


def _decode_clerk_token(token: str) -> dict:
    client = _get_jwk_client()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False})


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db),
) -> User | None:
    """The authenticated User, or None if no credentials were sent.

    Public routes and public datasets must work with no token at all —
    only `_get_jwk_client` (called lazily, only once a Bearer token shows
    up) requires CLERK_JWKS_URL to be configured. Routes that require a
    signed-in user should depend on `require_user` instead of this.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    claims = _decode_clerk_token(token)
    clerk_user_id = claims["sub"]

    user = session.execute(select(User).where(User.clerk_user_id == clerk_user_id)).scalar_one_or_none()
    if user is None:
        user = User(clerk_user_id=clerk_user_id, email=claims.get("email"))
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required.")
    return user
