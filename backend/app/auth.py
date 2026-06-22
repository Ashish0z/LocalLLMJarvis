from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings


def require_api_key(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    if not settings.jarvis_api_key:
        return

    supplied_key = request.headers.get("X-API-Key")
    if supplied_key == settings.jarvis_api_key:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key",
    )

