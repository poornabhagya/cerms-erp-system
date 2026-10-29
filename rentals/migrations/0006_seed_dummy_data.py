"""
Data migration to automatically populate the realistic Phase 1 mock test data
(10 customers, 50 equipment assets across 8 categories, 20 rental contracts)
on the database upon deployment.
"""

import sys
from django.db import migrations


def is_running_test(schema_editor):
    db_name = str(schema_editor.connection.settings_dict.get('NAME') or '')
    if 'test' in sys.argv or 'memorydb' in db_name or db_name.startswith('test_') or ':memory:' in db_name:
        return True
    return False


def seed_dummy_data_forward(apps, schema_editor):
    # Skip during unit test execution to maintain isolated test fixture assertions
    if is_running_test(schema_editor):
        return

    from django.core.management import call_command
    try:
        call_command('seed_dummy_data', force=True)
    except Exception as e:
        print(f"Notice during dummy data seeding: {e}")


def seed_dummy_data_reverse(apps, schema_editor):
    if is_running_test(schema_editor):
        return

    from django.core.management import call_command
    try:
        call_command('seed_dummy_data', clear=True, force=True)
    except Exception as e:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0005_dispatchreturn_has_minor_damage_and_more'),
        ('finance', '0001_initial'),
        ('fleet', '0002_equipment_has_minor_damage_and_more'),
        ('users', '0002_populate_rbac_group_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_dummy_data_forward, reverse_code=seed_dummy_data_reverse),
    ]
