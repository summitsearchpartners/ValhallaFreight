-- Additive only. Existing customer ownership, logins and freight remain intact.
CREATE TABLE IF NOT EXISTS broker_customer_assignments (
    customer_id INTEGER PRIMARY KEY REFERENCES customers(id),
    broker_company_id INTEGER NOT NULL REFERENCES customers(id),
    assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_broker_customer_assignments_broker_company_id
    ON broker_customer_assignments (broker_company_id);
