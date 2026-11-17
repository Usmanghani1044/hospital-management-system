# Architecture and database integrity

## Request flow

The browser sends JSON to the loopback Python HTTP server. `Hospital.act` validates a whitelisted operation inside a SQLite `BEGIN IMMEDIATE` transaction. Database checks and foreign keys enforce structural integrity. The operation and its activity event commit together. Read-only snapshot requests use one read transaction.

`BEGIN IMMEDIATE` obtains the SQLite write reservation before stock/balance checks. Concurrent writers wait, then validate against the committed result of the earlier writer. This avoids two payments both consuming the same outstanding balance or two dispensings consuming the same stock. It is suitable for this small local demo, not a high-concurrency hospital deployment.

## Where rules are enforced

| Rule | Enforcement |
| --- | --- |
| Related IDs must exist | Foreign keys enabled per connection; service existence checks provide messages |
| One doctor/patient per non-cancelled time slot | Unique indexes over IDs, time and generated active-slot marker |
| One active admission per bed/patient | Unique keys with generated active-stay marker; NULL permits historical stays |
| Positive quantities and valid status values | SQL CHECK constraints |
| Future booking, 30-minute boundary | Service validation |
| Encounter only for an eligible scheduled appointment | Service state check, unique appointment reference and atomic status update |
| Correct medicine, sufficient stock, unexpired batch | Service validation inside write transaction |
| Prescription dispensed once | Unique prescription reference plus service check |
| No overpayment | Service reads derived balance inside write transaction |
| Unique receipt reference | SQL UNIQUE constraint |
| Money has at most two decimal places | Decimal validation and integer-paisa storage |
| Audit entry and change succeed together | One transaction; failures roll back both |

Direct SQL writes can bypass service-only rules. The companion MySQL schema enforces its declared relational constraints, not every workflow rule. A MySQL implementation would need transactions and appropriate locking, such as locking the invoice or batch row before dependent reads and writes.

## Normalization decisions

Each table describes one entity or relationship. Patient details are stored once and referenced by ID. Department details are separated from doctors; ward details from beds; medicine descriptions from inventory batches. Prescriptions reference encounters, and encounters reference appointments rather than duplicating patient/doctor identity.

Invoice items and receipts are independent child relations. Totals are computed through a view instead of storing redundant balances. Item unit prices are historical sale prices, intentionally independent of changes to catalog prices. Generated markers support constraints and are not editable business attributes.

Under these declared dependencies, the design aims for third normal form: non-key attributes describe the key, rather than other non-key attributes. Having single-column keys alone does not establish 3NF. The polymorphic audit entity/ID is a deliberate exception to referential linkage: it is an event label, not a foreign key. Events are application history, not a tamper-proof compliance log.

## Local HTTP boundaries

Only loopback binding is supported. Host values are checked, API calls require a per-process demo token, SQL inputs use bound parameters, and static file routes are allowlisted. The UI escapes entered text before rendering HTML; CSV text starting with formula characters is prefixed with an apostrophe. A Content Security Policy restricts scripts and styles to this origin.

These measures do not provide user authentication. Anyone with access to the local machine can open the app and its database. Do not deploy this server publicly or use real patient information.

## Deliberate scope

Appointments last 30 minutes and use computer-local times, with no timezone conversion or doctor working-hours calendar. Cancelled slots can be rebooked. Completed slots remain occupied historically. Dispensing uses one batch for the full prescription; partial dispensing and batch splitting are not supported. The expiry date itself is treated as usable. Billing is manual and independent of admission or pharmacy events. Payment methods are labels, with no gateway. Reference-data maintenance, refunds, user roles, migrations and deployment infrastructure are future work.

## References

- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html)
- [SQLite foreign keys](https://sqlite.org/foreignkeys.html)
- [MySQL locking reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)
