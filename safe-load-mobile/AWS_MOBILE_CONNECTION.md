# Safe Load AWS Mobile Connection — v0.19.18

This package contains the full Valhalla Freight v0.19.17 TMS source plus a Safe Load mobile connection update (v0.19.18). No production backend or database migration is required for this connection-only change. **Do not deploy the entire ZIP to AWS just to test the phone.**

## First test (Windows PC + phone)

1. Unzip the full package into your local Valhalla Freight development folder, preserving your `.env` and local data. The changed files are confined to `safe-load-mobile/`.
2. On your Windows PC, open PowerShell and run:

   ```powershell
   Set-Location C:\GitHub\ValhallaFreight\safe-load-mobile
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-SafeLoad-AWS.ps1
   ```

3. The script runs `npm ci`, TypeScript checks and mobile tests, then starts Expo Go using a tunnel. Scan its QR code using a compatible Expo Go installation. If tunnel startup requests an additional Expo package, follow the prompt; it is required only on your PC. Alternatively run `-Connection lan` while your phone and PC are on the same network.
4. The mobile app's default TMS server is `https://valhallatms.com` (enter this **without** `/api/v1`). Existing saved server settings may override the default; correct the server field on the login screen if necessary.
5. Sign in using a **test** warehouse-capable account. Open a test shipment, capture front/back ID and VIN, submit, and confirm the result appears in the live TMS. This touches **production data**; use only test shipments and do not release real freight while validating.

## Important limits

- This is an Expo Go **development test**, not a signed app or production mobile distribution.
- Expo/Metro runs on your Windows PC, while the app's HTTPS requests go to AWS. The PC must remain running during Expo Go testing. The final standalone app does not need Metro.
- The AWS API routes, user roles, encryption, photo persistence, reverse proxy and server-side release checks must be validated end-to-end. Do not assume a successful login proves the complete Safe Load workflow.
- Safe Load documents contain sensitive driver information. Use role-restricted accounts, secure storage, HTTPS, audit logs and proper retention controls before operational use.
- For standalone apps, configure Expo EAS signing, build an Android APK/internal distribution and an iOS TestFlight build, then validate device permissions and release decisions. Do not publish until these checks pass.
