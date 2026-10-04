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

### Maintenance & Repair Flow

- **Step 1 (Assessment):** A `Technician` (or Field Officer) reports a breakdown or schedules maintenance[cite: 1, 33].
- **Step 2 (Review):** The `Workshop Manager` reviews the issue and estimates the repair cost[cite: 1, 33].
- **Step 3 (Financial Approval):** `Management` approves the repair cost[cite: 1, 33].
- **Step 4 (Execution):** Repair is executed[cite: 1, 33].
- **Step 5 (Resolution):** Job marked as `Completed`, and equipment status returns to `Available`[cite: 1, 33].
