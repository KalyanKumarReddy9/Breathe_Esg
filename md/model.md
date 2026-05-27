# Data Model

## Core Entities (Implemented)
- **Client**
	- `id`, `name`, `country`, `timezone`, `created_at`
- **IngestionBatch**
	- `client_id`, `source_type`, `file_name`, `uploaded_at`, `status`, `total_rows`, `parsed_rows`, `failed_rows`, `is_exported`
- **RawRecord**
	- `batch_id`, `raw_payload` (JSON), `parse_status`, `error_message`, `created_at`
- **NormalizedRecord**
	- `raw_record_id`, `client_id`, `batch_id`
	- `scope`, `category`, `quantity_value`, `quantity_unit_si`, `original_value`, `original_unit`
	- `period_start`, `period_end`, `facility_code`, `source_system`, `review_status`, `created_at`, `updated_at`
- **ReviewDecision**
	- `record_id`, `analyst_id`, `decision`, `note`, `decided_at`
- **AuditLog**
	- `record_id`, `analyst_id`, `field_changed`, `old_value`, `new_value`, `changed_at`
- **UnitLookup**
	- `code`, `si_unit`, `multiplier`, `description`
- **FacilityLookup**
	- `client_id`, `plant_code`, `description`, `country`

## Relationships
- `Client` 1 → many `IngestionBatch`, `NormalizedRecord`, `FacilityLookup`
- `IngestionBatch` 1 → many `RawRecord`, `NormalizedRecord`
- `RawRecord` 1 → 1 `NormalizedRecord`
- `NormalizedRecord` 1 → many `ReviewDecision`, `AuditLog`

## Normalization (Implemented)
- Unit conversion to SI via `UnitLookup` or default conversion table.
- Column alias mapping per source (SAP/Utility/Travel).
- Date parsing for common formats.
- Travel distance calculation from IATA codes for air segments.
