"""
CERMS - Hardware Renting System
Idempotent Initial Database Seeding Management Command
Reference: docs/15_DATA_SEEDING_AND_FIXTURES.md
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class Command(BaseCommand):
    help = "Populates the database with core RBAC groups and default superuser idempotently."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting initial database seeding for CERMS..."))

        # 1. Seed RBAC Roles / Groups
        roles = [
            'Administrator',
            'Management',
            'Rental Officer',
            'Operations Officer',
            'Workshop Manager',
            'Accountant',
            'Storekeeper',
            'Field Officer',
        ]

        for role_name in roles:
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Created Group/Role: {role_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"  [*] Group/Role already exists: {role_name}"))

        # 2. Seed Default Admin Superuser
        admin_username = "admin"
        admin_email = "admin@cerms.com"
        admin_password = "Admin@CERMS2026!"

        try:
            admin_user = User.objects.filter(username=admin_username).first()
            if not admin_user:
                admin_user = User.objects.create_superuser(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  [+] Created default Superuser: '{admin_username}' (email: {admin_email})"
                ))
            else:
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()
                self.stdout.write(self.style.WARNING(
                    f"  [*] Superuser '{admin_username}' already exists. Ensured staff and superuser flags."
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [-] Error checking/creating superuser: {e}"))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
