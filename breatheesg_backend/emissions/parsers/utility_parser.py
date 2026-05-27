"""
Utility CSV parser.
Handles billing period normalization, kWh/MWh conversion, meter data.
"""
import pandas as pd
from io import StringIO
from emissions.models import RawRecord, NormalizedRecord, ReviewDecision
from .normalizer import normalize_quantity, parse_date

# Column alias mapping for utility CSVs
UTILITY_ALIASES = {
    'account number': 'account_id',
    'account_number': 'account_id',
    'account': 'account_id',
    'meter account id': 'account_id',
    'service address': 'facility_address',
    'address': 'facility_address',
    'facility_address': 'facility_address',
    'bill start date': 'period_start',
    'start date': 'period_start',
    'period_start': 'period_start',
    'billing_start': 'period_start',
    'bill end date': 'period_end',
    'end date': 'period_end',
    'period_end': 'period_end',
    'billing_end': 'period_end',
    'kwh usage': 'consumption',
    'kwh': 'consumption',
    'usage': 'consumption',
    'consumption': 'consumption',
    'usage_kwh': 'consumption',
    'consumption_kwh': 'consumption',
    'tariff code': 'tariff_code',
    'tariff': 'tariff_code',
    'tariff_code': 'tariff_code',
    'meter id': 'meter_id',
    'meter': 'meter_id',
    'meter_id': 'meter_id',
    'demand (kw)': 'demand_kw',
    'demand_kw': 'demand_kw',
    'demand': 'demand_kw',
    'unit': 'unit',
    'units': 'unit',
}


def map_columns(df):
    """Map utility CSV headers to internal field names."""
    mapped = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        if col_lower in UTILITY_ALIASES:
            mapped[col] = UTILITY_ALIASES[col_lower]
        else:
            mapped[col] = col_lower.replace(' ', '_')
    return df.rename(columns=mapped)


def parse_utility_file(file_content, batch, client):
    """
    Parse utility CSV export.
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
        raw_payload = row.to_dict()
        row_errors = []

        # Parse period start
        start_str = raw_payload.get('period_start', '')
        start_date, start_ok, start_err = parse_date(str(start_str))
        if not start_ok:
            row_errors.append(f"Period start: {start_err}")

        # Parse period end
        end_str = raw_payload.get('period_end', '')
        end_date, end_ok, end_err = parse_date(str(end_str))
        if not end_ok:
            row_errors.append(f"Period end: {end_err}")

        # Parse consumption — default unit is kWh
        consumption_val = raw_payload.get('consumption', '')
        # Remove commas from numbers like "48,320"
        if isinstance(consumption_val, str):
            consumption_val = consumption_val.replace(',', '')
        unit = raw_payload.get('unit', 'kWh')
        if not unit or unit == 'nan':
            unit = 'kWh'
        norm_qty, si_unit, qty_ok, qty_err = normalize_quantity(consumption_val, str(unit))
        
        is_flagged = False
        flag_notes = []

        if not qty_ok and qty_err:
            # Instead of failing the parse, we import it as 0 and flag it
            is_flagged = True
            flag_notes.append(qty_err)
            norm_qty = 0.0
            if not si_unit:
                si_unit = 'UNKNOWN'

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
            facility = str(raw_payload.get('account_id', ''))
            if raw_payload.get('meter_id'):
                facility = f"{facility}/{raw_payload['meter_id']}"

            nr = NormalizedRecord.objects.create(
                raw_record=raw_record,
                client=client,
                batch=batch,
                scope='SCOPE_2',
                category='Purchased Electricity',
                quantity_value=norm_qty,
                quantity_unit_si=si_unit,
                original_value=None if not qty_ok else float(consumption_val),
                original_unit=str(unit),
                period_start=start_date,
                period_end=end_date,
                facility_code=facility,
                source_system='UTILITY',
                review_status='FLAGGED' if is_flagged else 'PENDING',
            )
            if is_flagged:
                ReviewDecision.objects.create(
                    record=nr,
                    decision='FLAGGED',
                    note='; '.join(flag_notes)
                )
            parsed_count += 1

    return (parsed_count, failed_count, errors)
