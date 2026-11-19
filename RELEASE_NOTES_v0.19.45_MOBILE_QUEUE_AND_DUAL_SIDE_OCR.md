# Valhalla TMS v0.19.45 — Safe Load queue and dual-side OCR

- Expo Go Safe Load shipment queue has three segmented views immediately below Refresh Shipments: Pending, Rejected, Released. Each shows its own count and only matching loads. Cancelled shipments are excluded.
- Rejected loads are no longer mixed into the pending list; released loads have their own view. Shipment detail and saved evidence flows remain unchanged.
- Dispatcher carrier submission waits for both front and back license images before starting automatic extraction; a front-photo replacement resets the back photo, and rotating the front re-reads only when the back is available.
- Upload and release security validation remains server-side; no verification bypasses were added.
- Requires rebuilding/restarting the Expo app for the mobile UI change. Frontend deployment is required for the carrier form change.
