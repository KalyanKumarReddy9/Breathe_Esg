# Key Decisions

- Use Django REST Framework for backend API.
- Use React (Create React App) for the analyst dashboard.
- Normalize all units to SI at ingestion; fall back to a default unit table if the DB is not seeded.
- Store raw and normalized data for auditability; raw rows are always persisted.
- Invalid quantities are ingested as flagged records (value 0) rather than dropped.
- Travel distances for flights are calculated from a local IATA subset for the prototype.
- Export locks batches to prevent post-export edits.
