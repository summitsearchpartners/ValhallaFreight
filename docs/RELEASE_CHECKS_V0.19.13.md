# v0.19.13 validation

Validation performed against the supplied v0.19.12 project plus these changes:

- Six new VIN-reader checks passed: actual Tesseract reading of synthetic framed, full-background and rotated photographs; multiple VIN rejection; incomplete evidence rejection; conservative letter-spacing parsing without guessing characters or joining lines.
- Mobile TypeScript check and 29 unit tests passed, including a wide VIN guide mapping to a real image crop, Accept/Retake ownership, upload serialization and back-photo compatibility.
- Frontend TypeScript and production build passed; existing dynamic-import/chunk notices remain.
- Browser end-to-end passed: manufacturer photo submission and wrong-VIN hold; broker encrypted front/back/VIN evidence rendering and extraction review; authorized broker release; confirmation number; live warehouse status update; narrow viewport; no page runtime errors.
- Source inventory compared to uploaded v0.19.12: no original source file removed. Compose and migration/schema-update files unchanged byte-for-byte. No personal screenshots, live database, secrets, node_modules or generated bundles included in the deliverable.

- Focused backend QA progress, ID back-photo, automation, photo, custody, camera and numbered-reader regression suites: **53 passed** (254.97 seconds). Together with the six new VIN checks: **59 backend checks passed**. Existing library/Python deprecation warnings remain. These checks do not constitute every product test or a physical-phone acceptance run.

## Limits

The attached VIN screenshot is a small full-frame preview. It did not yield one unambiguous VIN locally; testing with the original high-resolution camera file is still needed. The reader does not substitute the expected VIN, guess characters or promise perfect extraction. Existing rejected arrivals remain held until broker authorization.

Native Android/iOS bundle export was blocked by automatic approval review because the Expo command initiated an outbound Expo request with an unverified payload. No new native production-bundle verification is claimed. Local mobile TypeScript and tests passed. No physical Android camera or live Docker/PostgreSQL deployment was available here.
