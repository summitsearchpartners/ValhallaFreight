-- v0.19.0 additive tables. Existing startup creates these with metadata.create_all.
-- No existing table or data is changed. Keep your PostgreSQL volumes and encryption keys.
BEGIN;

CREATE TABLE IF NOT EXISTS safe_load_cases (
	shipment_id INTEGER NOT NULL,
	customer_id INTEGER NOT NULL,
	status VARCHAR(40) NOT NULL,
	revision INTEGER NOT NULL,
	driver_name VARCHAR(180),
	license_digest VARCHAR(64),
	license_last4 VARCHAR(4),
	issuing_state VARCHAR(3),
	license_expires TIMESTAMP WITHOUT TIME ZONE,
	vin VARCHAR(17),
	photo_path TEXT,
	photo_type VARCHAR(60),
	invite_digest VARCHAR(64),
	invite_expires TIMESTAMP WITHOUT TIME ZONE,
	approved_by INTEGER,
	verified_by INTEGER,
	verified_until TIMESTAMP WITHOUT TIME ZONE,
	released_by INTEGER,
	released_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (shipment_id),
	FOREIGN KEY(shipment_id) REFERENCES shipments (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id),
	FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(verified_by) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(released_by) REFERENCES users (id) ON DELETE SET NULL
)

;
CREATE INDEX IF NOT EXISTS ix_safe_load_cases_customer_id ON safe_load_cases (customer_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_safe_load_cases_invite_digest ON safe_load_cases (invite_digest);
CREATE INDEX IF NOT EXISTS ix_safe_load_cases_status ON safe_load_cases (status);

CREATE TABLE IF NOT EXISTS safe_load_events (
	id SERIAL NOT NULL,
	shipment_id INTEGER NOT NULL,
	customer_id INTEGER NOT NULL,
	action VARCHAR(60) NOT NULL,
	actor VARCHAR(180) NOT NULL,
	detail TEXT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(shipment_id) REFERENCES shipments (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id)
)

;
CREATE INDEX IF NOT EXISTS ix_safe_load_events_shipment_id ON safe_load_events (shipment_id);
CREATE INDEX IF NOT EXISTS ix_safe_load_events_customer_id ON safe_load_events (customer_id);

CREATE TABLE IF NOT EXISTS truckload_orders (
	id SERIAL NOT NULL,
	customer_id INTEGER NOT NULL,
	shipment_id INTEGER,
	reference VARCHAR(120) NOT NULL,
	status VARCHAR(40) NOT NULL,
	equipment VARCHAR(40) NOT NULL,
	commodity VARCHAR(240) NOT NULL,
	weight_lbs INTEGER NOT NULL,
	packages INTEGER NOT NULL,
	temperature_min INTEGER,
	temperature_max INTEGER,
	stops JSON NOT NULL,
	customer_price NUMERIC(12, 2) NOT NULL,
	selected_bid_id INTEGER,
	notes TEXT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id),
	FOREIGN KEY(shipment_id) REFERENCES shipments (id)
)

;
CREATE UNIQUE INDEX IF NOT EXISTS ix_truckload_orders_shipment_id ON truckload_orders (shipment_id);
CREATE INDEX IF NOT EXISTS ix_truckload_orders_customer_id ON truckload_orders (customer_id);

CREATE TABLE IF NOT EXISTS truckload_bids (
	id SERIAL NOT NULL,
	order_id INTEGER NOT NULL,
	customer_id INTEGER NOT NULL,
	carrier_id INTEGER NOT NULL,
	carrier_cost NUMERIC(12, 2) NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	note TEXT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(order_id) REFERENCES truckload_orders (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id),
	FOREIGN KEY(carrier_id) REFERENCES carriers (id)
)

;
CREATE INDEX IF NOT EXISTS ix_truckload_bids_customer_id ON truckload_bids (customer_id);
CREATE INDEX IF NOT EXISTS ix_truckload_bids_order_id ON truckload_bids (order_id);
COMMIT;
