def format_us_phone(value: str | None) -> str | None:
    if not value:
        return value
    digits = ''.join(ch for ch in value if ch.isdigit())
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return value.strip()
