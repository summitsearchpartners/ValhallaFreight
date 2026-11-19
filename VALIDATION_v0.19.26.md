# Valhalla Freight v0.19.26 — Warehouse Security Regression Candidate

This package retains the v0.19.25 OCR and backend fixes and adds `backend/tests/test_warehouse_security.py` (37 warehouse-specific security cases).

## Run on Windows (PowerShell 5.1)

```powershell
Set-Location C:\GitHub\ValhallaFreight\backend
& "..\.venv-warehouse-test\Scripts\python.exe" -m pytest tests/test_warehouse_security.py -q --tb=short --disable-warnings
& "..\.venv-warehouse-test\Scripts\python.exe" -m pytest tests -q --tb=short --disable-warnings
```

Do NOT deploy unless both suites pass and any authorization gaps are resolved. The new security tests could reveal issues; do not modify test expectations to hide access failures.

## Validation in package creation environment

- Python syntax compilation: passed.
- Full pytest run: unavailable because the container lacks the project's `passlib` dependency.
- Windows Tesseract tests: must be rerun locally if backend code changes after this candidate.

## Scope

- Manufacturer/child-company Safe Load queue scoping.
- Cross-manufacturer Safe Load evidence and mutation endpoint denials.
- Warehouse broker/export action denials.
- Warehouse TMS/admin API restrictions.
- Company context override denial.
- Existing-token assignment and deactivation enforcement.
- Manufacturer admin cross-company warehouse management restrictions.

No production deployment or database changes are included.
