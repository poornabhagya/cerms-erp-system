"""
CERMS - Hardware Renting System
Idempotent Initial Database Seeding Management Command
Reference: docs/15_DATA_SEEDING_AND_FIXTURES.md & docs/23_PHASE_1_ROADMAP.md
"""

from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from fleet.models import Category, Equipment, RentalRate
from rentals.models import Customer, ProjectSite

User = get_user_model()


class Command(BaseCommand):
    help = "Populates the database with core RBAC groups, default users, fleet categories, equipment master assets, and rental rates."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("================================================================="))
        self.stdout.write(self.style.NOTICE("   Starting Idempotent Initial Database Seeding for CERMS"))
        self.stdout.write(self.style.NOTICE("================================================================="))

        # ---------------------------------------------------------------------
        # 1. Seed RBAC Roles / Groups
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # 2. Seed Default Superuser & Demo RBAC Staff Users
        # ---------------------------------------------------------------------
        admin_username = "admin"
        admin_email = "admin@cerms.com"
        admin_password = "Admin@CERMS2026!"

        try:
            admin_user = User.objects.filter(username=admin_username).first()
            if not admin_user:
                admin_user = User.objects.create_superuser(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password,
                    role=User.Role.ADMINISTRATOR,
                    first_name="System",
                    last_name="Administrator",
                    employee_id="EMP-ADM-001"
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  [+] Created default Superuser: '{admin_username}' (email: {admin_email})"
                ))
            else:
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.role = User.Role.ADMINISTRATOR
                admin_user.save()
                self.stdout.write(self.style.WARNING(
                    f"  [*] Superuser '{admin_username}' already exists. Ensured staff and admin role."
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [-] Error checking/creating superuser: {e}"))

        # Create demo staff users for quick manual testing
        demo_users = [
            {
                'username': 'rental_officer',
                'email': 'rental@cerms.com',
                'role': User.Role.RENTAL_OFFICER,
                'first_name': 'Kamal',
                'last_name': 'Perera',
                'employee_id': 'EMP-RNT-002',
            },
            {
                'username': 'workshop_mgr',
                'email': 'workshop@cerms.com',
                'role': User.Role.WORKSHOP_MANAGER,
                'first_name': 'Nimal',
                'last_name': 'Fernando',
                'employee_id': 'EMP-WRK-003',
            },
            {
                'username': 'field_officer',
                'email': 'field@cerms.com',
                'role': User.Role.FIELD_OFFICER,
                'first_name': 'Sunil',
                'last_name': 'Silva',
                'employee_id': 'EMP-FLD-004',
            },
            {
                'username': 'accountant',
                'email': 'accountant@cerms.com',
                'role': User.Role.ACCOUNTANT,
                'first_name': 'Anura',
                'last_name': 'Jayasinghe',
                'employee_id': 'EMP-ACC-005',
            },
        ]

        for udata in demo_users:
            u, created = User.objects.get_or_create(
                username=udata['username'],
                defaults={
                    'email': udata['email'],
                    'role': udata['role'],
                    'first_name': udata['first_name'],
                    'last_name': udata['last_name'],
                    'employee_id': udata['employee_id'],
                    'is_staff': True,
                    'is_active': True,
                }
            )
            if created:
                u.set_password("Staff@CERMS2026!")
                u.save()
                self.stdout.write(self.style.SUCCESS(f"  [+] Created Demo User: '{u.username}' ({u.get_role_display()})"))
            else:
                self.stdout.write(self.style.WARNING(f"  [*] Demo User already exists: '{u.username}'"))

        # ---------------------------------------------------------------------
        # 3. Seed Equipment Categories
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--- Seeding Fleet Categories ---"))
        categories_data = [
            {
                'name': 'Excavators',
                'code': 'EXC',
                'description': 'Hydraulic crawler and wheeled excavators for earthmoving, trenching, and demolition.'
            },
            {
                'name': 'Generators & Power',
                'code': 'GEN',
                'description': 'Heavy industrial silent diesel generators and mobile site lighting towers.'
            },
            {
                'name': 'Cranes & Lifting',
                'code': 'CRN',
                'description': 'Mobile rough-terrain and all-terrain telescopic hydraulic cranes.'
            },
            {
                'name': 'Compaction & Rollers',
                'code': 'CMP',
                'description': 'Single-drum vibratory soil compactors and tandem asphalt rollers.'
            },
        ]

        categories_map = {}
        for cdata in categories_data:
            cat, created = Category.objects.update_or_create(
                code=cdata['code'],
                defaults={
                    'name': cdata['name'],
                    'description': cdata['description']
                }
            )
            categories_map[cdata['code']] = cat
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Created Category: {cat.name} ({cat.code})"))
            else:
                self.stdout.write(self.style.WARNING(f"  [*] Category already exists / updated: {cat.name} ({cat.code})"))

        # ---------------------------------------------------------------------
        # 4. Seed Equipment Master Assets & Rental Rate Cards
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--- Seeding Equipment Fleet & Rental Rate Cards ---"))
        equipment_data = [
            {
                'asset_code': 'EQ-CAT-320-001',
                'equipment_name': 'Caterpillar 320D Hydraulic Excavator',
                'category': categories_map['EXC'],
                'brand': 'Caterpillar',
                'model_number': '320D',
                'serial_number': 'CAT320D-2026-X1',
                'manufacture_year': 2022,
                'purchase_cost': Decimal('28500000.00'),
                'purchase_date': date(2022, 5, 15),
                'current_hour_meter': Decimal('1450.50'),
                'status': Equipment.Status.AVAILABLE,
                'specifications': {
                    'Operating Weight': '22.0 Ton',
                    'Engine Power': '150 HP (Cat C6.4 ACERT)',
                    'Bucket Capacity': '1.2 m³',
                    'Max Digging Depth': '6.7 m',
                    'Fuel Capacity': '410 L'
                },
                'rate': {
                    'daily_rate': Decimal('45000.00'),
                    'hourly_rate': Decimal('6000.00'),
                    'weekly_rate': Decimal('280000.00'),
                    'monthly_rate': Decimal('1100000.00'),
                    'overtime_hourly_rate': Decimal('7500.00'),
                    'minimum_rental_hours': 8,
                }
            },
            {
                'asset_code': 'EQ-KOM-PC200-002',
                'equipment_name': 'Komatsu PC200-8MO Crawler Excavator',
                'category': categories_map['EXC'],
                'brand': 'Komatsu',
                'model_number': 'PC200-8MO',
                'serial_number': 'KOMPC200-2026-K2',
                'manufacture_year': 2023,
                'purchase_cost': Decimal('31000000.00'),
                'purchase_date': date(2023, 2, 20),
                'current_hour_meter': Decimal('820.00'),
                'status': Equipment.Status.AVAILABLE,
                'specifications': {
                    'Operating Weight': '20.5 Ton',
                    'Engine Power': '148 HP (Komatsu SAA6D107E-1)',
                    'Bucket Capacity': '1.0 m³',
                    'Max Digging Reach': '9.8 m',
                },
                'rate': {
                    'daily_rate': Decimal('42000.00'),
                    'hourly_rate': Decimal('5500.00'),
                    'weekly_rate': Decimal('260000.00'),
                    'monthly_rate': Decimal('1050000.00'),
                    'overtime_hourly_rate': Decimal('7000.00'),
                    'minimum_rental_hours': 8,
                }
            },
            {
                'asset_code': 'EQ-CUM-150KVA-001',
                'equipment_name': 'Cummins 150 kVA Silent Diesel Generator',
                'category': categories_map['GEN'],
                'brand': 'Cummins',
                'model_number': 'C150D5',
                'serial_number': 'CUM150-2026-G1',
                'manufacture_year': 2023,
                'purchase_cost': Decimal('8500000.00'),
                'purchase_date': date(2023, 7, 10),
                'current_hour_meter': Decimal('460.00'),
                'status': Equipment.Status.AVAILABLE,
                'specifications': {
                    'Prime Output': '150 kVA / 120 kW',
                    'Voltage': '400V / 230V 3-Phase 50Hz',
                    'Fuel Tank Capacity': '350 L',
                    'Noise Level': '68 dBA @ 7m',
                    'Fuel Consumption @ 75%': '24.5 L/hr'
                },
                'rate': {
                    'daily_rate': Decimal('22000.00'),
                    'hourly_rate': Decimal('3000.00'),
                    'weekly_rate': Decimal('135000.00'),
                    'monthly_rate': Decimal('520000.00'),
                    'overtime_hourly_rate': Decimal('3500.00'),
                    'minimum_rental_hours': 8,
                }
            },
            {
                'asset_code': 'EQ-CAT-CS533-001',
                'equipment_name': 'Caterpillar CS533E Vibratory Soil Compactor',
                'category': categories_map['CMP'],
                'brand': 'Caterpillar',
                'model_number': 'CS533E',
                'serial_number': 'CATCS533-2026-C1',
                'manufacture_year': 2021,
                'purchase_cost': Decimal('14200000.00'),
                'purchase_date': date(2021, 11, 5),
                'current_hour_meter': Decimal('2100.00'),
                'status': Equipment.Status.AVAILABLE,
                'specifications': {
                    'Operating Weight': '10.8 Ton',
                    'Drum Width': '2134 mm',
                    'Centrifugal Force': '234 kN',
                    'Engine Power': '130 HP'
                },
                'rate': {
                    'daily_rate': Decimal('28000.00'),
                    'hourly_rate': Decimal('3800.00'),
                    'weekly_rate': Decimal('175000.00'),
                    'monthly_rate': Decimal('680000.00'),
                    'overtime_hourly_rate': Decimal('4500.00'),
                    'minimum_rental_hours': 8,
                }
            },
        ]

        for eq_item in equipment_data:
            rate_info = eq_item.pop('rate')
            eq, created = Equipment.objects.update_or_create(
                asset_code=eq_item['asset_code'],
                defaults=eq_item
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Created Equipment: {eq.asset_code} - {eq.equipment_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"  [*] Equipment already exists / updated: {eq.asset_code}"))

            # Idempotently seed or update active RentalRate card
            rate, r_created = RentalRate.objects.update_or_create(
                equipment=eq,
                is_active=True,
                defaults={
                    'daily_rate': rate_info['daily_rate'],
                    'hourly_rate': rate_info['hourly_rate'],
                    'weekly_rate': rate_info['weekly_rate'],
                    'monthly_rate': rate_info['monthly_rate'],
                    'overtime_hourly_rate': rate_info['overtime_hourly_rate'],
                    'minimum_rental_hours': rate_info['minimum_rental_hours'],
                    'effective_from': timezone.now().date(),
                }
            )
            if r_created:
                self.stdout.write(self.style.SUCCESS(f"      [+] Attached Rate Card: Rs. {rate.daily_rate}/day"))
            else:
                self.stdout.write(self.style.WARNING(f"      [*] Updated Rate Card: Rs. {rate.daily_rate}/day"))

        # ---------------------------------------------------------------------
        # 5. Seed Corporate Customers & Project Sites
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--- Seeding Corporate Customers & Project Sites ---"))
        customers_data = [
            {
                'customer_code': 'CUST-2026-001',
                'company_name': 'Access Engineering PLC',
                'contact_person': 'Sunil Jayawardena',
                'phone': '+94 11 234 5678',
                'email': 'procurement@accesseng.lk',
                'billing_address': 'No. 278, Union Place, Colombo 02, Sri Lanka',
                'vat_tax_number': 'VAT-102938475',
                'credit_limit': Decimal('5000000.00'),
                'current_outstanding_balance': Decimal('1500000.00'),
                'status': Customer.Status.ACTIVE,
                'sites': [
                    {
                        'project_code': 'PRJ-COL-001',
                        'project_name': 'Port City Elevated Highway Package 2',
                        'site_address': 'Marine Drive / Chaithya Road, Colombo 01',
                        'gps_coordinates': '6.9344,79.8428',
                        'site_contact_person': 'Eng. Nimal Rathnayake',
                        'site_contact_phone': '+94 77 123 4567',
                        'status': ProjectSite.Status.ACTIVE,
                    },
                    {
                        'project_code': 'PRJ-KTY-002',
                        'project_name': 'Katunayake Expressway Expansion',
                        'site_address': 'Peliyagoda Interchange, Kelaniya',
                        'gps_coordinates': '6.9667,79.8833',
                        'site_contact_person': 'Eng. Sanjeewa Silva',
                        'site_contact_phone': '+94 71 888 9999',
                        'status': ProjectSite.Status.ACTIVE,
                    }
                ]
            },
            {
                'customer_code': 'CUST-2026-002',
                'company_name': 'MAGA Engineering (Pvt) Ltd',
                'contact_person': 'Rohan Gunasekara',
                'phone': '+94 11 456 7890',
                'email': 'logistics@maga.lk',
                'billing_address': 'No. 200, Nawala Road, Narahenpita, Colombo 05',
                'vat_tax_number': 'VAT-987654321',
                'credit_limit': Decimal('8000000.00'),
                'current_outstanding_balance': Decimal('2200000.00'),
                'status': Customer.Status.ACTIVE,
                'sites': [
                    {
                        'project_code': 'PRJ-KND-003',
                        'project_name': 'Central Expressway Stage III (Pothuhera - Galagedara)',
                        'site_address': 'Alawwa Highway Yard, Kurunegala',
                        'gps_coordinates': '7.3000,80.2500',
                        'site_contact_person': 'Eng. Priyantha Bandara',
                        'site_contact_phone': '+94 70 444 3322',
                        'status': ProjectSite.Status.ACTIVE,
                    }
                ]
            },
            {
                'customer_code': 'CUST-2026-003',
                'company_name': 'Nawaloka Construction Co.',
                'contact_person': 'Dinesh Perera',
                'phone': '+94 11 789 1234',
                'email': 'equipment@nawalokaconstruction.lk',
                'billing_address': 'No. 115, Sir James Peiris Mawatha, Colombo 02',
                'vat_tax_number': 'VAT-456123789',
                'credit_limit': Decimal('3000000.00'),
                'current_outstanding_balance': Decimal('0.00'),
                'status': Customer.Status.ACTIVE,
                'sites': []
            }
        ]

        for citem in customers_data:
            sites_list = citem.pop('sites')
            cust, created = Customer.objects.update_or_create(
                customer_code=citem['customer_code'],
                defaults=citem
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Created Customer: {cust.company_name} ({cust.customer_code})"))
            else:
                self.stdout.write(self.style.WARNING(f"  [*] Customer already exists / updated: {cust.company_name}"))

            for sitem in sites_list:
                sitem['customer'] = cust
                psite, s_created = ProjectSite.objects.update_or_create(
                    project_code=sitem['project_code'],
                    defaults=sitem
                )
                if s_created:
                    self.stdout.write(self.style.SUCCESS(f"      [+] Created Site: {psite.project_name} ({psite.project_code})"))
                else:
                    self.stdout.write(self.style.WARNING(f"      [*] Site already exists: {psite.project_name}"))

        self.stdout.write(self.style.NOTICE("================================================================="))
        self.stdout.write(self.style.SUCCESS("✓ All Initial Database Entities & Fleet/Customer Data Seeded Successfully!"))
        self.stdout.write(self.style.NOTICE("================================================================="))
