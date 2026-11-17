# Entity relationships

The diagrams group the schema by workflow. Entities repeated across diagrams are the same database table.

## Patient consultations

```mermaid
erDiagram
    department ||--o{ doctor : contains
    doctor ||--o{ appointment : attends
    patient ||--o{ appointment : books
    appointment ||--o| encounter : produces
    encounter ||--o{ prescription : includes
```

## Bed allocation

```mermaid
erDiagram
    department ||--o{ ward : contains
    ward ||--o{ bed : contains
    ward ||--o{ nurse : assigns
    bed ||--o{ admission : has_history
    patient ||--o{ admission : has_history
    doctor ||--o{ admission : supervises
```

The bed/admission relation is one-to-many historically. The generated active-stay constraints limit each bed and patient to one current admission.

## Pharmacy

```mermaid
erDiagram
    medicine ||--o{ medicine_batch : stocked_in
    medicine ||--o{ prescription : requested_by
    prescription ||--o| dispensing : fulfilled_by
    medicine_batch ||--o{ dispensing : supplies
```

The service checks that the batch's medicine matches the prescription. Dispensing is a whole-prescription event, not a partial fulfillment.

## Billing

```mermaid
erDiagram
    patient ||--o{ invoice : receives
    invoice ||--|{ invoice_item : contains
    invoice ||--o{ payment : settled_by
```

The service creates at least one invoice item atomically with its invoice. SQL foreign keys alone do not require a header to have a child. Payment status and balances are derived.

`audit_event` records application actions and IDs separately, without a foreign key to every entity type. It is not a security audit system.
