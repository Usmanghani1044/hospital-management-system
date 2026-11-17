"""Integration tests against fresh temporary SQLite databases."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from hospital.service import Hospital, money

class Workflows(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Hospital(Path(self.tmp.name)/'test.sqlite3');self.s.initialize()
    def tearDown(self):self.tmp.cleanup()
    def value(self,sql,args=()):
        c=self.s.connect()
        try:return c.execute(sql,args).fetchone()[0]
        finally:c.close()
    def future(self):return str(date.today()+timedelta(days=3))+'T10:00'
    def test_initialization_and_integrity(self):
        self.assertFalse(self.s.initialize());self.assertEqual(self.value('SELECT COUNT(*) FROM patient'),8)
        self.assertEqual(self.value('PRAGMA integrity_check'),'ok')
        c=self.s.connect()
        try:self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        finally:c.close()
    def test_register_and_invalid_birth(self):
        p={'name':'Test Patient','dob':'2000-01-01','gender':'Other','blood_group':'Unknown'}
        i=self.s.act('patient',p);self.assertEqual(self.value('SELECT name FROM patient WHERE id=?',(i,)),p['name'])
        for change in ({'dob':'2999-01-01'},{'name':' '},{'gender':'invalid'}):
            with self.assertRaises(ValueError):self.s.act('patient',{**p,**change})
    def test_booking_and_cancellation(self):
        p={'patient_id':1,'doctor_id':1,'starts_at':self.future()};i=self.s.act('book',p)
        for change in ({'patient_id':2},{'doctor_id':2}):
            with self.assertRaises(ValueError):self.s.act('book',{**p,**change})
        self.s.act('cancel',{'appointment_id':i});self.assertGreater(self.s.act('book',p),i)
        with self.assertRaises(ValueError):self.s.act('book',{**p,'starts_at':self.future().replace('10:00','10:15')})
    def test_concurrent_bookings(self):
        def attempt(patient):
            try:self.s.act('book',{'patient_id':patient,'doctor_id':1,'starts_at':self.future()});return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,[1,2]))
        self.assertEqual(sum(results),1)
    def test_encounter_and_distinct_patients(self):
        with self.s.transaction() as c:
            a=c.execute('INSERT INTO appointment (patient_id,doctor_id,starts_at) VALUES (1,1,?)',((datetime.now()-timedelta(days=2)).isoformat(timespec='seconds'),)).lastrowid
        self.s.act('encounter',{'appointment_id':a,'diagnosis':'Demo follow-up'})
        self.assertEqual(self.value('SELECT status FROM appointment WHERE id=?',(a,)),'Completed')
        d=next(d for d in self.s.snapshot()['doctor_activity'] if d['id']==1)
        self.assertEqual((d['visits'],d['patients']),(2,1))
        with self.assertRaises(ValueError):self.s.act('encounter',{'appointment_id':a,'diagnosis':'Again'})
    def test_future_encounter_rejected(self):
        i=self.s.act('book',{'patient_id':1,'doctor_id':1,'starts_at':self.future()})
        with self.assertRaises(ValueError):self.s.act('encounter',{'appointment_id':i,'diagnosis':'Too early'})
        self.s.act('cancel',{'appointment_id':i})
        with self.assertRaises(ValueError):self.s.act('encounter',{'appointment_id':i,'diagnosis':'Cancelled'})
    def test_bed_exclusivity_and_discharge(self):
        for p in ({'patient_id':2,'doctor_id':1,'bed_id':1},{'patient_id':1,'doctor_id':1,'bed_id':2}):
            with self.assertRaises(ValueError):self.s.act('admit',p)
        self.s.act('discharge',{'admission_id':1})
        self.assertGreater(self.s.act('admit',{'patient_id':2,'doctor_id':1,'bed_id':1}),1)
        with self.assertRaises(ValueError):self.s.act('discharge',{'admission_id':1})
    def test_dispense_only_once(self):
        self.s.act('dispense',{'prescription_id':1,'batch_id':1})
        with self.assertRaises(ValueError):self.s.act('dispense',{'prescription_id':1,'batch_id':1})
        self.assertEqual(self.value('SELECT stock FROM medicine_batch WHERE id=1'),75)
    def test_invalid_batches(self):
        with self.assertRaises(ValueError):self.s.act('dispense',{'prescription_id':1,'batch_id':2})
        with self.s.transaction() as c:c.execute("UPDATE medicine_batch SET expiry_date='2000-01-01' WHERE id=1")
        with self.assertRaises(ValueError):self.s.act('dispense',{'prescription_id':1,'batch_id':1})
        with self.s.transaction() as c:c.execute('UPDATE medicine_batch SET expiry_date=?,stock=1 WHERE id=1',(str(date.today()+timedelta(days=10)),))
        with self.assertRaises(ValueError):self.s.act('dispense',{'prescription_id':1,'batch_id':1})
        self.assertEqual(self.value('SELECT stock FROM medicine_batch WHERE id=1'),1)
    def test_itemized_invoice_and_payments(self):
        i=self.s.act('invoice',{'patient_id':1,'items':[{'description':'Consultation','quantity':2,'unit_price':'1500.25'},{'description':'Demo service','quantity':1,'unit_price':'499.50'}]})
        self.assertEqual(self.value('SELECT total FROM v_invoice_balance WHERE id=?',(i,)),350000)
        self.s.act('payment',{'invoice_id':i,'amount':'1000','method':'Cash','reference':'TEST-1'})
        self.assertEqual(self.value('SELECT status FROM v_invoice_balance WHERE id=?',(i,)),'Partial')
        with self.assertRaises(ValueError):self.s.act('payment',{'invoice_id':i,'amount':'2500.01','method':'Cash','reference':'OVER'})
        self.s.act('payment',{'invoice_id':i,'amount':'2500','method':'Card','reference':'TEST-2'})
        self.assertEqual(self.value('SELECT status FROM v_invoice_balance WHERE id=?',(i,)),'Paid')
    def test_invoice_rollback(self):
        n=self.value('SELECT COUNT(*) FROM invoice')
        with self.assertRaises(ValueError):self.s.act('invoice',{'patient_id':1,'items':[{'description':'Valid','quantity':1,'unit_price':'100'},{'description':'Invalid','quantity':0,'unit_price':'20'}]})
        self.assertEqual(self.value('SELECT COUNT(*) FROM invoice'),n)
    def test_concurrent_overpayment_and_duplicate_reference(self):
        def pay(reference):
            try:self.s.act('payment',{'invoice_id':3,'amount':'1000','method':'Cash','reference':reference});return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(pay,['TEST-A','TEST-B']))
        self.assertEqual(sum(results),1)
        ref='TEST-A' if self.value("SELECT COUNT(*) FROM payment WHERE reference='TEST-A'") else 'TEST-B'
        with self.assertRaises(ValueError):self.s.act('payment',{'invoice_id':2,'amount':'1','method':'Cash','reference':ref})
    def test_audit_failure_rolls_back_stock(self):
        with patch.object(self.s,'audit',side_effect=RuntimeError('Simulated failure')):
            with self.assertRaises(RuntimeError):self.s.act('dispense',{'prescription_id':1,'batch_id':1})
        self.assertEqual(self.value('SELECT stock FROM medicine_batch WHERE id=1'),80)
        self.assertEqual(self.value('SELECT COUNT(*) FROM dispensing'),0)
    def test_exact_money(self):
        self.assertEqual(money('10.25'),1025)
        for value in ['NaN','Infinity','-1','0','1.001']:
            with self.assertRaises(ValueError):money(value)
    def test_export_and_backup(self):
        self.s.act('patient',{'name':'=DEMO()','dob':'2000-01-01','gender':'Other','blood_group':'Unknown'})
        self.assertIn("'=DEMO()",self.s.export('patients'))
        path=Path(self.tmp.name)/'backup.sqlite3';self.s.backup(path)
        self.assertEqual(Hospital(path).snapshot()['stats'],self.s.snapshot()['stats'])
        with self.assertRaises(ValueError):self.s.export('bad;DROP TABLE patient')
    def test_new_batch_and_prescription(self):
        i=self.s.act('batch',{'medicine_id':1,'batch_code':'TEST-BATCH','expiry_date':str(date.today()+timedelta(days=30)),'stock':50})
        self.assertEqual(self.value('SELECT stock FROM medicine_batch WHERE id=?',(i,)),50)
        rx=self.s.act('prescribe',{'encounter_id':1,'medicine_id':1,'quantity':3,'instructions':'Demo only'})
        self.s.act('dispense',{'prescription_id':rx,'batch_id':i})
        self.assertEqual(self.value('SELECT stock FROM medicine_batch WHERE id=?',(i,)),47)
    def test_missing_foreign_keys(self):
        with self.assertRaises(ValueError):self.s.act('admit',{'patient_id':999,'doctor_id':1,'bed_id':2})
        self.assertEqual(self.value('SELECT COUNT(*) FROM admission'),2)

if __name__=='__main__':unittest.main()
