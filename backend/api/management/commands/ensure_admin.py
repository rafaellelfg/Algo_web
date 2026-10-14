"""python manage.py ensure_admin <username> <password>

Create the admin account if it does not exist (or reset its password and make
it staff if it does). Used by the Playwright tests in ../e2e; also handy to
create an admin without the interactive `createsuperuser` questions.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update a staff (admin) user non-interactively."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument("--name", default="Admin")
        parser.add_argument(
            "--if-missing", action="store_true", help="only create it; leave an existing account (and its password) alone"
        )

    def handle(self, *args, username, password, name, if_missing, **options):
        if if_missing and User.objects.filter(username=username).exists():
            self.stdout.write(f"Admin '{username}' already exists - left unchanged.")
            return
        user, created = User.objects.get_or_create(username=username, defaults={"first_name": name})
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(f"{'Created' if created else 'Updated'} admin '{username}'.")
