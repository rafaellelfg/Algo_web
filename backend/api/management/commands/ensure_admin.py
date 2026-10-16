"""python manage.py ensure_admin [username password]

Make sure the admin account exists, is staff, and has this password.
Without arguments it uses ADMIN_USERNAME and ADMIN_PASSWORD from the .env file
(`python run.py` does that on every start, so .env is where you change them).
The Playwright tests in ../e2e pass their own test account as arguments.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a staff (admin) user non-interactively (default: the admin from .env)."

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?", help="default: ADMIN_USERNAME from .env")
        parser.add_argument("password", nargs="?", help="default: ADMIN_PASSWORD from .env")
        parser.add_argument("--name", default="Admin")
        parser.add_argument(
            "--if-missing", action="store_true", help="only create it; leave an existing account (and its password) alone"
        )

    def handle(self, *args, username, password, name, if_missing, **options):
        username = username or settings.ADMIN_USERNAME
        password = password or settings.ADMIN_PASSWORD
        if not username or not password:
            raise CommandError("No admin account given: pass username and password, or set ADMIN_USERNAME and ADMIN_PASSWORD in .env")

        user = User.objects.filter(username=username).first()
        if user and if_missing:
            return
        created = user is None
        if created:
            user = User(username=username, first_name=name)
        changed = created
        if created or not user.check_password(password):
            user.set_password(password)
            changed = True
        for flag in ("is_staff", "is_superuser", "is_active"):
            if not getattr(user, flag):
                setattr(user, flag, True)
                changed = True
        if changed:
            user.save()
            self.stdout.write(f"{'Created' if created else 'Updated'} admin '{username}'.")
