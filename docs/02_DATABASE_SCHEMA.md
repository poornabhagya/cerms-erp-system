# 02_DATABASE_SCHEMA

## 1. Overview and ORM Guidelines

This document defines the core database schema and relationships for the CERMS project. The database will be managed strictly through the Django ORM.

**Critical ORM Rules:**

- **Foreign Keys:** Always use `models.ForeignKey` for One-to-Many relationships.
- **Data Integrity:** Never use `on_delete=models.CASCADE` for critical business records (e.g., Customers, Equipment, Invoices). Always use `on_delete=models.PROTECT` or `models.SET_NULL` to prevent accidental data loss.
- **Base Model:** All models should ideally inherit from a `TimeStampedModel` that provides `created_at` and `updated_at` fields automatically.

## 2. Models by Django Application

The schema is distributed across the 5 core Django apps defined in the project architecture[cite: 4].

### App: `users` (Core Authentication)

- **User (Custom User Model)**
  - `id` (PK)
  - `username`, `password_hash`, `email`, `is_active`
  - `role` (Choices: Administrator, Management, Rental Officer, Operations Officer, Workshop Manager, Accountant, Storekeeper, Field Officer)

### App: `fleet` (Asset Management)

- **Category**
  - `id` (PK)
  - `name`, `description`
- **Equipment**
  - `asset_code` (PK - CharField/Slug)
  - `equipment_name`, `brand`, `model`, `serial_number`, `purchase_cost`
  - `category` (FK -> Category)
  - `hour_meter`, `status` (Choices: Available, On Rent, Reserved, Maintenance, Breakdown, Inactive)
- **RentalRate**
  - `rate_id` (PK)
  - `equipment` (FK -> Equipment)
  - `hourly_rate`, `daily_rate`, `weekly_rate`, `monthly_rate`, `overtime_rate`, `minimum_rental_hours`
- **SparePart**
  - `part_id` (PK)
  - `part_name`, `category`, `quantity_in_stock`, `unit_cost`
- **TransportRequest** (Transport_Log)
  - `transport_id` (PK)
  - `equipment` (FK -> Equipment)
  - `from_location`, `to_location`, `transporter_name`, `transport_cost`, `status`
  - _(Note: Will also have FKs to Customer and ProjectSite from the rentals app)_

### App: `rentals` (Rental Lifecycle)

- **Customer**
  - `customer_code` (PK)
  - `company_name`, `contact_person`, `mobile`, `email`, `vat_no`, `credit_limit`, `status`
- **ProjectSite**
  - `project_code` (PK)
  - `customer` (FK -> Customer)
  - `project_name`, `site_address`, `gps_location`, `status`
- **Quotation**
  - `quotation_no` (PK)
  - `customer` (FK -> Customer), `project` (FK -> ProjectSite), `equipment` (FK -> fleet.Equipment)
  - `rental_period`, `total_amount`, `security_deposit`, `discount`, `status` (Pending, Approved)
- **RentalContract**
  - `contract_no` (PK)
  - `quotation` (OneToOne/FK -> Quotation), `customer` (FK -> Customer), `equipment` (FK -> fleet.Equipment)
  - `billing_cycle`, `deposit_amount`, `status` (Active, Completed)
- **DispatchReturn** (Consolidated logistics handling)
  - `transaction_id` (PK)
  - `contract` (FK -> RentalContract), `equipment` (FK -> fleet.Equipment)
  - `dispatch_date`, `dispatch_hour_meter`, `dispatch_fuel_level`
  - `return_date`, `return_hour_meter`, `return_fuel_level`, `damage_status`

### App: `operations` (Field & Maintenance)

- **Operator**
  - `operator_id` (PK)
  - `name`, `license_no`, `expiry_date`, `status`
- **MaintenanceJob**
  - `maintenance_id` (PK)
  - `equipment` (FK -> fleet.Equipment)
  - `maintenance_type` (Choices: Preventive, Breakdown), `priority`
  - `cost`, `technician_name`, `status`
- **FuelLog**
  - `fuel_log_id` (PK)
  - `equipment` (FK -> fleet.Equipment)
  - `date`, `quantity`, `fuel_type`, `rate`, `hour_meter_at_fueling`, `total_cost`

### App: `finance` (Billing & Payments)

- **Invoice**
  - `invoice_no` (PK)
  - `contract` (FK -> rentals.RentalContract), `customer` (FK -> rentals.Customer)
  - `amount`, `due_date`, `status` (Choices: Pending, Paid, Overdue)
- **Payment**
  - `payment_id` (PK)
  - `invoice` (FK -> Invoice), `customer` (FK -> rentals.Customer)
  - `paid_amount`, `payment_date`, `payment_method`

## 3. Relational Mapping Considerations

- **Cross-App Foreign Keys:** Django handles cross-app relationships easily (e.g., `models.ForeignKey('rentals.Customer', on_delete=models.PROTECT)`). Ensure circular imports are avoided by using string references for models in other apps.
