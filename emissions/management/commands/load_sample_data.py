import os

from django.conf import settings
from django.core.management.base import BaseCommand

from emissions.models import Client, UnitLookup
from emissions.parsers.normalizer import DEFAULT_UNITS
from emissions.parsers.sap_parser import parse_sap_file
from emissions.parsers.utility_parser import parse_utility_file
from emissions.parsers.travel_parser import parse_travel_file


class Command(BaseCommand):
    help = 'Load sample_data files into the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client',
            default='Sample Client',
            help='Client name to attach sample data to.'
        )

    def handle(self, *args, **options):
        client_name = options['client']
        client, _created = Client.objects.get_or_create(name=client_name)

        for code, (si_unit, multiplier) in DEFAULT_UNITS.items():
            UnitLookup.objects.get_or_create(
                code=code,
                defaults={'si_unit': si_unit, 'multiplier': multiplier},
            )

        base_dir = settings.BASE_DIR
        sample_dir = os.path.join(base_dir, 'sample_data')

        files = [
            ('SAP', 'sap_fuel_sample.csv', parse_sap_file),
            ('UTILITY', 'utility_electricity_sample.csv', parse_utility_file),
            ('TRAVEL', 'travel_concur_sample.csv', parse_travel_file),
        ]

        for source_type, filename, parser_fn in files:
            path = os.path.join(sample_dir, filename)
            if not os.path.exists(path):
                self.stderr.write(f"Missing sample file: {path}")
                continue

            with open(path, 'r', encoding='utf-8') as handle:
                content = handle.read()

            batch = client.batches.create(
                source_type=source_type,
                file_name=filename,
                status='PROCESSING',
            )

            parsed, failed, errors = parser_fn(content, batch, client)
            batch.total_rows = parsed + failed
            batch.parsed_rows = parsed
            batch.failed_rows = failed
            batch.status = 'COMPLETED' if failed == 0 else 'FAILED'
            batch.save()

            self.stdout.write(
                f"{source_type}: parsed={parsed} failed={failed} errors={len(errors)}"
            )

        self.stdout.write(self.style.SUCCESS('Sample data load complete.'))
