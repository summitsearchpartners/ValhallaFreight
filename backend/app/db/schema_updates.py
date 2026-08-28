from sqlalchemy import text
from sqlalchemy.engine import Engine


def apply_schema_updates(engine: Engine) -> None:
    """Small, idempotent upgrades for local/dev databases created before formal migrations.

    Keep changes isolated here until Alembic becomes the deployment migration authority.
    """
    statements = [
        "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS requested_pickup_at TIMESTAMP NULL",
        "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS requested_delivery_at TIMESTAMP NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS scheduled_pickup_at TIMESTAMP NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS requested_delivery_at TIMESTAMP NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS actual_pickup_at TIMESTAMP NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS po_number VARCHAR(80) NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS customer_reference VARCHAR(120) NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS package_count INTEGER NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS package_type VARCHAR(60) NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS commodity_description TEXT NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS nmfc_number VARCHAR(60) NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS hazmat_emergency_contact VARCHAR(180) NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS hazmat_emergency_phone VARCHAR(60) NULL",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS declared_value NUMERIC(12,2) NULL",
        "ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS margin_protection_threshold NUMERIC(12,2) DEFAULT 75.00",
        "ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS margin_protection_internal_notify BOOLEAN DEFAULT TRUE",
        "ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS margin_protection_customer_notify BOOLEAN DEFAULT TRUE",
        "ALTER TABLE carrier_bills ADD COLUMN IF NOT EXISTS threshold_at_audit NUMERIC(12,2) DEFAULT 75.00",
        "ALTER TABLE carrier_bills ADD COLUMN IF NOT EXISTS invoice_source VARCHAR(60) DEFAULT 'manual'",
        "ALTER TABLE carrier_bills ADD COLUMN IF NOT EXISTS matched_by VARCHAR(40) NULL",
        "ALTER TABLE carrier_bills ADD COLUMN IF NOT EXISTS exception_reason TEXT NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS legal_name VARCHAR(180) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS website VARCHAR(220) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS main_phone VARCHAR(50) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS dispatch_email VARCHAR(180) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS billing_email VARCHAR(180) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS address1 VARCHAR(220) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS city VARCHAR(100) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS state VARCHAR(30) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20) NULL",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS country VARCHAR(60) DEFAULT 'USA'",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS onboarding_status VARCHAR(40) DEFAULT 'approved'",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS safety_rating VARCHAR(40) DEFAULT 'satisfactory'",
        "ALTER TABLE carrier_profiles ADD COLUMN IF NOT EXISTS preferred_rank INTEGER NULL",
        "ALTER TABLE carrier_compliance ADD COLUMN IF NOT EXISTS document_name VARCHAR(255) NULL",
        "ALTER TABLE carrier_compliance ADD COLUMN IF NOT EXISTS document_content_type VARCHAR(120) NULL",
        "ALTER TABLE carrier_compliance ADD COLUMN IF NOT EXISTS document_size_bytes INTEGER NULL",
        "ALTER TABLE carrier_compliance ADD COLUMN IF NOT EXISTS document_uploaded_at TIMESTAMP NULL",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
