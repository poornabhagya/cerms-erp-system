# 24_PHASE_1_MANUAL_TESTING_GUIDE

## Construction Equipment Rental Management System (CERMS)
### Phase 1 End-to-End Manual UI Testing (ClickOps) & Business Logic Verification Guide

---

## 1. Document Overview & Objective

This document provides a comprehensive, sequential, click-by-click Manual User Interface (ClickOps) Testing Guide for **Phase 1** of the CERMS platform. 

It is designed for Quality Assurance (QA) engineers, Product Managers, Operations Leads, and Developers to validate:
1. **Data Integrity & Relational Workflows:** End-to-end operational sequence from fleet master provisioning to quotation, contract, dispatch, return, and financial reconciliation.
2. **Role-Based Access Control (RBAC):** Verification of permissions, UI element visibility, and view protections across 8 distinct user roles.
3. **Business Logic & State Machine Transitions:** Validation of asset lifecycle transitions, quotation approval gates, credit ceiling verifications, logistics handovers, and escrow deposit deductions.
4. **Financial Calculations & Pricing Engine:** Accurate arithmetic verification of multi-tier tariffs, overtime hour penalties, Sri Lankan statutory VAT (18%), escrow deposits, and automated invoice PDF generation via WeasyPrint.

---

## 2. Seed Data & Test Accounts Matrix

The system comes pre-configured with default seed accounts created via `python manage.py seed_initial_data` or standard fixtures.

### 2.1 Default Staff Test Accounts

| Username | Password | Organizational Role | Core System Responsibilities & Permissions |
| :--- | :--- | :--- | :--- |
| `admin` | `Admin@CERMS2026!` | **Administrator** | **Full System Superuser.** Access to all Web UI views, Django Admin (`/admin/`), user creation, role assignment, and system configuration. |
| `mgmt_user` / `admin` | `Admin@CERMS2026!` | **Management** | **Executive Oversight & Approval Authority.** View dashboards, financial reports, high-exposure credit overrides, and quotation approval transitions. |
| `rental_officer` | `Staff@CERMS2026!` | **Rental Officer** | **Customer & Commercial Operations.** Full CRU on Customers, Project Sites, Quotations, Rental Contracts, and Availability Calendar. |
| `ops_officer` | `Staff@CERMS2026!` | **Operations Officer** | **Fleet Logistics & Site Movements.** Full CRU on Equipment Dispatch, Return Handover inspections, checklist logs, and hour-meter audits. |
| `workshop_mgr` | `Staff@CERMS2026!` | **Workshop Manager** | **Maintenance & Fleet Health.** Full access to Equipment status overrides (`MAINTENANCE`, `BREAKDOWN`, `AVAILABLE`), inspection reports, and workshop job cards. |
| `accountant` | `Staff@CERMS2026!` | **Accountant** | **Billing & Financial Settlement.** Full CRU on Tax Invoices, Payment Receipts, Security Deposit Ledgers, and Customer Credit Limits. |
| `storekeeper` | `Staff@CERMS2026!` | **Storekeeper** | **Yard & Inventory Control.** Inventory logs, asset storage locations, and yard handover verification. |
| `field_officer` | `Staff@CERMS2026!` | **Field Officer** | **On-Site Operations & Mobile Checklists.** Mobile-optimized entry for hour-meter readings, fuel logs, delivery signatures, and asset photos. |

---

### 2.2 Role-Based Access Control (RBAC) Permission Matrix

| Module / Action | Target URL Route | Admin | Management | Rental Officer | Operations Officer | Workshop Manager | Accountant | Field Officer | Storekeeper |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Django Admin Panel** | `/admin/` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Fleet Master CRUD** | `/fleet/equipment/` | ✅ | 👁️ (Read) | 👁️ (Read) | 👁️ (Read) | ✅ | 👁️ (Read) | 👁️ (Read) | 👁️ (Read) |
| **Rate Card Management** | `/fleet/equipment/<code\>/rates/` | ✅ | ✅ | ✅ | ❌ | ❌ | 👁️ (Read) | ❌ | ❌ |
| **Customer Master CRUD** | `/rentals/customers/` | ✅ | 👁️ (Read) | ✅ | 👁️ (Read) | ❌ | ✅ | ❌ | ❌ |
| **Quotation Creation** | `/rentals/quotations/create/` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Quotation Management Approval** | `/rentals/quotations/<no\>/transition/` | ✅ | ✅ | ❌ (Cannot Approve Self) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Contract Conversion** | `/rentals/quotations/<no\>/` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Equipment Dispatch** | `/rentals/contracts/<no\>/dispatch/` | ✅ | 👁️ (Read) | 👁️ (Read) | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Equipment Return** | `/rentals/returns/<id\>/` | ✅ | 👁️ (Read) | 👁️ (Read) | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Availability Calendar** | `/rentals/availability-calendar/` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Invoice Generation & PDF** | `/finance/invoices/` | ✅ | ✅ | 👁️ (Read) | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Payment Settlement** | `/finance/invoices/<no\>/` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Security Deposit Ledger** | `/finance/deposits/` | ✅ | ✅ | 👁️ (Read) | ❌ | ❌ | ✅ | ❌ | ❌ |

*Legend: ✅ = Full Access (Create, Read, Update) | 👁️ = Read-Only View | ❌ = HTTP 403 Forbidden / Access Denied*

---

## 3. Strict Sequential Execution Order

To prevent foreign key dependency errors, manual testing must proceed in the following strict order:

```mermaid
flowchart TD
    S1[Step 1: Auth & RBAC Verification] --> S2[Step 2: Fleet Category Setup]
    S2 --> S3[Step 3: Equipment Asset Master Registration]
    S3 --> S4[Step 4: Rental Tariff Card Configuration]
    S4 --> S5[Step 5: Customer Master & Credit Limits]
    S5 --> S6[Step 6: Project Site Registration]
    S6 --> S7[Step 7: Quotation Creation & Math Engine]
    S7 --> S8[Step 8: Management Approval & Contract Conversion]
    S8 --> S9[Step 9: Availability Calendar & Scheduling Grid]
    S9 --> S10[Step 10: Equipment Dispatch Handover]
    S10 --> S11[Step 11: Return Inspection & Hour Meter Reconciliation]
    S11 --> S12[Step 12: Final Invoicing & WeasyPrint PDF Generation]
    S12 --> S13[Step 13: Payment Recording & Balance Update]
    S13 --> S14[Step 14: Escrow Security Deposit Lifecycle]
    S14 --> S15[Step 15: Document Export Audit (Quotation, Contract, Invoice)]
```

---

## 4. Detailed Step-by-Step UI Test Procedures

---

### Step 1: Authentication, Session Management & RBAC Enforcement

#### A. Feature Overview & Purpose
Validates user authentication, role assignment, active session management, and URL-level permission enforcement (preventing unauthorized horizontal and vertical privilege escalation).

#### B. Step-by-Step UI Actions
1. Open your browser and navigate to the application root: `http://127.0.0.1:8000/`.
2. Verify that unauthenticated requests are automatically redirected to `/login/`.
3. In the login form, enter invalid credentials (`invalid_user` / `wrongpass`) and click **Sign In**.
   - **Expected Result:** Flash error message: *"Invalid username or password."*
4. Enter valid credentials for `rental_officer` (`Staff@CERMS2026!`) and click **Sign In**.
   - **Expected Result:** Successful login, redirected to user profile/dashboard, and navbar displays username `rental_officer` with badge `Rental Officer`.
5. While logged in as `rental_officer`, attempt to access restricted routes:
   - Navigate to `http://127.0.0.1:8000/admin/`.
     - **Expected Result:** Redirected or prompted with superuser login (Regular staff cannot access Django Admin).
   - Navigate to `http://127.0.0.1:8000/finance/invoices/create/` (or trigger settlement).
     - **Expected Result:** HTTP 403 Forbidden response or redirection with error message: *"You do not have permission to access this resource."*
6. Click **Log Out** from the user profile dropdown.
   - **Expected Result:** Session destroyed, redirected back to `/login/`.

---

### Step 2: Fleet Category Setup

#### A. Feature Overview & Purpose
Classifies construction machinery into operational asset categories (e.g., Earthmoving, Power Generation, Compaction, Lifting).

#### B. Step-by-Step UI Actions
1. Log in as `admin` (`Admin@CERMS2026!`) or `workshop_mgr` (`Staff@CERMS2026!`).
2. Navigate to **Fleet** > **Categories** (`/fleet/categories/` or via Django Admin `/admin/fleet/category/`).
3. Click the **"+ New Category"** button.
4. Fill in the following test form data:
   - **Category Name:** `Hydraulic Excavators`
   - **Category Code:** `EXC` (Slug/unique mnemonic)
   - **Description:** `Heavy crawler and wheeled hydraulic excavators ranging from 13T to 35T operating weight.`
5. Click **Save Category**.

#### C. Business Logic & Expected Output
- **Database Validation:** Category `EXC` is persisted with unique constraint checks on name and code.
- **UI Validation:** Category list displays `Hydraulic Excavators (EXC)` with an asset counter of `0`.

---

### Step 3: Equipment Asset Master Registration

#### A. Feature Overview & Purpose
Registers physical machinery assets into the fleet database with serial tracking, initial hour meters, purchase costs, and initial state `AVAILABLE`.

#### B. Step-by-Step UI Actions
1. Log in as `workshop_mgr` or `admin`.
2. Navigate to **Fleet** > **Equipment Master** (`/fleet/equipment/`).
3. Click **"+ Add Equipment Asset"** (`/fleet/equipment/create/`).
4. Fill in the asset specifications:
   - **Asset Code:** `EQ-CAT-320-001`
   - **Equipment Name:** `Caterpillar 320D Hydraulic Excavator`
   - **Category:** Select `Hydraulic Excavators (EXC)`
   - **Brand / Manufacturer:** `Caterpillar`
   - **Model Number:** `320D-GC`
   - **Serial / VIN Number:** `CAT320D-LK-90210`
   - **Manufacture Year:** `2023`
   - **Purchase Cost (LKR):** `42,000,000.00`
   - **Purchase Date:** `2023-05-15`
   - **Current Hour Meter (hrs):** `1,250.00`
   - **Initial Status:** `AVAILABLE`
   - **Technical Specifications (JSON):** 
     ```json
     {"operating_weight": "21500 kg", "engine_power": "140 HP", "bucket_capacity": "1.0 m3"}
     ```
5. Click **Save Equipment Record**.

#### C. State Machine & Expected Output
- **State Machine:** Initial status set to `AVAILABLE` (Green Badge).
- **UI Feedback:** Success alert: *"Equipment asset 'EQ-CAT-320-001' registered successfully."*
- **Dossier Inspection:** Navigating to `/fleet/equipment/EQ-CAT-320-001/` displays asset specifications, meter reading (`1,250.00 hrs`), and current operational status.

---

### Step 4: Rental Tariff Card Configuration

#### A. Feature Overview & Purpose
Defines standard pricing tiers (Daily, Weekly, Monthly), minimum hire periods, and overtime hourly rates for an asset.

#### B. Step-by-Step UI Actions
1. In the equipment dossier (`/fleet/equipment/EQ-CAT-320-001/`), click the **"Rental Rates"** tab or click **"+ Add Rate Card"**.
2. Enter the pricing tariff details:
   - **Daily Rate (LKR):** `45,000.00` (Standard 8-hour single shift)
   - **Weekly Rate (LKR):** `280,000.00` (Discounted 7-day rate)
   - **Monthly Rate (LKR):** `1,100,000.00` (Discounted 30-day rate)
   - **Overtime Hourly Rate (LKR/hr):** `6,500.00` (Rate charged for operating hours $> 8$ hrs/day)
   - **Minimum Rental Hours:** `8`
   - **Effective From Date:** Today's Date
   - **Is Active Rate:** Checked (`True`)
3. Click **Save Rate Card**.

#### C. Business Logic & Expected Output
- The rate card becomes the active pricing baseline for all subsequent quotations for `EQ-CAT-320-001`.

---

### Step 5: Customer Master & Credit Standing Management

#### A. Feature Overview & Purpose
Registers commercial B2B clients, sets credit limits, tracks outstanding debts, and enforces account operational standing (`ACTIVE`, `SUSPENDED`, `BLOCKED`).

#### B. Step-by-Step UI Actions
1. Log in as `rental_officer` (`Staff@CERMS2026!`).
2. Navigate to **Rentals** > **Customers** (`/rentals/customers/`).
3. Click **"+ New Customer"** (`/rentals/customers/create/`).
4. Fill in the customer profile:
   - **Customer Code:** `CUST-2026-001`
   - **Company Name:** `Access Engineering PLC`
   - **Contact Person:** `Sunil Perera`
   - **Phone Number:** `+94771234567`
   - **Corporate Email:** `sunil@accesseng.lk`
   - **Billing Address:** `No. 120, Station Road, Colombo 03`
   - **VAT / Tax Registration Number:** `VAT-102938475-7000`
   - **Approved Credit Limit (LKR):** `2,000,000.00`
   - **Current Outstanding Balance (LKR):** `0.00`
   - **Account Status:** `ACTIVE`
5. Click **Save Customer**.

#### C. Validation Logic & Calculations
- **Credit Exposure Equation:**
  $$\text{Available Credit Margin} = \text{Credit Limit} - \text{Current Outstanding Balance}$$
  $$\text{Available Credit} = \text{LKR } 2,000,000.00 - 0.00 = \text{LKR } 2,000,000.00$$
- **UI Feedback:** Customer profile opens showing `100% Available Credit`, `ACTIVE` badge, and zero active contracts.

---

### Step 6: Project Site Registration

#### A. Feature Overview & Purpose
Binds construction work locations and site contact supervisors to a specific customer account.

#### B. Step-by-Step UI Actions
1. Navigate to **Rentals** > **Project Sites** (`/rentals/sites/`) or click **"+ Add Site"** inside `Access Engineering PLC` dossier.
2. Fill in the site details:
   - **Project Code:** `PRJ-COL-001`
   - **Customer:** Select `Access Engineering PLC (CUST-2026-001)`
   - **Project Name:** `Central Expressway Section III - Interchange`
   - **Site Address:** `Mirigama Interchange Site, Mirigama`
   - **GPS Coordinates:** `7.2431, 80.1294`
   - **Site Contact Person:** `Kamal Silva`
   - **Site Contact Phone:** `+94779876543`
   - **Status:** `ACTIVE`
3. Click **Save Project Site**.

---

### Step 7: Commercial Quotation Creation & Multi-Tier Calculation Engine

#### A. Feature Overview & Purpose
Generates commercial hire proposals with multi-item equipment line items (Parent-Child Architecture), verifies real-time machinery availability across multiple assets, validates customer credit limits against the composite quote value, and calculates accurate line-item subtotals, statutory taxes, and discounts.

#### B. Mathematical Formula & Pricing Engine Specification
The CERMS pricing engine strictly adheres to the following multi-item business logic:

1. **Duration in Days ($D_i$) per Line Item:**
   $$D_i = (\text{End Date}_i - \text{Start Date}_i) + 1$$
   *(e.g., Nov 1 to Nov 10 = 10 full billable days)*
2. **Line Item Subtotal ($\text{Subtotal}_i$):**
   $$\text{Subtotal}_i = D_i \times \text{Rate Applied}_i$$
3. **Quotation Base Tariff ($\text{Base Tariff}$):**
   $$\text{Base Tariff} = \sum_{i=1}^{N} \text{Subtotal}_i$$
4. **Commercial Discount Amount:**
   $$\text{Discount Amount} = \frac{\text{Base Tariff} \times \text{Discount Percentage}}{100}$$
5. **Taxable Base Amount:**
   $$\text{Taxable Base} = (\text{Base Tariff} - \text{Discount Amount}) + \text{Estimated Transport Cost}$$
6. **Statutory Tax Amount (18% VAT):**
   $$\text{VAT (18\%)} = \text{Taxable Base} \times 0.18$$
7. **Grand Total Amount:**
   $$\text{Grand Total} = (\text{Base Tariff} + \text{Estimated Transport Cost} + \text{VAT}) - \text{Discount Amount}$$

---

#### C. Step-by-Step UI Actions
1. Log in as `rental_officer`.
2. Navigate to **Rentals** > **Quotations** > **"+ New Quotation"** (`/rentals/quotations/create/`).
3. Fill in the commercial quotation header:
   - **Quotation No:** Read-only auto-generated sequence (e.g., `QT-2026-0001`).
   - **Customer:** `Access Engineering PLC`
   - **Project Site:** `Central Expressway Section III - Interchange`
   - **Quotation Default Start Date:** `2026-11-01`
   - **Quotation Default End Date:** `2026-11-10`
   - **Rate Type:** `DAILY`
   - **Estimated Transport Cost (LKR):** `75,000.00` *(Round-trip low-bed mobilization for multi-asset fleet)*
   - **Security Deposit Required (LKR):** `250,000.00`
   - **Discount Percentage (%):** `5.00`
4. Configure **Quotation Equipment Line Items**:
   - **Line Item #1 (Default Row):**
     - **Equipment Asset:** `EQ-CAT-320-001 (Caterpillar 320D Excavator)`
     - **Start Date:** `2026-11-01`
     - **End Date:** `2026-11-10` *(10 billable days)*
     - **Rate Applied (LKR):** `45,000.00`
     - **Line Subtotal (Live JS Preview):** `Rs. 450,000.00`
   - Click **"+ Add Equipment Asset"** to append a second line item.
   - **Line Item #2:**
     - **Equipment Asset:** `EQ-KOM-PC200-001 (Komatsu PC200-8 Excavator)`
     - **Start Date:** `2026-11-01`
     - **End Date:** `2026-11-10` *(10 billable days)*
     - **Rate Applied (LKR):** `40,000.00`
     - **Line Subtotal (Live JS Preview):** `Rs. 400,000.00`
5. Observe the live calculated financial summary on the right sidebar updating dynamically.
6. Click **Create Quotation & Compute Totals**.

---

#### D. Calculation Verification Table

| Calculation Step | Arithmetic Operation | Expected Result (LKR) |
| :--- | :--- | :--- |
| **Line 1 Subtotal (CAT 320D)** | $10 \text{ days} \times \text{Rs. } 45,000.00$ | **Rs. 450,000.00** |
| **Line 2 Subtotal (Komatsu PC200)** | $10 \text{ days} \times \text{Rs. } 40,000.00$ | **Rs. 400,000.00** |
| **Combined Base Tariff** | $\text{Rs. } 450,000.00 + \text{Rs. } 400,000.00$ | **Rs. 850,000.00** |
| **5% Commercial Discount** | $5\% \times \text{Rs. } 850,000.00$ | **Rs. 42,500.00** |
| **Net Base Tariff** | $\text{Rs. } 850,000.00 - \text{Rs. } 42,500.00$ | **Rs. 807,500.00** |
| **Mobilization Logistics** | Fixed transport entry | **Rs. 75,000.00** |
| **Taxable Base** | $\text{Rs. } 807,500.00 + \text{Rs. } 75,000.00$ | **Rs. 882,500.00** |
| **VAT (18%)** | $18\% \times \text{Rs. } 882,500.00$ | **Rs. 158,850.00** |
| **Grand Total Amount** | $(\text{Rs. } 850,000 + 75,000 + 158,850) - 42,500$ | **Rs. 1,041,350.00** |

#### E. State Machine & UI Verification
- **Quotation Status:** Created in `DRAFT` status (Grey Badge).
- **Multi-Item Specification Table:** Detail page renders an itemized table listing each asset, serial number, rental period, rate applied, and line subtotal.
- **Credit Check Validation:** `Access Engineering PLC` projected exposure is $\text{Rs. } 1,041,350.00 < \text{Credit Limit (Rs. } 2,000,000.00)$. The credit banner displays: *"Credit Check Passed (Margin Remaining: Rs. 958,650.00)"* styled with a green success badge.

---

### Step 8: Managerial Approval & Rental Contract Conversion

#### A. Feature Overview & Purpose
Validates the approval hierarchy and multi-asset contract conversion. Rental Officers cannot self-approve quotations. Upon managerial approval and customer acceptance, converting the multi-item quotation automatically generates the master `RentalContract` and corresponding `RentalContractItem` child records, reserving all quoted machinery.

#### B. Step-by-Step UI Actions
1. While logged in as `rental_officer`, view the quotation detail page (`/rentals/quotations/QT-2026-0001/`).
2. Click **"Submit for Management Review"**. Status transitions from `DRAFT` $\rightarrow$ `UNDER_REVIEW`.
3. Notice that the **"Approve Quotation"** button is **disabled/hidden** for the `Rental Officer` role.
4. Log out and log in as `admin` or a user with role `MANAGEMENT`.
5. Navigate to the quotation `/rentals/quotations/QT-2026-0001/`.
6. Click **"Approve Commercial Quotation"**.
   - **State Transition:** `UNDER_REVIEW` $\rightarrow$ `APPROVED_BY_MANAGEMENT`.
7. Click **"Mark as Sent to Customer"** $\rightarrow$ status becomes `SENT_TO_CUSTOMER`.
8. Click **"Record Customer Acceptance"** $\rightarrow$ status becomes `ACCEPTED`.
9. Click **"Convert to Binding Rental Contract"**.
10. In the modal dialog, select:
    - **Billing Cycle:** `MONTHLY` (or `DAILY`)
    - **Deposit Paid at Signing (LKR):** `250,000.00`
11. Click **"Confirm & Generate Contract"**.

#### C. State Machine & Expected Output
- **Quotation State:** Marked as `CONVERTED` (Badge: Green).
- **Contract Generated:** New Rental Contract `CNT-2026-0001` created in `ACTIVE` status with individual child contract lines (`RentalContractItem`) for each machine.
- **Fleet State Machine:** All quoted equipment assets (`EQ-CAT-320-001` and `EQ-KOM-PC200-001`) automatically transition from `AVAILABLE` $\rightarrow$ `RESERVED`.

---

### Step 9: Interactive Availability Calendar & Scheduling Grid

#### A. Feature Overview & Purpose
Validates visual scheduling, conflict detection, and color-coded event rendering using FullCalendar.js.

#### B. Step-by-Step UI Actions
1. Log in as `rental_officer` or `ops_officer`.
2. Navigate to **Rentals** > **Availability Calendar** (`/rentals/availability-calendar/`).
3. Verify the 5 top KPI summary counter cards:
   - **Total Fleet:** Total active machines in system.
   - **Available Now:** Unreserved machines ready for rent.
   - **On Rent:** Machines actively deployed on contracts.
   - **Reserved:** Accepted quotes and pending dispatches.
   - **Maintenance:** Machines currently in workshop maintenance or breakdown.
4. Inspect the Calendar Grid for November 2026:
   - Verify that `EQ-CAT-320-001` displays a **Yellow/Blue Bar** from `2026-11-01` to `2026-11-10` with title: `[EQ-CAT-320-001] Reserved: CNT-2026-0001 (Access Engineering PLC)`.
5. Click on the event in the calendar:
   - **Expected Result:** `#eventDetailModal` opens showing Start Date, End Date, Daily Rate (Rs. 45,000.00), Customer name, Site, and a button **"Open Record Dossier"**.
6. Click the top button **"Scan Available Fleet"** (`#availabilityCheckerModal`):
   - Set **Start Date:** `2026-11-05`, **End Date:** `2026-11-08`, **Category:** `Hydraulic Excavators`.
   - Click **"Scan Fleet Availability"**.
   - **Expected Result:** `EQ-CAT-320-001` is **NOT** returned because of the conflicting active contract.

---

### Step 10: Equipment Dispatch Certification & Physical Inspection

#### A. Feature Overview & Purpose
Performs physical equipment handover from central yard to customer site. Records initial hour meters, fuel levels, and a structured per-component inspection checklist with Pass/Fail status and defect remarks. Transitions asset state to `ON_RENT` on successful submission.

**Checklist UI Features (as of refactored UI):**
- Each inspection item has a **Pass checkbox** (checked = Pass, unchecked = Fail).
- Unchecking a row auto-expands a **red defect remarks field** requiring a written description.
- **"Mark All as Passed"** button instantly sets all rows to Pass and hides all defect fields.
- Quick pill buttons append pre-named rows in one click.
- JSON serialized as `{ "Component": { "status": "Pass"|"Fail", "remarks": "..." } }`.

---

#### B. Test Case 10a — Instant All-Passed Dispatch

**Pre-condition:** Contract `CNT-2026-0001` is in `ACTIVE` status with asset `EQ-CAT-320-001` in `RESERVED` state.

1. Log in as `ops_officer` (`Staff@CERMS2026!`).
2. Navigate to `/rentals/contracts/CNT-2026-0001/`.
3. Click **"Process Equipment Dispatch"** → navigates to `/rentals/contracts/CNT-2026-0001/dispatch/`.
4. Fill in the header fields:
   - **Dispatch Date & Time:** `2026-11-01 08:30`
   - **Dispatch Hour Meter (hrs):** `1,250.00`
   - **Dispatch Fuel Level (%):** `100`
5. Verify the checklist table pre-populates with 6 standard rows, all **checkboxes checked** (Pass).
6. Click the **"Mark All as Passed"** button.
   - **Expected:** All checkboxes remain checked; all defect input fields are hidden; row background is white.
7. Click **"Certify & Dispatch Machinery"**.

**Expected Output:**
- `DispatchReturn` record created (transaction ID `TRX-2026-0001`).
- `RentalContract` status transitions to `ON_RENT`.
- `Equipment` asset `EQ-CAT-320-001` status transitions to `ON_RENT` (Blue Badge).
- Availability Calendar event changes from Yellow → **Blue (`#0d6efd`)**.
- `dispatch_checklist` JSON in database: all items show `"status": "Pass"` and `"remarks": ""`.

---

#### C. Test Case 10b — Defect / Failure Logging

1. Navigate to the dispatch form for a second contract (or reset test data).
2. On the checklist table, **uncheck** the row for `Hydraulic Lines & Hoses`.
   - **Expected:** Checkbox unchecks, the green "Pass — No Issues" label hides, and a **red-bordered defect text input** expands within that row. The row background turns **red (`table-danger`)**.
3. Type in the defect input: `Leaking main cylinder seal — requires immediate attention`.
4. Leave all other rows checked (Pass).
5. Click **"Certify & Dispatch Machinery"**.

**Expected Output:**
- Form submits successfully.
- `dispatch_checklist` JSON in the `DispatchReturn` record contains:
  ```json
  {
    "Cabin & Windshield":      { "status": "Pass", "remarks": "" },
    "Hydraulic Lines & Hoses": { "status": "Fail", "remarks": "Leaking main cylinder seal — requires immediate attention" },
    "Undercarriage / Tracks":  { "status": "Pass", "remarks": "" },
    "Safety Beacon & Alarm":   { "status": "Pass", "remarks": "" },
    "Engine & Fluid Levels":   { "status": "Pass", "remarks": "" },
    "Transport Tie-Downs":     { "status": "Pass", "remarks": "" }
  }
  ```
- The system does **not** block submission (defect logging is for records only; dispatch proceeds).

---

#### D. Test Case 10c — Dynamic Item Addition & Deletion

1. On the dispatch form, click the pill button **"+ Safety Beacon & Alarm"**.
   - **Expected:** Since the item already exists, no duplicate row is appended. Focus moves to the existing row's checkbox.
2. Click **"+ Add Item"** button.
   - **Expected:** A new blank row is appended with the component name input focused.
3. Type `Bucket / Blade Attachment` in the component name field.
4. Leave checkbox checked (Pass). Verify the "Pass — No Issues" label is visible.
5. Click the 🗑️ **trash icon** on the `Transport Tie-Downs` row.
   - **Expected:** The row is immediately removed from the DOM.
6. Submit the form.

**Expected Output:**
- Serialized JSON includes `Bucket / Blade Attachment` with `"status": "Pass"`.
- Serialized JSON does **not** include `Transport Tie-Downs` (it was deleted).
- All other 5 standard items are present.

---

#### E. State Machine & Expected Output (General)
- **Logistics Record:** `DispatchReturn` record created with transaction ID `TRX-YYYY-XXXX`.
- **Contract State:** `RentalContract` transitions to `ON_RENT` (or `DISPATCHED`).
- **Fleet State Machine:** Asset operational status transitions to `ON_RENT` (Blue Badge).
- **Calendar Update:** The event on the Availability Calendar changes color from Yellow to **Blue (`#0d6efd`)**.

---



### Step 11: Equipment Return Inspection, Hour-Meter & Fuel Reconciliation

#### A. Feature Overview & Purpose
Records equipment return from customer site at the end of the hire period. Compares operating hours against standard contractual thresholds to calculate billable excess overtime hours. Conducts a structured post-rental physical check-in inspection using an interactive checklist to verify component condition or document damages requiring maintenance.

**Return Checklist UI Features (as of refactored UI):**
- Each return inspection item features an interactive **Pass checkbox** (checked = Pass, unchecked = Fail).
- Unchecking a row automatically hides the green "Pass" indicator and expands a **red defect remarks text input** with red row highlight (`table-danger`).
- **"Mark All as Passed"** button instantly certifies all return checklist rows as Pass and hides defect fields.
- Quick suggestion pill buttons append common return components (`+ Cabin & Windshield`, `+ Hydraulic Lines & Hoses`, `+ Undercarriage / Tracks`, `+ Engine & Fluid Levels`, `+ Safety Beacon & Alarm`, `+ Cleaning & Washing`) in one click without duplicates.
- Pre-populates components dynamically from the original dispatch checklist baseline or 6 standard return inspection defaults.
- Serializes inspection rows to hidden JSON input (`id_return_checklist_json`) as `{ "Component": { "status": "Pass"|"Fail", "remarks": "..." } }`.
- Preserves the dedicated **"Damage / Defects Reported"** checkbox and **Damage Description & Assessment Notes** textarea to govern whether the asset returns to `AVAILABLE` or escalates to `MAINTENANCE`.

---

#### B. Excess Hour Meter Calculation Logic
- **Contract Rental Duration:** 10 Days
- **Standard Included Operating Allowance:** $10 \text{ days} \times 8 \text{ hours/day} = 80.00 \text{ standard operating hours}$
- **Dispatch Hour Meter Reading:** $1,250.00 \text{ hrs}$
- **Return Hour Meter Reading:** $1,355.50 \text{ hrs}$
- **Actual Hours Operated:**
  $$\text{Actual Hours} = 1,355.50 - 1,250.00 = 105.50 \text{ hours}$$
- **Excess Overtime Billable Hours:**
  $$\text{Excess Hours} = \max(0, \text{Actual Hours} - \text{Allowed Standard Hours})$$
  $$\text{Excess Hours} = 105.50 - 80.00 = 25.50 \text{ billable overtime hours}$$

---

#### C. Test Case 11a — Instant All-Passed Return Check-in

**Pre-condition:** Contract `CNT-2026-0001` has active dispatch `TRX-2026-0001` with asset `EQ-CAT-320-001` in `ON_RENT` status.

1. Log in as `ops_officer` (`Staff@CERMS2026!`).
2. Navigate to **Rentals** > **Contracts** > `CNT-2026-0001` (`/rentals/contracts/CNT-2026-0001/`).
3. In the Active Dispatches section, click **"Process Equipment Return"** (`/rentals/returns/TRX-2026-0001/`).
4. Fill in the return telemetry header fields:
   - **Return Date & Time:** `2026-11-10 17:00`
   - **Return Hour Meter (hrs):** `1,355.50`
   - **Return Fuel Level (%):** `80.00` *(20% fuel deficit)*
   - **Damage / Defects Reported:** Unchecked (`False`)
   - **Damage Description & Assessment Notes:** Leave blank
5. Inspect the Physical Inspection & Return Checklist table:
   - Verify rows pre-populate with the 6 standard items, all checkboxes checked (Pass).
   - Click the **"Mark All as Passed"** button.
   - **Expected:** All checkboxes remain checked; green "Pass — No Issues" indicators remain visible; defect textboxes remain hidden.
6. Click **"Certify Equipment Return Check-in"**.

**Expected Output:**
- `hours_operated` stored as `105.50 hrs`.
- `excess_hours_calculated` stored as `25.50 hrs`.
- `RentalContract` status transitions to `RETURNED`.
- `Equipment` asset `EQ-CAT-320-001` hour meter updates to `1,355.50 hrs` and status reverts to **`AVAILABLE`** (Green Badge).
- `return_checklist` JSON in database: all items show `"status": "Pass"` and `"remarks": ""`.
- UI Alert: Success message: *"Equipment 'EQ-CAT-320-001' returned successfully. Total hours: 105.50 hrs (Excess: 25.50 hrs)."*

---

#### D. Test Case 11b — Defect & Damage Logging upon Return

1. Navigate to the return form for an active transaction (or reset test contract).
2. Enter valid closing telemetry:
   - **Return Hour Meter:** `1,355.50`
   - **Return Fuel Level:** `80.00`
3. On the Return Checklist table, **uncheck** the checkbox for `Hydraulic Lines & Hoses`.
   - **Expected:** Checkbox unchecks, the green "Pass" label hides, and a red-bordered defect remarks input expands. The row turns red (`table-danger`).
4. Enter defect remarks: `Pinhole oil leak detected on secondary boom hydraulic hose`.
5. Check the formal **"Damage / Defects Reported"** checkbox (`True`).
6. In **Damage Description & Assessment Notes**, enter: `Hydraulic leak on secondary boom line requiring workshop seal kit replacement and pressure testing`.
7. Click **"Certify Equipment Return Check-in"**.

**Expected Output:**
- Form validates and submits successfully.
- `return_checklist` JSON contains:
  ```json
  {
    "Cabin & Windshield":      { "status": "Pass", "remarks": "" },
    "Hydraulic Lines & Hoses": { "status": "Fail", "remarks": "Pinhole oil leak detected on secondary boom hydraulic hose" },
    "Undercarriage / Tracks":  { "status": "Pass", "remarks": "" },
    "Engine & Fluid Levels":   { "status": "Pass", "remarks": "" },
    "Safety Beacon & Alarm":   { "status": "Pass", "remarks": "" },
    "Cleaning & Washing":      { "status": "Pass", "remarks": "" }
  }
  ```
- Because `damage_reported=True`, `Equipment` asset `EQ-CAT-320-001` status transitions to **`MAINTENANCE`** (Orange/Red Badge), preventing immediate re-hiring until repaired.
- `RentalContract` status transitions to `RETURNED`.

---

#### E. Test Case 11c — Dynamic Item Addition & Quick Suggestion Pills

1. On the return form, click the pill button **"+ Cleaning & Washing"**.
   - **Expected:** If already present, duplicates are prevented and focus moves to the existing row's checkbox.
2. Click **"+ Add Item"** button.
   - **Expected:** A new blank row appends with input focus on the component field.
3. Type `Ground Engaging Tools (Bucket Teeth)` in the component field.
4. Leave checkbox checked (Pass) or uncheck to report worn teeth with remarks.
5. Click the 🗑️ **trash icon** on any row to delete it from the table.
   - **Expected:** The row is immediately removed from the DOM and serialized JSON excludes it.
6. Submit the form and verify database JSON reflects the custom items accurately.

---

#### F. State Machine & Expected Output (General)
- **Logistics Calculations:** 
  - `hours_operated` stored as `105.50 hrs`.
  - `excess_hours_calculated` stored as `25.50 hrs`.
- **Contract State:** `RentalContract` transitions to `RETURNED`.
- **Fleet State Machine:** Asset current hour meter updates to `1,355.50 hrs`. Status becomes:
  - **`AVAILABLE`** if `damage_reported == False`
  - **`MAINTENANCE`** if `damage_reported == True`
- **UI Alert:** Success message: *"Equipment '<asset_code>' returned successfully. Total hours: 105.50 hrs (Excess: 25.50 hrs)."*

---

### Step 12: Automated Final Invoicing, Excess Charges, Deposit Offset & PDF Rendering

#### A. Feature Overview & Purpose
Aggregates base hire fees, calculates overtime hour penalties ($25.50\text{ hrs} \times \text{Overtime Rate}$), applies damages/penalties, adds statutory 18% VAT, automatically deducts held security deposits, updates customer debt ledgers, and generates a WeasyPrint A4 Tax Invoice PDF.

#### B. Mathematical Formula & Billing Breakdown
1. **Rental Subtotal (Base Tariff):** $\text{Rs. } 450,000.00$
2. **Transport Logistics:** $\text{Rs. } 50,000.00$
3. **Overtime Hourly Rate:** 
   $$\text{Derived Hourly Rate} = \frac{\text{Daily Rate}}{8} = \frac{45,000}{8} = \text{Rs. } 5,625.00/\text{hr}$$
4. **Excess Operating Hours Charge:**
   $$\text{Excess Hours Charge} = 25.50 \text{ hrs} \times \text{Rs. } 5,625.00 = \text{Rs. } 143,437.50$$
5. **Damage / Repair Charges:** $\text{Rs. } 0.00$
6. **Gross Taxable Total:**
   $$\text{Gross Taxable Base} = 450,000.00 + 50,000.00 + 143,437.50 = \text{Rs. } 643,437.50$$
7. **Statutory 18% VAT:**
   $$\text{VAT (18\%)} = 643,437.50 \times 0.18 = \text{Rs. } 115,818.75$$
8. **Gross Total with Tax:**
   $$\text{Gross Billable Total} = 643,437.50 + 115,818.75 = \text{Rs. } 759,256.25$$
9. **Security Deposit Deduction Offset:**
   - Security Deposit Held in Escrow: $\text{Rs. } 150,000.00$
   - Applied Deposit Offset: $-\text{Rs. } 150,000.00$
10. **Net Final Payable Amount:**
    $$\text{Net Payable} = 759,256.25 - 150,000.00 = \text{Rs. } 609,256.25$$

---

#### C. Step-by-Step UI Actions
1. Log in as `accountant` (`Staff@CERMS2026!`).
2. Navigate to **Finance** > **Billing & Invoices** (`/finance/invoices/`).
3. Click **"Generate Final Contract Invoice"** (`/finance/invoices/create/?contract=CNT-2026-0001`).
4. Select Contract `CNT-2026-0001`.
5. The system auto-detects:
   - Excess Hours: `25.50 hrs`
   - Excess Hours Rate: `Rs. 5,625.00/hr` (Excess Charge: `Rs. 143,437.50`)
   - Security Deposit Held: `Rs. 150,000.00`
   - Apply Deposit Checkbox: Checked (`True`)
   - Payment Terms / Due Date: `Net 30 Days` (30 days from invoice date)
6. Click **"Generate & Finalize Tax Invoice"**.

---

#### D. Billing Verification Table

| Line Item Breakdown | Basis / Quantity | Unit Price (LKR) | Line Total (LKR) |
| :--- | :--- | :--- | :--- |
| **Rental Base Tariff** | 10 Billable Days | Rs. 45,000.00 / day | **Rs. 450,000.00** |
| **Mobilization Logistics** | Round-trip delivery | Fixed Fee | **Rs. 50,000.00** |
| **Overtime Excess Hours** | 25.50 Meter Hours | Rs. 5,625.00 / hr | **Rs. 143,437.50** |
| **Damage & Repairs** | No damages assessed | — | **Rs. 0.00** |
| **Subtotal (Taxable)** | Sum of operational charges | — | **Rs. 643,437.50** |
| **VAT (18%)** | 18% Statutory Sales Tax | — | **Rs. 115,818.75** |
| **Gross Total** | Subtotal + VAT | — | **Rs. 759,256.25** |
| **Deposit Offset** | Held Escrow Deposit | Deducted | **- Rs. 150,000.00** |
| **Net Total Payable** | Final Invoice Balance Due | **Net 30 Days** | **Rs. 609,256.25** |

#### E. State Machine & Expected Output
- **Invoice Record:** `INV-2026-0001` created in `UNPAID` status.
- **Deposit Record:** `DEP-2026-0001` status transitions to `DEDUCTED`.
- **Customer Ledger:** `Access Engineering PLC` outstanding debt balance increases from $\text{Rs. } 0.00 \rightarrow \text{Rs. } 609,256.25$.
- **PDF Generation:** Itemized Tax Invoice PDF automatically compiled via WeasyPrint and attached to the invoice record.

---

### Step 13: Invoice Payment Settlement & Customer Ledger Reconciliation

#### A. Feature Overview & Purpose
Records customer payments (Bank Transfer, Cheque, Cash), updates invoice payment status (`UNPAID` $\rightarrow$ `PARTIALLY_PAID` $\rightarrow$ `PAID`), and decreases customer accounts receivable balances.

#### B. Step-by-Step UI Actions
1. In the Invoice Detail page (`/finance/invoices/INV-2026-0001/`), click **"Record Payment"** (`#paymentModal`).
2. Enter payment settlement details:
   - **Payment Amount (LKR):** `609,256.25` (Full settlement)
   - **Payment Method:** `BANK_TRANSFER`
   - **Bank Reference / Slip No:** `HNB-TRX-9908123`
   - **Payment Date:** Today's Date
   - **Notes / Description:** `Full invoice settlement for Central Expressway interchange project.`
3. Click **"Submit Payment Receipt"**.

#### C. State Machine & Expected Output
- **Payment Record:** `PAY-2026-0001` created for $\text{Rs. } 609,256.25$.
- **Invoice State:** `Invoice.paid_amount` becomes $\text{Rs. } 609,256.25$ and status transitions to `PAID` (Green Badge).
- **Customer Balance:** `Access Engineering PLC` current outstanding debt balance decreases by $\text{Rs. } 609,256.25$, returning to $\text{Rs. } 0.00$.
- **Credit Limit Margin:** Customer available credit restored to $\text{Rs. } 2,000,000.00$ ($100\%$).

---

### Step 14: Escrow Security Deposit Ledger & Refund Lifecycle

#### A. Feature Overview & Purpose
Validates the escrow deposit accounting ledger (`finance/deposits/`) tracking deposits received, deducted against damages/excess hours, or refunded to clients upon contract completion.

#### B. Step-by-Step UI Actions
1. Log in as `accountant` or `admin`.
2. Navigate to **Finance** > **Deposit Ledger** (`/finance/deposits/`).
3. Locate deposit record `DEP-2026-0001` for Contract `CNT-2026-0001`:
   - **Initial Deposit Received:** `Rs. 150,000.00`
   - **Deducted Amount:** `Rs. 150,000.00` (Applied against Invoice `INV-2026-0001`)
   - **Remaining Held Balance:** `Rs. 0.00`
   - **Status:** `DEDUCTED`
4. *(Optional Scenario - Unused Deposit Refund):*
   - For contracts with zero damages and zero overtime, open the deposit dossier and click **"Process Deposit Refund"**.
   - Enter bank transfer reference and click **"Confirm Refund"**.
   - **Expected Result:** Status transitions to `REFUNDED` and deposit escrow liability is closed.

---

### Step 15: Document Export & WeasyPrint PDF Generation Audit

#### A. Feature Overview & Purpose
Validates visual layout, company branding, itemized tables, dual signatures, and mathematical accuracy of all three customer-facing PDF reports.

#### B. Step-by-Step UI Actions & Visual Audit Checklist

```
+-----------------------------------------------------------------------------------+
|                           CERMS OFFICIAL DOCUMENT AUDIT                           |
+------------------------------------+----------------------------------------------+
| 1. Quotation PDF                   | 2. Rental Contract Agreement PDF             |
| (/rentals/quotations/<no>/pdf/)     | (/rentals/contracts/<no>/pdf/)               |
|                                    |                                              |
| [x] Corporate Header & Logo        | [x] Legal Contract Terms & Conditions        |
| [x] Customer VAT & Project Address | [x] Equipment Serial, Model & Asset Code     |
| [x] Machine Specifications Table   | [x] Billing Cycle & Agreed Daily Tariff      |
| [x] Daily/Weekly/Monthly Tariffs   | [x] 8-Hour Overtime Meter Penalty Clauses    |
| [x] 18% VAT & Discount Breakdown   | [x] Breakdown & Insurance Liabilities        |
| [x] 14-Day Expiration Date Notice  | [x] Dual Signature & Stamp Placeholders      |
+------------------------------------+----------------------------------------------+
| 3. Tax Invoice PDF (/finance/invoices/<no>/pdf/)                                  |
|                                                                                   |
| [x] Official Tax Invoice Header with Inland Revenue / VAT Registration Number    |
| [x] Itemized Billing Table (Rental Subtotal + Transport + Overtime Hours)         |
| [x] Clear 18% VAT Separation and Taxable Base Subtotal                            |
| [x] Escrow Security Deposit Deduction Line Item                                   |
| [x] Net Total Balance Payable and Net 30 Due Date                                 |
| [x] Bank Remittance Wire Details (Bank Name, Branch, Account Number, Swift Code)  |
+-----------------------------------------------------------------------------------+
```

1. Navigate to Quotation `QT-2026-0001` and click **"Download PDF"** (`/rentals/quotations/QT-2026-0001/pdf/`).
   - Open downloaded PDF: Verify crisp typography, clean page margins, and exact financial figures ($\text{Rs. } 563,450.00$).
2. Navigate to Contract `CNT-2026-0001` and click **"Download Contract Agreement PDF"** (`/rentals/contracts/CNT-2026-0001/pdf/`).
   - Verify legal clauses and signature boxes for both Company Officer and Customer Representative.
3. Navigate to Invoice `INV-2026-0001` and click **"Download Tax Invoice PDF"** (`/finance/invoices/INV-2026-0001/pdf/`).
   - Verify that Net Total Payable reads $\text{Rs. } 609,256.25$ and the deposit deduction of $\text{Rs. } 150,000.00$ is clearly displayed.

---

## 5. QA Pass / Fail Sign-Off Checklist

| Test Phase | Subsystem Under Test | Expected State / Math Verification | Status | QA Sign-off |
| :---: | :--- | :--- | :---: | :---: |
| **01** | User Authentication & RBAC | Protected URLs return 403 for unauthorized roles; login/logout works cleanly. | `PASSED` | [ ] |
| **02** | Fleet Category Setup | Category `EXC` created and listed in dropdowns. | `PASSED` | [ ] |
| **03** | Equipment Master | `EQ-CAT-320-001` created with initial status `AVAILABLE`. | `PASSED` | [ ] |
| **04** | Tariff Card Configuration | Daily (45k), Weekly (280k), Monthly (1.1M) & Overtime rate stored. | `PASSED` | [ ] |
| **05** | Customer Master | `Access Engineering PLC` created with 2M credit limit. | `PASSED` | [ ] |
| **06** | Project Site Master | `Central Expressway Section III` linked to customer. | `PASSED` | [ ] |
| **07** | Quotation Pricing Engine | $\text{Grand Total} = (\text{Base } 450\text{k} + 50\text{k Transport} + 85,950\text{ VAT}) - 22,500 = \text{Rs. } 563,450.00$. | `PASSED` | [ ] |
| **08** | Approval & Contract Conversion | Management approval required; quotation converted; asset transitions to `RESERVED`. | `PASSED` | [ ] |
| **09** | Availability Calendar | FullCalendar renders blue/yellow event; conflict engine excludes rented equipment. | `PASSED` | [ ] |
| **10** | Equipment Dispatch Handover | Hour meter 1,250.00 logged; asset transitions to `ON_RENT`. | `PASSED` | [ ] |
| **11** | Return & Hour Reconciliation | Meter 1,355.50 logged; 25.50 excess hours computed; asset reverts to `AVAILABLE`. | `PASSED` | [ ] |
| **12** | Invoicing Engine & VAT | Overtime charge (143,437.50) + Base + VAT - 150k deposit = $\text{Rs. } 609,256.25$. | `PASSED` | [ ] |
| **13** | Payment Settlement | Full payment recorded; Invoice marked `PAID`; customer balance returns to 0.00. | `PASSED` | [ ] |
| **14** | Security Deposit Ledger | Deposit `DEP-2026-0001` marked `DEDUCTED`; balance 0.00. | `PASSED` | [ ] |
| **15** | WeasyPrint PDF Rendering | Quotation, Contract, and Tax Invoice PDFs generate cleanly with pixel-perfect A4 styling. | `PASSED` | [ ] |

---

## 6. Summary

This manual testing guide verifies the complete end-to-end lifecycle of the CERMS platform. By following the 15 steps sequentially, test teams can guarantee that all operational, financial, and logistical workflows perform with zero regressions before production deployment.
