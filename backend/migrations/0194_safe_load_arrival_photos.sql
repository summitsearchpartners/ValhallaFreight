CREATE TABLE IF NOT EXISTS safe_load_broker_contacts (
 shipment_id INTEGER PRIMARY KEY REFERENCES shipments(id),
 customer_id INTEGER NOT NULL REFERENCES customers(id),
 broker_name VARCHAR(180) NOT NULL,
 phone VARCHAR(60) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_safe_load_broker_contacts_customer_id ON safe_load_broker_contacts(customer_id);
CREATE TABLE IF NOT EXISTS safe_load_photo_attempts (
 id SERIAL PRIMARY KEY,
 shipment_id INTEGER NOT NULL REFERENCES shipments(id),
 customer_id INTEGER NOT NULL REFERENCES customers(id),
 revision INTEGER NOT NULL,
 operator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
 license_path TEXT NOT NULL,
 vin_path TEXT NOT NULL,
 status VARCHAR(40) NOT NULL,
 reasons JSON NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_safe_load_photo_attempts_shipment_id ON safe_load_photo_attempts(shipment_id);
CREATE INDEX IF NOT EXISTS ix_safe_load_photo_attempts_customer_id ON safe_load_photo_attempts(customer_id);
