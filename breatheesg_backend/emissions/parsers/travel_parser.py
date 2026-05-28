"""
Corporate travel CSV parser (Concur-compatible format).
Handles flight segments with IATA distance calc, hotel nights, ground transport.
"""
import pandas as pd
from io import StringIO
from emissions.models import RawRecord, NormalizedRecord
from .normalizer import parse_date
from .airports import get_distance_km

# Column alias mapping for travel CSVs
TRAVEL_ALIASES = {
    'trip id': 'trip_id',
    'trip_id': 'trip_id',
    'employee': 'employee_name',
    'employee_name': 'employee_name',
    'traveler': 'employee_name',
    'segment type': 'segment_type',
    'segment_type': 'segment_type',
    'type': 'segment_type',
    'travel type': 'segment_type',
    'origin': 'origin',
    'departure': 'origin',
    'from': 'origin',
    'origin_iata': 'origin',
    'destination': 'destination',
    'arrival': 'destination',
    'to': 'destination',
    'dest_iata': 'destination',
    'departure date': 'departure_date',
    'departure_date': 'departure_date',
    'date': 'departure_date',
    'travel_date': 'departure_date',
    'return date': 'return_date',
    'return_date': 'return_date',
    'end_date': 'return_date',
    'nights': 'nights',
    'hotel nights': 'nights',
    'hotel_nights': 'nights',
    'distance': 'distance',
    'distance_km': 'distance',
    'cabin class': 'cabin_class',
    'cabin_class': 'cabin_class',
    'class': 'cabin_class',
}

SEGMENT_CATEGORIES = {
    'FLIGHT': 'Business Travel — Air',
    'AIR': 'Business Travel — Air',
    'HOTEL': 'Business Travel — Hotel',
    'CAR': 'Business Travel — Ground',
    'CAR RENTAL': 'Business Travel — Ground',
    'RAIL': 'Business Travel — Ground',
    'TRAIN': 'Business Travel — Ground',
}


def map_columns(df):
    mapped = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        if col_lower in TRAVEL_ALIASES:
            mapped[col] = TRAVEL_ALIASES[col_lower]
        else:
            mapped[col] = col_lower.replace(' ', '_')
    return df.rename(columns=mapped)


def _clean_value(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    if pd.isna(value):
        return ''
    return str(value).strip()


def _sanitize_row(row):
    return {key: (None if pd.isna(value) else value) for key, value in row.to_dict().items()}


def _parse_float(value, default=None):
    cleaned = _clean_value(value)
    if not cleaned:
        return default
    try:
        parsed = float(cleaned)
    except (TypeError, ValueError):
        return default
    if pd.isna(parsed):
        return default
    return parsed


def parse_travel_file(file_content, batch, client):
    """
    Parse Concur-style travel CSV.
    Returns (parsed_count, failed_count, errors).
    """
    parsed_count = 0
    failed_count = 0
    errors = []

    try:
        df = pd.read_csv(StringIO(file_content), dtype=str)
        df = df.dropna(how='all')
        df = map_columns(df)
    except Exception as e:
        errors.append(f"Failed to parse file: {str(e)}")
        return (0, 0, errors)

    for idx, row in df.iterrows():
        raw_payload = _sanitize_row(row)
        row_errors = []

        # Parse departure date
        date_str = _clean_value(raw_payload.get('departure_date', ''))
        date_obj, date_ok, date_err = parse_date(date_str)
        if not date_ok:
            row_errors.append(f"Departure date: {date_err}")

        # Parse return date (optional)
        return_str = _clean_value(raw_payload.get('return_date', ''))
        return_date = None
        if return_str:
            return_date, return_ok, return_err = parse_date(return_str)
            if not return_ok:
                row_errors.append(f"Return date: {return_err}")

        # Determine segment type and calculate quantity
        segment_type = _clean_value(raw_payload.get('segment_type', '')).upper()
        category = SEGMENT_CATEGORIES.get(segment_type, f'Business Travel — {segment_type}')
        quantity = 0.0
        si_unit = 'km'

        if segment_type in ('FLIGHT', 'AIR'):
            # Calculate distance from IATA codes
            origin = _clean_value(raw_payload.get('origin', ''))
            dest = _clean_value(raw_payload.get('destination', ''))
            if origin and dest:
                dist, dist_ok, dist_err = get_distance_km(origin, dest)
                if dist_ok:
                    quantity = dist
                else:
                    row_errors.append(dist_err)
            else:
                row_errors.append("Missing origin or destination airport code")

        elif segment_type == 'HOTEL':
            # Hotel: quantity = number of nights
            nights = _parse_float(raw_payload.get('nights', ''), default=1.0)
            quantity = 1.0 if nights is None else nights
            if quantity <= 0:
                quantity = 1.0
            si_unit = 'nights'

        elif segment_type in ('CAR', 'CAR RENTAL'):
            # Car: use stated distance or fallback 100km/day
            dist_value = _parse_float(raw_payload.get('distance', ''), default=None)
            if dist_value is not None:
                quantity = dist_value
            else:
                # Fallback: 100km per day
                if date_obj and return_date:
                    days = max(1, (return_date - date_obj).days)
                    quantity = days * 100.0
                else:
                    quantity = 100.0

        elif segment_type in ('RAIL', 'TRAIN'):
            dist_value = _parse_float(raw_payload.get('distance', ''), default=None)
            if dist_value is not None:
                quantity = dist_value
            else:
                quantity = 0.0
                row_errors.append("No distance provided for rail segment")
        else:
            row_errors.append(f"Unknown segment type: '{segment_type}'")

        # Create RawRecord
        raw_record = RawRecord.objects.create(
            batch=batch,
            raw_payload=raw_payload,
            parse_status='FAILED' if row_errors else 'SUCCESS',
            error_message='; '.join(row_errors),
        )

        if row_errors:
            failed_count += 1
            errors.append(f"Row {idx + 1}: {'; '.join(row_errors)}")
        else:
            NormalizedRecord.objects.create(
                raw_record=raw_record,
                client=client,
                batch=batch,
                scope='SCOPE_3',
                category=category,
                quantity_value=quantity,
                quantity_unit_si=si_unit,
                original_value=quantity,
                original_unit=si_unit,
                period_start=date_obj,
                period_end=return_date,
                facility_code='',
                source_system='TRAVEL',
            )
            parsed_count += 1

    return (parsed_count, failed_count, errors)
