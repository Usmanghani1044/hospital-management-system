-- MySQL 8.0.16+ companion: run once in a NEW empty database.
-- Not the dashboard backend; application-only rules are documented in docs/architecture.md.
CREATE DATABASE IF NOT EXISTS hospital_portfolio CHARACTER SET utf8mb4;
USE hospital_portfolio;

CREATE TABLE department (
 id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(200) NOT NULL UNIQUE, location VARCHAR(200) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE doctor (
 id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(200) NOT NULL, specialty VARCHAR(200) NOT NULL,
 department_id INT NOT NULL, email VARCHAR(200) UNIQUE,
 FOREIGN KEY (department_id) REFERENCES department(id)
) ENGINE=InnoDB;
CREATE TABLE ward (
 id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(200) NOT NULL UNIQUE,
 department_id INT NOT NULL,
 FOREIGN KEY (department_id) REFERENCES department(id)
) ENGINE=InnoDB;
CREATE TABLE bed (
 id INT PRIMARY KEY AUTO_INCREMENT, ward_id INT NOT NULL,
 label VARCHAR(200) NOT NULL, UNIQUE(ward_id,label),
 FOREIGN KEY (ward_id) REFERENCES ward(id)
) ENGINE=InnoDB;
CREATE TABLE nurse (
 id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(200) NOT NULL, ward_id INT NOT NULL,
 shift VARCHAR(200) NOT NULL CHECK(shift IN ('Morning','Evening','Night')),
 FOREIGN KEY (ward_id) REFERENCES ward(id)
) ENGINE=InnoDB;
CREATE TABLE patient (
 id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(200) NOT NULL CHECK(length(trim(name))>0),
 dob DATE NOT NULL, gender VARCHAR(200) NOT NULL CHECK(gender IN ('Male','Female','Other')),
 phone VARCHAR(200), address VARCHAR(200), blood_group VARCHAR(200) CHECK(blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-','Unknown')),
 created_at DATETIME NOT NULL
) ENGINE=InnoDB;
CREATE TABLE appointment (
 id INT PRIMARY KEY AUTO_INCREMENT, patient_id INT NOT NULL,
 doctor_id INT NOT NULL, starts_at DATETIME NOT NULL,
 status VARCHAR(200) NOT NULL DEFAULT 'Scheduled' CHECK(status IN ('Scheduled','Completed','Cancelled')),
 active_slot INT GENERATED ALWAYS AS (CASE WHEN status <> 'Cancelled' THEN 1 ELSE NULL END) STORED,
 UNIQUE(doctor_id,starts_at,active_slot), UNIQUE(patient_id,starts_at,active_slot),
 FOREIGN KEY (patient_id) REFERENCES patient(id),
 FOREIGN KEY (doctor_id) REFERENCES doctor(id)
) ENGINE=InnoDB;
CREATE TABLE encounter (
 id INT PRIMARY KEY AUTO_INCREMENT, appointment_id INT NOT NULL UNIQUE,
 diagnosis VARCHAR(500) NOT NULL, notes VARCHAR(2000) NOT NULL DEFAULT '', recorded_at DATETIME NOT NULL,
 FOREIGN KEY (appointment_id) REFERENCES appointment(id)
) ENGINE=InnoDB;
CREATE TABLE medicine (
 id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(200) NOT NULL UNIQUE, unit_price BIGINT NOT NULL CHECK(unit_price>=0),
 reorder_level INT NOT NULL DEFAULT 20 CHECK(reorder_level>=0)
) ENGINE=InnoDB;
CREATE TABLE medicine_batch (
 id INT PRIMARY KEY AUTO_INCREMENT, medicine_id INT NOT NULL,
 batch_code VARCHAR(200) NOT NULL UNIQUE, expiry_date DATE NOT NULL,
 stock INT NOT NULL CHECK(stock>=0),
 FOREIGN KEY (medicine_id) REFERENCES medicine(id)
) ENGINE=InnoDB;
CREATE TABLE prescription (
 id INT PRIMARY KEY AUTO_INCREMENT, encounter_id INT NOT NULL,
 medicine_id INT NOT NULL, quantity INT NOT NULL CHECK(quantity>0),
 instructions VARCHAR(500) NOT NULL,
 FOREIGN KEY (encounter_id) REFERENCES encounter(id),
 FOREIGN KEY (medicine_id) REFERENCES medicine(id)
) ENGINE=InnoDB;
CREATE TABLE dispensing (
 id INT PRIMARY KEY AUTO_INCREMENT, prescription_id INT NOT NULL UNIQUE,
 batch_id INT NOT NULL, quantity INT NOT NULL CHECK(quantity>0),
 dispensed_at DATETIME NOT NULL,
 FOREIGN KEY (prescription_id) REFERENCES prescription(id),
 FOREIGN KEY (batch_id) REFERENCES medicine_batch(id)
) ENGINE=InnoDB;
CREATE TABLE admission (
 id INT PRIMARY KEY AUTO_INCREMENT, patient_id INT NOT NULL,
 doctor_id INT NOT NULL, bed_id INT NOT NULL,
 admitted_at DATETIME NOT NULL, discharged_at DATETIME,
 active_stay INT GENERATED ALWAYS AS (CASE WHEN discharged_at IS NULL THEN 1 ELSE NULL END) STORED,
 CHECK(discharged_at IS NULL OR discharged_at>=admitted_at),
 UNIQUE(bed_id,active_stay), UNIQUE(patient_id,active_stay),
 FOREIGN KEY (patient_id) REFERENCES patient(id),
 FOREIGN KEY (doctor_id) REFERENCES doctor(id),
 FOREIGN KEY (bed_id) REFERENCES bed(id)
) ENGINE=InnoDB;
CREATE TABLE invoice (
 id INT PRIMARY KEY AUTO_INCREMENT, patient_id INT NOT NULL,
 issued_at DATETIME NOT NULL,
 FOREIGN KEY (patient_id) REFERENCES patient(id)
) ENGINE=InnoDB;
CREATE TABLE invoice_item (
 id INT PRIMARY KEY AUTO_INCREMENT, invoice_id INT NOT NULL,
 description VARCHAR(200) NOT NULL, quantity INT NOT NULL CHECK(quantity>0),
 unit_price BIGINT NOT NULL CHECK(unit_price>0),
 FOREIGN KEY (invoice_id) REFERENCES invoice(id)
) ENGINE=InnoDB;
CREATE TABLE payment (
 id INT PRIMARY KEY AUTO_INCREMENT, invoice_id INT NOT NULL,
 amount BIGINT NOT NULL CHECK(amount>0), method VARCHAR(200) NOT NULL CHECK(method IN ('Cash','Card','Transfer')),
 `reference` VARCHAR(200) NOT NULL UNIQUE, paid_at DATETIME NOT NULL,
 FOREIGN KEY (invoice_id) REFERENCES invoice(id)
) ENGINE=InnoDB;
CREATE TABLE audit_event (
 id INT PRIMARY KEY AUTO_INCREMENT, occurred_at DATETIME NOT NULL, action VARCHAR(200) NOT NULL,
 entity VARCHAR(200) NOT NULL, entity_id INT NOT NULL, summary VARCHAR(500) NOT NULL
) ENGINE=InnoDB;
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
