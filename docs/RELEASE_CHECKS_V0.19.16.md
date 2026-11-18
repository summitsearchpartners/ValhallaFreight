# v0.19.16 validation

- Seven new backend orientation checks passed: real local direction recognition at all four quarter turns, actual upright pixel dimensions/corner-marker placement, EXIF applied once, no forced orientation of unreadable blank data, and legacy dispatcher/onsite previews with unchanged encrypted files and valid custody.
- Existing photo, saved-preview, retained-evidence, back-photo and VIN-reader suites: 27 passed (127.16 seconds). These cover protected previews, stored evidence, release/rejection and the local VIN reader after sharing its initialized CPU model for document direction detection.
- After enabling the same upload normalization for back IDs, the orientation and back-photo suites were rerun together: 14 passed (66.77 seconds). These overlap the suites above; **34 distinct backend tests passed**, not 48.
- Fresh mobile pinned install, TypeScript and **41 mobile tests passed**, including transformed candidate ownership, Accept of the rotated URI, discarding late rotation after Cancel, and preferring a corrected saved preview only for the capture that was actually submitted.
- Frontend TypeScript and production build passed. Existing bundler dynamic-import/directive notices remain.
- Browser test passed: sideways dispatcher upload preview, real-pixel Rotate Right, submitted file, upright stored dispatcher image, view-only left/right, successful automatic QA/release/receipt, three saved onsite images, onsite view rotation, narrow layout, custody integrity and no page runtime errors. Final run retained full-size image links and view-only labelling.
- The supplied screenshot's private orientation check returned the correct 270-degree clockwise correction. No supplied screenshots or identity photographs are packaged.
- Existing source inventory retained; Compose, migrations/schema updates and dependency manifests remain unchanged apart from application version fields. No live database, secrets, uploads or runtime dependencies are included in the ZIP.

These are focused Safe Load checks, not every product test. No physical Android camera/manipulator run, live Docker/PostgreSQL deployment or native production export was performed. The existing Expo export approval block was not bypassed. Unclear layouts can require the explicit preview rotation controls; no guarantee of perfect orientation or identity authentication is made.
