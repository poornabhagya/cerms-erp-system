"""
CERMS - Hardware Renting System
Dynamic Realistic Test Data Seeding Management Command
Reference: docs/15_DATA_SEEDING_AND_FIXTURES.md & docs/23_PHASE_1_ROADMAP.md
"""

from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker

from fleet.models import Category, Equipment, RentalRate
from rentals.models import (
    Customer,
    ProjectSite,
    Quotation,
    QuotationItem,
    RentalContract,
    RentalContractItem,
    DispatchReturn,
)
from finance.models import Invoice, Payment, SecurityDeposit

User = get_user_model()


class Command(BaseCommand):
    help = "Generates realistic mock data (10 customers, 50 equipment assets, 20 rental contracts) for Phase 1 testing."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete previously generated dummy data before seeding.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Bypass the settings.DEBUG safety check to run in non-DEBUG environments.',
        )

    def handle(self, *args, **options):
        # ---------------------------------------------------------------------
        # 1. Environment Safety Check (docs/15_DATA_SEEDING_AND_FIXTURES.md §4)
        # ---------------------------------------------------------------------
        if not settings.DEBUG and not options.get('force'):
            raise CommandError(
                "CRITICAL: Refusing to generate dummy data in a non-DEBUG environment without the '--force' flag."
            )

        self.stdout.write(self.style.NOTICE("================================================================="))
        self.stdout.write(self.style.NOTICE("   Starting Realistic Test Data Generation for CERMS (Phase 1)"))
        self.stdout.write(self.style.NOTICE("================================================================="))

        # ---------------------------------------------------------------------
        # 2. Clear Existing Dummy Data If Requested
        # ---------------------------------------------------------------------
        if options.get('clear'):
            self.stdout.write(self.style.WARNING("Clearing previously generated dummy data..."))
            Payment.objects.filter(payment_id__startswith='PAY-DUMMY-').delete()
            Invoice.objects.filter(invoice_no__startswith='INV-DUMMY-').delete()
            SecurityDeposit.objects.filter(deposit_id__startswith='DEP-DUMMY-').delete()
            DispatchReturn.objects.filter(transaction_id__startswith='TRX-DUMMY-').delete()
            RentalContractItem.objects.filter(contract__contract_no__startswith='CNT-DUMMY-').delete()
            RentalContract.objects.filter(contract_no__startswith='CNT-DUMMY-').delete()
            QuotationItem.objects.filter(quotation__quotation_no__startswith='QT-DUMMY-').delete()
            Quotation.objects.filter(quotation_no__startswith='QT-DUMMY-').delete()
            ProjectSite.objects.filter(project_code__startswith='PRJ-DUMMY-').delete()
            Customer.objects.filter(customer_code__startswith='CUST-DUMMY-').delete()
            RentalRate.objects.filter(equipment__asset_code__startswith='EQ-DUMMY-').delete()
            Equipment.objects.filter(asset_code__startswith='EQ-DUMMY-').delete()
            self.stdout.write(self.style.SUCCESS("  [SUCCESS] Cleared previously seeded dummy records."))

        fake = Faker()

        # Find or use staff users for audit fields
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(role=User.Role.ADMINISTRATOR).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@cerms.com',
                password='Admin@CERMS2026!',
                role=User.Role.ADMINISTRATOR,
            )

        rental_officer = User.objects.filter(role=User.Role.RENTAL_OFFICER).first() or admin_user
        workshop_mgr = User.objects.filter(role=User.Role.WORKSHOP_MANAGER).first() or admin_user
        accountant = User.objects.filter(role=User.Role.ACCOUNTANT).first() or admin_user

        # ---------------------------------------------------------------------
        # 3. Ensure Equipment Categories Exist
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--- [Step 1/4] Ensuring Equipment Categories ---"))
        categories_def = [
            ('EXC', 'Excavators', 'Hydraulic crawler and wheeled excavators for earthmoving and trenching.'),
            ('GEN', 'Generators & Power', 'Prime and standby silent diesel generators, distribution panels, and power plants.'),
            ('CRN', 'Cranes & Lifting', 'Rough-terrain, all-terrain, and telescopic mobile cranes for heavy rigging.'),
            ('CMP', 'Compaction & Rollers', 'Single-drum vibratory soil compactors and tandem asphalt rollers.'),
            ('LDR', 'Wheel Loaders', 'High-capacity front-end wheel loaders for bulk aggregate handling.'),
            ('BKH', 'Backhoe Loaders', 'Versatile multi-purpose backhoes for trenching, loading, and urban excavation.'),
            ('CNC', 'Concrete Equipment', 'Truck mixers, stationary and boom concrete pumps, and heavy trowels.'),
            ('FLT', 'Forklifts & Material Handling', 'Diesel and rough-terrain industrial forklifts and telehandlers.'),
        ]

        categories = {}
        for code, name, desc in categories_def:
            cat, _ = Category.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc}
            )
            categories[code] = cat
        self.stdout.write(self.style.SUCCESS(f"  [+] Categories verified ({len(categories)} categories ready)."))

        # ---------------------------------------------------------------------
        # 4. Generate 10 Realistic Customers & Associated Project Sites
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--- [Step 2/4] Generating 10 Realistic Customers & Project Sites ---"))
        customers_catalog = [
            ("Access Engineering PLC", "Sanjeewa Bandara", "+94 11 2760760", "sanjeewa.b@accesseng.com", "Access Towers, 278 Union Place, Colombo 02", "102938475-7000", Decimal("15000000.00")),
            ("Maga Engineering (Pvt) Ltd", "Rohan Karunaratne", "+94 11 2808835", "rohan.k@maga.lk", "200 Nawala Road, Narahenpita, Colombo 05", "203948571-7000", Decimal("12000000.00")),
            ("Sierra Construction Ltd", "Priyantha Kariyawasam", "+94 11 4344444", "priyantha.k@sierralk.com", "112 Asgiriya Road, Gampaha", "304958672-7000", Decimal("10000000.00")),
            ("Nawaloka Construction Co.", "Chathura Senanayake", "+94 11 2544444", "chathura.s@nawaloka.lk", "115 Sir James Peiris Mawatha, Colombo 02", "405968783-7000", Decimal("8000000.00")),
            ("Sanken Construction (Pvt) Ltd", "Mahen Fernando", "+94 11 2697891", "mahen.f@sanken.com", "295 Madampitiya Road, Colombo 14", "506978894-7000", Decimal("14000000.00")),
            ("Edward & Christie Ltd", "Nuwan Christie", "+94 11 2435888", "nuwan.c@edwardchristie.lk", "45 Temple Road, Nugegoda", "607989905-7000", Decimal("6000000.00")),
            ("CML-MTD Construction Ltd", "Dayan Dassanayake", "+94 11 2865566", "dayan.d@cml-mtd.com", "364/18 High Level Road, Nawinna, Maharagama", "708990016-7000", Decimal("9000000.00")),
            ("V. V. Karunaratne & Co.", "Vijitha Karunaratne", "+94 81 2234567", "vijitha.k@vvkco.lk", "88 Katugastota Road, Kandy", "809001127-7000", Decimal("5000000.00")),
            ("International Construction Consortium", "Harsha Wickramasinghe", "+94 11 4400400", "harsha.w@icc-construct.com", "Kohuwala, Nugegoda", "910112238-7000", Decimal("11000000.00")),
            ("Tudawe Brothers (Pvt) Ltd", "Ajith Tudawe", "+94 11 2441084", "ajith.t@tudawe.com", "505/2 Elvitigala Mawatha, Colombo 05", "112233449-7000", Decimal("7500000.00")),
        ]

        sites_pool = [
            ("Central Expressway Section III - Kurunegala", "Kurunegala Interchange, Dambulla Road", "7.4863,80.3623"),
            ("Colombo Port City Lot 4 Commercial Complex", "Marine Drive, Port City Financial District", "6.9344,79.8428"),
            ("Marine Drive Extension Project - Wellawatte", "Marine Drive Sea Wall Section, Colombo 06", "6.8741,79.8588"),
            ("Kandy Multimodal Transport Terminal", "Goodshed Yard, William Gopallawa Mawatha, Kandy", "7.2891,80.6315"),
            ("Southern Highway Link - Hambantota Port Zone", "Mirijjawila Industrial Estate, Hambantota", "6.1248,81.1185"),
            ("Katunayake Airport Terminal 2 Expansion", "BIA Cargo Perimeter, Airport Road, Katunayake", "7.1808,79.8841"),
            ("Ruwanpura Expressway Interchange - Kahathuduwa", "Kahathuduwa Exit 02, Horana Highway Link", "6.7924,79.9981"),
            ("Victoria Dam Canal Spillway Rehabilitation", "Teldeniya - Victoria Dam Reserve, Digana", "7.2435,80.7932"),
            ("Waterfront Logistics Hub - Peliyagoda", "New Kelani Bridge Access Corridor, Peliyagoda", "6.9584,79.8821"),
            ("Biyagama Export Processing Zone Extension", "Zone B Access Gate 4, Biyagama", "6.9388,79.9882"),
        ]

        seeded_customers = []
        seeded_sites = []

        for idx, (c_name, c_person, c_phone, c_email, c_addr, c_vat, c_limit) in enumerate(customers_catalog, start=1):
            c_code = f"CUST-DUMMY-{idx:03d}"
            customer, created = Customer.objects.update_or_create(
                customer_code=c_code,
                defaults={
                    'company_name': c_name,
                    'contact_person': c_person,
                    'phone': c_phone,
                    'email': c_email,
                    'billing_address': c_addr,
                    'vat_tax_number': c_vat,
                    'credit_limit': c_limit,
                    'status': Customer.Status.ACTIVE,
                }
            )
            seeded_customers.append(customer)

            # Create 1-2 project sites per customer
            site_count = 2 if idx <= 6 else 1
            for s_idx in range(1, site_count + 1):
                site_def_idx = ((idx - 1) * 2 + s_idx - 1) % len(sites_pool)
                s_name, s_addr, s_gps = sites_pool[site_def_idx]
                s_code = f"PRJ-DUMMY-{idx:03d}-{s_idx:02d}"

                site, _ = ProjectSite.objects.update_or_create(
                    project_code=s_code,
                    defaults={
                        'customer': customer,
                        'project_name': f"{s_name} (Site {s_idx})",
                        'site_address': s_addr,
                        'gps_coordinates': s_gps,
                        'site_contact_person': f"{c_person} (Site Rep)",
                        'site_contact_phone': c_phone,
                        'status': ProjectSite.Status.ACTIVE,
                    }
                )
                seeded_sites.append(site)

        self.stdout.write(self.style.SUCCESS(
            f"  [+] Seeded {len(seeded_customers)} Customers and {len(seeded_sites)} Project Sites."
        ))

        # ---------------------------------------------------------------------
        # 5. Generate 50 Realistic Equipment Assets Across All Categories
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--- [Step 3/4] Generating 50 Realistic Equipment Assets & Rate Cards ---"))

        equipment_definitions = [
            # EXC - 10 units
            ("EXC", "CAT", "320D", "Caterpillar 320D Hydraulic Excavator", 2021, Decimal("28500000.00"), Decimal("1420.50"), {"operating_weight": "22.2 ton", "engine_power": "140 hp", "bucket_capacity": "1.0 m3"}, Decimal("45000.00")),
            ("EXC", "KOM", "PC200", "Komatsu PC200-8MO Hydraulic Excavator", 2020, Decimal("26000000.00"), Decimal("2150.00"), {"operating_weight": "20.5 ton", "engine_power": "147 hp", "bucket_capacity": "0.9 m3"}, Decimal("42000.00")),
            ("EXC", "KOB", "SK210", "Kobelco SK210LC Generation 10 Excavator", 2022, Decimal("31000000.00"), Decimal("980.00"), {"operating_weight": "21.4 ton", "engine_power": "150 hp", "bucket_capacity": "1.1 m3"}, Decimal("44000.00")),
            ("EXC", "HIT", "ZX200", "Hitachi ZX200-5G Hydraulic Excavator", 2021, Decimal("29000000.00"), Decimal("1650.00"), {"operating_weight": "20.0 ton", "engine_power": "168 hp", "bucket_capacity": "0.9 m3"}, Decimal("43000.00")),
            ("EXC", "CAT", "336D", "Caterpillar 336D2 Heavy Excavator", 2019, Decimal("42000000.00"), Decimal("3800.00"), {"operating_weight": "36.5 ton", "engine_power": "268 hp", "bucket_capacity": "1.9 m3"}, Decimal("75000.00")),
            ("EXC", "SAN", "SY215", "Sany SY215C Medium Crawler Excavator", 2023, Decimal("24000000.00"), Decimal("620.00"), {"operating_weight": "21.9 ton", "engine_power": "155 hp", "bucket_capacity": "0.93 m3"}, Decimal("38000.00")),
            ("EXC", "VOL", "EC210", "Volvo EC210B Prime Crawler Excavator", 2020, Decimal("27500000.00"), Decimal("2450.00"), {"operating_weight": "21.0 ton", "engine_power": "159 hp", "bucket_capacity": "1.0 m3"}, Decimal("42000.00")),
            ("EXC", "DOO", "DX225", "Doosan DX225LCA Tracked Excavator", 2021, Decimal("25500000.00"), Decimal("1800.00"), {"operating_weight": "22.5 ton", "engine_power": "155 hp", "bucket_capacity": "1.05 m3"}, Decimal("40000.00")),
            ("EXC", "JCB", "JS205", "JCB JS205 Heavy Earth Excavator", 2022, Decimal("26500000.00"), Decimal("1100.00"), {"operating_weight": "20.5 ton", "engine_power": "140 hp", "bucket_capacity": "0.9 m3"}, Decimal("41000.00")),
            ("EXC", "KOM", "PC130", "Komatsu PC130-7 Compact Midi Excavator", 2022, Decimal("18000000.00"), Decimal("850.00"), {"operating_weight": "12.8 ton", "engine_power": "95 hp", "bucket_capacity": "0.55 m3"}, Decimal("32000.00")),

            # GEN - 8 units
            ("GEN", "CUM", "100KVA", "Cummins 100 kVA Silent Diesel Generator", 2022, Decimal("7800000.00"), Decimal("950.00"), {"rated_output": "100 kVA / 80 kW", "fuel_tank": "280 L", "noise_level": "68 dBA @ 7m"}, Decimal("18000.00")),
            ("GEN", "CUM", "150KVA", "Cummins 150 kVA Soundproof Power Generator", 2021, Decimal("9500000.00"), Decimal("1450.00"), {"rated_output": "150 kVA / 120 kW", "fuel_tank": "350 L", "noise_level": "70 dBA @ 7m"}, Decimal("22000.00")),
            ("GEN", "CAT", "200KVA", "Caterpillar DE200 200 kVA Generator", 2023, Decimal("12500000.00"), Decimal("520.00"), {"rated_output": "200 kVA / 160 kW", "fuel_tank": "420 L", "noise_level": "69 dBA @ 7m"}, Decimal("28000.00")),
            ("GEN", "CAT", "250KVA", "Caterpillar DE250 250 kVA Generator", 2020, Decimal("15000000.00"), Decimal("2100.00"), {"rated_output": "250 kVA / 200 kW", "fuel_tank": "500 L", "noise_level": "72 dBA @ 7m"}, Decimal("35000.00")),
            ("GEN", "DEN", "125KVA", "Denyo DCA-125USI Silent Diesel Generator", 2022, Decimal("8900000.00"), Decimal("1150.00"), {"rated_output": "125 kVA / 100 kW", "fuel_tank": "300 L", "noise_level": "65 dBA @ 7m"}, Decimal("20000.00")),
            ("GEN", "DEN", "60KVA", "Denyo DCA-60USI Compact Generator", 2023, Decimal("5500000.00"), Decimal("420.00"), {"rated_output": "60 kVA / 48 kW", "fuel_tank": "180 L", "noise_level": "63 dBA @ 7m"}, Decimal("14000.00")),
            ("GEN", "PER", "80KVA", "Perkins 80 kVA Heavy Duty Generator", 2021, Decimal("6800000.00"), Decimal("1750.00"), {"rated_output": "80 kVA / 64 kW", "fuel_tank": "240 L", "noise_level": "68 dBA @ 7m"}, Decimal("16000.00")),
            ("GEN", "VOL", "300KVA", "Volvo Penta 300 kVA Prime Industrial Generator", 2021, Decimal("19500000.00"), Decimal("1880.00"), {"rated_output": "300 kVA / 240 kW", "fuel_tank": "650 L", "noise_level": "72 dBA @ 7m"}, Decimal("42000.00")),

            # CRN - 6 units
            ("CRN", "TAD", "GR550", "Tadano GR-550XL 55 Ton Rough Terrain Crane", 2020, Decimal("48000000.00"), Decimal("2200.00"), {"lifting_capacity": "55 ton", "boom_length": "42 m", "engine_power": "270 hp"}, Decimal("85000.00")),
            ("CRN", "KATO", "SR300", "Kato SR-300R 30 Ton City Terrain Crane", 2021, Decimal("34000000.00"), Decimal("1400.00"), {"lifting_capacity": "30 ton", "boom_length": "30.5 m", "engine_power": "210 hp"}, Decimal("58000.00")),
            ("CRN", "XCMG", "QY50", "XCMG QY50K 50 Ton Hydraulic Truck Crane", 2022, Decimal("39000000.00"), Decimal("950.00"), {"lifting_capacity": "50 ton", "boom_length": "40 m", "outrigger_span": "6.6 m"}, Decimal("72000.00")),
            ("CRN", "ZOO", "ZMC60", "Zoomlion 60 Ton Telescopic Mobile Crane", 2020, Decimal("44000000.00"), Decimal("2600.00"), {"lifting_capacity": "60 ton", "boom_length": "43 m", "counterweight": "11.5 ton"}, Decimal("80000.00")),
            ("CRN", "LIE", "LTM1050", "Liebherr LTM 1050-3.1 All-Terrain Crane", 2019, Decimal("52000000.00"), Decimal("3100.00"), {"lifting_capacity": "50 ton", "boom_length": "38 m", "axles": "3-axle"}, Decimal("88000.00")),
            ("CRN", "TER", "RT35", "Terex RT35 35 Ton Rough Terrain Crane", 2022, Decimal("36000000.00"), Decimal("1180.00"), {"lifting_capacity": "35 ton", "boom_length": "32 m", "drive_steer": "4x4x4"}, Decimal("62000.00")),

            # CMP - 6 units
            ("CMP", "CAT", "CS533", "Caterpillar CS533E Vibratory Soil Compactor", 2021, Decimal("17500000.00"), Decimal("1320.00"), {"operating_weight": "10.8 ton", "drum_width": "2134 mm", "frequency": "31.9 Hz"}, Decimal("28000.00")),
            ("CMP", "BOM", "BW211", "Bomag BW211 D-40 Single Drum Vibratory Roller", 2020, Decimal("16000000.00"), Decimal("1950.00"), {"operating_weight": "11.2 ton", "drum_width": "2130 mm", "engine_power": "133 hp"}, Decimal("26000.00")),
            ("CMP", "DYN", "CA250", "Dynapac CA250D Vibratory Soil Roller", 2022, Decimal("18500000.00"), Decimal("870.00"), {"operating_weight": "12.0 ton", "drum_width": "2130 mm", "centrifugal_force": "246 kN"}, Decimal("29000.00")),
            ("CMP", "SAK", "SW652", "Sakai SW652 Tandem Vibratory Roller", 2021, Decimal("13500000.00"), Decimal("1420.00"), {"operating_weight": "7.2 ton", "drum_width": "1480 mm", "application": "Asphalt Paving"}, Decimal("22000.00")),
            ("CMP", "HAM", "311D", "Hamm 311 Compactor Single Drum Roller", 2020, Decimal("15500000.00"), Decimal("2200.00"), {"operating_weight": "11.0 ton", "drum_width": "2140 mm", "gradeability": "55%"}, Decimal("25000.00")),
            ("CMP", "CAT", "CB24", "Caterpillar CB24B Tandem Asphalt Roller", 2023, Decimal("9800000.00"), Decimal("480.00"), {"operating_weight": "2.7 ton", "drum_width": "1200 mm", "water_tank": "235 L"}, Decimal("18000.00")),

            # LDR - 6 units
            ("LDR", "CAT", "950GC", "Caterpillar 950GC Heavy Wheel Loader", 2021, Decimal("32000000.00"), Decimal("1650.00"), {"operating_weight": "18.6 ton", "bucket_capacity": "3.1 m3", "net_power": "241 hp"}, Decimal("48000.00")),
            ("LDR", "KOM", "WA380", "Komatsu WA380-6 Heavy Wheel Loader", 2020, Decimal("29500000.00"), Decimal("2350.00"), {"operating_weight": "17.8 ton", "bucket_capacity": "3.3 m3", "breakout_force": "172 kN"}, Decimal("45000.00")),
            ("LDR", "VOL", "L120", "Volvo L120F High Performance Wheel Loader", 2019, Decimal("33500000.00"), Decimal("3100.00"), {"operating_weight": "19.2 ton", "bucket_capacity": "3.5 m3", "torque_parallel": "Yes"}, Decimal("49000.00")),
            ("LDR", "SDLG", "LG958", "SDLG LG958L Medium Heavy Wheel Loader", 2022, Decimal("21000000.00"), Decimal("1080.00"), {"operating_weight": "16.8 ton", "bucket_capacity": "3.0 m3", "engine": "Weichai 220hp"}, Decimal("36000.00")),
            ("LDR", "CAT", "930K", "Caterpillar 930K Compact Wheel Loader", 2022, Decimal("24500000.00"), Decimal("920.00"), {"operating_weight": "13.8 ton", "bucket_capacity": "2.3 m3", "hydrostatic_drive": "Yes"}, Decimal("39000.00")),
            ("LDR", "LIU", "856H", "LiuGong CLG 856H Wheel Loader", 2021, Decimal("22500000.00"), Decimal("1500.00"), {"operating_weight": "17.1 ton", "bucket_capacity": "3.0 m3", "transmission": "ZF 4WG200"}, Decimal("37000.00")),

            # BKH - 5 units
            ("BKH", "JCB", "3DX", "JCB 3DX Super EcoXcellence Backhoe Loader", 2022, Decimal("14500000.00"), Decimal("1250.00"), {"max_dig_depth": "4.77 m", "loader_capacity": "1.1 m3", "engine_power": "76 hp"}, Decimal("25000.00")),
            ("BKH", "CAT", "428F", "Caterpillar 428F2 Side-Shift Backhoe Loader", 2021, Decimal("16500000.00"), Decimal("1720.00"), {"max_dig_depth": "4.68 m", "loader_capacity": "1.03 m3", "hydraulics": "Variable flow"}, Decimal("27000.00")),
            ("BKH", "CASE", "580N", "CASE 580N High Performance Backhoe Loader", 2020, Decimal("15000000.00"), Decimal("2100.00"), {"max_dig_depth": "4.49 m", "loader_capacity": "1.0 m3", "procontrol": "Yes"}, Decimal("24000.00")),
            ("BKH", "KOM", "WB97", "Komatsu WB97R-5 Heavy Duty Backhoe Loader", 2021, Decimal("15800000.00"), Decimal("1490.00"), {"max_dig_depth": "4.90 m", "loader_capacity": "1.1 m3", "transmission": "Full Powershift"}, Decimal("26000.00")),
            ("BKH", "JCB", "4DX", "JCB 4DX Heavy Duty Trenching Backhoe", 2023, Decimal("16900000.00"), Decimal("650.00"), {"max_dig_depth": "5.36 m", "loader_capacity": "1.2 m3", "engine_power": "92 hp"}, Decimal("28000.00")),

            # CNC - 5 units
            ("CNC", "SCH", "PUM28", "Schwing Stetter 28m Truck Concrete Boom Pump", 2020, Decimal("38000000.00"), Decimal("1850.00"), {"vertical_reach": "27.5 m", "output_capacity": "90 m3/h", "pipeline_diameter": "125 mm"}, Decimal("68000.00")),
            ("CNC", "PUT", "BSF36", "Putzmeister BSF 36 Concrete Boom Pump", 2019, Decimal("46000000.00"), Decimal("2750.00"), {"vertical_reach": "35.6 m", "output_capacity": "160 m3/h", "mast_arms": "4-arm Z-fold"}, Decimal("78000.00")),
            ("CNC", "STE", "AM7", "Stetter AM 7 FHC Transit Concrete Mixer 7m3", 2021, Decimal("21000000.00"), Decimal("1920.00"), {"nominal_capacity": "7.0 m3", "water_tank": "650 L", "drum_drive": "Hydraulic"}, Decimal("35000.00")),
            ("CNC", "FIO", "DB460", "Fiori DB 460 Self-Loading Concrete Mixer", 2022, Decimal("19500000.00"), Decimal("1100.00"), {"batch_yield": "4.0 m3", "4wd_4ws": "Yes", "electronic_weighing": "Integrated"}, Decimal("33000.00")),
            ("CNC", "WAK", "CRT48", "Wacker Neuson CRT 48 Ride-on Concrete Trowel", 2023, Decimal("6500000.00"), Decimal("410.00"), {"trowel_diameter": "2x 1220 mm", "rotor_speed": "165 rpm", "steering": "Twin-lever"}, Decimal("16000.00")),

            # FLT - 4 units
            ("FLT", "TOY", "8FGU", "Toyota 8FGU25 2.5 Ton Diesel Industrial Forklift", 2022, Decimal("7200000.00"), Decimal("1150.00"), {"capacity": "2.5 ton", "lift_height": "4.5 m", "engine": "Toyota 1ZS Diesel"}, Decimal("18000.00")),
            ("FLT", "KOM", "FD30", "Komatsu FD30T-17 3.0 Ton Rough Terrain Forklift", 2021, Decimal("8500000.00"), Decimal("1680.00"), {"capacity": "3.0 ton", "lift_height": "4.0 m", "mast": "3-stage full free view"}, Decimal("21000.00")),
            ("FLT", "CAT", "DP30", "Caterpillar DP30NT 3.0 Ton Heavy Forklift", 2020, Decimal("8200000.00"), Decimal("2100.00"), {"capacity": "3.0 ton", "lift_height": "4.5 m", "transmission": "Powershift"}, Decimal("20000.00")),
            ("FLT", "HYU", "50D", "Hyundai 50D-9 5.0 Ton Heavy Material Forklift", 2022, Decimal("12800000.00"), Decimal("950.00"), {"capacity": "5.0 ton", "lift_height": "5.0 m", "cabin": "Full AC Operator Cabin"}, Decimal("28000.00")),
        ]

        seeded_equipment = []

        minor_damage_descriptions = [
            "Minor scratch on rear counterweight from site barricade brush.",
            "Cabin door rubber seal slightly weathered; does not affect sealing.",
            "Left mudguard panel has superficial paint scuff; lamps operational.",
            "Right side outrigger pad showing surface oxidation; structural integrity certified.",
            "Front work lamp plastic bezel cracked; LED bulb intact.",
            "Boom rest cushioning rubber pad 15% worn; replaced during next service.",
            "Side engine canopy latch requires firm push to lock.",
            "Exhaust heat wrap lightly frayed near manifold clamp.",
        ]

        for idx, (cat_code, brand, model_num, eq_name, mfg_year, p_cost, hrs, specs, daily_rate) in enumerate(equipment_definitions, start=1):
            category = categories[cat_code]
            asset_code = f"EQ-DUMMY-{cat_code}-{brand}-{model_num}-{idx:02d}"
            serial_num = f"VIN-DUMMY-{cat_code}-{brand}-{mfg_year}-{idx:04d}"

            # Determine minor damage flag
            has_damage = (idx % 6 == 0)
            damage_notes = minor_damage_descriptions[(idx // 6) % len(minor_damage_descriptions)] if has_damage else ""

            # Preliminary operational status (will align with active contracts later)
            if idx in [47, 48, 49]:
                initial_status = Equipment.Status.BREAKDOWN
            elif idx in [41, 42, 43, 44, 45, 46]:
                initial_status = Equipment.Status.MAINTENANCE
            else:
                initial_status = Equipment.Status.AVAILABLE

            eq, created = Equipment.objects.update_or_create(
                asset_code=asset_code,
                defaults={
                    'equipment_name': eq_name,
                    'category': category,
                    'brand': brand,
                    'model_number': model_num,
                    'serial_number': serial_num,
                    'manufacture_year': mfg_year,
                    'purchase_cost': p_cost,
                    'purchase_date': date(mfg_year, (idx % 12) + 1, (idx % 25) + 1),
                    'current_hour_meter': hrs,
                    'status': initial_status,
                    'specifications': specs,
                    'has_minor_damage': has_damage,
                    'minor_damage_notes': damage_notes,
                }
            )
            seeded_equipment.append(eq)

            # Create or update active RentalRate card
            weekly_rate = (daily_rate * Decimal("6.00")).quantize(Decimal("0.01"))
            monthly_rate = (daily_rate * Decimal("22.00")).quantize(Decimal("0.01"))
            ot_rate = ((daily_rate / Decimal("8.00")) * Decimal("1.25")).quantize(Decimal("0.01"))

            RentalRate.objects.update_or_create(
                equipment=eq,
                is_active=True,
                defaults={
                    'daily_rate': daily_rate,
                    'weekly_rate': weekly_rate,
                    'monthly_rate': monthly_rate,
                    'hourly_rate': (daily_rate / Decimal("8.00")).quantize(Decimal("0.01")),
                    'overtime_hourly_rate': ot_rate,
                    'minimum_rental_hours': 8,
                    'effective_from': date(2026, 1, 1),
                }
            )

        self.stdout.write(self.style.SUCCESS(
            f"  [+] Seeded {len(seeded_equipment)} Equipment assets across {len(categories)} categories with active Rate Cards."
        ))

        # ---------------------------------------------------------------------
        # 6. Generate 20 Rental Contracts Across Full Lifecycle
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--- [Step 4/4] Generating 20 Rental Contracts & Full Lifecycle Entities ---"))

        # Lifecycle distribution:
        # Contracts 01 - 05: CLOSED (Historical, Returned, Invoiced & Settled)
        # Contracts 06 - 13: ON_RENT (Currently active on customer site)
        # Contracts 14 - 16: DISPATCHED (Mobilized / in-transit to site)
        # Contracts 17 - 20: ACTIVE (Converted from quote, pending logistics mobilization)

        today = timezone.now().date()
        seeded_contracts = []

        # We will assign machines [0..19] to the 20 contracts
        for c_idx in range(1, 21):
            contract_no = f"CNT-DUMMY-{c_idx:04d}"
            quote_no = f"QT-DUMMY-{c_idx:04d}"

            # Customer and Site assignment
            customer = seeded_customers[(c_idx - 1) % len(seeded_customers)]
            site_candidates = [s for s in seeded_sites if s.customer_id == customer.customer_code]
            site = site_candidates[0] if site_candidates else seeded_sites[0]

            # Primary equipment for this contract
            eq = seeded_equipment[c_idx - 1]
            rate_card = eq.rental_rates.filter(is_active=True).first()
            daily_rate = rate_card.daily_rate if rate_card else Decimal("35000.00")

            # Determine dates and lifecycle state
            if c_idx <= 5:
                # Completed historical contracts (30 to 75 days ago)
                start_d = today - timedelta(days=65 - (c_idx * 5))
                end_d = start_d + timedelta(days=20)
                c_status = RentalContract.Status.CLOSED
                billing_cycle = RentalContract.BillingCycle.ON_RETURN
                deposit_status = SecurityDeposit.Status.REFUNDED
            elif c_idx <= 13:
                # Active On-Rent contracts (started 10-15 days ago, ending in 15-30 days)
                start_d = today - timedelta(days=12 - (c_idx % 5))
                end_d = start_d + timedelta(days=35)
                c_status = RentalContract.Status.ON_RENT
                billing_cycle = RentalContract.BillingCycle.MONTHLY
                deposit_status = SecurityDeposit.Status.HELD
            elif c_idx <= 16:
                # Dispatched / In Transit (started 1-2 days ago, ending in 25 days)
                start_d = today - timedelta(days=1)
                end_d = start_d + timedelta(days=25)
                c_status = RentalContract.Status.DISPATCHED
                billing_cycle = RentalContract.BillingCycle.MONTHLY
                deposit_status = SecurityDeposit.Status.HELD
            else:
                # Converted / Pending Dispatch (starts in 3 days, ending in 20 days)
                start_d = today + timedelta(days=3)
                end_d = start_d + timedelta(days=20)
                c_status = RentalContract.Status.ACTIVE
                billing_cycle = RentalContract.BillingCycle.MONTHLY
                deposit_status = SecurityDeposit.Status.PENDING

            duration_days = (end_d - start_d).days + 1
            line_subtotal = (daily_rate * Decimal(duration_days)).quantize(Decimal("0.01"))
            transport_cost = Decimal("45000.00")
            tax_amt = ((line_subtotal + transport_cost) * Decimal("0.18")).quantize(Decimal("0.01"))
            grand_total = line_subtotal + transport_cost + tax_amt
            deposit_req = Decimal("200000.00")

            # 1. Originating Quotation
            quotation, _ = Quotation.objects.update_or_create(
                quotation_no=quote_no,
                defaults={
                    'customer': customer,
                    'project_site': site,
                    'start_date': start_d,
                    'end_date': end_d,
                    'rate_type': Quotation.RateType.DAILY,
                    'estimated_transport_cost': transport_cost,
                    'security_deposit_required': deposit_req,
                    'discount_percentage': Decimal("0.00"),
                    'subtotal_amount': line_subtotal,
                    'total_tax_amount': tax_amt,
                    'grand_total_amount': grand_total,
                    'status': Quotation.Status.CONVERTED,
                    'approved_by': admin_user,
                    'approval_date': timezone.now() - timedelta(days=40),
                }
            )

            # 2. Quotation Line Item
            QuotationItem.objects.update_or_create(
                quotation=quotation,
                equipment=eq,
                defaults={
                    'start_date': start_d,
                    'end_date': end_d,
                    'rate_type': Quotation.RateType.DAILY,
                    'rate_applied': daily_rate,
                    'subtotal_amount': line_subtotal,
                }
            )

            # 3. Rental Contract
            contract, _ = RentalContract.objects.update_or_create(
                contract_no=contract_no,
                defaults={
                    'quotation': quotation,
                    'customer': customer,
                    'project_site': site,
                    'equipment': eq,
                    'contract_start_date': start_d,
                    'contract_end_date': end_d,
                    'billing_cycle': billing_cycle,
                    'agreed_rate': daily_rate,
                    'deposit_paid': deposit_req if deposit_status != SecurityDeposit.Status.PENDING else Decimal("0.00"),
                    'status': c_status,
                }
            )
            seeded_contracts.append(contract)

            # 4. Rental Contract Item
            RentalContractItem.objects.update_or_create(
                contract=contract,
                equipment=eq,
                defaults={
                    'start_date': start_d,
                    'end_date': end_d,
                    'rate_applied': daily_rate,
                    'rate_type': Quotation.RateType.DAILY,
                    'subtotal_amount': line_subtotal,
                }
            )

            # 5. Update Equipment Live Operational Status
            if c_status in [RentalContract.Status.ON_RENT, RentalContract.Status.DISPATCHED]:
                eq.status = Equipment.Status.ON_RENT
                eq.save(update_fields=['status'])
            elif c_status == RentalContract.Status.ACTIVE:
                eq.status = Equipment.Status.RESERVED
                eq.save(update_fields=['status'])
            elif c_status == RentalContract.Status.CLOSED:
                eq.status = Equipment.Status.AVAILABLE
                eq.save(update_fields=['status'])

            # 6. Security Deposit Escrow Record
            SecurityDeposit.objects.update_or_create(
                deposit_id=f"DEP-DUMMY-{c_idx:04d}",
                defaults={
                    'contract': contract,
                    'customer': customer,
                    'deposit_amount': deposit_req,
                    'received_date': start_d - timedelta(days=2) if deposit_status != SecurityDeposit.Status.PENDING else None,
                    'refunded_amount': deposit_req if deposit_status == SecurityDeposit.Status.REFUNDED else Decimal("0.00"),
                    'deducted_amount': Decimal("0.00"),
                    'status': deposit_status,
                }
            )

            # 7. Logistics Handover: DispatchReturn Records
            if c_status in [RentalContract.Status.ON_RENT, RentalContract.Status.DISPATCHED, RentalContract.Status.CLOSED]:
                tz = timezone.get_current_timezone()
                disp_dt = timezone.make_aware(
                    timezone.datetime.combine(start_d, timezone.datetime.min.time().replace(hour=8, minute=30)),
                    tz
                )

                if c_status == RentalContract.Status.CLOSED:
                    ret_dt = timezone.make_aware(
                        timezone.datetime.combine(end_d, timezone.datetime.min.time().replace(hour=17, minute=0)),
                        tz
                    )
                    ret_hrs = eq.current_hour_meter
                    disp_hrs = max(Decimal("0.00"), eq.current_hour_meter - Decimal("160.00"))
                    ret_officer = workshop_mgr
                else:
                    ret_dt = None
                    ret_hrs = None
                    disp_hrs = eq.current_hour_meter
                    ret_officer = None

                DispatchReturn.objects.update_or_create(
                    transaction_id=f"TRX-DUMMY-{c_idx:04d}",
                    defaults={
                        'contract': contract,
                        'equipment': eq,
                        'dispatch_datetime': disp_dt,
                        'dispatch_hour_meter': disp_hrs,
                        'dispatch_fuel_level': Decimal("100.00"),
                        'dispatch_officer': rental_officer,
                        'dispatch_checklist': {
                            'tires_tracks': 'Good (80%+)',
                            'hydraulics': 'Clean, no leaks',
                            'fluids_engine': 'Optimal',
                            'safety_cabin': 'Certified',
                        },
                        'return_datetime': ret_dt,
                        'return_hour_meter': ret_hrs,
                        'return_fuel_level': Decimal("95.00") if ret_dt else None,
                        'return_officer': ret_officer,
                        'return_checklist': {
                            'tires_tracks': 'Standard wear',
                            'hydraulics': 'Sound',
                            'defects_found': 'None',
                        } if ret_dt else {},
                        'damage_reported': False,
                        'excess_hours_calculated': Decimal("0.00"),
                    }
                )

            # 8. Financial Billing & Settlement for Closed Contracts
            if c_status == RentalContract.Status.CLOSED:
                inv_no = f"INV-DUMMY-{c_idx:04d}"
                pay_id = f"PAY-DUMMY-{c_idx:04d}"

                invoice, _ = Invoice.objects.update_or_create(
                    invoice_no=inv_no,
                    defaults={
                        'contract': contract,
                        'customer': customer,
                        'invoice_date': end_d,
                        'due_date': end_d + timedelta(days=14),
                        'billing_period_start': start_d,
                        'billing_period_end': end_d,
                        'rental_subtotal': line_subtotal,
                        'excess_hours_charge': Decimal("0.00"),
                        'damage_charges': Decimal("0.00"),
                        'transport_charges': transport_cost,
                        'tax_amount': tax_amt,
                        'deposit_deducted': Decimal("0.00"),
                        'net_total_payable': grand_total,
                        'paid_amount': grand_total,
                        'status': Invoice.Status.PAID,
                    }
                )

                Payment.objects.update_or_create(
                    payment_id=pay_id,
                    defaults={
                        'invoice': invoice,
                        'customer': customer,
                        'amount': grand_total,
                        'payment_date': end_d + timedelta(days=5),
                        'payment_type': Payment.PaymentType.RENTAL_PAYMENT,
                        'payment_method': Payment.PaymentMethod.BANK_TRANSFER,
                        'reference_number': f"TXN-SLIP-{c_idx:04d}-BOC",
                        'recorded_by': accountant,
                        'notes': f"Full settlement for contract {contract.contract_no}",
                    }
                )

        # 9. Standalone Quotations for Dashboard Breadth
        standalone_quotes_def = [
            (Quotation.Status.DRAFT, 1, 0, 5, 20),
            (Quotation.Status.PENDING_INTERNAL_APPROVAL, 2, 1, 7, 25),
            (Quotation.Status.APPROVED_BY_MANAGEMENT, 3, 2, 10, 30),
            (Quotation.Status.REJECTED, 4, 3, -15, -5),
        ]

        for s_status, cust_idx, eq_idx, start_offset, end_offset in standalone_quotes_def:
            sq_no = f"QT-DUMMY-STANDALONE-{s_status[:4]}"
            cust = seeded_customers[cust_idx % len(seeded_customers)]
            site = seeded_sites[cust_idx % len(seeded_sites)]
            eq = seeded_equipment[eq_idx % len(seeded_equipment)]
            rate_card = eq.rental_rates.filter(is_active=True).first()
            d_rate = rate_card.daily_rate if rate_card else Decimal("30000.00")
            s_date = today + timedelta(days=start_offset)
            e_date = today + timedelta(days=end_offset)
            days = (e_date - s_date).days + 1
            subtot = (d_rate * Decimal(days)).quantize(Decimal("0.01"))
            tax = (subtot * Decimal("0.18")).quantize(Decimal("0.01"))

            sq, _ = Quotation.objects.update_or_create(
                quotation_no=sq_no,
                defaults={
                    'customer': cust,
                    'project_site': site,
                    'start_date': s_date,
                    'end_date': e_date,
                    'rate_type': Quotation.RateType.DAILY,
                    'estimated_transport_cost': Decimal("35000.00"),
                    'security_deposit_required': Decimal("150000.00"),
                    'discount_percentage': Decimal("0.00"),
                    'subtotal_amount': subtot,
                    'total_tax_amount': tax,
                    'grand_total_amount': subtot + Decimal("35000.00") + tax,
                    'status': s_status,
                    'approved_by': admin_user if s_status == Quotation.Status.APPROVED_BY_MANAGEMENT else None,
                    'approval_date': timezone.now() if s_status == Quotation.Status.APPROVED_BY_MANAGEMENT else None,
                }
            )

            QuotationItem.objects.update_or_create(
                quotation=sq,
                equipment=eq,
                defaults={
                    'start_date': s_date,
                    'end_date': e_date,
                    'rate_type': Quotation.RateType.DAILY,
                    'rate_applied': d_rate,
                    'subtotal_amount': subtot,
                }
            )

        self.stdout.write(self.style.SUCCESS(
            f"  [+] Seeded {len(seeded_contracts)} Rental Contracts across all lifecycle stages (5 Closed, 8 On-Rent, 3 Dispatched, 4 Active)."
        ))
        self.stdout.write(self.style.SUCCESS(
            "  [+] Seeded originating Quotations, QuotationItems, ContractItems, DispatchReturns, Invoices, Payments, and Escrow Deposits."
        ))

        self.stdout.write(self.style.NOTICE("\n================================================================="))
        self.stdout.write(self.style.SUCCESS("[SUCCESS] Realistic Phase 1 Test Data Generated Successfully!"))
        self.stdout.write(self.style.NOTICE("================================================================="))
