# Validation for v0.19.14

Run against this update on 2026-11-14:

- **53 focused backend regression checks passed** (283.07 seconds): QA progress, back photos, automation, photo decisions, custody, camera, numbered ID reader. Includes renewal handling, scope isolation, encrypted evidence, automatic release and broker exception workflow. Existing Python/library deprecation warnings remain.
- **8 VIN-reader checks passed** (23.17 seconds): strip/full/rotated photographs, differing VINs held, incomplete text held, conservative letter spacing, actual local neural recognition of a synthetic dirty italic label, prediction with Python network connections blocked.
- **2 evidence/API checks passed** (18.22 seconds): all three stored photos are unchanged and accessible to the authorized manufacturer after rejection and broker-authorized release, denied to the other manufacturer, and linked to valid custody. A matching neural-read VIN flows through actual QA to confirmation and in-transit status with reader provenance saved.
- Total: **63 backend checks passed**, counting the three suites above once each.
- Fresh mobile pinned dependency installation, TypeScript check and **33 unit checks passed**. Includes retained local preview selection, authenticated restored evidence URLs, no token in URLs, assignment/load/login isolation, absent optional back photos, crop geometry, upload bytes and capture ownership.
- Frontend TypeScript and production build passed. Existing bundler dynamic-import notices remain.
- Browser end-to-end passed: manufacturer submission, wrong VIN rejection, broker front/back/VIN encrypted evidence and extracted field display, authorized broker release, confirmation receipt and live warehouse status update, narrow layout and no page runtime errors. Reader provenance display is checked in the final browser run.
- The supplied VIN screenshot was privately tested: the neural reader extracted all 17 characters exactly as independently transcribed. The reader was not given the expected VIN. No supplied image or identifying screenshot is packaged.
- Source inventory retains every original v0.19.13 file. Compose and migrations/schema updates are byte-identical. Requirements and backend Dockerfile intentionally change to install the CPU neural reader and its runtime libraries.

## Limits

No full-product regression rerun, physical Android camera test or live Docker/PostgreSQL deployment was available. Native production bundle export was not rerun; the previously reported outbound Expo approval block was not bypassed. Mobile validation here is TypeScript and local tests, not a claim of a signed APK/App Store build.

The real-photo result is a regression example, not a guarantee about all dirty, reflective or obscured VINs. Only readable matching evidence releases; prior rejections still require broker authorization. The reader compares text and does not authenticate a face, document, DMV record or truck ownership.

All neural inference is local, with ONNX telemetry disabled and models bundled by the pinned RapidOCR distribution. Building the Docker image downloads normal dependencies; photo QA does not call an external OCR API. CPU behavior was exercised on Linux/Python 3.12 with ONNX Runtime 1.32.0 and OpenCV 4.14.0.94.
