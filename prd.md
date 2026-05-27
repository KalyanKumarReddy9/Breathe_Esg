BREATHE ESG
Emissions Data Ingestion Platform
PRODUCT REQUIREMENTS DOCUMENT

Document Type	Product Requirements Document (PRD)
Product	ESG Emissions Ingestion & Review Platform
Version	1.0 — Initial Release
Author	Tech Intern Assignment
Date	May 25, 2026
Status	DRAFT — Under Review
Audience	Engineering, Product, Auditors
Priority	HIGH — 4-Day Build Sprint




1. Executive Summary
Breathe ESG provides carbon accounting infrastructure for enterprise clients. The core challenge is not computing carbon emissions — it is ingesting data from heterogeneous, messy, real-world sources across client organizations. SAP exports, utility portal CSVs, and corporate travel APIs each come in different shapes, with different gaps, and require normalization before analysis.

This document specifies requirements for an Emissions Data Ingestion & Review Platform — a Django REST + React application that ingests data from three source types, normalizes it to a unified schema, and surfaces a review dashboard where analysts can inspect, flag, and approve records before they are locked for audit.

Scope 1 — Fuel & Procurement (SAP)	Scope 2 — Electricity (Utility Portals)	Scope 3 — Business Travel (Concur/Navan)


2. Problem Statement
Enterprise clients generate emissions data across dozens of internal systems. A single onboarding engagement may require pulling:
•Fuel and procurement records from SAP ERP (IDoc flat files, OData, BAPI, or direct DB extracts)
•Electricity consumption from utility portals as CSV exports, PDF bills, or scrapped portal data
•Business travel itineraries from platforms like Concur, Navan, or TripActions — with incomplete distance data

Without a normalized ingestion layer, analysts spend the majority of onboarding time on manual data wrangling rather than analysis. This platform eliminates that burden.

2.1 Pain Points Addressed
Pain Point	Platform Resolution
Inconsistent units (kWh, MWh, GJ, liters, gallons)	Automated unit normalization to standard SI units at ingestion
SAP German column headers and plant codes	Configurable column mapping + lookup table per client tenant
Utility billing periods ≠ calendar months	Period-aware normalization with proration logic
Missing flight distances (airport codes only)	IATA airport code lookup + great-circle distance calculation
No audit trail on edits	Immutable source-of-truth log + edit tracking with analyst attribution
No review step before auditor export	Analyst approval workflow with row-level sign-off

3. Objectives & Success Metrics
3.1 Primary Objectives
•Ingest real-world emissions data from SAP, utility portals, and travel platforms without manual transformation
•Normalize all ingested data to a unified schema with Scope 1/2/3 classification
•Surface a review dashboard enabling analysts to inspect, flag, and approve records
•Produce an immutable, auditor-ready export of approved records with full provenance
•Support multi-tenant architecture from day one

3.2 Success Metrics
Metric	Target	Priority
Ingestion parse success rate	>= 95% of valid files	P0
Unit normalization accuracy	100% (tested against known values)	P0
Analyst review cycle time	< 30 min per client dataset	P1
Audit export completeness	Zero unapproved rows in export	P0
Multi-tenant data isolation	Zero cross-tenant data leakage	P0
Failed row visibility	100% of parse failures surfaced in UI	P1

4. Scope
4.1 In Scope
•Django REST API backend with PostgreSQL
•React frontend analyst dashboard
•Three ingestion pipelines: SAP flat file, Utility CSV, Travel API/CSV
•Unit normalization engine (energy, volume, distance, mass)
•Scope 1/2/3 classification logic
•Analyst review workflow with row-level approval and flagging
•Audit trail on all edits and approvals
•Multi-tenant client isolation
•Deployed, publicly accessible instance

4.2 Explicitly Out of Scope (v1)
•Real-time API integrations with live SAP, utility, or travel systems
•Automated emission factor computation (inputs only, not outputs)
•Role-based access control beyond analyst/admin
•PDF bill parsing (utility CSV only in v1)
•Mobile-responsive design

5. Data Sources & Ingestion Design
5.1 Source 1 — SAP Fuel & Procurement (Scope 1)
Real-World Format Research
SAP exports data in multiple formats depending on client configuration: IDocs (Intermediate Documents) for system-to-system transfer, OData services via SAP Gateway, BAPI function calls, or flat file extracts from transaction ME2M (purchase orders) and MB51 (material documents). For this prototype, we handle SAP flat file exports (.txt / .csv) from transaction MB51, which exports material movements including fuel purchases.

Format Selection: SAP MB51 Flat File Export
Justification: MB51 flat files are the most common analyst-accessible export mechanism at mid-enterprise clients without dedicated SAP middleware. They require no API credentials or BAPI access.

Expected challenges and handling:
•Column headers may appear in German (e.g., 'Werk' = Plant, 'Menge' = Quantity, 'Basismengeneinheit' = Base Unit) — handled via configurable column alias mapping per tenant
•Date formats: DD.MM.YYYY (European SAP default) — normalized to ISO 8601 at parse time
•Units: L, KG, GAL, M3 — mapped to standard SI units via lookup table
•Plant codes (e.g., 'PL01', '1000') — stored raw with optional description lookup table
•Material numbers (e.g., '1001234') — mapped to emission categories via material group lookup

Sample Data Columns
SAP Column	Alias (EN)	Example Value	Normalized Field
Buchungsdatum	Posting Date	15.03.2024	date (ISO)
Werk	Plant	PL01	facility_code
Material	Material No.	1001234	material_id
Menge	Quantity	500.00	quantity (float)
Basismengeneinheit	Unit	L	unit → liters
Bewegungsart	Movement Type	101	movement_type
Lieferant	Vendor	V-00123	vendor_id
Einkaufsorg.	Purch. Org.	1000	purchase_org

5.2 Source 2 — Utility Electricity Data (Scope 2)
Real-World Format Research
Facilities teams typically access electricity data through three channels: (a) utility web portal CSV exports (most common for US commercial accounts), (b) Green Button data standard (XML/JSON — available from some utilities), or (c) manual PDF bill extraction. We select utility portal CSV export as the ingestion mode.

Justification: Portal CSV exports are available from all major US utilities (PG&E, ComEd, Duke, etc.) without API credentials or utility data agreements. PDF parsing adds significant complexity for v1 scope.

Key complexity areas:
•Billing periods do not align with calendar months — a bill may span Jan 18 to Feb 17
•Units vary: kWh, MWh, therms (for gas on same bill), kVAR for reactive power
•Tariff codes embedded in exports (e.g., 'TOU-GS-3-E') affecting emission factors
•Multiple meters per facility on a single export
•Demand charges vs. consumption charges — only consumption maps to emissions

Sample Data Columns
Column	Example	Unit Handling	Normalized Field
Account Number	0023456789-01	—	meter_account_id
Service Address	123 Industrial Blvd	—	facility_address
Bill Start Date	01/18/2024	→ ISO 8601	period_start
Bill End Date	02/17/2024	→ ISO 8601	period_end
kWh Usage	48,320	kWh → MWh	consumption_kwh
Tariff Code	TOU-GS-3-E	Stored raw	tariff_code
Meter ID	MTR-00234	—	meter_id
Demand (kW)	312.4	Excluded from emissions	demand_kw (info only)

5.3 Source 3 — Corporate Travel (Scope 3)
Real-World Format Research
Platforms like Concur Travel & Expense, Navan (formerly TripActions), and Egencia expose travel data via REST APIs with OAuth 2.0 and as CSV exports from expense reports. Concur's Travel Itinerary API returns structured JSON with segment-level detail (air, hotel, car, rail). Navan exports include trip segments with booking metadata.

Ingestion mode: CSV export from travel platform (Concur-compatible format). Justification: Direct API integration requires client OAuth credentials and approval — not feasible at prototype stage. CSV export from expense reports is the universal fallback available to any travel platform admin.

Key complexity areas:
•Air segments: origin/destination as IATA codes only — distance must be computed via great-circle calculation
•Hotel nights: property address available but emission factors require per-night room-count logic
•Ground transport: car rental vs. rideshare vs. personal vehicle each have different emission factors
•Category mixing: a single expense report may contain all three segment types
•Currency and amount fields present but not used for emissions (distance/duration is what matters)

Segment Type Handling
Segment Type	Distance Source	Emission Basis
Flight (Air)	IATA origin+dest → great-circle km	kg CO2e per passenger-km
Hotel	Nights × room count	kg CO2e per room-night
Car Rental	Trip duration estimate (fallback: 100km/day)	kg CO2e per km (by car class)
Rail	Station pair lookup or stated distance	kg CO2e per passenger-km

6. Data Model
6.1 Core Design Principles
•Multi-tenancy: every table carries a client_id foreign key; no cross-tenant queries permitted
•Source-of-truth tracking: every normalized row links to its raw ingestion record
•Audit trail: all edits captured as append-only log entries with analyst attribution
•Unit normalization: all quantities stored in SI base units (kWh, kg, km) regardless of input unit
•Scope classification: Scope 1 / 2 / 3 assigned at parse time, overridable by analyst

6.2 Entity Relationship Summary
Entity	Key Fields	Purpose
Client	id, name, country, timezone	Tenant root — all data scoped here
IngestionBatch	id, client_id, source_type, file_name, uploaded_at, status	Tracks each upload/pull event
RawRecord	id, batch_id, raw_payload (JSON), parse_status, error_message	Immutable copy of each parsed row
NormalizedRecord	id, raw_record_id, client_id, scope, category, quantity_value, quantity_unit_si, period_start, period_end, facility_code, source_system, created_at	Unified normalized row ready for review
ReviewDecision	id, record_id, analyst_id, decision (approved/flagged/rejected), note, decided_at	Analyst sign-off record
AuditLog	id, record_id, analyst_id, field_changed, old_value, new_value, changed_at	Immutable edit history
UnitLookup	code, si_unit, multiplier	Unit conversion registry
FacilityLookup	client_id, plant_code, description, country	SAP plant code → human label

6.3 Scope Classification Logic
Scope	Source	Category	Classification Rule
Scope 1	SAP	Fuel Combustion	movement_type IN (101, 261) AND material_group = 'FUEL'
Scope 2	Utility	Purchased Electricity	source_type = UTILITY AND commodity = ELECTRICITY
Scope 3	Travel	Business Travel — Air	segment_type = FLIGHT
Scope 3	Travel	Business Travel — Hotel	segment_type = HOTEL
Scope 3	Travel	Business Travel — Ground	segment_type IN (CAR, RAIL)

7. Functional Requirements
7.1 Ingestion
•FR-ING-01: System SHALL accept file uploads (CSV, TXT) for SAP and utility sources
•FR-ING-02: System SHALL parse SAP flat files with configurable column alias mapping per tenant
•FR-ING-03: System SHALL normalize date formats (DD.MM.YYYY, MM/DD/YYYY, YYYY-MM-DD) to ISO 8601
•FR-ING-04: System SHALL convert all quantity values to SI base units using the UnitLookup table
•FR-ING-05: System SHALL store the original raw payload for every ingested row, immutably
•FR-ING-06: System SHALL tag every ingested row with source_system, batch_id, and ingested_at timestamp
•FR-ING-07: System SHALL assign Scope 1/2/3 classification at parse time using classification rules
•FR-ING-08: Rows that fail parsing SHALL be stored in RawRecord with parse_status=FAILED and a descriptive error_message
•FR-ING-09: System SHALL compute great-circle distances from IATA airport code pairs for air travel segments

7.2 Review Dashboard
•FR-DASH-01: Dashboard SHALL display all NormalizedRecords grouped by IngestionBatch
•FR-DASH-02: Dashboard SHALL surface failed rows separately with error details
•FR-DASH-03: Dashboard SHALL flag records with anomalies (e.g., quantity > 3 std deviations from batch mean)
•FR-DASH-04: Analyst SHALL be able to approve, flag, or reject individual rows
•FR-DASH-05: Analyst SHALL be able to edit the quantity_value and scope fields with reason note
•FR-DASH-06: All edits SHALL be recorded in AuditLog with old/new values and analyst identity
•FR-DASH-07: Dashboard SHALL show batch-level summary: total rows, approved, flagged, failed
•FR-DASH-08: Dashboard SHALL prevent export until all rows have a ReviewDecision

7.3 Audit Export
•FR-EXP-01: System SHALL produce a CSV export of all approved NormalizedRecords for a batch
•FR-EXP-02: Export SHALL include: record_id, client_id, scope, category, quantity_value, quantity_unit_si, period_start, period_end, facility_code, source_system, approved_by, approved_at
•FR-EXP-03: Export SHALL be locked — no further edits permitted after export
•FR-EXP-04: Export SHALL include a manifest row count for auditor verification

8. Non-Functional Requirements
Category	Requirement
Multi-tenancy	All data queries MUST be scoped to a single client_id. No ORM query without client_id filter.
Data Immutability	RawRecord table is append-only. No UPDATE or DELETE permitted on raw records.
Security	API endpoints require authentication. Tenant isolation enforced at the ORM layer, not just UI.
Performance	Batch upload of up to 10,000 rows SHALL complete ingestion in < 30 seconds.
Deployment	Application MUST be deployed and publicly accessible. Local-only is not acceptable.
Traceability	Every NormalizedRecord MUST link to its RawRecord and IngestionBatch.
Frontend Colors	UI palette restricted to: White (#FFFFFF), Green (#1A7A3A), Red (#C0392B), Black (#111111). Minimal visual effects.

9. Analyst UX Requirements
The dashboard must be usable by a non-engineer sustainability analyst without training. Design constraints:
•No jargon without tooltip explanation (e.g., 'Scope 1' must show 'Direct emissions from owned sources' on hover)
•Color coding: green rows = approved, red rows = failed/rejected, white rows = pending
•Suspicious rows (statistical outliers) flagged with a red warning icon
•Batch summary card at top of each ingestion showing: total, approved %, failed count
•One-click approve for clean rows; flagging requires a mandatory text note
•Export button locked and grayed out until 100% of rows have decisions — tooltip explains why
•Upload interface accepts drag-and-drop; shows per-row parse results in real time

Screen Inventory
Screen	Purpose
/	Client & batch selector dashboard
/batches/:id	Ingestion batch review — all rows, filters, approve/flag/reject actions
/batches/:id/failures	Failed row explorer with parse error detail
/upload	File upload wizard for all three source types
/export/:id	Audit export preview and download

10. Deliverables & Submission
#	Deliverable	Description
1	Working App (Deployed)	Django REST + React, live URL required. Render / Railway / Fly.io
2	MODEL.md	Data model rationale: multi-tenancy, Scope classification, source-of-truth, unit norm, audit trail
3	DECISIONS.md	Every resolved ambiguity: format choices, subset handled, what was asked of PM
4	TRADEOFFS.md	3 things deliberately not built and why
5	SOURCES.md	Per-source: real-world format researched, sample data rationale, what breaks in production

Submission
•Reply to assignment email with: GitHub repo link, deployed app URL, login credentials
•Share GitHub repo (private OK) with: saurav@breatheesg.com, rahul@breatheesg.com, shivang@breatheesg.com
•Deadline: 4 days from receipt

11. Grading Criteria
Weight	Criterion	What to Demonstrate
35%	Data Model Quality	Sharp schema, real tradeoffs explained, defensible in code review
25%	Decision Defense (Post-submission)	You understand why every choice was made — not 'AI suggested it'
20%	Source Realism	Research visible in data shapes, column names, unit handling, edge cases
10%	Analyst UX	A non-engineer can operate the dashboard without help
10%	What You Didn't Build	Deliberate, justified scope cuts — not omissions

12. Open Questions for PM
•Which SAP export transaction is accessible at the client — MB51, ME2M, or a custom report?
•Do client utility accounts already have portal CSV export enabled, or will data be provided manually?
•Is Concur or Navan the primary travel platform? Do we have read API credentials or CSV-only?
•What emission factors should be used — IPCC AR6, EPA eGRID, DEFRA 2024? Per client or global config?
•Should the platform support multiple currencies for travel expense records (even if not used for emissions)?
•Is there a required audit export format (e.g., GHG Protocol template, CDP format) or is CSV sufficient?
•Multi-tenancy: will the prototype need to demonstrate client isolation with two separate test clients?

13. Recommended Tech Stack
Layer	Technology	Justification
Backend	Django 5 + Django REST Framework	Assignment requirement; ORM-level tenant isolation
Database	PostgreSQL 16	JSONB for raw payload storage; row-level security support
Frontend	React 18 + Vite	Assignment requirement; fast dev iteration
Styling	Plain CSS / CSS Modules	No Tailwind — enforce color palette (#FFF/#1A7A3A/#C0392B/#111)
Deployment	Railway or Render	Free tier, Postgres included, supports Django + React
File Upload	Django multipart + pandas	CSV/TXT parsing with dtype inference
Distance Calc	geopy (great-circle)	Airport code → lat/lon → Haversine distance