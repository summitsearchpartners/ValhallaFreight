"""A shipment's package count always matches its quoted freight lines."""
from fastapi import HTTPException
from decimal import Decimal, InvalidOperation


def confirmed_package_count(units, submitted=None):
    if not units:
        raise HTTPException(422, "Add at least one freight line before booking.")
    total = 0
    for unit in units:
        try:
            value = Decimal(str(unit.get("quantity", 0)))
            if not value.is_finite() or value < 1 or value != value.to_integral_value():
                raise ValueError()
            total += int(value)
        except (ValueError, InvalidOperation, TypeError):
            raise HTTPException(422, "Every freight line requires a positive whole package quantity. Re-rate the quote to correct it.")
    if submitted is not None and submitted != total:
        raise HTTPException(422, f"Package count must match the freight lines ({total}). Refresh the quote before booking.")
    return total
