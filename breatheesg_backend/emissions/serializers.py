from rest_framework import serializers
from .models import (
    Client, IngestionBatch, RawRecord, NormalizedRecord,
    ReviewDecision, AuditLog, UnitLookup, FacilityLookup,
)


class ClientSerializer(serializers.ModelSerializer):
    batch_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'name', 'country', 'timezone', 'created_at', 'batch_count']

    def get_batch_count(self, obj):
        return obj.batches.count()


class IngestionBatchSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    approved_count = serializers.SerializerMethodField()
    flagged_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    rejected_count = serializers.SerializerMethodField()

    class Meta:
        model = IngestionBatch
        fields = [
            'id', 'client', 'client_name', 'source_type', 'file_name',
            'uploaded_at', 'status', 'total_rows', 'parsed_rows', 'failed_rows',
            'is_exported', 'approved_count', 'flagged_count', 'pending_count',
            'rejected_count',
        ]

    def get_approved_count(self, obj):
        return obj.normalized_records.filter(review_status='APPROVED').count()

    def get_flagged_count(self, obj):
        return obj.normalized_records.filter(review_status='FLAGGED').count()

    def get_pending_count(self, obj):
        return obj.normalized_records.filter(review_status='PENDING').count()

    def get_rejected_count(self, obj):
        return obj.normalized_records.filter(review_status='REJECTED').count()


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ['id', 'batch', 'raw_payload', 'parse_status', 'error_message', 'created_at']


class ReviewDecisionSerializer(serializers.ModelSerializer):
    analyst_name = serializers.CharField(source='analyst.username', read_only=True, default='')

    class Meta:
        model = ReviewDecision
        fields = ['id', 'record', 'analyst', 'analyst_name', 'decision', 'note', 'decided_at']


class AuditLogSerializer(serializers.ModelSerializer):
    analyst_name = serializers.CharField(source='analyst.username', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = ['id', 'record', 'analyst', 'analyst_name', 'field_changed', 'old_value', 'new_value', 'changed_at']


class NormalizedRecordSerializer(serializers.ModelSerializer):
    raw_payload = serializers.JSONField(source='raw_record.raw_payload', read_only=True)
    decisions = ReviewDecisionSerializer(many=True, read_only=True)
    batch_source_type = serializers.CharField(source='batch.source_type', read_only=True)

    class Meta:
        model = NormalizedRecord
        fields = [
            'id', 'raw_record', 'client', 'batch', 'batch_source_type',
            'scope', 'category', 'quantity_value', 'quantity_unit_si',
            'original_value', 'original_unit',
            'period_start', 'period_end', 'facility_code', 'source_system',
            'review_status', 'created_at', 'updated_at',
            'raw_payload', 'decisions',
        ]
        read_only_fields = ['raw_record', 'client', 'batch', 'created_at', 'updated_at']


class UnitLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitLookup
        fields = ['id', 'code', 'si_unit', 'multiplier', 'description']


class FacilityLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityLookup
        fields = ['id', 'client', 'plant_code', 'description', 'country']


class ReviewActionSerializer(serializers.Serializer):
    """Serializer for review actions (approve/flag/reject)."""
    decision = serializers.ChoiceField(choices=['APPROVED', 'FLAGGED', 'REJECTED'])
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        if data['decision'] == 'FLAGGED' and not data.get('note', '').strip():
            raise serializers.ValidationError({'note': 'A note is required when flagging a record.'})
        return data


class RecordEditSerializer(serializers.Serializer):
    """Serializer for editing a normalized record's quantity or scope."""
    quantity_value = serializers.FloatField(required=False)
    scope = serializers.ChoiceField(
        choices=['SCOPE_1', 'SCOPE_2', 'SCOPE_3'],
        required=False,
    )
    reason = serializers.CharField(required=True, help_text='Reason for the edit')
