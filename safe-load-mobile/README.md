# AWS mobile connection test — v0.19.18

See AWS_MOBILE_CONNECTION.md and Start-SafeLoad-AWS.ps1.

# Current release: v0.19.16

See ../docs/V0.19.16_SAFE_LOAD_UPRIGHT_PHOTOS.md. Adds conservative automatic ID orientation and Rotate Left/Right in upload/camera previews and saved web viewers. Update backend/frontend/mobile; verify App v0.19.16. Existing encrypted evidence remains unchanged.

# Previous release: v0.19.15

See ../docs/V0.19.15_SAFE_LOAD_SAVED_PHOTOS.md. Saved onsite photos now load through the authenticated API as data URIs, with loading/error/retry states. Update backend and mobile together; verify App v0.19.15. Existing stored photos do not need retaking.

# Previous release: v0.19.14

See ../docs/V0.19.14_SAFE_LOAD_RETAINED_PHOTOS_VIN.md. Onsite photos remain after QA/release and reload from protected evidence on reopening. New local neural VIN reader; rebuild the backend and restart Metro. Verify App v0.19.14.

# Previous release: v0.19.13

See ../docs/V0.19.13_SAFE_LOAD_VIN.md. VIN capture now saves only the outlined area; server VIN reading uses localized text and rotation. Rebuild Docker and restart Metro, then verify App v0.19.13.

# Previous release: v0.19.12

See ../docs/V0.19.12_SAFE_LOAD_READER.md for changes and update/test instructions. Photo order: front ID, back ID, truck VIN. Rebuild Docker and restart Metro; verify App v0.19.12.

# Previous mobile release: v0.19.11

See ../docs/V0.19.11_SAFE_LOAD_ID_PHOTOS.md. Front/back ID photos are cropped to the guide and reviewed before Accept. Take ID Back Photo replaces live scanning; barcode extraction happens during server QA. Capture is manual; no timed automatic shutter remains. Backend rebuild is required. Verify App v0.19.11.

# Previous mobile release: v0.19.10

See ../docs/V0.19.10_SAFE_LOAD_REVIEW.md. One candidate photo stops at Accept Photo/Retake; barcode scanning uses native result events with explicit single-frame fallback and no repeating photos. Includes a new armored vector lock mark. Restart Metro with updated dependencies and verify App v0.19.10.

# Previous mobile release: v0.19.9

See ../docs/V0.19.9_SAFE_LOAD_CAMERA.md. Autofocus and live/frame barcode paths, guided two-frame ID auto-capture with manual shutter/Cancel, visible refresh, fixed sign-out header and lock branding. Backend rebuild is required for new camera/readiness endpoints and OpenCV. Scan the NEW Metro QR and verify App v0.19.9.

# Previous mobile release: v0.19.8

See ../docs/V0.19.8_SAFE_LOAD_QA_BARCODE.md. One capture section, Submit Photos, live PDF417/VIN scan options, server-stage progress popup and persistent release confirmation. Update backend as well as this mobile folder; restart Metro, scan the NEW QR and verify App v0.19.8. Existing rejected shipments still require broker authorization.

# Previous mobile release: v0.19.7

Fixes the SDK58 camera photo multipart error. See ../docs/V0.19.7_SAFE_LOAD_UPLOAD_FIX.md. Stop old Metro, copy this mobile folder, run Start-SafeLoad.ps1 and scan the NEW QR code. Verify App v0.19.7 before retaking both photos. `npm test` runs the upload regression checks. The remaining workflow is unchanged from v0.19.6.

# Previous mobile release: v0.19.6

See ../docs/V0.19.6_SAFE_LOAD_AUTOMATIC_REVIEW.md for the current automatic two-photo workflow, shared broker contact, broker evidence review and release. Verify App v0.19.6 on your phone after restarting Metro. The warehouse has no visual-comparison checkbox. This update changes both backend and mobile source, so rebuild Docker and restart Metro.

# Safe Load mobile — iPhone/iPad and Android phones/tablets

This is the source project for native device testing and eventual store distribution, not a published app or signed binary. It uses Expo SDK 58 / React Native 0.88.1, Expo Camera (PDF417, Code 39/128 and QR), and Expo SecureStore. `package-lock.json` pins the tested dependency tree.

## Windows LAN test — v0.19.2

Keep Docker running and stop the old Metro window with Ctrl+C. Replace the existing safe-load-mobile source with this release (do not copy old node_modules). Use Expo Go SDK 58 on Android.

```powershell
Set-Location C:\GitHub\ValhallaFreight\safe-load-mobile
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-SafeLoad.ps1 -ComputerIP 192.168.1.195
```

The helper installs pinned dependencies and clears Metro caches. The existing local-network firewall rule for TCP 8081 still applies. Open Expo Go and scan the QR code or enter `exp://192.168.1.195:8081`. Sign into Safe Load with TMS server URL `http://192.168.1.195:8000` (no /api/v1 suffix) and the manufacturer's existing credentials. For v0.19.6, rebuild the backend/frontend first as described in the current release guide above. The host IP may change after reconnecting, so check it if this URL stops working.

This is the native Safe Load application running inside Expo Go for development. It is not yet a standalone signed APK or store release. Expo Go must match SDK 58; a later automatic Expo Go SDK update can require another upgrade or a dedicated development build.

## Development

Install Node 22.13+ or Node 24.3+ LTS and run in this directory:

```sh
npm ci
npm run check
npx expo start --go --lan --clear
```

Use a matching SDK-58 Expo Go installation where available, or a development build. Current App Store Expo Go versions may no longer support older SDKs; in that case use a development/preview binary. A camera/device is required to validate physical scans; simulator/emulator results are not sufficient for release acceptance.

For LAN development, phone and computer must be on the same network. Enter your computer's LAN URL (for example http://192.168.1.20:8000) in the mobile sign-in screen; `localhost` on a phone points to the phone. HTTP is accepted only in JavaScript development mode; preview/production requires an HTTPS TMS server. Only expose a local test backend to the devices you intend to test. No driver images or credentials are placed in the project.

## Native builds

With your own Expo account and project configured:

```sh
npx eas-cli login
npx eas-cli build:configure
npx eas-cli build --profile preview --platform android
npx eas-cli build --profile development --platform ios
```

The preview profile produces an internally installable Android APK. iOS development distribution requires an Apple developer team and registered devices/provisioning. The development profile includes `expo-dev-client` for device testing. Production uses App Store / Play signing through your accounts:

```sh
npx eas-cli build --profile production --platform all
npx eas-cli submit --platform ios
npx eas-cli submit --platform android
```

Run submission only after device testing, signing and store metadata are complete. Replace `com.valhallafreight.safeload` with an identifier you own; choose your Expo project/owner, store listings, support URL, privacy policy, screenshots and appropriate Apple privacy / Google Data Safety answers. Verify current Expo, Apple SDK and Play target requirements before store release; upgrade the SDK if the store or build image requires it. No store project IDs, Apple team IDs, credentials or paid accounts are fabricated here.

## Device behavior

- Sign in with an existing assigned company account. Super Admin remains responsible for account creation. Carrier dispatcher submission uses the secure browser invitation form; it does not grant a carrier access to the warehouse app.
- The active queue refreshes about every three seconds. There are no background push notifications yet.
- Photograph the arriving driver's physical ID and truck VIN with the rear camera. The server can decode a sharp PDF417 photo or read supported printed fields. Hold steady and scan the actual truck VIN label, not a copied label provided by someone else. Compare the person and physical ID to the submitted photo; the app does not perform face recognition or DMV authentication.
- The API authorizes every record, revision and release decision. Network errors block release. The photo-submit action records release only after the server confirms the current match; wait for CONFIRMED / RELEASED — IN TRANSIT. Rejected arrivals stay held until broker authorization or corrected-assignment verification. Rejected packets require broker resolution/approval and a new scan.
- Tokens use SecureStore. Raw scans are memory-only and cleared after verification or assignment changes. Photos are fetched from authenticated endpoints. Treat visible ID photos/screenshots and OS/device access as sensitive data.

## Store privacy and pilot acceptance

Before collecting real IDs, configure HTTPS, stable encryption keys, staff authorization, consent/notice, retention/deletion and backup controls. Document all collected data: driver names/license images/issuer/expiry, license matching hashes, VINs, company/shipment identifiers, employee account/access/audit information. There are no advertising or analytics SDKs in this project. Complete the store forms based on your actual deployed system and operations rather than copying generic privacy answers.

Test real PDF417 formats on each supported iPhone/iPad and Android device, camera-denied states, expired/unsupported cards, wrong IDs/VINs, replaced assignments, time expiry, app backgrounding, network loss and concurrent operators. Android/iOS JavaScript bundles and TypeScript compilation were checked in this release; no physical device test, signed native binary or store approval has been performed.
