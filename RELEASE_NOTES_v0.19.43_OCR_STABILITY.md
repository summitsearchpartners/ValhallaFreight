# Valhalla TMS v0.19.43 — Safe Load OCR name clarity and database pool safety

- Keeps local RapidOCR ONNX inference; no driver-license images sent to third-party OCR providers.
- Reads neural OCR text rows with line-height-sensitive grouping to reduce merged name fields.
- Adds one enlarged targeted neural name-region read on landscape license images; conflicting name observations are left blank for review rather than guessed.
- Releases the read-only authorization database transaction before the license-preview endpoint starts potentially expensive image processing. This addresses one verified risk for SQLAlchemy connection pool exhaustion.
- Does not change shipment release decisions, database schema, customer records, or Safe Load photo retention.

**Note:** A screenshot of populated form fields cannot prove the true spelling printed on the ID. Verify with an actual license test image (redact personally identifying fields if sharing), and do not assume perfect OCR. Other database-session leaks may still require investigation.
