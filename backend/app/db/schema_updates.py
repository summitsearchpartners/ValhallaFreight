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
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
