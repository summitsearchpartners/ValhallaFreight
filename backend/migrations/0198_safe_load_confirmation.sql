-- Additive only; existing releases are not backfilled with fabricated confirmations.
CREATE TABLE IF NOT EXISTS safe_load_release_receipts (
 shipment_id INTEGER PRIMARY KEY REFERENCES shipments(id),
 customer_id INTEGER NOT NULL REFERENCES customers(id),
 confirmation_number VARCHAR(50) UNIQUE NOT NULL,
 revision INTEGER NOT NULL,
 released_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 released_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 method VARCHAR(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_safe_load_release_receipts_customer_id ON safe_load_release_receipts(customer_id);
