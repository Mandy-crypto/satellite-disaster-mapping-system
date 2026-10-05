"""Optional API key guard for operations that modify uploaded/project data."""

import hmac

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

_admin_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)


async def require_admin(api_key: str | None = Security(_admin_header)):
    """Require the configured admin key; unset locally for backward compatibility."""
    if settings.ADMIN_API_KEY and not hmac.compare_digest(api_key or "", settings.ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="A valid X-Admin-API-Key is required for this operation")
