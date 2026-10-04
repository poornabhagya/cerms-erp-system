# 17_MIGRATIONS_AND_DATA_INTEGRITY

## 1. The Importance of Data Integrity

In a monolithic ERP system like CERMS, data loss is catastrophic. AI-assisted development tools (like Antigravity) often attempt to resolve database conflicts by suggesting destructive operations (e.g., dropping columns, deleting old migration files, or using `CASCADE` deletes). This document establishes strict rules to prevent accidental data destruction.

## 2. Foreign Key Deletion Rules (No CASCADE)

To preserve historical records and audit trails (e.g., keeping an invoice even if the customer is marked inactive), **`on_delete=models.CASCADE` is strictly prohibited** for all critical business records[cite: 16].

When defining relationships across the 5 core apps (`fleet`, `rentals`, `finance`, `operations`, `intelligence`), you must use one of the following safe alternatives[cite: 16]:

- **`models.PROTECT`**: Use this when a record should never be deleted if related data exists.
  - _Example:_ You cannot delete an `Equipment` record if it has an associated `FuelLog` or `RentalContract`.
  - `customer = models.ForeignKey('rentals.Customer', on_delete=models.PROTECT)`
- **`models.SET_NULL`**: Use this when a relationship is optional, and the child record should survive even if the parent is deleted. You must also set `null=True`.
  - _Example:_ If a `MaintenanceJob` is deleted, the `Equipment` record should still exist.
  - `assigned_operator = models.ForeignKey('operations.Operator', on_delete=models.SET_NULL, null=True)`

## 3. Safe Migration Workflow

When altering database models, follow this exact sequence to ensure migrations are applied safely:

1.  **Never delete existing migration files** in the `migrations/` folder. They are a permanent historical record.
2.  If modifying an existing column (e.g., changing a `CharField` to an `IntegerField`), provide a default value or allow nulls temporarily to prevent `IntegrityError` on existing rows.
3.  Execute migrations safely:
    ```bash
    python manage.py makemigrations
    python manage.py makemigrations --dry-run  # Optional: Review the SQL operations
    python manage.py migrate
    ```

## 4. Handling Legacy Data and Destructive Changes

If a feature requires removing a column or a table:

- **Do NOT** delete the field from the model immediately.
- **DO** mark the field as `null=True, blank=True` and stop using it in the code.
- If the table must be dropped entirely, a custom data migration must be written first to back up or transfer the existing data before applying the structural `RemoveField` migration.
