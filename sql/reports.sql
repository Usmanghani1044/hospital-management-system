-- Read-only portfolio queries. Monetary columns use integer paisa.
-- 1. Patient appointments with their doctors.
SELECT a.id,p.name AS patient,d.name AS doctor,a.starts_at,a.status
FROM appointment a JOIN patient p ON p.id=a.patient_id
JOIN doctor d ON d.id=a.doctor_id ORDER BY a.starts_at;

-- 2. Completed visits versus distinct patients (repeat visits count once per patient).
SELECT d.id,d.name,COUNT(e.id) AS visits,
COUNT(DISTINCT CASE WHEN e.id IS NOT NULL THEN a.patient_id END) AS distinct_patients
FROM doctor d LEFT JOIN appointment a ON a.doctor_id=d.id
LEFT JOIN encounter e ON e.appointment_id=a.id GROUP BY d.id,d.name;

-- 3. Outstanding invoices, derived from separate item and receipt aggregates.
SELECT * FROM v_invoice_balance WHERE balance>0 ORDER BY balance DESC;

-- 4. Receipts collected by method. Invoice value is not collected revenue.
SELECT method,SUM(amount) AS collected_paisa FROM payment GROUP BY method;

-- 5. Current occupancy per ward, including empty wards with beds.
SELECT ward,COUNT(*) AS beds,SUM(CASE WHEN status='Occupied' THEN 1 ELSE 0 END) AS occupied
FROM v_bed_status GROUP BY ward;

-- 6. Available beds.
SELECT id,ward,label FROM v_bed_status WHERE status='Available';

-- 7. Admissions with no discharge yet.
SELECT a.id,p.name AS patient,d.name AS doctor,b.label,a.admitted_at
FROM admission a JOIN patient p ON p.id=a.patient_id JOIN doctor d ON d.id=a.doctor_id
JOIN bed b ON b.id=a.bed_id WHERE a.discharged_at IS NULL;

-- 8. Low usable stock (expired stock is excluded).
SELECT m.id,m.name,m.reorder_level,
COALESCE(SUM(CASE WHEN b.expiry_date>=CURRENT_DATE THEN b.stock ELSE 0 END),0) AS usable_stock
FROM medicine m LEFT JOIN medicine_batch b ON b.medicine_id=m.id
GROUP BY m.id,m.name,m.reorder_level
HAVING COALESCE(SUM(CASE WHEN b.expiry_date>=CURRENT_DATE THEN b.stock ELSE 0 END),0)<m.reorder_level;

-- 9. Expired batches with stock remaining.
SELECT * FROM medicine_batch WHERE expiry_date<CURRENT_DATE AND stock>0;

-- 10. Prescriptions still awaiting dispensing.
SELECT r.id,r.encounter_id,m.name,r.quantity FROM prescription r
JOIN medicine m ON m.id=r.medicine_id LEFT JOIN dispensing d ON d.prescription_id=r.id
WHERE d.id IS NULL;

-- 11. Scheduled appointments by department.
SELECT dp.id,dp.name,COUNT(a.id) AS scheduled
FROM department dp JOIN doctor d ON d.department_id=dp.id
LEFT JOIN appointment a ON a.doctor_id=d.id AND a.status='Scheduled'
GROUP BY dp.id,dp.name;

-- 12. Latest workflow events.
SELECT occurred_at,action,entity,entity_id,summary FROM audit_event ORDER BY id DESC LIMIT 20;
