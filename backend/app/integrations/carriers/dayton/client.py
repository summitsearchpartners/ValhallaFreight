from __future__ import annotations
import httpx
from app.core.config import settings
from app.integrations.base.exceptions import CarrierCredentialsMissing, CarrierRemoteError

class DaytonClient:
    def __init__(self):
        self.base_url = settings.dayton_api_base_url.rstrip('/')
        self.username = settings.dayton_api_username.strip()
        self.password = settings.dayton_api_password
        self.account = settings.dayton_api_account.strip()

    @property
    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    def require_credentials(self):
        if not self.has_credentials:
            raise CarrierCredentialsMissing('Dayton Freight API credentials are not configured. Add DAYTON_API_USERNAME and DAYTON_API_PASSWORD to .env.')

    async def request(self, method: str, path: str, *, params=None, json=None, require_auth: bool=True):
        if require_auth:
            self.require_credentials()
        auth = httpx.BasicAuth(self.username[:10], self.password) if self.has_credentials else None
        headers = {'Accept':'application/json'}
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=25.0, auth=auth, headers=headers) as client:
                response = await client.request(method, path, params=params, json=json)
        except httpx.HTTPError as exc:
            raise CarrierRemoteError(f'Dayton Freight request failed: {exc}') from exc
        payload = None
        try: payload = response.json()
        except Exception: payload = response.text
        if response.status_code >= 400:
            detail = payload.get('message') if isinstance(payload, dict) else str(payload or '')
            raise CarrierRemoteError(detail or f'Dayton Freight returned HTTP {response.status_code}', response.status_code, payload)
        return payload
