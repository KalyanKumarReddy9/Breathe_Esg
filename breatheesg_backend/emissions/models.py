from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    """Multi-tenant root — all data scoped to a client."""
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=64, default='UTC')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class IngestionBatch(models.Model):
    """Tracks each upload/pull event."""
    SOURCE_TYPE_CHOICES = [
        ('SAP', 'SAP Fuel & Procurement'),
        ('UTILITY', 'Utility Electricity'),
        ('TRAVEL', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=16, choices=SOURCE_TYPE_CHOICES)
    file_name = models.CharField(max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='PROCESSING')
    total_rows = models.IntegerField(default=0)
    parsed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    is_exported = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Batch {self.id} — {self.source_type} — {self.client.name}"


class RawRecord(models.Model):
    """Immutable copy of each parsed row. Append-only — no UPDATE or DELETE."""
    PARSE_STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='raw_records')
    raw_payload = models.JSONField(help_text='Original row data as received')
    parse_status = models.CharField(max_length=10, choices=PARSE_STATUS_CHOICES, default='SUCCESS')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Raw #{self.id} — {self.parse_status}"


class NormalizedRecord(models.Model):
    """Unified normalized row ready for analyst review."""
    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1 — Direct Emissions'),
        ('SCOPE_2', 'Scope 2 — Indirect (Electricity)'),
        ('SCOPE_3', 'Scope 3 — Other Indirect'),
    ]
    REVIEW_STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('FLAGGED', 'Flagged'),
        ('REJECTED', 'Rejected'),
    ]

    raw_record = models.OneToOneField(RawRecord, on_delete=models.CASCADE, related_name='normalized')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='normalized_records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='normalized_records')

    # Classification
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=128, help_text='e.g. Fuel Combustion, Purchased Electricity, Business Travel')

    # Normalized values — all stored in SI base units
    quantity_value = models.FloatField(help_text='Quantity in SI base unit')
    quantity_unit_si = models.CharField(max_length=16, help_text='SI unit: kWh, kg, km, L')
    original_value = models.FloatField(null=True, blank=True, help_text='Original quantity before conversion')
    original_unit = models.CharField(max_length=16, blank=True, default='')

    # Time period
    period_start = models.DateField()
    period_end = models.DateField(null=True, blank=True)

    # Source identifiers
    facility_code = models.CharField(max_length=64, blank=True, default='')
    source_system = models.CharField(max_length=32)

    # Review
    review_status = models.CharField(max_length=10, choices=REVIEW_STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.scope} | {self.category} | {self.quantity_value} {self.quantity_unit_si}"


class ReviewDecision(models.Model):
    """Analyst sign-off on a normalized record."""
    DECISION_CHOICES = [
        ('APPROVED', 'Approved'),
        ('FLAGGED', 'Flagged'),
        ('REJECTED', 'Rejected'),
    ]

    record = models.ForeignKey(NormalizedRecord, on_delete=models.CASCADE, related_name='decisions')
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    note = models.TextField(blank=True, default='')
    decided_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review #{self.id} — {self.decision} on Record #{self.record_id}"


class AuditLog(models.Model):
    """Immutable edit history. Append-only."""
    record = models.ForeignKey(NormalizedRecord, on_delete=models.CASCADE, related_name='audit_logs')
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    field_changed = models.CharField(max_length=64)
    old_value = models.TextField(blank=True, default='')
    new_value = models.TextField(blank=True, default='')
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"Audit: {self.field_changed} on Record #{self.record_id}"


class UnitLookup(models.Model):
    """Unit conversion registry. Maps source units to SI base units."""
    code = models.CharField(max_length=16, unique=True, help_text='Source unit code (e.g. GAL, MWh, therms)')
    si_unit = models.CharField(max_length=16, help_text='Target SI unit (e.g. L, kWh, kWh)')
    multiplier = models.FloatField(help_text='Multiply source value by this to get SI value')
    description = models.CharField(max_length=128, blank=True, default='')

    def __str__(self):
        return f"{self.code} → {self.si_unit} (×{self.multiplier})"


class FacilityLookup(models.Model):
    """Maps SAP plant codes to human-readable descriptions."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='facilities')
    plant_code = models.CharField(max_length=32)
    description = models.CharField(max_length=200, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        unique_together = ['client', 'plant_code']

    def __str__(self):
        return f"{self.plant_code} — {self.description}"
