"""
SAP MB51 flat file parser.
Handles German column headers, DD.MM.YYYY dates, and unit normalization.
"""
import pandas as pd
from io import StringIO
from emissions.models import RawRecord, NormalizedRecord, ReviewDecision
from .normalizer import normalize_quantity, parse_date

# Default column alias mapping: German SAP → internal field names
DEFAULT_SAP_ALIASES = {
    'buchungsdatum': 'posting_date',
    'posting date': 'posting_date',
    'posting_date': 'posting_date',
    'date': 'posting_date',
    'werk': 'plant',
    'plant': 'plant',
    'facility': 'plant',
    'material': 'material_id',
    'material no.': 'material_id',
    'material_id': 'material_id',
    'menge': 'quantity',
    'quantity': 'quantity',
    'amount': 'quantity',
    'basismengeneinheit': 'unit',
    'unit': 'unit',
    'base unit': 'unit',
    'bewegungsart': 'movement_type',
    'movement type': 'movement_type',
    'movement_type': 'movement_type',
    'mvt type': 'movement_type',
    'lieferant': 'vendor_id',
    'vendor': 'vendor_id',
    'vendor_id': 'vendor_id',
    'einkaufsorg.': 'purchase_org',
    'purch. org.': 'purchase_org',
    'purchase_org': 'purchase_org',
}


def map_columns(df):
    """Map SAP German column headers to internal field names."""
    mapped = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        if col_lower in DEFAULT_SAP_ALIASES:
            mapped[col] = DEFAULT_SAP_ALIASES[col_lower]
        else:
            mapped[col] = col_lower.replace(' ', '_')
    return df.rename(columns=mapped)


def classify_scope1(row):
    """
    Classify SAP record as Scope 1 Fuel Combustion.
    movement_type IN (101, 261) AND material looks like fuel.
    """
    return 'Fuel Combustion'


def parse_sap_file(file_content, batch, client):
    """
    Parse SAP MB51 flat file export.
    Returns (parsed_count, failed_count, errors).
    """
    parsed_count = 0
    failed_count = 0
    errors = []

    try:
        # Try tab-separated first, then comma
        try:
            df = pd.read_csv(StringIO(file_content), sep='\t', dtype=str)
            if len(df.columns) <= 1:
                df = pd.read_csv(StringIO(file_content), sep=',', dtype=str)
        except Exception:
            df = pd.read_csv(StringIO(file_content), sep=',', dtype=str)

        df = df.dropna(how='all')
        df = map_columns(df)

    except Exception as e:
        errors.append(f"Failed to parse file: {str(e)}")
        return (0, 0, errors)

    for idx, row in df.iterrows():
        raw_payload = row.to_dict()
        row_errors = []

        # Parse date
        date_val = raw_payload.get('posting_date', '')
        date_obj, date_ok, date_err = parse_date(str(date_val))
        if not date_ok:
            row_errors.append(date_err)

        # Parse quantity
        qty_val = raw_payload.get('quantity', '')
        unit_val = raw_payload.get('unit', 'L')
        norm_qty, si_unit, qty_ok, qty_err = normalize_quantity(qty_val, str(unit_val))
        
        is_flagged = False
        flag_notes = []

        if not qty_ok and qty_err:
            # Instead of failing the parse, we import it as 0 and flag it
            is_flagged = True
            flag_notes.append(qty_err)
            norm_qty = 0.0
            if not si_unit:
                si_unit = 'UNKNOWN'

        # Create RawRecord (always — even on failure)
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
            # Create NormalizedRecord
            nr = NormalizedRecord.objects.create(
                raw_record=raw_record,
                client=client,
                batch=batch,
                scope='SCOPE_1',
                category=classify_scope1(raw_payload),
                quantity_value=norm_qty,
                quantity_unit_si=si_unit,
                original_value=None if not qty_ok else float(qty_val),
                original_unit=str(unit_val),
                period_start=date_obj,
                facility_code=str(raw_payload.get('plant', '')),
                source_system='SAP',
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
