import json
import os
from django.db import migrations
from django.conf import settings


def apply_group_permissions(apps, schema_editor):
    """
    Populates all 8 core RBAC groups with granular model permissions from
    users/fixtures/core_roles.json and assigns all existing users to their
    corresponding groups based on user.role.
    """
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    User = apps.get_model('users', 'User')

    # Ensure all content types and permissions are created
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions
    for app_config in global_apps.get_app_configs():
        try:
            create_permissions(app_config, verbosity=0)
        except Exception:
            pass

    # Read the core_roles fixture
    fixture_path = os.path.join(settings.BASE_DIR, 'users', 'fixtures', 'core_roles.json')
    if os.path.exists(fixture_path):
        with open(fixture_path, 'r', encoding='utf-8') as f:
            roles_data = json.load(f)

        for item in roles_data:
            fields = item.get('fields', {})
            group_name = fields.get('name')
            perm_triples = fields.get('permissions', [])

            group, _ = Group.objects.get_or_create(name=group_name)

            perm_objs = []
            for triple in perm_triples:
                if len(triple) == 3:
                    codename, app_label, model = triple
                    try:
                        p = Permission.objects.get(
                            codename=codename,
                            content_type__app_label=app_label,
                            content_type__model=model
                        )
                        perm_objs.append(p)
                    except Permission.DoesNotExist:
                        pass

            if perm_objs:
                group.permissions.set(perm_objs)

    # Sync all existing users to their corresponding role group
    ROLE_TO_GROUP = {
        'ADMINISTRATOR': 'Administrator',
        'MANAGEMENT': 'Management',
        'RENTAL_OFFICER': 'Rental Officer',
        'OPERATIONS_OFFICER': 'Operations Officer',
        'WORKSHOP_MANAGER': 'Workshop Manager',
        'ACCOUNTANT': 'Accountant',
        'STOREKEEPER': 'Storekeeper',
        'FIELD_OFFICER': 'Field Officer',
    }

    for user in User.objects.all():
        group_name = ROLE_TO_GROUP.get(user.role)
        if group_name:
            try:
                g = Group.objects.get(name=group_name)
                user.groups.add(g)
            except Group.DoesNotExist:
                pass


def rollback_group_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for g in Group.objects.all():
        g.permissions.clear()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('fleet', '0002_equipment_has_minor_damage_and_more'),
        ('rentals', '0005_dispatchreturn_has_minor_damage_and_more'),
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(apply_group_permissions, reverse_code=rollback_group_permissions),
    ]
