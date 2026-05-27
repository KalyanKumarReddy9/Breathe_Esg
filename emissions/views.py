import csv
import io
from datetime import datetime

from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import (
    Client, IngestionBatch, RawRecord, NormalizedRecord,
    ReviewDecision, AuditLog, UnitLookup, FacilityLookup,
)
from .serializers import (
    ClientSerializer, IngestionBatchSerializer, RawRecordSerializer,
    NormalizedRecordSerializer, ReviewDecisionSerializer, AuditLogSerializer,
    UnitLookupSerializer, FacilityLookupSerializer,
    ReviewActionSerializer, RecordEditSerializer,
)


class ClientViewSet(viewsets.ModelViewSet):
    """CRUD for clients (tenants)."""
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


class IngestionBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve ingestion batches with summary stats."""
    queryset = IngestionBatch.objects.select_related('client').all()
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        client_id = self.request.query_params.get('client')
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs


class NormalizedRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """List and filter normalized records."""
    queryset = NormalizedRecord.objects.select_related('raw_record', 'batch').prefetch_related('decisions').all()
    serializer_class = NormalizedRecordSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        client_id = self.request.query_params.get('client')
        if client_id:
            qs = qs.filter(client_id=client_id)
        review_status = self.request.query_params.get('status')
        if review_status:
            qs = qs.filter(review_status=review_status.upper())
        scope = self.request.query_params.get('scope')
        if scope:
            qs = qs.filter(scope=scope.upper())
        return qs


class RawRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """View raw records — especially failed ones."""
    queryset = RawRecord.objects.all()
    serializer_class = RawRecordSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(parse_status=status_filter.upper())
        return qs


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """View audit logs."""
    queryset = AuditLog.objects.select_related('analyst').all()
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        record_id = self.request.query_params.get('record')
        if record_id:
            qs = qs.filter(record_id=record_id)
        return qs


# --- File Upload Endpoint ---

@api_view(['POST'])
def upload_file(request):
    """
    Upload a CSV/TXT file for ingestion.
    Required params: client_id, source_type, file.
    """
    client_id = request.data.get('client_id')
    source_type = request.data.get('source_type', '').upper()
    uploaded_file = request.FILES.get('file')

    if not client_id:
        return Response({'error': 'client_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not uploaded_file:
        return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
    if source_type not in ('SAP', 'UTILITY', 'TRAVEL'):
        return Response({'error': 'source_type must be SAP, UTILITY, or TRAVEL'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return Response({'error': f'Client {client_id} not found'}, status=status.HTTP_404_NOT_FOUND)

    # Create batch
    batch = IngestionBatch.objects.create(
        client=client,
        source_type=source_type,
        file_name=uploaded_file.name,
    )

    # Read file content
    try:
        file_content = uploaded_file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_content = uploaded_file.read().decode('latin-1')

    # Parse based on source type
    try:
        if source_type == 'SAP':
            from .parsers.sap_parser import parse_sap_file
            parsed, failed, errors = parse_sap_file(file_content, batch, client)
        elif source_type == 'UTILITY':
            from .parsers.utility_parser import parse_utility_file
            parsed, failed, errors = parse_utility_file(file_content, batch, client)
        elif source_type == 'TRAVEL':
            from .parsers.travel_parser import parse_travel_file
            parsed, failed, errors = parse_travel_file(file_content, batch, client)

        batch.total_rows = parsed + failed
        batch.parsed_rows = parsed
        batch.failed_rows = failed
        batch.status = 'COMPLETED'
        batch.save()

        return Response({
            'batch_id': batch.id,
            'total_rows': parsed + failed,
            'parsed_rows': parsed,
            'failed_rows': failed,
            'errors': errors[:20],  # Return first 20 errors
            'status': 'COMPLETED',
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        batch.status = 'FAILED'
        batch.save()
        return Response({'error': str(e), 'batch_id': batch.id}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Review Endpoint ---

@api_view(['POST'])
def review_record(request, record_id):
    """
    Approve, flag, or reject a normalized record.
    """
    try:
        record = NormalizedRecord.objects.get(id=record_id)
    except NormalizedRecord.DoesNotExist:
        return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check if batch is already exported
    if record.batch.is_exported:
        return Response({'error': 'Cannot modify records in an exported batch'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ReviewActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    decision = serializer.validated_data['decision']
    note = serializer.validated_data.get('note', '')

    # Create review decision
    ReviewDecision.objects.create(
        record=record,
        analyst=request.user if request.user.is_authenticated else None,
        decision=decision,
        note=note,
    )

    # Update record status
    record.review_status = decision
    record.save()

    return Response({
        'record_id': record.id,
        'new_status': decision,
        'note': note,
    })


# --- Bulk Review Endpoint ---

@api_view(['POST'])
def bulk_review(request):
    """
    Approve/flag/reject multiple records at once.
    Body: { record_ids: [1,2,3], decision: "APPROVED", note: "" }
    """
    record_ids = request.data.get('record_ids', [])
    decision = request.data.get('decision', '').upper()
    note = request.data.get('note', '')

    if not record_ids:
        return Response({'error': 'record_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
    if decision not in ('APPROVED', 'FLAGGED', 'REJECTED'):
        return Response({'error': 'decision must be APPROVED, FLAGGED, or REJECTED'}, status=status.HTTP_400_BAD_REQUEST)
    if decision == 'FLAGGED' and not note.strip():
        return Response({'error': 'A note is required when flagging records'}, status=status.HTTP_400_BAD_REQUEST)

    records = NormalizedRecord.objects.filter(id__in=record_ids, batch__is_exported=False)
    updated = 0
    for record in records:
        ReviewDecision.objects.create(
            record=record,
            analyst=request.user if request.user.is_authenticated else None,
            decision=decision,
            note=note,
        )
        record.review_status = decision
        record.save()
        updated += 1

    return Response({'updated': updated, 'decision': decision})


# --- Edit Record Endpoint ---

@api_view(['PATCH'])
def edit_record(request, record_id):
    """
    Edit quantity_value or scope of a normalized record.
    Creates an audit log entry.
    """
    try:
        record = NormalizedRecord.objects.get(id=record_id)
    except NormalizedRecord.DoesNotExist:
        return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)

    if record.batch.is_exported:
        return Response({'error': 'Cannot edit records in an exported batch'}, status=status.HTTP_403_FORBIDDEN)

    serializer = RecordEditSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    reason = serializer.validated_data['reason']
    analyst = request.user if request.user.is_authenticated else None

    if 'quantity_value' in serializer.validated_data:
        old_val = str(record.quantity_value)
        new_val = serializer.validated_data['quantity_value']
        AuditLog.objects.create(
            record=record, analyst=analyst,
            field_changed='quantity_value',
            old_value=old_val, new_value=str(new_val),
        )
        record.quantity_value = new_val

    if 'scope' in serializer.validated_data:
        old_scope = record.scope
        new_scope = serializer.validated_data['scope']
        AuditLog.objects.create(
            record=record, analyst=analyst,
            field_changed='scope',
            old_value=old_scope, new_value=new_scope,
        )
        record.scope = new_scope

    record.save()
    return Response(NormalizedRecordSerializer(record).data)


# --- Export Endpoint ---

@api_view(['GET'])
def export_batch(request, batch_id):
    """
    Export approved records from a batch as CSV.
    Locks the batch after export (no further edits).
    """
    try:
        batch = IngestionBatch.objects.get(id=batch_id)
    except IngestionBatch.DoesNotExist:
        return Response({'error': 'Batch not found'}, status=status.HTTP_404_NOT_FOUND)

    records = NormalizedRecord.objects.filter(batch=batch)
    total = records.count()

    if total == 0:
        return Response({'error': 'No records in this batch'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if all records have been reviewed
    pending = records.filter(review_status='PENDING').count()
    if pending > 0:
        return Response({
            'error': f'{pending} records still pending review. All records must be reviewed before export.',
            'pending_count': pending,
        }, status=status.HTTP_400_BAD_REQUEST)

    # Only export approved records
    approved = records.filter(review_status='APPROVED')

    # Check if just a preview is requested
    preview = request.query_params.get('preview', 'false').lower() == 'true'
    if preview:
        serializer = NormalizedRecordSerializer(approved, many=True)
        return Response({
            'batch_id': batch.id,
            'total_records': total,
            'approved_records': approved.count(),
            'records': serializer.data,
            'is_exported': batch.is_exported,
        })

    # Generate CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="batch_{batch_id}_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    # Header row
    writer.writerow([
        'record_id', 'client_id', 'scope', 'category',
        'quantity_value', 'quantity_unit_si',
        'period_start', 'period_end', 'facility_code',
        'source_system', 'approved_at',
    ])

    # Data rows
    for rec in approved:
        latest_approval = rec.decisions.filter(decision='APPROVED').order_by('-decided_at').first()
        writer.writerow([
            rec.id, rec.client_id, rec.scope, rec.category,
            rec.quantity_value, rec.quantity_unit_si,
            rec.period_start, rec.period_end or '', rec.facility_code,
            rec.source_system,
            latest_approval.decided_at.isoformat() if latest_approval else '',
        ])

    # Manifest row
    writer.writerow([])
    writer.writerow(['# MANIFEST', f'Total approved rows: {approved.count()}', f'Export time: {datetime.now().isoformat()}'])

    # Lock the batch
    batch.is_exported = True
    batch.save()

    return response


# --- Batch Summary Endpoint ---

@api_view(['GET'])
def batch_summary(request, batch_id):
    """Get summary statistics for a batch."""
    try:
        batch = IngestionBatch.objects.get(id=batch_id)
    except IngestionBatch.DoesNotExist:
        return Response({'error': 'Batch not found'}, status=status.HTTP_404_NOT_FOUND)

    records = NormalizedRecord.objects.filter(batch=batch)
    failed_raw = RawRecord.objects.filter(batch=batch, parse_status='FAILED')

    return Response({
        'batch_id': batch.id,
        'source_type': batch.source_type,
        'file_name': batch.file_name,
        'uploaded_at': batch.uploaded_at,
        'status': batch.status,
        'is_exported': batch.is_exported,
        'total_rows': batch.total_rows,
        'parsed_rows': batch.parsed_rows,
        'failed_rows': batch.failed_rows,
        'review_summary': {
            'pending': records.filter(review_status='PENDING').count(),
            'approved': records.filter(review_status='APPROVED').count(),
            'flagged': records.filter(review_status='FLAGGED').count(),
            'rejected': records.filter(review_status='REJECTED').count(),
        },
        'failed_records': RawRecordSerializer(failed_raw, many=True).data,
    })


# --- Seed Default Unit Lookups ---

@api_view(['POST'])
def seed_units(request):
    """Seed the UnitLookup table with default conversions."""
    from .parsers.normalizer import DEFAULT_UNITS

    created = 0
    for code, (si_unit, multiplier) in DEFAULT_UNITS.items():
        _, was_created = UnitLookup.objects.get_or_create(
            code=code,
            defaults={'si_unit': si_unit, 'multiplier': multiplier},
        )
        if was_created:
            created += 1

    return Response({'created': created, 'total': UnitLookup.objects.count()})
