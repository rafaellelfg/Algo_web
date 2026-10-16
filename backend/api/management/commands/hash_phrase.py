"""python manage.py hash_phrase "PHRASE"  → prints its hash.

Optional: put the output into .env as ADMIN_PHRASE_HASH=... and delete the
ADMIN_SECRET_PHRASE line, so the phrase itself is not kept anywhere.
"""
from django.core.management.base import BaseCommand

from api.login import hash_phrase


class Command(BaseCommand):
    help = "Hash an admin phrase. Put the output into .env as ADMIN_PHRASE_HASH."

    def add_arguments(self, parser):
        parser.add_argument("phrase")

    def handle(self, *args, phrase, **options):
        self.stdout.write(hash_phrase(phrase))
