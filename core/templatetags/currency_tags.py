from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def rands(value):
    """Formats a decimal or numeric value as South African Rands: R 1,234.56"""
    if value is None or value == '':
        return "R 0.00"
    try:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned.startswith('R '):
                cleaned = cleaned[2:].strip().replace(',', '')
            elif cleaned.startswith('R'):
                cleaned = cleaned[1:].strip().replace(',', '')
            val = float(cleaned)
        else:
            val = float(value)
        if val < 0:
            return f"-R {abs(val):,.2f}"
        return f"R {val:,.2f}"
    except (ValueError, TypeError, InvalidOperation):
        return f"R {value}"

@register.filter
def percentage(value):
    """Formats a decimal or numeric value as a percentage with 1 decimal place."""
    if value is None or value == '':
        return "0.0%"
    try:
        if isinstance(value, str):
            cleaned = value.strip().rstrip('%').strip()
            val = float(cleaned)
        else:
            val = float(value)
        return f"{val:.1f}%"
    except (ValueError, TypeError, InvalidOperation):
        return f"{value}%"
