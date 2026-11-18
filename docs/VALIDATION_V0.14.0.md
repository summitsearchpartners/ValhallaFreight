# v0.14.0 validation

- **31 backend tests passed** in 66.74 seconds using isolated SQLite databases. These cover prior profile/settings/account/permission behavior; manufacturer-owned customer creation and isolation; explicit super-user login assignment; root and child customer multi-class quote/booking/BOL-number workflows; primary contacts; portal changes; admin-only launch; password failures; single-use ticket redemption; customer-bound grants; expiry and revocation; support-token rejection as an ordinary bearer token; encrypted authenticator enrollment, fresh-code checks and replay prevention; verification lockout; real-admin activity records without secrets.
- **Frontend production build passed** (`npm run build`). Existing bundle size, module directive and ineffective dynamic-import warnings remain non-blocking. Python application compilation passed.
- **Headless Chromium checks passed** with API fixtures: portal search and previous/next selection, separate popup launch, exactly one redemption, ticket removal from the URL, reload using the window-scoped grant, retained admin identity/token, authenticator setup modal and required-code state, blocked direct portal URL, responsive directory/support views, and no JavaScript exceptions. Desktop light/dark and narrow layouts were visually inspected. The customer portal's inherited internal-workspace margin was corrected and verified on desktop/mobile.
- Previous migration statements remain byte-for-byte equivalent in their original order after the two additive ownership statements. Compose configuration and seed behavior are unchanged. PostgreSQL and document volume names are preserved.

Docker and PostgreSQL executables are unavailable in this build environment. Actual Docker startup, upgrades of a live PostgreSQL volume, QR scanning with a real phone, browser pop-up permissions and live carrier integration requests remain local acceptance checks. No existing database or volume was reset.

## Reproduce

Frontend:

```sh
cd frontend
npm ci
npm run build
```

Backend (Python 3.12):

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt pytest httpx
PYTHONPATH=backend python -m pytest backend/tests -q
```

On Windows PowerShell use `.venv\Scripts\Activate.ps1` and set `$env:PYTHONPATH="backend"` before running pytest. Backend tests create isolated databases and use mocked carrier responses rather than contacting live freight services.
