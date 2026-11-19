# v0.19.44 — Dispatcher PDF417 parity

- Dispatcher carrier license preview accepts an optional photo of the license back and uses the **same PDF417 barcode decoder** as onsite verification.
- When a valid, unambiguous ID-back barcode is present, its structured AAMVA identity fields take priority over front-image OCR. Conflicting barcode evidence fails closed.
- Without a back photo, the existing front OCR reader remains available as a fallback.
- Dispatcher preview formats the name in given-name / middle-name / surname order rather than surname-first.
- Carrier submission UI prompts for the back barcode and re-runs preview when selected; the back photo is only sent to the transient preview endpoint and is not persisted by the assignment endpoint.
- No change to onsite rejection, broker authorization, or freight-release safeguards.

Important: The dispatcher must verify the extracted name against the physical license and correct the assignment if necessary. Existing rejected attempts do not automatically become approved. This does not authenticate a license or its holder.
