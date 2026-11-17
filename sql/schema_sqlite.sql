-- Hospital Management | Muhammad Usman Ghani
-- SQLite runtime schema. Money is integer PKR paisa (100 paisa = 1 rupee).
PRAGMA foreign_keys = ON;
CREATE TABLE department (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, location TEXT NOT NULL
);
CREATE TABLE doctor (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, specialty TEXT NOT NULL,
 department_id INTEGER NOT NULL REFERENCES department(id), email TEXT UNIQUE
);
CREATE TABLE ward (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
 department_id INTEGER NOT NULL REFERENCES department(id)
);
CREATE TABLE bed (
 id INTEGER PRIMARY KEY, ward_id INTEGER NOT NULL REFERENCES ward(id),
 label TEXT NOT NULL, UNIQUE(ward_id,label)
);
CREATE TABLE nurse (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, ward_id INTEGER NOT NULL REFERENCES ward(id),
 shift TEXT NOT NULL CHECK(shift IN ('Morning','Evening','Night'))
);
CREATE TABLE patient (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(trim(name))>0),
 dob TEXT NOT NULL, gender TEXT NOT NULL CHECK(gender IN ('Male','Female','Other')),
 phone TEXT, address TEXT, blood_group TEXT CHECK(blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-','Unknown')),
 created_at TEXT NOT NULL
);
CREATE TABLE appointment (
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patient(id),
 doctor_id INTEGER NOT NULL REFERENCES doctor(id), starts_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Scheduled' CHECK(status IN ('Scheduled','Completed','Cancelled')),
 active_slot INTEGER GENERATED ALWAYS AS (CASE WHEN status <> 'Cancelled' THEN 1 ELSE NULL END) STORED,
 UNIQUE(doctor_id,starts_at,active_slot), UNIQUE(patient_id,starts_at,active_slot)
);
CREATE TABLE encounter (
 id INTEGER PRIMARY KEY, appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointment(id),
 diagnosis TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', recorded_at TEXT NOT NULL
);
CREATE TABLE medicine (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, unit_price INTEGER NOT NULL CHECK(unit_price>=0),
 reorder_level INTEGER NOT NULL DEFAULT 20 CHECK(reorder_level>=0)
);
CREATE TABLE medicine_batch (
 id INTEGER PRIMARY KEY, medicine_id INTEGER NOT NULL REFERENCES medicine(id),
 batch_code TEXT NOT NULL UNIQUE, expiry_date TEXT NOT NULL,
 stock INTEGER NOT NULL CHECK(stock>=0)
);
CREATE TABLE prescription (
 id INTEGER PRIMARY KEY, encounter_id INTEGER NOT NULL REFERENCES encounter(id),
 medicine_id INTEGER NOT NULL REFERENCES medicine(id), quantity INTEGER NOT NULL CHECK(quantity>0),
 instructions TEXT NOT NULL
);
CREATE TABLE dispensing (
 id INTEGER PRIMARY KEY, prescription_id INTEGER NOT NULL UNIQUE REFERENCES prescription(id),
 batch_id INTEGER NOT NULL REFERENCES medicine_batch(id), quantity INTEGER NOT NULL CHECK(quantity>0),
 dispensed_at TEXT NOT NULL
);
CREATE TABLE admission (
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patient(id),
 doctor_id INTEGER NOT NULL REFERENCES doctor(id), bed_id INTEGER NOT NULL REFERENCES bed(id),
 admitted_at TEXT NOT NULL, discharged_at TEXT,
 active_stay INTEGER GENERATED ALWAYS AS (CASE WHEN discharged_at IS NULL THEN 1 ELSE NULL END) STORED,
 CHECK(discharged_at IS NULL OR discharged_at>=admitted_at),
 UNIQUE(bed_id,active_stay), UNIQUE(patient_id,active_stay)
);
CREATE TABLE invoice (
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patient(id),
 issued_at TEXT NOT NULL
);
CREATE TABLE invoice_item (
 id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoice(id),
 description TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0),
 unit_price INTEGER NOT NULL CHECK(unit_price>0)
);
CREATE TABLE payment (
 id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoice(id),
 amount INTEGER NOT NULL CHECK(amount>0), method TEXT NOT NULL CHECK(method IN ('Cash','Card','Transfer')),
 reference TEXT NOT NULL UNIQUE, paid_at TEXT NOT NULL
);
CREATE TABLE audit_event (
 id INTEGER PRIMARY KEY, occurred_at TEXT NOT NULL, action TEXT NOT NULL,
 entity TEXT NOT NULL, entity_id INTEGER NOT NULL, summary TEXT NOT NULL
);
CREATE INDEX appointment_date_idx ON appointment(starts_at,status);
CREATE INDEX encounter_date_idx ON encounter(recorded_at);
CREATE INDEX admission_patient_idx ON admission(patient_id,admitted_at);
CREATE INDEX batch_expiry_idx ON medicine_batch(expiry_date);
CREATE INDEX invoice_patient_idx ON invoice(patient_id);
CREATE INDEX payment_invoice_idx ON payment(invoice_id);
CREATE INDEX item_invoice_idx ON invoice_item(invoice_id);
CREATE VIEW v_invoice_balance AS
SELECT i.id,i.patient_id,p.name AS patient,i.issued_at,
 COALESCE(t.total,0) AS total,COALESCE(pay.paid,0) AS paid,
 COALESCE(t.total,0)-COALESCE(pay.paid,0) AS balance,
 CASE WHEN COALESCE(t.total,0)=COALESCE(pay.paid,0) THEN 'Paid'
      WHEN COALESCE(pay.paid,0)>0 THEN 'Partial' ELSE 'Unpaid' END AS status
FROM invoice i JOIN patient p ON p.id=i.patient_id
LEFT JOIN (SELECT invoice_id,SUM(quantity*unit_price) AS total FROM invoice_item GROUP BY invoice_id) t ON t.invoice_id=i.id
LEFT JOIN (SELECT invoice_id,SUM(amount) AS paid FROM payment GROUP BY invoice_id) pay ON pay.invoice_id=i.id;
CREATE VIEW v_bed_status AS
SELECT b.id,w.name AS ward,b.label,a.id AS admission_id,a.patient_id,p.name AS patient,
 CASE WHEN a.id IS NULL THEN 'Available' ELSE 'Occupied' END AS status
FROM bed b JOIN ward w ON b.ward_id=w.id
LEFT JOIN admission a ON a.bed_id=b.id AND a.discharged_at IS NULL
LEFT JOIN patient p ON a.patient_id=p.id;
