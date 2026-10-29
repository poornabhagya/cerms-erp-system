"""
Data migration to backfill created_by for all pre-existing records across
users, fleet, rentals, and finance models to ensure full auditability.
"""

from django.db import migrations


def backfill_created_by_forward(apps, schema_editor):
    User = apps.get_model('users', 'User')

    # Find the primary administrative user
    admin_user = (
        User.objects.filter(is_superuser=True).first()
        or User.objects.filter(role='ADMINISTRATOR').first()
        or User.objects.first()
    )

    if not admin_user:
        return

    # Backfill User records (excluding the admin itself)
    User.objects.filter(created_by__isnull=True).exclude(pk=admin_user.pk).update(created_by=admin_user)

    target_models = [
        ('fleet', 'Category'),
        ('fleet', 'Equipment'),
        ('fleet', 'RentalRate'),
        ('rentals', 'Customer'),
        ('rentals', 'ProjectSite'),
        ('rentals', 'Quotation'),
        ('rentals', 'QuotationItem'),
        ('rentals', 'RentalContract'),
        ('rentals', 'RentalContractItem'),
        ('rentals', 'DispatchReturn'),
        ('finance', 'Invoice'),
        ('finance', 'Payment'),
        ('finance', 'SecurityDeposit'),
    ]

    for app_label, model_name in target_models:
        try:
            Model = apps.get_model(app_label, model_name)
            Model.objects.filter(created_by__isnull=True).update(created_by=admin_user)
        except Exception as e:
            print(f"Notice during {app_label}.{model_name} created_by backfill: {e}")


def backfill_created_by_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_created_by'),
        ('fleet', '0003_category_created_by_equipment_created_by_and_more'),
        ('rentals', '0007_customer_created_by_dispatchreturn_created_by_and_more'),
        ('finance', '0002_invoice_created_by_payment_created_by_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_created_by_forward, reverse_code=backfill_created_by_reverse),
    ]
