# 03_ROLES_AND_PERMISSIONS

## 1. Overview

The CERMS platform enforces strict Role-Based Access Control (RBAC) to ensure users can only view or modify data relevant to their specific job functions[cite: 1]. This document defines the exact permission levels for the 8 core roles within the system[cite: 26].

## 2. Core User Roles & Access Levels

### 1. Administrator

- **Main Access:** Full system access[cite: 1].
- **Permissions:** Can Create, Read, Update, and Delete (CRUD) records across all modules[cite: 1]. Manages system settings, user creation, and role assignment.

### 2. Management

- **Main Access:** Dashboard, approvals, reports, and financial overview[cite: 1].
- **Permissions:** Read-only access to all operational data. Has specific execution rights for higher-level approvals (e.g., approving high-value quotations or maintenance costs)[cite: 1].

### 3. Rental Officer

- **Main Access:** Customers, quotations, contracts, and rentals[cite: 1].
- **Permissions:** Create, Read, and Update (CRU) access to the `rentals` app (Customers, Quotations, Contracts). Cannot delete records[cite: 1].

### 4. Operations Officer

- **Main Access:** Dispatch, returns, and movement[cite: 1].
- **Permissions:** Create, Read, and Update (CRU) access to the `DispatchReturn` processes and movement logs[cite: 1]. Can view active contracts but cannot modify financial terms.

### 5. Workshop Manager

- **Main Access:** Maintenance, breakdowns, and parts[cite: 1].
- **Permissions:** Create, Read, and Update (CRU) access to the `operations` app (Maintenance Jobs, Breakdowns) and `fleet` app (Spare Parts)[cite: 1].

### 6. Accountant

- **Main Access:** Invoices, payments, and receivables[cite: 1].
- **Permissions:** Create, Read, and Update (CRU) access to the `finance` app (Invoices, Payments, Deposits)[cite: 1]. Can view rental contracts to generate invoices but cannot modify the contract terms.

### 7. Storekeeper

- **Main Access:** Spare parts and inventory[cite: 1].
- **Permissions:** Create, Read, and Update (CRU) access restricted to the `SparePart` model and inventory logs within the `fleet` app[cite: 1, 26].

### 8. Field Officer

- **Main Access:** Inspection, hour meter, photos, and status updates[cite: 1].
- **Permissions:** Create and Update (CU) access specifically tailored for mobile-responsive field operations[cite: 1]. Can input hour meter readings, fuel logs, and dispatch/return checklists.

## 3. Implementation Guidelines

- **Django Groups:** These 8 roles should be implemented using Django's native `Group` model.
- **Custom User Model:** The custom `User` model should include a `role` field that maps directly to these groups for easier querying (e.g., `if user.role == 'Rental Officer':`)[cite: 26].
- **View Protection:** Every Django View or API Endpoint must explicitly check permissions using decorators (e.g., `@permission_required`) or Mixins (e.g., `PermissionRequiredMixin`) before executing logic.
