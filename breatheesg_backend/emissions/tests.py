from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from emissions.models import Client, IngestionBatch, RawRecord, NormalizedRecord, ReviewDecision, UnitLookup
from emissions.parsers.sap_parser import parse_sap_file
from emissions.parsers.normalizer import normalize_quantity

class EmissionsParserTests(TestCase):
    def setUp(self):
        self.client = Client.objects.create(name='Test Client')
        self.batch = IngestionBatch.objects.create(
            client=self.client,
            source_type='SAP',
            file_name='test.csv'
        )
        UnitLookup.objects.create(code='L', si_unit='L', multiplier=1.0)
        UnitLookup.objects.create(code='KG', si_unit='kg', multiplier=1.0)

    def test_normalize_quantity_valid(self):
        norm_qty, si_unit, qty_ok, qty_err = normalize_quantity("500", "L")
        self.assertTrue(qty_ok)
        self.assertEqual(norm_qty, 500.0)
        self.assertEqual(si_unit, "L")
        
    def test_normalize_quantity_invalid(self):
        norm_qty, si_unit, qty_ok, qty_err = normalize_quantity("invalid_qty", "L")
        self.assertFalse(qty_ok)
        self.assertIn("Cannot convert value", qty_err)
        
    def test_sap_parser_with_invalid_qty(self):
        csv_content = (
            "Buchungsdatum,Werk,Material,Menge,Basismengeneinheit,Bewegungsart,Lieferant,Einkaufsorg.\n"
            "21.03.2024,PL01,1001234,invalid_qty,L,101,V-00123,1000\n"
            "22.03.2024,PL01,1001239,150.00,L,101,V-00129,1000\n"
        )
        
        parsed, failed, errors = parse_sap_file(csv_content, self.batch, self.client)
        
        self.assertEqual(parsed, 2)
        self.assertEqual(failed, 0)
        self.assertEqual(len(errors), 0)
        
        records = NormalizedRecord.objects.filter(batch=self.batch).order_by('id')
        self.assertEqual(records.count(), 2)
        
        rec1 = records[0]
        self.assertEqual(rec1.quantity_value, 0.0)
        self.assertEqual(rec1.review_status, 'FLAGGED')
        
        decision = ReviewDecision.objects.filter(record=rec1).first()
        self.assertIsNotNone(decision)
        self.assertEqual(decision.decision, 'FLAGGED')
        self.assertIn("Cannot convert value 'invalid_qty' to number", decision.note)
        
        rec2 = records[1]
        self.assertEqual(rec2.quantity_value, 150.0)
        self.assertEqual(rec2.review_status, 'PENDING')


class EmissionsApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.client_obj = Client.objects.create(name='API Client')
        UnitLookup.objects.create(code='L', si_unit='L', multiplier=1.0)
        UnitLookup.objects.create(code='KG', si_unit='kg', multiplier=1.0)
        UnitLookup.objects.create(code='KWH', si_unit='kWh', multiplier=1.0)
        UnitLookup.objects.create(code='MWH', si_unit='kWh', multiplier=1000.0)

    def test_upload_sap_creates_batch(self):
        csv_content = (
            "Buchungsdatum,Werk,Material,Menge,Basismengeneinheit,Bewegungsart,Lieferant,Einkaufsorg.\n"
            "15.03.2024,PL01,1001234,500.00,L,101,V-00123,1000\n"
        )
        upload = SimpleUploadedFile("sap.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = self.api.post(
            "/api/upload/",
            {"client_id": self.client_obj.id, "source_type": "SAP", "file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(IngestionBatch.objects.count(), 1)
        self.assertEqual(NormalizedRecord.objects.count(), 1)

    def test_batch_summary_counts(self):
        batch = IngestionBatch.objects.create(
            client=self.client_obj,
            source_type='SAP',
            file_name='sap.csv',
            status='COMPLETED',
            total_rows=2,
            parsed_rows=1,
            failed_rows=1,
        )
        raw_failed = RawRecord.objects.create(
            batch=batch,
            raw_payload={"row": "bad"},
            parse_status='FAILED',
            error_message='bad row',
        )
        raw_ok = RawRecord.objects.create(
            batch=batch,
            raw_payload={"row": "ok"},
            parse_status='SUCCESS',
            error_message='',
        )
        NormalizedRecord.objects.create(
            raw_record=raw_ok,
            client=self.client_obj,
            batch=batch,
            scope='SCOPE_1',
            category='Fuel Combustion',
            quantity_value=10.0,
            quantity_unit_si='L',
            original_value=10.0,
            original_unit='L',
            period_start=date(2024, 3, 15),
            facility_code='PL01',
            source_system='SAP',
            review_status='PENDING',
        )

        response = self.api.get(f"/api/batches/{batch.id}/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['failed_rows'], 1)
        self.assertEqual(len(response.data['failed_records']), 1)
        self.assertEqual(response.data['failed_records'][0]['id'], raw_failed.id)

    def test_review_flag_requires_note(self):
        batch = IngestionBatch.objects.create(
            client=self.client_obj,
            source_type='SAP',
            file_name='sap.csv',
        )
        raw = RawRecord.objects.create(
            batch=batch,
            raw_payload={"row": "ok"},
            parse_status='SUCCESS',
            error_message='',
        )
        record = NormalizedRecord.objects.create(
            raw_record=raw,
            client=self.client_obj,
            batch=batch,
            scope='SCOPE_1',
            category='Fuel Combustion',
            quantity_value=10.0,
            quantity_unit_si='L',
            original_value=10.0,
            original_unit='L',
            period_start=date(2024, 3, 15),
            facility_code='PL01',
            source_system='SAP',
            review_status='PENDING',
        )

        response = self.api.post(f"/api/records/{record.id}/review/", {"decision": "FLAGGED"})

        self.assertEqual(response.status_code, 400)
        self.assertIn('note', response.data)

    def test_export_locks_batch(self):
        batch = IngestionBatch.objects.create(
            client=self.client_obj,
            source_type='SAP',
            file_name='sap.csv',
            status='COMPLETED',
        )
        raw = RawRecord.objects.create(
            batch=batch,
            raw_payload={"row": "ok"},
            parse_status='SUCCESS',
            error_message='',
        )
        record = NormalizedRecord.objects.create(
            raw_record=raw,
            client=self.client_obj,
            batch=batch,
            scope='SCOPE_1',
            category='Fuel Combustion',
            quantity_value=10.0,
            quantity_unit_si='L',
            original_value=10.0,
            original_unit='L',
            period_start=date(2024, 3, 15),
            facility_code='PL01',
            source_system='SAP',
            review_status='APPROVED',
        )
        ReviewDecision.objects.create(record=record, decision='APPROVED', note='ok')

        response = self.api.get(f"/api/batches/{batch.id}/export/")

        self.assertEqual(response.status_code, 200)
        batch.refresh_from_db()
        self.assertTrue(batch.is_exported)
