-- Additive evidence only. No changes to existing photos, shipments or releases.
CREATE TABLE IF NOT EXISTS safe_load_back_photos (
 attempt_id INTEGER PRIMARY KEY REFERENCES safe_load_photo_attempts(id),
 customer_id INTEGER NOT NULL REFERENCES customers(id),
 path VARCHAR(500) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_safe_load_back_photos_customer_id ON safe_load_back_photos(customer_id);
