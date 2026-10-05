import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_token(token: str | None) -> bool:
    if not settings.api_token:
        return True
    return secrets.compare_digest(token or "", settings.api_token)


async def require_token(authorization: str | None = Header(default=None)) -> None:
    if not settings.api_token:
        return
    prefix = "Bearer "
    token = None
    if authorization and authorization.startswith(prefix):
        token = authorization[len(prefix):]
    if not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
