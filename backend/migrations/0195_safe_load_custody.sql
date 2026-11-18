-- Additive only. No changes to prior evidence, driver assignments or shipment data.
CREATE TABLE IF NOT EXISTS safe_load_custody_snapshots (
 id SERIAL PRIMARY KEY,
 shipment_id INTEGER NOT NULL REFERENCES shipments(id),
 customer_id INTEGER NOT NULL REFERENCES customers(id),
 revision INTEGER NOT NULL,
 action VARCHAR(60) NOT NULL,
 phase VARCHAR(40) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 payload JSON NOT NULL,
 previous_digest VARCHAR(64) NOT NULL,
 digest VARCHAR(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_safe_load_custody_snapshots_shipment_id ON safe_load_custody_snapshots(shipment_id);
CREATE INDEX IF NOT EXISTS ix_safe_load_custody_snapshots_customer_id ON safe_load_custody_snapshots(customer_id);
