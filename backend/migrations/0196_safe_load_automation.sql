-- Additive only. Existing accounts, loads, evidence and custody snapshots remain intact.
CREATE TABLE IF NOT EXISTS safe_load_call_profiles (
 scope_key VARCHAR(80) PRIMARY KEY,
 customer_id INTEGER UNIQUE REFERENCES customers(id),
 contact_name VARCHAR(180) NOT NULL,
 phone VARCHAR(60) NOT NULL,
 updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS safe_load_photo_extractions (
 attempt_id INTEGER PRIMARY KEY REFERENCES safe_load_photo_attempts(id),
 customer_id INTEGER NOT NULL REFERENCES customers(id),
 summary JSON NOT NULL,
 encrypted_data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_safe_load_photo_extractions_customer_id ON safe_load_photo_extractions(customer_id);
