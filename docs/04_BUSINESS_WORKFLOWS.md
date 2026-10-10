# 04_BUSINESS_WORKFLOWS

## 1. Overview

The CERMS platform automates the complex physical and financial operations of a construction equipment rental business. This document maps out the core operational lifecycles and approval workflows that the code must strictly enforce[cite: 1, 33].

## 2. The Rental Lifecycle (Data Flow)

The primary data flow for renting an asset must follow these sequential steps without skipping phases[cite: 1, 33]:

1.  **Customer Enquiry:** The process begins with an availability check based on `EquipmentMaster` data[cite: 1, 33].
2.  **Quotation:** A draft quotation is generated detailing the equipment, rates, transport, and fuel costs[cite: 1, 33].
3.  **Approval:** The quotation undergoes the internal and external Approval Workflow (see Section 4)[cite: 1, 33].
4.  **Contract (Agreement):** Once approved, the Quotation is converted into an active `RentalContract`[cite: 1, 33].
5.  **Reservation:** The assigned equipment status is updated to `Reserved`[cite: 1, 33].
6.  **Dispatch:** Pre-dispatch inspection is completed (photos, hour meter, fuel level logged). Status becomes `Dispatched` or `On Rent`[cite: 1, 33].
7.  **Usage (Active Rent):** The equipment is actively used. `HourMeter` and `FuelLog` entries are recorded incrementally[cite: 1, 33].
8.  **Billing:** Periodic or recurring invoices are generated based on the contract's billing cycle[cite: 1, 33].
9.  **Return:** Equipment is received. Return inspection is conducted to assess damage, closing hour meter, and fuel levels[cite: 1, 33].
10. **Final Bill & Payment:** Any damages, missing parts, or excess usage are calculated. The final invoice is settled, and the contract is marked `Completed`[cite: 1, 33].

## 3. Equipment Lifecycle

The physical status of an asset dictates its availability in the system. The `status` field in the `Equipment` model must transition strictly as follows[cite: 1, 33]:

`Purchase` &rarr; `Equipment Registration` &rarr; **`Available`** &rarr; `Reserved` (Quotation Approved) &rarr; `Dispatched` &rarr; `On Rent` &rarr; `Usage Monitoring` &rarr; `Return` (Inspection) &rarr; `Final Billing` &rarr; **`Maintenance`** (if required) &rarr; **`Available`**[cite: 1, 33].

## 4. Approval Workflows

To maintain financial and operational control, key actions require explicit approval steps[cite: 1, 33]:

### Quotation Approval Flow

- **Step 1 (Draft):** Created by the `Rental Officer`[cite: 1, 33].
- **Step 2 (Internal Review):** Approved by `Management` (Manager Approval)[cite: 1, 33].
- **Step 3 (Client Acceptance):** Approved by the `Customer`[cite: 1, 33].
- **Step 4 (Execution):** Converted to a Rental Contract[cite: 1, 33].

> **Business Rule (Assets Under Maintenance/Breakdown in Quotations):**
> *Assets under maintenance are not blocked from being quoted to accommodate future rental dates. However, they trigger a soft warning during quotation creation and managerial approval to ensure repair timelines are verified prior to contract conversion.*

### Maintenance & Repair Flow

- **Step 1 (Assessment):** A `Technician` (or Field Officer) reports a breakdown or schedules maintenance[cite: 1, 33].
- **Step 2 (Review):** The `Workshop Manager` reviews the issue and estimates the repair cost[cite: 1, 33].
- **Step 3 (Financial Approval):** `Management` approves the repair cost[cite: 1, 33].
- **Step 4 (Execution):** Repair is executed[cite: 1, 33].
- **Step 5 (Resolution):** Job marked as `Completed`, and equipment status returns to `Available`[cite: 1, 33].

## 5. Bifurcated Damage Handling & Decoupled Maintenance Routing

CERMS decouples cosmetic/minor damage tracking from workshop maintenance gating to avoid unnecessary asset downtime while preserving complete operational audit trails.

### Dual Damage Classification Architecture

1. **Log Minor Damage / Defect (`has_minor_damage`):**
   - Intended for non-critical cosmetic or minor defects (e.g., paint scratch, small dent, worn bucket teeth).
   - **Return Workflow Impact:** When only minor damage is checked, the equipment transitions back to **`AVAILABLE`** (eligible for immediate future hiring). The asset is flagged with `has_minor_damage = True` and displays persistent dual status badges (e.g., `[AVAILABLE]` + `[MINOR DAMAGE]`) on Fleet Master and Contract pages.
   - **Dispatch Workflow Impact:** Can be dispatched to site. If an asset has pre-existing minor damage from previous rentals, a prominent alert banner is displayed at the top of the dispatch form: `Unresolved Previous Damages: [Damage Notes]` to establish baseline machine condition before site departure.

2. **Require Maintenance / Ground Asset (`requires_maintenance`):**
   - Intended for major mechanical, electrical, structural, or safety-critical defects requiring workshop intervention.
   - **Return Workflow Impact:** Transitions the equipment directly to **`MAINTENANCE`**, grounding the asset and blocking future contract dispatch until workshop technicians complete repairs.
   - **Dispatch Workflow Impact:** Blocks equipment dispatch and triggers an immediate validation exception, grounding the asset to `MAINTENANCE`.

### Dynamic UI Behavior
- The **"Damage Description & Assessment Notes"** textarea is completely hidden by default on both Dispatch and Return forms.
- Vanilla JavaScript dynamically reveals and expands the textarea **only if** either `Log Minor Damage / Defect` or `Require Maintenance / Ground Asset` is checked.

### Checklist Independence
- Component inspections and checklist pass/fail evaluations serve purely as physical condition logs in JSON format (`{ "Component": { "status": "Pass"|"Fail", "remarks": "..." } }`).
- Marking an item as `Fail` in the checklist does **NOT** automatically ground equipment into `MAINTENANCE`. The asset returns to `AVAILABLE` unless the explicit `Require Maintenance / Ground Asset` checkbox is selected by the certifying officer.

### Maintenance Resolution Lifecycle
- When maintenance or overhaul is completed (transitioning an asset from `MAINTENANCE` or `BREAKDOWN` back to `AVAILABLE`), the system automatically clears unresolved minor damage flags and resets `has_minor_damage = False` and `minor_damage_notes = ""`.
