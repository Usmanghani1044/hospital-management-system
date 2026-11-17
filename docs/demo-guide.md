# Five-minute demonstration

Use fictional values only. Initial IDs below apply to a newly created database.

1. **Overview:** explain the four summary cards, appointment queue, occupied beds and financial overview. Initial receipts total PKR 2,000; outstanding invoices total PKR 2,500.
2. **Patients:** register “Demo Visitor”, a past date of birth, a gender and a blood group. Search for the name and open History.
3. **Appointments:** book this patient with a doctor tomorrow at 10:00. Try the same doctor/time for another patient: it should reject the collision. Cancel the first appointment, then rebook the released slot.
4. **Beds & admissions:** admit the new patient to an available bed. Try an occupied bed for another patient: it must fail. Discharge the new admission and show that the bed becomes available again.
5. **Clinical records:** the initial database has two completed encounters. Add a fictional prescription to encounter #1 using Demo medicine A, quantity 5 and fictional instructions. New future appointments cannot be completed before their scheduled time; this is intentional. To demonstrate a new encounter, schedule a slot that is about to start, wait until that time, then record it.
6. **Pharmacy:** dispense the new prescription using DEMO-BATCH-1. Stock decreases by 5. Trying to dispense it again must fail. Receive a new batch for Demo medicine B with a future expiry date to clear its low-stock alert.
7. **Billing & payments:** create an invoice with two items (for example, 1 consultation at PKR 1,500 and 2 demo services at PKR 250 each). Total is PKR 2,000. Record PKR 500 using a unique reference such as DEMO-NEW-001. Status becomes Partial and balance becomes PKR 1,500. An attempted PKR 1,600 payment should be rejected. A PKR 1,500 receipt with a new reference completes it.
8. **Reports & activity:** inspect the activity log, compare completed visits with distinct patients, export a CSV, and download a database backup.

## Useful screenshots for your README

Capture the browser's app area: (1) Overview, (2) bed availability, (3) invoice ledger showing Paid and Partial invoices. Use only fictional demo data. Save your own captures under a `screenshots` folder and add relative Markdown image links to README. No screenshots are prepackaged because the browser rendering was not visually verified in the delivery environment.

## Explaining the work in an interview

Explain one workflow in depth: “When dispensing a prescription, the service starts a write transaction, checks medicine identity, expiry, stock and prior dispensing, reduces stock, records dispensing and writes an activity event. Any failure rolls back everything.”

Be clear that the browser app uses SQLite; MySQL scripts are a separate coursework companion. Describe the AI-assisted extension honestly and be ready to explain the SQL and tests yourself.
