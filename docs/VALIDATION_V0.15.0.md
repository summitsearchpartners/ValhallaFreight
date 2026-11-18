# v0.15.0 executed validation

## Passed

- **43 backend tests passed** in the final full run (98.12 seconds). This includes the original 34 account/manufacturer/support-window/profile/preferences and quote/shipment/BOL-number checks plus nine operational review tests.
- New tests cover null percentages with no qualifying shipments, measured delivery denominators, separate benchmarks, credential configuration versus verification, stale/failed live checks, credential-change invalidation, configuration-only reviews, company isolation, administrator-only retries, superseded run rejection, actionable overdue shipment links, CSV/XLSX preview and mapping, preservation of leading-zero ZIPs, invalid data rejection, non-annualized totals, and conditional hazmat requirements.
- Tracking tests verify repeated refreshes do not duplicate events, offset-bearing carrier timestamps become UTC, and a Valhalla Admin retry uses the manufacturer's original connection rather than the global broker connection.
- **Frontend TypeScript/Vite production build passed**. Existing module-directive, bundle-size and ineffective dynamic-import warnings remain non-blocking. Python application compilation also passed.
- **Headless Chromium checks with API fixtures passed** for freight inputs and multiple freight lines at 1366, 1100, 800 and 500px widths; rated options on narrow screens; booking confirmation at those widths; an uncovered persistent booking summary; conditional hazmat fields; meaningful Visibility/Analytics/Claims empty states; prospect preview/mapping before explicit analysis; Integration Hub definition/adapter/credential/verification labels; actual run/retry controls; a 7:37 PM evening greeting; the matching selected-timezone report end date; actionable Command Center links; and absence of JavaScript exceptions.
- Updated desktop/narrow layouts were visually inspected. A separate fixed-width booking constraint and stacking overlap found during visual QA were corrected and rechecked.
- Byte comparisons confirm the existing schema-update script, Compose configuration and seed implementation are unchanged. The new operation history table is additive through the existing startup metadata path. No database or document volume was deleted or reset.

## Local acceptance still required

Docker and PostgreSQL executables are not available in this build environment. Backend tests use isolated SQLite databases; browser workflow checks use API fixtures. Test Docker startup against your existing PostgreSQL volume, actual Google Places address selection, real carrier credentials/network calls, phone/browser MFA enrollment if used, real historical files including your XLS exports, and a representative final shipment/BOL document locally.

Browser fixture checks do not establish live vendor availability. The application intentionally requires a successful real check before showing current live health. Existing third-party font/resource requests may be blocked in this build environment; the checked layouts use browser fallbacks where needed.

## Reproduce

Frontend:

```sh
cd frontend
npm ci
npm run build
```

Backend (Python 3.12; from project root):

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt pytest httpx
PYTHONPATH=backend python -m pytest backend/tests -q
```

On PowerShell, activate `.venv\Scripts\Activate.ps1` and set `$env:PYTHONPATH="backend"` before running pytest.
