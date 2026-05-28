"""
Unit normalizer — converts source units to SI base units using the UnitLookup table.
Falls back to a hardcoded default table if DB entries don't exist.
"""
import math

from emissions.models import UnitLookup

# Default unit conversions (code → (si_unit, multiplier))
DEFAULT_UNITS = {
    # Energy
    'KWH': ('kWh', 1.0),
    'MWH': ('kWh', 1000.0),
    'GWH': ('kWh', 1_000_000.0),
    'GJ': ('kWh', 277.778),
    'MMBTU': ('kWh', 293.071),
    'THERMS': ('kWh', 29.3071),
    'THERM': ('kWh', 29.3071),
    # Volume
    'L': ('L', 1.0),
    'LITERS': ('L', 1.0),
    'LITRES': ('L', 1.0),
    'GAL': ('L', 3.78541),
    'GALLON': ('L', 3.78541),
    'GALLONS': ('L', 3.78541),
    'M3': ('L', 1000.0),
    'BBL': ('L', 158.987),
    # Mass
    'KG': ('kg', 1.0),
    'T': ('kg', 1000.0),
    'TONNE': ('kg', 1000.0),
    'TONNES': ('kg', 1000.0),
    'TON': ('kg', 907.185),
    'LB': ('kg', 0.453592),
    'LBS': ('kg', 0.453592),
    # Distance
    'KM': ('km', 1.0),
    'MI': ('km', 1.60934),
    'MILE': ('km', 1.60934),
    'MILES': ('km', 1.60934),
    'NM': ('km', 1.852),
}


def get_conversion(unit_code):
    """
    Look up unit conversion. Try DB first, fall back to defaults.
    Returns (si_unit, multiplier) or None if unknown.
    """
    code_upper = str(unit_code).strip().upper()

    if code_upper in ('', 'NAN', 'NONE', 'NULL'):
        return None

    # Try DB lookup
    try:
        lookup = UnitLookup.objects.get(code__iexact=code_upper)
        return (lookup.si_unit, lookup.multiplier)
    except UnitLookup.DoesNotExist:
        pass

    # Fall back to defaults
    if code_upper in DEFAULT_UNITS:
        return DEFAULT_UNITS[code_upper]

    return None


def normalize_quantity(value, unit_code):
    """
    Convert a quantity to its SI base unit.
    Returns (normalized_value, si_unit, success, error_msg).
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        return (None, None, False, f"Cannot convert value '{value}' to number")

    if not math.isfinite(value):
        return (None, None, False, f"Cannot convert value '{value}' to number")

    conversion = get_conversion(unit_code)
    if conversion is None:
        return (value, unit_code, False, f"Unknown unit: '{unit_code}'")

    si_unit, multiplier = conversion
    normalized = round(value * multiplier, 6)
    return (normalized, si_unit, True, '')


def parse_date(date_str):
    """
    Parse dates in multiple formats:
    - DD.MM.YYYY (SAP German default)
    - MM/DD/YYYY (US utility)
    - YYYY-MM-DD (ISO 8601)
    Returns (date_obj, success, error_msg).
    """
    from datetime import date, datetime

    if isinstance(date_str, datetime):
        return (date_str.date(), True, '')

    if isinstance(date_str, date):
        return (date_str, True, '')

    if date_str is None:
        return (None, False, "Invalid date: ''")

    if not isinstance(date_str, str):
        date_str = str(date_str)

    date_str = date_str.strip()
    if not date_str or date_str.lower() in ('nan', 'none', 'null'):
        return (None, False, "Invalid date: ''")

    formats = [
        ('%d.%m.%Y', 'DD.MM.YYYY'),
        ('%m/%d/%Y', 'MM/DD/YYYY'),
        ('%Y-%m-%d', 'YYYY-MM-DD'),
        ('%d/%m/%Y', 'DD/MM/YYYY'),
        ('%Y/%m/%d', 'YYYY/MM/DD'),
        ('%m-%d-%Y', 'MM-DD-YYYY'),
        ('%d-%m-%Y', 'DD-MM-YYYY'),
        ('%Y.%m.%d', 'YYYY.MM.DD'),
        ('%Y-%m-%d %H:%M:%S', 'YYYY-MM-DD HH:MM:SS'),
    ]

    for fmt, _label in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return (dt.date(), True, '')
        except ValueError:
            continue

    return (None, False, f"Cannot parse date: '{date_str}'")
