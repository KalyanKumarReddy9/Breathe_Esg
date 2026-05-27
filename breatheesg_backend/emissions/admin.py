from django.contrib import admin
from .models import (
    Client, IngestionBatch, RawRecord, NormalizedRecord,
    ReviewDecision, AuditLog, UnitLookup, FacilityLookup,
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'country', 'timezone', 'created_at')
    search_fields = ('name', 'country')


@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'source_type', 'file_name', 'status', 'total_rows', 'parsed_rows', 'failed_rows', 'uploaded_at')
    list_filter = ('source_type', 'status', 'client')
    search_fields = ('file_name',)


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'batch', 'parse_status', 'error_message', 'created_at')
    list_filter = ('parse_status',)


@admin.register(NormalizedRecord)
class NormalizedRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'batch', 'scope', 'category', 'quantity_value', 'quantity_unit_si', 'review_status', 'period_start')
    list_filter = ('scope', 'review_status', 'source_system', 'client')
    search_fields = ('category', 'facility_code')


@admin.register(ReviewDecision)
class ReviewDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'record', 'analyst', 'decision', 'decided_at')
    list_filter = ('decision',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'record', 'analyst', 'field_changed', 'old_value', 'new_value', 'changed_at')
    list_filter = ('field_changed',)


@admin.register(UnitLookup)
class UnitLookupAdmin(admin.ModelAdmin):
    list_display = ('code', 'si_unit', 'multiplier', 'description')
    search_fields = ('code', 'si_unit')


@admin.register(FacilityLookup)
class FacilityLookupAdmin(admin.ModelAdmin):
    list_display = ('client', 'plant_code', 'description', 'country')
    list_filter = ('client',)
