from __future__ import annotations
import httpx
from app.core.config import settings
from app.integrations.base.exceptions import CarrierCredentialsMissing, CarrierRemoteError

class DaytonClient:
    def __init__(self, *, base_url: str|None=None, username: str|None=None, password: str|None=None, account: str|None=None):
        self.base_url = (base_url or settings.dayton_api_base_url).rstrip('/')
        self.username = (username if username is not None else settings.dayton_api_username).strip()
        self.password = password if password is not None else settings.dayton_api_password
        self.account = (account if account is not None else settings.dayton_api_account).strip()

    @classmethod
    def from_db(cls, db):
        # Database-managed credentials are preferred; .env remains a backward-compatible fallback.
        from app.integrations.service import get_dayton_connection, credential_payload
        row=get_dayton_connection(db)
        from app.db.tenant_scope import integration_company
        company=integration_company(db)
        fallback_username='' if company is not None else settings.dayton_api_username
        fallback_password='' if company is not None else settings.dayton_api_password
        fallback_account='' if company is not None else settings.dayton_api_account
        cfg=row.settings or {}
        creds=credential_payload(db,row.id)
        return cls(
            base_url=cfg.get('base_url') or settings.dayton_api_base_url,
            username=creds.get('username') if creds.get('username') is not None else fallback_username,
            password=creds.get('password') if creds.get('password') is not None else fallback_password,
            account=cfg.get('account') or fallback_account,
        )

    @property
    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    def require_credentials(self):
        if not self.has_credentials:
            raise CarrierCredentialsMissing('Dayton Freight API credentials are not configured. Open Integration Hub → Dayton Freight → Credentials & Authentication.')

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
