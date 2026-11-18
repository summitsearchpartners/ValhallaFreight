# v0.19.15 checks

- Backend preview, retained evidence, back-photo and custody suites: **17 passed**, 123.93 seconds. Validates released front/back/VIN JSON previews against existing binary evidence bytes, actual JPEG decoding, correct metadata, no-store headers, manufacturer/broker/Super Admin access, other-manufacturer and anonymous denial, missing optional back and unknown image rejection, release unchanged and custody integrity. Existing Python/library deprecation warnings remain.
- Mobile fresh pinned install, TypeScript check and **38 tests passed**. New cases cover data-only image sources, all three loaded images, partial failure/retry, malformed or wrong-context responses, optional missing back, stale results after navigation/sign-out and no token in image sources. Existing capture/crop/upload checks remain.
- Frontend TypeScript and production build passed, with existing bundler dynamic-import notices.
- Browser workflow passed: manufacturer submission, rejection, broker evidence review and release, confirmation number, live warehouse update, narrow layout and no page runtime errors.
- New browser transport check used the actual mobile submittedEvidence.ts helper against the authenticated API after release/reopen. All three generated data-URI JPEGs decoded with positive dimensions, and image sources required no image HTTP/auth-header request.
- All original v0.19.14 source files retained; Compose and migration/schema-update files byte-identical. OCR code/dependencies, booking/release behavior and broker image endpoints unchanged.

No full-product regression rerun, live Docker/PostgreSQL deployment or physical Android/emulator renderer test was available here. Native production bundle export was not rerun. No real user images or live database/secrets are packaged.
