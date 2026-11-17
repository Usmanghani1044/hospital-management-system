# Data dictionary

Money values are integer PKR paisa. Runtime dates are ISO strings; local timestamps use `YYYY-MM-DDTHH:MM:SS`. Each table has a primary key named `id`.

## department

Clinical department reference data.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `name` | TEXT | Required |
| `location` | TEXT | Required |

## doctor

Doctors and departmental affiliation.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `name` | TEXT | Required |
| `specialty` | TEXT | Required |
| `department_id` | INTEGER | Required; References department.id |
| `email` | TEXT | Optional |

## ward

Wards linked to departments.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `name` | TEXT | Required |
| `department_id` | INTEGER | Required; References department.id |

## bed

Individually allocated beds.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `ward_id` | INTEGER | Required; References ward.id |
| `label` | TEXT | Required |

## nurse

Nursing roster and ward assignment.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `name` | TEXT | Required |
| `ward_id` | INTEGER | Required; References ward.id |
| `shift` | TEXT | Required |

## patient

Patient demographic record.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `name` | TEXT | Required |
| `dob` | TEXT | Required |
| `gender` | TEXT | Required |
| `phone` | TEXT | Optional |
| `address` | TEXT | Optional |
| `blood_group` | TEXT | Optional |
| `created_at` | TEXT | Required |

## appointment

Scheduled, cancelled or completed slots.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `patient_id` | INTEGER | Required; References patient.id |
| `doctor_id` | INTEGER | Required; References doctor.id |
| `starts_at` | TEXT | Required |
| `status` | TEXT | Required |
| `active_slot` | INTEGER | Generated, not directly editable |

## encounter

One consultation record per completed appointment.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `appointment_id` | INTEGER | Required; References appointment.id |
| `diagnosis` | TEXT | Required |
| `notes` | TEXT | Required |
| `recorded_at` | TEXT | Required |

## medicine

Fictional catalog and reorder threshold.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `name` | TEXT | Required |
| `unit_price` | INTEGER | Required; Integer paisa |
| `reorder_level` | INTEGER | Required |

## medicine_batch

Expiry and current stock per batch.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `medicine_id` | INTEGER | Required; References medicine.id |
| `batch_code` | TEXT | Required |
| `expiry_date` | TEXT | Required |
| `stock` | INTEGER | Required |

## prescription

Requested medicine and quantity for an encounter.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `encounter_id` | INTEGER | Required; References encounter.id |
| `medicine_id` | INTEGER | Required; References medicine.id |
| `quantity` | INTEGER | Required |
| `instructions` | TEXT | Required |

## dispensing

One fulfillment event per prescription.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `prescription_id` | INTEGER | Required; References prescription.id |
| `batch_id` | INTEGER | Required; References medicine_batch.id |
| `quantity` | INTEGER | Required |
| `dispensed_at` | TEXT | Required |

## admission

Bed stays, including discharge history.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `patient_id` | INTEGER | Required; References patient.id |
| `doctor_id` | INTEGER | Required; References doctor.id |
| `bed_id` | INTEGER | Required; References bed.id |
| `admitted_at` | TEXT | Required |
| `discharged_at` | TEXT | Optional |
| `active_stay` | INTEGER | Generated, not directly editable |

## invoice

Invoice header for a patient.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `patient_id` | INTEGER | Required; References patient.id |
| `issued_at` | TEXT | Required |

## invoice_item

Historical charges and quantities.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `invoice_id` | INTEGER | Required; References invoice.id |
| `description` | TEXT | Required |
| `quantity` | INTEGER | Required |
| `unit_price` | INTEGER | Required; Integer paisa |

## payment

Recorded receipts, methods and unique references.

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `invoice_id` | INTEGER | Required; References invoice.id |
| `amount` | INTEGER | Required; Integer paisa |
| `method` | TEXT | Required |
| `reference` | TEXT | Required |
| `paid_at` | TEXT | Required |

## audit_event

Local application event history (not tamper-proof).

| Column | SQLite type | Constraint / link |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `occurred_at` | TEXT | Required |
| `action` | TEXT | Required |
| `entity` | TEXT | Required |
| `entity_id` | INTEGER | Required |
| `summary` | TEXT | Required |

## Reporting views

`v_invoice_balance` derives total, paid, outstanding balance and payment status. `v_bed_status` derives current availability and occupant from active admissions. See the schema for all CHECK and UNIQUE clauses.
