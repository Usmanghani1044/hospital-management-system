"""Transactional workflows. Author: Muhammad Usman Ghani.

AI-assisted extension of the author's original database coursework.
SQLite uses BEGIN IMMEDIATE to serialize writes before validating balances/stock.
"""
import csv
import io
import sqlite3
from contextlib import contextmanager, nullcontext
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now().isoformat(timespec='seconds')


def required(value, label, maximum=200):
    text = str(value or '').strip()
    if not text or len(text) > maximum:
        raise ValueError(f'{label} is required (maximum {maximum} characters).')
    return text


def integer(value, label, minimum=1, maximum=1000000):
    try:
        result = int(str(value))
    except (ValueError, TypeError):
        raise ValueError(f'{label} must be a whole number.')
    if not minimum <= result <= maximum:
        raise ValueError(f'{label} must be between {minimum} and {maximum}.')
    return result


def money(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0 or number > 10000000:
            raise ValueError('Amount must be positive and at most PKR 10,000,000.')
        if number != number.quantize(Decimal('0.01')):
            raise ValueError('Use at most two decimal places for money.')
        return int(number * 100)
    except (InvalidOperation, TypeError):
        raise ValueError('Enter a valid amount in PKR.')


class Hospital:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        return c

    @contextmanager
    def transaction(self):
        c = self.connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except sqlite3.IntegrityError as exc:
            c.rollback()
            raise ValueError('This conflicts with an existing record or a database constraint. Check the IDs, booking slot, bed, or reference.') from exc
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as c:
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='patient'").fetchone():
                return False
            for statement in (ROOT / 'sql/schema_sqlite.sql').read_text(encoding='utf-8').split(';'):
                if statement.strip():
                    c.execute(statement)
            self.seed(c)
        return True

    def seed(self, connection=None):
        """Entirely fictional demo records; no real patient information."""
        today = date.today()
        with (nullcontext(connection) if connection is not None else self.transaction()) as c:
            c.executemany('INSERT INTO department VALUES (?,?,?)',[(1,'Cardiology','North wing'),(2,'General Medicine','East wing'),(3,'Pediatrics','South wing')])
            c.executemany('INSERT INTO doctor VALUES (?,?,?,?,?)',[(1,'Dr. Amina Shah','Cardiology',1,'amina@example.test'),(2,'Dr. Omar Malik','General Medicine',2,'omar@example.test'),(3,'Dr. Sara Noor','Pediatrics',3,'sara@example.test')])
            c.executemany('INSERT INTO ward VALUES (?,?,?)',[(1,'Cardiac Ward',1),(2,'General Ward',2),(3,'Pediatric Ward',3)])
            c.executemany('INSERT INTO bed VALUES (?,?,?)',[(i,(i-1)//4+1,f'B-{i:02}') for i in range(1,13)])
            c.executemany('INSERT INTO nurse VALUES (?,?,?,?)',[(1,'Nurse Hina',1,'Morning'),(2,'Nurse Bilal',2,'Evening'),(3,'Nurse Zara',3,'Night')])
            names=['Ali Raza','Sana Tariq','Kamran Iqbal','Maryam Shafiq','Tariq Mehmood','Nida Butt','Hassan Nawaz','Zoya Alam']
            for i,name in enumerate(names,1):
                c.execute('INSERT INTO patient VALUES (?,?,?,?,?,?,?,?)',(i,name,f'{1980+i*3}-05-12','Male' if i%2 else 'Female',f'DEMO-{i:03}','Fictional demo address','Unknown',now()))
            for i in range(1,9):
                day=today-timedelta(days=1) if i<3 else today+timedelta(days=1)
                stamp=f'{day}T{8+i:02}:00:00'
                c.execute('INSERT INTO appointment (id,patient_id,doctor_id,starts_at,status) VALUES (?,?,?,?,?)',(i,i,(i-1)%3+1,stamp,'Completed' if i<3 else 'Scheduled'))
            for i in (1,2):
                c.execute('INSERT INTO encounter VALUES (?,?,?,?,?)',(i,i,'Demo consultation','Fictional record for software testing.',now()))
            for i,(name,price) in enumerate([('Demo medicine A',5000),('Demo medicine B',12000),('Demo medicine C',8500)],1):
                c.execute('INSERT INTO medicine VALUES (?,?,?,?)',(i,name,price,20))
                c.execute('INSERT INTO medicine_batch VALUES (?,?,?,?,?)',(i,i,f'DEMO-BATCH-{i}',str(today+timedelta(days=180)),80 if i==1 else 12))
            c.execute('INSERT INTO prescription VALUES (1,1,1,5,?)',('Demo instructions only; not medical advice.',))
            c.execute('INSERT INTO admission (patient_id,doctor_id,bed_id,admitted_at) VALUES (1,1,1,?)',(now(),))
            c.execute('INSERT INTO admission (patient_id,doctor_id,bed_id,admitted_at) VALUES (3,2,5,?)',(now(),))
            for i in (1,2,3):
                c.execute('INSERT INTO invoice VALUES (?,?,?)',(i,i,now()))
                c.execute('INSERT INTO invoice_item (invoice_id,description,quantity,unit_price) VALUES (?,?,?,?)',(i,'Consultation',1,150000))
            c.execute('INSERT INTO payment (invoice_id,amount,method,reference,paid_at) VALUES (1,150000,?,?,?)',('Cash','DEMO-PAY-001',now()))
            c.execute('INSERT INTO payment (invoice_id,amount,method,reference,paid_at) VALUES (2,50000,?,?,?)',('Card','DEMO-PAY-002',now()))
            self.audit(c,'seed','database',0,'Fictional demonstration data initialized')

    @staticmethod
    def audit(c,action,entity,entity_id,summary):
        c.execute('INSERT INTO audit_event (occurred_at,action,entity,entity_id,summary) VALUES (?,?,?,?,?)',(now(),action,entity,entity_id,summary))

    @staticmethod
    def exists(c,table,identifier):
        # table names are internal constants, never user input.
        row=c.execute(f'SELECT * FROM {table} WHERE id=?',(identifier,)).fetchone()
        if row is None:
            raise ValueError(f'{table.replace("_"," ").title()} ID {identifier} does not exist.')
        return row

    def act(self,action,p):
        handlers={'patient':self.add_patient,'book':self.book,'cancel':self.cancel,
                  'encounter':self.encounter,'prescribe':self.prescribe,'dispense':self.dispense,
                  'admit':self.admit,'discharge':self.discharge,'invoice':self.invoice,
                  'payment':self.payment,'batch':self.batch}
        if action not in handlers:
            raise ValueError('Unknown action.')
        with self.transaction() as c:
            identifier=handlers[action](c,p)
            self.audit(c,action,action,identifier,'Completed via local application')
        return identifier

    def add_patient(self,c,p):
        name=required(p.get('name'),'Name',100)
        try:
            dob=date.fromisoformat(p.get('dob',''))
        except (ValueError,TypeError):
            raise ValueError('Date of birth must be a valid date.')
        if dob>date.today() or dob.year<1900:
            raise ValueError('Date of birth must be between 1900 and today.')
        gender=p.get('gender','');blood=p.get('blood_group','Unknown')
        phone=str(p.get('phone','')).strip();address=str(p.get('address','')).strip()
        if len(phone)>30 or len(address)>200:
            raise ValueError('Phone or address is too long.')
        return c.execute('INSERT INTO patient (name,dob,gender,phone,address,blood_group,created_at) VALUES (?,?,?,?,?,?,?)',(name,str(dob),gender,phone,address,blood,now())).lastrowid

    def book(self,c,p):
        patient=integer(p.get('patient_id'),'Patient ID');doctor=integer(p.get('doctor_id'),'Doctor ID')
        self.exists(c,'patient',patient);self.exists(c,'doctor',doctor)
        try:
            stamp=datetime.fromisoformat(p.get('starts_at',''))
        except (ValueError,TypeError):
            raise ValueError('Choose a valid appointment date and time.')
        if stamp.tzinfo is not None or stamp<datetime.now() or stamp.minute not in (0,30) or stamp.second or stamp.microsecond:
            raise ValueError('Choose a future local time on a 30-minute boundary (:00 or :30).')
        return c.execute('INSERT INTO appointment (patient_id,doctor_id,starts_at) VALUES (?,?,?)',(patient,doctor,stamp.isoformat(timespec='seconds'))).lastrowid

    def cancel(self,c,p):
        i=integer(p.get('appointment_id'),'Appointment ID');row=self.exists(c,'appointment',i)
        if row['status']!='Scheduled':raise ValueError('Only scheduled appointments can be cancelled.')
        c.execute("UPDATE appointment SET status='Cancelled' WHERE id=?",(i,));return i

    def encounter(self,c,p):
        i=integer(p.get('appointment_id'),'Appointment ID');row=self.exists(c,'appointment',i)
        if row['status']!='Scheduled':raise ValueError('An encounter requires a scheduled appointment.')
        if datetime.fromisoformat(row['starts_at'])>datetime.now():raise ValueError('A future appointment cannot be completed yet.')
        diagnosis=required(p.get('diagnosis'),'Diagnosis',500);notes=str(p.get('notes',''))
        if len(notes)>2000:raise ValueError('Notes must be at most 2,000 characters.')
        e=c.execute('INSERT INTO encounter (appointment_id,diagnosis,notes,recorded_at) VALUES (?,?,?,?)',(i,diagnosis,notes,now())).lastrowid
        c.execute("UPDATE appointment SET status='Completed' WHERE id=?",(i,));return e

    def prescribe(self,c,p):
        e=integer(p.get('encounter_id'),'Encounter ID');m=integer(p.get('medicine_id'),'Medicine ID')
        self.exists(c,'encounter',e);self.exists(c,'medicine',m)
        return c.execute('INSERT INTO prescription (encounter_id,medicine_id,quantity,instructions) VALUES (?,?,?,?)',(e,m,integer(p.get('quantity'),'Quantity',1,10000),required(p.get('instructions'),'Instructions',500))).lastrowid

    def dispense(self,c,p):
        i=integer(p.get('prescription_id'),'Prescription ID');b=integer(p.get('batch_id'),'Batch ID')
        rx=self.exists(c,'prescription',i);batch=self.exists(c,'medicine_batch',b)
        if rx['medicine_id']!=batch['medicine_id']:raise ValueError('Batch does not contain the prescribed medicine.')
        if date.fromisoformat(batch['expiry_date'])<date.today():raise ValueError('Expired batches cannot be dispensed.')
        if batch['stock']<rx['quantity']:raise ValueError('Insufficient stock in this batch.')
        if c.execute('SELECT 1 FROM dispensing WHERE prescription_id=?',(i,)).fetchone():raise ValueError('This prescription has already been dispensed.')
        c.execute('UPDATE medicine_batch SET stock=stock-? WHERE id=?',(rx['quantity'],b))
        return c.execute('INSERT INTO dispensing (prescription_id,batch_id,quantity,dispensed_at) VALUES (?,?,?,?)',(i,b,rx['quantity'],now())).lastrowid

    def admit(self,c,p):
        patient=integer(p.get('patient_id'),'Patient ID');doctor=integer(p.get('doctor_id'),'Doctor ID');bed=integer(p.get('bed_id'),'Bed ID')
        self.exists(c,'patient',patient);self.exists(c,'doctor',doctor);self.exists(c,'bed',bed)
        return c.execute('INSERT INTO admission (patient_id,doctor_id,bed_id,admitted_at) VALUES (?,?,?,?)',(patient,doctor,bed,now())).lastrowid

    def discharge(self,c,p):
        i=integer(p.get('admission_id'),'Admission ID');row=self.exists(c,'admission',i)
        if row['discharged_at']:raise ValueError('This admission is already discharged.')
        c.execute('UPDATE admission SET discharged_at=? WHERE id=?',(now(),i));return i

    def invoice(self,c,p):
        patient=integer(p.get('patient_id'),'Patient ID');self.exists(c,'patient',patient)
        items=p.get('items')
        if not isinstance(items,list) or not 1<=len(items)<=20:raise ValueError('An invoice needs 1–20 line items.')
        i=c.execute('INSERT INTO invoice (patient_id,issued_at) VALUES (?,?)',(patient,now())).lastrowid
        total=0
        for item in items:
            quantity=integer(item.get('quantity'),'Quantity',1,1000);price=money(item.get('unit_price'))
            total+=quantity*price
            if total>1000000000:raise ValueError('Invoice total exceeds the demo limit of PKR 10,000,000.')
            c.execute('INSERT INTO invoice_item (invoice_id,description,quantity,unit_price) VALUES (?,?,?,?)',(i,required(item.get('description'),'Description'),quantity,price))
        return i

    def payment(self,c,p):
        i=integer(p.get('invoice_id'),'Invoice ID');self.exists(c,'invoice',i)
        amount=money(p.get('amount'));balance=c.execute('SELECT balance FROM v_invoice_balance WHERE id=?',(i,)).fetchone()[0]
        if amount>balance:raise ValueError('Payment exceeds the outstanding balance.')
        return c.execute('INSERT INTO payment (invoice_id,amount,method,reference,paid_at) VALUES (?,?,?,?,?)',(i,amount,p.get('method'),required(p.get('reference'),'Unique payment reference',100),now())).lastrowid

    def batch(self,c,p):
        m=integer(p.get('medicine_id'),'Medicine ID');self.exists(c,'medicine',m)
        try:expiry=date.fromisoformat(p.get('expiry_date',''))
        except (ValueError,TypeError):raise ValueError('Expiry must be a valid date.')
        if expiry<date.today():raise ValueError('New stock must not already be expired.')
        return c.execute('INSERT INTO medicine_batch (medicine_id,batch_code,expiry_date,stock) VALUES (?,?,?,?)',(m,required(p.get('batch_code'),'Batch code',100),str(expiry),integer(p.get('stock'),'Stock',1))).lastrowid

    def snapshot(self):
        queries={
            'patients':'SELECT * FROM patient ORDER BY id DESC',
            'doctors':'SELECT d.*,dp.name department FROM doctor d JOIN department dp ON dp.id=d.department_id',
            'nurses':'SELECT n.*,w.name ward FROM nurse n JOIN ward w ON w.id=n.ward_id',
            'appointments':'''SELECT a.id,a.patient_id,p.name patient,a.doctor_id,d.name doctor,a.starts_at,a.status FROM appointment a JOIN patient p ON p.id=a.patient_id JOIN doctor d ON d.id=a.doctor_id ORDER BY a.starts_at DESC''',
            'encounters':'''SELECT e.*,p.name patient,d.name doctor FROM encounter e JOIN appointment a ON a.id=e.appointment_id JOIN patient p ON p.id=a.patient_id JOIN doctor d ON d.id=a.doctor_id ORDER BY e.id DESC''',
            'beds':'SELECT * FROM v_bed_status ORDER BY id',
            'admissions':'''SELECT a.*,p.name patient,d.name doctor,b.label bed,w.name ward FROM admission a JOIN patient p ON p.id=a.patient_id JOIN doctor d ON d.id=a.doctor_id JOIN bed b ON b.id=a.bed_id JOIN ward w ON w.id=b.ward_id ORDER BY a.id DESC''',
            'invoices':'SELECT * FROM v_invoice_balance ORDER BY id DESC',
            'invoice_items':'SELECT * FROM invoice_item ORDER BY id',
            'payments':'SELECT * FROM payment ORDER BY id DESC',
            'medicines':'SELECT * FROM medicine ORDER BY id',
            'batches':'''SELECT b.*,m.name medicine FROM medicine_batch b JOIN medicine m ON m.id=b.medicine_id ORDER BY b.expiry_date''',
            'prescriptions':'''SELECT r.*,m.name medicine,p.name patient,CASE WHEN ds.id IS NULL THEN 'Pending' ELSE 'Dispensed' END status FROM prescription r JOIN medicine m ON m.id=r.medicine_id JOIN encounter e ON e.id=r.encounter_id JOIN appointment a ON a.id=e.appointment_id JOIN patient p ON p.id=a.patient_id LEFT JOIN dispensing ds ON ds.prescription_id=r.id ORDER BY r.id DESC''',
            'doctor_activity':'''SELECT d.id,d.name,COUNT(e.id) visits,COUNT(DISTINCT CASE WHEN e.id IS NOT NULL THEN a.patient_id END) patients FROM doctor d LEFT JOIN appointment a ON a.doctor_id=d.id LEFT JOIN encounter e ON e.appointment_id=a.id GROUP BY d.id,d.name''',
            'audit':'SELECT * FROM audit_event ORDER BY id DESC LIMIT 100'
        }
        c=self.connect()
        try:
            # One read snapshot prevents inconsistent totals during concurrent writes.
            c.execute('BEGIN')
            result={key:[dict(row) for row in c.execute(sql)] for key,sql in queries.items()}
            result['today']=str(date.today())
            result['stats']={'patients':len(result['patients']),'scheduled':sum(a['status']=='Scheduled' for a in result['appointments']),
                'occupied':sum(b['status']=='Occupied' for b in result['beds']),'beds':len(result['beds']),
                'collected':sum(p['amount'] for p in result['payments']),'outstanding':sum(i['balance'] for i in result['invoices'])}
            return result
        finally:c.close()

    def export(self,name):
        allowed={'patients','appointments','admissions','invoices','payments','doctor_activity'}
        if name not in allowed:raise ValueError('Unknown export.')
        rows=self.snapshot()[name];out=io.StringIO()
        if rows:
            w=csv.DictWriter(out,fieldnames=rows[0].keys());w.writeheader()
            # Protect exported spreadsheets from interpreting text as formulas.
            w.writerows({k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()} for row in rows)
        return out.getvalue()

    def backup(self,destination):
        source=self.connect();target=sqlite3.connect(destination)
        try:source.backup(target)
        finally:target.close();source.close()
