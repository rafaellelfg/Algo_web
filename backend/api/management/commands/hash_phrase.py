"""python manage.py hash_phrase "NEW PHRASE"  → prints a hash for ADMIN_PHRASE_HASH."""
from django.core.management.base import BaseCommand

from api.login import hash_phrase


class Command(BaseCommand):
    help = "Hash a new admin phrase. Put the output into the ADMIN_PHRASE_HASH environment variable."

    def add_arguments(self, parser):
        parser.add_argument("phrase")

    def handle(self, *args, phrase, **options):
        self.stdout.write(hash_phrase(phrase))
