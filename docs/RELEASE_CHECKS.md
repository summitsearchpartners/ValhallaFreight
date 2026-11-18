# v0.19.11 cropped front/back ID photo workflow

- **28 mobile tests passed**. Three new geometry cases validate portrait crop bounds, cover-preview offsets and clamped/invalid guide coordinates. Two new upload cases verify that ID back is a third File part and an old backend cannot silently discard it. Existing review, cancellation, ownership and multipart tests remain. Native crop execution is a physical-device acceptance check; geometry/bridge tests do not claim an Android camera was used.
- **31 focused backend checks passed** across the 24 existing photo/QA/custody tests and 7 new back-evidence cases. Actual PDF417 image decoding drives release despite unreadable front OCR; wrong/expired/incomplete/unreadable/conflicting back codes hold release. Tests verify encrypted third-photo storage, scoped retrieval, evidence flags, valid custody hashes, designated Muse access and backend capability reporting. The entire backend suite was not rerun; earlier full-suite results below are historical.
- Browser walkthrough passed: third ID-back image rendered from authenticated encrypted storage; existing front/VIN and extracted fields visible; rejection; broker evidence review/authorization; confirmation and Clear - For Transit on both portals via live update; mobile width and no runtime exceptions. Fictional fixtures only.
- Frontend and native TypeScript/builds passed. Android/iOS Hermes exports passed and were checked for v0.19.11 and front/back photo labels, and absence of the Google/native scanner/live-preview buttons. The active capture screen has no capture timers or barcode-scanner invocations. The timed automatic attempt was deliberately removed, not relabeled as reliable auto-capture.
- Cropping uses SDK58-compatible expo-image-manipulator against the measured guide and actual picture dimensions. Full raw ID frames are not uploaded; the accepted crop supplies the evidence URI. VIN photography remains manual. The existing armored vector mark remains unchanged.
- One additive back-evidence table/migration was added. Metadata upgrade applied twice preserved existing users/password hashes, company, quote and custody fixture values; PostgreSQL DDL compiled. Prior migrations, seed/schema-update code and Compose volume names are byte-identical to the supplied baseline.
- No live Docker/PostgreSQL startup or physical phone focus/orientation/crop/barcode-layout test was performed. This is source for local testing, not a signed store binary. See V0.19.11_SAFE_LOAD_ID_PHOTOS.md for update, manual-capture behavior and device acceptance steps. Existing PostgreSQL/document volumes must be retained.

Prior release checks follow.

# v0.19.10 single-photo review and native barcode sessions

- **23 mobile tests passed**: existing upload/decoder/policy checks plus 9 new photo-review/native-session regressions. They cover bounded automatic attempts after failed alignment, freezing a candidate before Accept, explicit-only adoption, Retake cleanup/rearming, failed-save preview retention, accepted-file ownership across parent unmount, cancellation/late captures, native launch resolving before its barcode event, duplicate-event suppression, cancellation cleanup and invalid-scan retry. Native services use deterministic bridges; physical camera execution is not claimed.
- **26 focused backend tests passed**: camera-frame decoding/readiness, barcode/photo QA, scope/revision restrictions, encrypted evidence, confirmations and rejection/release paths. Actual generated PDF417/Code128 images and local OCR continue to exercise real server readers. Backend functional code, requirements, all migrations and Compose are byte-identical to the uploaded v0.19.9 baseline; only backend application-version metadata changed. The full 137-test run listed below belongs to v0.19.9 and was not rerun for this mobile behavior change.
- Native TypeScript and frontend TypeScript/production build passed. Android/iOS Hermes bundles exported successfully from local dependencies. They contain App v0.19.10, Accept Photo, Retake, Use Scanned Data, native barcode handling and the armored mark. Existing frontend bundler warnings remain nonblocking.
- The repeating still-photo timer is removed. An ID opening/Retake permits one readiness candidate, then either review or a paused failure; subsequent attempts require user action. Barcode mode takes no photographs automatically. Native scanner result listeners remain until result/error/cancellation rather than disappearing when launch completes. Explicit Decode One Frame is still available as a single-frame fallback.
- The custom armored vector lock was rendered and visually inspected. Editable SVG and bundled XML match. react-native-svg 15.16.0 matches Expo SDK58's installed bundled-module map; no pre-existing mobile lock entries/dependencies were changed, only the new vector dependency and its transitive packages were added. No database, seeding, integration or volume changes occurred.
- No physical Android/iOS camera/native Google scanner test, live Docker/PostgreSQL startup, signed binary or app-store submission occurred here. Focus, native scanner availability, real card layouts and lighting require your device acceptance test. See V0.19.10_SAFE_LOAD_REVIEW.md.

Prior release checks follow.

# v0.19.9 camera scans, guided auto-capture and mobile UI

- Full backend suite: **137 passed**. Camera-specific focused run: **8 passed** (included in the full suite). Actual generated PDF417 and Code128 camera-frame images decode through the authenticated new endpoints. Tests cover extracted ID fields/DOB, live scan evidence reaching existing QA/release, canonical VIN/AIM/Code39 formats, no-code/stale/cross-company rejection, and real centered sharp versus blurred/off-center card readiness. Readiness/preview calls cannot create release receipts or bypass required evidence.
- Mobile **14 tests passed** (7 existing upload + 7 camera/policy checks): installed Expo multipart encoding with actual File-byte semantics, live preview completeness, canonical server VIN handling, actionable retry/stale status, temporary frame API paths/auth, two clear/stationary frames before auto-capture, motion/blur reset and supported picture resolution limits. Native File and camera access use test bridges; no physical Android callback is claimed.
- Native TypeScript passed. Android/iOS Hermes exports passed and both were inspected for App v0.19.9 and current scan/auto-capture/refresh/lock controls. Frontend TypeScript/production build passed with existing nonblocking bundler warnings. Desktop frontend behavior changed only in the version display.
- CameraView now explicitly enables autofocus and correct scan formats. Invalid live results do not latch/close the scanner; camera-frame decoding is a real alternate input path, not simulated scan success. Torch, zoom, in-camera status, manual capture and Cancel remain available. Temporary quality/scan frames are discarded rather than stored as shipment evidence. Document readiness uses headless OpenCV; matching/release still uses the existing independent QA and broker rules.
- The lock mark/login design, fixed top-right sign-out header, refresh spinner/pull refresh and successful refresh sequence/time/count are included in current native source/bundles. These are compile/bundle checks, not a claim of pixel-perfect physical-device rendering.
- Prior migrations, Compose volume configuration, seed/schema-update code and mobile/frontend pinned dependency trees are byte-identical apart from application version metadata. No schema/data reset was introduced. Backend requirements add opencv-python-headless; local installation/import and actual quality tests passed. Rebuild backend Docker image for this dependency and the new routes.
- No live Windows Docker/PostgreSQL container startup, physical Android/iOS focus/barcode/autocapture test, signed APK or app-store publication occurred in this environment. Real cameras, glare, motion, network speed and card layouts need local acceptance testing. Barcode/field matching is not facial/DMV authentication. See V0.19.9_SAFE_LOAD_CAMERA.md for update and test steps.

Prior release checks follow.

# v0.19.8 capture consolidation, barcode QA, progress and confirmations

- Full backend regression run: **119 passed**. After adding the new QA cases and sparse OCR refinement, the final focused photo/barcode run: **18 passed** (10 new QA/barcode tests plus 8 existing photo tests). These runs cover 129 distinct cases, not a single 129-test suite invocation.
- New checks cover PDF417 preview including DOB without persistence, tenant/revision restrictions, required photo evidence, scan-assisted extraction, wrong/expired/malformed identity/VIN rejection, conflicting photo/live barcode rejection, persistent/idempotent confirmation numbers, broker exception confirmations, earlier rejection hold preservation, exact server milestone sequence and sparse two-column real OCR. Existing tests continue to cover real barcode photographs, broker notifications, encrypted evidence, authorization and release/custody flow.
- Mobile **7 upload regression tests passed**, including actual installed Expo SDK58 multipart encoding of scanned metadata/newlines and both photo byte streams. Native TypeScript passed; Android/iOS Hermes exports passed and both were inspected for v0.19.8, the single Submit Photos control, scan/progress/green-clear UI. Source inspection confirms one ID capture button and one VIN capture button (the duplicate top card was removed). Physical camera gestures/scanning/dialogs are not claimed as automated tests.
- Frontend TypeScript/build passed. Browser workflow passed: manufacturer photo submission without checkbox, actual OCR wrong-VIN rejection, broker evidence/extraction view, broker authorization, confirmation number plus Clear - For Transit on both portals, warehouse live update without reload and phone-width layout. No page runtime errors. Initial stock Chromium could not launch under the sandbox; the supported bundled headless Chromium was used. Existing frontend bundler warnings are nonblocking.
- Labelled fictional PDF417 and Code128 test fixtures were generated and decoded byte-for-byte. No real identity documents or user screenshots were used as deliverables.
- Prior-version SQLite fixture upgraded twice with prior company/user/password hash/quote/custody values preserved. PostgreSQL receipt DDL compiled. Prior migrations, Compose, schema-update/seed code and pinned dependency trees are unchanged. The only new table is safe_load_release_receipts. Confirmation numbers are included in new custody snapshots; old releases are not backfilled.
- Progress percentages are actual completed workflow milestones, not facial identity confidence, time estimates or a simulated timer. Progress is transient and bounded in the current single-process API deployment. Release, evidence, receipt and custody decisions remain transactional and persistent.
- No live Docker/PostgreSQL startup, physical Android/iOS camera or store submission was performed here. Barcode/field checks do not authenticate a face, DMV record or VIN ownership. See V0.19.8_SAFE_LOAD_QA_BARCODE.md for update, privacy and local test instructions.

Prior release checks follow.

# v0.19.7 SDK58 camera upload hotfix

- Six mobile upload regression tests passed against the installed Expo SDK58 FormData patch/converter. The previous URI-only payload reproduces the exact reported Unsupported FormDataPart implementation error. New File-byte parts encode both JPEGs and required metadata, round-trip the actual test JPEGs without alteration, and retain actionable errors for transport/validation/invalid-response/missing-file/size failures. Native File access uses a bytes-compatible test bridge, not a physical camera.
- Seventeen focused backend Safe Load photo/automation checks passed. An additional wire test submitted the exact Expo-encoded test-image multipart body to FastAPI, exercised real local OCR/QA, reached Released/In Transit, and retrieved both stored images as broker: 18 backend/wire checks. The full backend suite was not rerun for this mobile-only behavioral change; prior release full-suite results below are historical.
- Frontend TypeScript/production build and native TypeScript passed. Android and iOS Hermes bundles exported successfully from fresh local pinned dependencies; both inspected for App v0.19.7 and the new upload handler error text/camera controls. Existing frontend nonblocking bundler warnings remain.
- Backend functional code, migration files and Compose config are byte-identical to the supplied v0.19.6 baseline; only backend application-version metadata changed. All original source/assets remain in the complete ZIP. No data/schema/volume/credential or SDK dependency upgrades were introduced.
- No physical Android/iOS camera, live Windows Docker/PostgreSQL or app-store build test occurred here. Verify App v0.19.7 after restarting Metro and scanning the new QR code. Retake both onsite photos. See V0.19.7_SAFE_LOAD_UPLOAD_FIX.md.

Prior release checks follow.

# v0.19.6 automatic onsite QA and shared broker callback

- Full backend regression run: **116 passed**. After adding unreadable-photo/profile permission cases and the final designated-Muse contact-snapshot refinement, the final **9 automation tests passed**. These runs cover **119 distinct cases**; this is not a claim of a single 119-test suite run.
- Actual local OCR/barcode tests cover no-checkbox automatic release, wrong ID/name/VIN rejection, rotated ID, valid renewed expiration/suffix formatting, changed license broker acknowledgement, no-contact hold with evidence retained, encrypted photo/extraction storage, broker-only full extraction, tenant isolation, shared profile override/clear, regular Broker read-only access, Super Admin context and designated Muse-booking access.
- Browser walkthrough passed: Broker Admin My Profile single Save and shared callback; manufacturer two-photo form with zero checkboxes; actual OCR wrong-VIN rejection; broker notification action; both saved onsite images rendered and extracted full fields displayed; broker authorization; warehouse live release without reload; custody JSON export; phone width; no page runtime errors. Browser testing used only fictional TEST DOCUMENT fixtures.
- Frontend TypeScript/build passed, with existing nonblocking bundler warnings. Native TypeScript passed. Android and iOS Hermes bundles exported from a fresh local SDK58 dependency installation and both were inspected for App v0.19.6 and the onsite ID/VIN camera controls. The local Expo SDK58 dependency compatibility map matched the pinned declared native packages; dependency trees remain unchanged except application version.
- Additive metadata creation applied twice over a prior-version SQLite fixture preserved prior company/user/password-hash/quotes/custody values; PostgreSQL DDL compiled. The new SQL migration is additive. Prior migration files, startup schema-update/seed code and Compose configuration are byte-identical to the supplied v0.19.5 ZIP. All 6 PowerShell scripts passed syntax parsing.
- No live Docker/PostgreSQL startup, physical Android/iOS camera/dialer test, DMV/biometric authentication or live freight test occurred in this environment. Bundles are JavaScript exports, not signed store binaries. See V0.19.6_SAFE_LOAD_AUTOMATIC_REVIEW.md for local acceptance and update steps. Existing local data volumes must be retained; this source ZIP contains no live database, secrets or identity documents.

Prior release verification follows.

# v0.19.5 onsite capture, broker release and custody

- Full backend regression run: 109 passed. Final focused photo/custody run: 14 passed, including the added native capture-event case. After the final public hash/export refinement, all 6 custody tests passed again. These runs cover 110 distinct cases; this is not a claim of a single 110-test run.
- Tests cover first-arrival auto-transit without hidden initial approval, persistent rejection holds, broker authorization/scoping, stale decisions, required photos, preserved failed results, actor/device metadata, retained dispatcher image versions, append-only snapshots and valid hash chains.
- Browser walkthrough passed pending-dispatcher photo-control visibility; actual local OCR wrong-VIN rejection; broker notification review/release action; live warehouse update without reloading; custody JSON download and mobile web width. No runtime exceptions. The exported custody chain was independently verified from its public JSON payloads.
- Frontend build and mobile TypeScript passed. Android/iOS Hermes bundles exported from fresh local dependencies, and both bundles were inspected for App v0.19.5 and the two onsite camera labels. Local SDK 58 dependency compatibility map matched the pinned installed packages. Online Expo dependency validation timed out through the environment proxy; offline/local validation was used.
- Additive schema creation applied twice over the prior-version fixture preserved company, user password hash and quote; PostgreSQL DDL compiled. PowerShell launcher syntax passed. Existing migrations and Compose volumes are preserved.
- Physical Android camera/dialer/popups and live Docker/PostgreSQL startup remain local acceptance checks. No real freight, real ID or external message was used. See V0.19.5_SAFE_LOAD_ONSITE_CUSTODY.md for installation, test and audit limits.

Prior release verification follows.

# v0.19.4 arrival photo verification

- Full backend regression run: 102 tests passed. Final photo-specific checks: 7 workflow tests passed after adding explicit visual-person mismatch reporting, plus the PDF417/Code128 photograph decoding test passed separately (104 distinct cases covered across these runs).
- Actual local OCR/barcode-reader pipeline exercised with fictional text images; no mocked OCR for release/rejection tests. Wrong license, wrong name, wrong VIN, unreadable content, prerequisites, encrypted evidence, authorization and automatic pickup release covered.
- Browser: normalized dispatcher image rendered; saved broker contact; actual OCR wrong-VIN rejection and broker reapproval; matching two-photo auto-release; scoped evidence images and mobile width; no browser runtime exceptions.
- Frontend and mobile TypeScript checks, Expo dependency check, Android/iOS Hermes exports passed. Existing non-blocking bundler warnings remain.
- Prior migration/volume configuration is preserved. Two additive tables are initialized on startup. Docker image now installs local Tesseract; pip includes the barcode reader. Physical Android camera/display, live Docker/PostgreSQL and real state-license layouts remain local acceptance tests.

See V0.19.4_SAFE_LOAD_PHOTOS.md for install, phone test and OCR limits. Earlier release history follows.

# v0.19.3 broker customer access

- Full backend regression run: 93 tests passed. After final scope/rating refinements and added cases, the 11 broker customer tests passed. These runs cover 96 distinct test cases; they are not a single 96-test full-suite run.
- New checks cover Super Admin-only management, independent manufacturer assignment, new customer creation, invalid broker targets, conflict prevention, child customer inheritance, direct-ID/quote scope, normal LTL rating and retained carrier hide controls, financial privacy, linked Safe Load release, and revocation without breaking the manufacturer's own release.
- Frontend TypeScript/Vite build passed. Final browser check passed assign/create/remove, broker account-popup shortcut, scope and revocation, and mobile width with no runtime exceptions.
- Additive schema creation applied twice over a previous-version fixture, preserving company, user password hash and quote. New PostgreSQL table DDL compiled. Existing migrations and Compose volumes remain unchanged.
- No live Docker/PostgreSQL, live freight or physical phone test was performed in this environment. The existing SDK 58 mobile source is unchanged.

Current usage is documented in V0.19.3_BROKER_CUSTOMERS.md. Prior release checks below describe earlier builds, not a new physical-device or live-carrier test.

# Safe Load v0.19.2 mobile compatibility update

See V0.19.2_SAFE_LOAD_SDK58.md for current mobile checks and LAN startup. Desktop/backend validation below belongs to v0.19.1 and was not rerun for this mobile-only change.

# v0.19.1 verification

- Full backend suite: 85 tests passed, including full-state normalization and invalid-state field errors.
- Frontend TypeScript and production build passed.
- Browser walkthrough: required-field feedback, server 422 field mapping/correction, saved-facility autofill, responsive entry, carrier bids/booking, Safe Load rejection/approval/release, route completion and PDF download passed without runtime exceptions.
- No schema or PostgreSQL/document volume changes. Existing v0.19.0 data and migrations are preserved.
- Live Google suggestions require the customer key and enabled APIs; no live Google lookup was performed. Local Docker/PostgreSQL and physical mobile/store validation remain local acceptance tasks.

## Prior v0.19.0 checks

# v0.19.0 verification

- The latest v0.18.5(2) upload was compared against v0.18.5(1): file contents are identical. This release preserves that source baseline and extends it.
- Backend full suite: 78 tests passed. The final Truckload/Safe Load rerun passed 14 tests, including the additional multi-pickup rejection test. Existing quote classes, booking/BOL, Muse approval/booking, account/role/company restrictions, branding/preferences, pricing privacy and finance tests remain covered.
- New tests cover truckload quote/bid/book idempotence, locked booked quotes and invalidated edited bids, full driver assignment/approval/scan/release, mismatched ID/VIN/expiry, missing visual confirmation, no status-alias/manual-tracking bypass, scoped photo access/encryption, stale revisions/invitation rotation/verification expiry, normal LTL automatic holds, Muse-only scoped cross-company access and rejection alerts, cancellation, and refusing additional warehouse pickups without a separate Safe Load decision.
- Frontend TypeScript check and Vite production build passed. Existing non-blocking bundler warnings remain.
- Browser walkthrough passed: quote entry, carrier bid selection, truckload booking, event-stream assignment update, encrypted-photo retrieval, manufacturer permissions, wrong-VIN rejection, broker vouching, successful re-scan/release, sequential route execution, rate-confirmation PDF download and mobile web width. No browser runtime exceptions were observed.
- Native mobile TypeScript and Expo dependency compatibility checks passed. Android and iOS production JavaScript/Hermes bundles exported successfully with camera/SecureStore/dev-client modules. These are bundle checks, not signed native binaries or physical camera validation.
- Additive schema upgrade was applied twice to a v0.18.5 SQLite fixture; prior company, user/password hash and quote values remained unchanged. PostgreSQL DDL compiled successfully. Existing schema-update/seeding code and the credit application PDF were preserved.
- Compose YAML and PowerShell script syntax passed. PostgreSQL configuration, volume definitions and document mounts remain unchanged. Frontend API URL and backend CORS settings now accept .env overrides while preserving localhost defaults. Demo transfer scripts include the mobile source and correct the earlier invalid compose-run flag.
- Docker/PostgreSQL container startup, physical phone/tablet cameras, live carrier movement and App Store/Google Play submission could not be exercised in this environment. No production shipment, store listing or outbound carrier message was created. See the feature guide and mobile README for acceptance and deployment steps.
