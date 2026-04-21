from backend.db.database import engine, SessionLocal, Base
from backend.db.models import (
    Customer, Loan, PaymentHistory, InteractionHistory,
    GraceRequest, RestructureRequest, CustomerPreference,
    ChatSession, ChatMessage, BankOfficer,
    BounceRiskProfile, AutoPayMandate, BouncePreventionAction
)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Customer).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    print("Seeding database...")

    # ── Bank Officers ──────────────────────────────────────────────
    officers = [
        BankOfficer(officer_id="920532", officer_name="Rajesh Kumar",  email="rajesh.kumar@unionbank.com",  password="Ub@920532", department="Collections"),
        BankOfficer(officer_id="920614", officer_name="Priya Sharma",  email="priya.sharma@unionbank.com",  password="Ub@920614", department="Recovery"),
        BankOfficer(officer_id="820654", officer_name="Anand Verma",   email="anand.verma@unionbank.com",   password="Ub@820654", department="Collections"),
        BankOfficer(officer_id="830271", officer_name="Deepa Nair",    email="deepa.nair@unionbank.com",    password="Ub@830271", department="Recovery"),
        BankOfficer(officer_id="910488", officer_name="Suresh Pillai", email="suresh.pillai@unionbank.com", password="Ub@910488", department="Collections"),
    ]
    db.add_all(officers)

    # ── 50 Customers ───────────────────────────────────────────────
    customers = [
        Customer(customer_id="CUST001", customer_name="Arun Mehta",       mobile_number="9876543210",    email_id="arun.mehta@email.com",          preferred_language="English",   preferred_channel="WhatsApp",   credit_score=620, monthly_income=45000.0, password="password123", relationship_assessment="You have maintained a generally stable repayment pattern. A few short-term delays were observed recently but overall behavior remains positive."),
        Customer(customer_id="CUST002", customer_name="Sunita Rao",        mobile_number="9845678901",    email_id="sunita.rao@email.com",           preferred_language="Hindi",     preferred_channel="SMS",        credit_score=710, monthly_income=72000.0, password="password123", relationship_assessment="Excellent repayment track record. Consistent and timely payments reflect strong financial discipline."),
        Customer(customer_id="CUST003", customer_name="Vikram Nair",       mobile_number="9712345678",    email_id="vikram.nair@email.com",          preferred_language="English",   preferred_channel="Email",      credit_score=540, monthly_income=38000.0, password="password123", relationship_assessment="Recent payment behavior shows irregularity with multiple missed EMIs. Please contact the bank to discuss support options."),
        Customer(customer_id="CUST004", customer_name="Meena Pillai",      mobile_number="9632587410",    email_id="meena.pillai@email.com",         preferred_language="Tamil",     preferred_channel="Voice Call", credit_score=680, monthly_income=55000.0, password="password123", relationship_assessment="Consistent repayment behavior over the past year. A minor delay last month appears isolated. Your next EMI is due in 3 days."),
        Customer(customer_id="CUST005", customer_name="Rahul Joshi",       mobile_number="9523698741",    email_id="rahul.joshi@email.com",          preferred_language="English",   preferred_channel="Email",      credit_score=490, monthly_income=32000.0, password="password123", relationship_assessment="Account flagged for high delinquency risk. Multiple EMIs missed in past 2 months. Please contact the bank at the earliest."),
        Customer(customer_id="CUST006", customer_name="Anjali Singh",      mobile_number="9874563210",    email_id="anjali.singh@email.com",         preferred_language="Hindi",     preferred_channel="WhatsApp",   credit_score=750, monthly_income=90000.0, password="password123", relationship_assessment="Premium customer with outstanding repayment history. All EMIs paid on time. Thank you for your continued trust."),
        Customer(customer_id="CUST007", customer_name="Prabhat Kumar",     mobile_number="+919958270536", email_id="prabhatkumar.tech20@gmail.com",  preferred_language="English",   preferred_channel="Email",      credit_score=720, monthly_income=65000.0, password="password123", relationship_assessment="Valued customer with good repayment track record. One loan has a minor overdue of 7 days. We encourage timely payment."),
        Customer(customer_id="CUST008", customer_name="Kiran Desai",       mobile_number="9811223344",    email_id="kiran.desai@email.com",          preferred_language="Gujarati",  preferred_channel="WhatsApp",   credit_score=580, monthly_income=41000.0, password="password123", relationship_assessment="Moderate repayment behaviour with occasional delays. Your account requires closer monitoring."),
        Customer(customer_id="CUST009", customer_name="Pooja Iyer",        mobile_number="9922334455",    email_id="pooja.iyer@email.com",           preferred_language="Tamil",     preferred_channel="SMS",        credit_score=730, monthly_income=68000.0, password="password123", relationship_assessment="Strong payment history with no significant overdue. A reliable borrower."),
        Customer(customer_id="CUST010", customer_name="Mohit Agarwal",     mobile_number="9033445566",    email_id="mohit.agarwal@email.com",        preferred_language="Hindi",     preferred_channel="Email",      credit_score=510, monthly_income=29000.0, password="password123", relationship_assessment="High risk profile. Multiple EMIs overdue. Immediate outreach required."),
        Customer(customer_id="CUST011", customer_name="Sneha Kulkarni",    mobile_number="9144556677",    email_id="sneha.kulkarni@email.com",       preferred_language="Marathi",   preferred_channel="WhatsApp",   credit_score=695, monthly_income=57000.0, password="password123", relationship_assessment="Generally timely payments with one minor delay in last quarter. Good standing."),
        Customer(customer_id="CUST012", customer_name="Arvind Chauhan",    mobile_number="9255667788",    email_id="arvind.chauhan@email.com",       preferred_language="Hindi",     preferred_channel="Voice Call", credit_score=460, monthly_income=25000.0, password="password123", relationship_assessment="Critical risk. Loan severely overdue. Legal escalation may be warranted."),
        Customer(customer_id="CUST013", customer_name="Neha Bhatia",       mobile_number="9366778899",    email_id="neha.bhatia@email.com",          preferred_language="English",   preferred_channel="Email",      credit_score=760, monthly_income=95000.0, password="password123", relationship_assessment="Excellent credit profile. All dues cleared consistently. Premium borrower."),
        Customer(customer_id="CUST014", customer_name="Suresh Tiwari",     mobile_number="9477889900",    email_id="suresh.tiwari@email.com",        preferred_language="Hindi",     preferred_channel="SMS",        credit_score=575, monthly_income=36000.0, password="password123", relationship_assessment="Moderate risk. Payments often delayed by 5-10 days. Needs reminders."),
        Customer(customer_id="CUST015", customer_name="Kavitha Menon",     mobile_number="9588990011",    email_id="kavitha.menon@email.com",        preferred_language="Malayalam", preferred_channel="WhatsApp",   credit_score=640, monthly_income=48000.0, password="password123", relationship_assessment="Stable payment behaviour. Minor delay in last 2 months. Self-cure likely."),
        Customer(customer_id="CUST016", customer_name="Deepak Saxena",     mobile_number="9699001122",    email_id="deepak.saxena@email.com",        preferred_language="Hindi",     preferred_channel="Email",      credit_score=525, monthly_income=31000.0, password="password123", relationship_assessment="High risk. Repeated partial payments. Restructuring discussion recommended."),
        Customer(customer_id="CUST017", customer_name="Lakshmi Venkat",    mobile_number="9700112233",    email_id="lakshmi.venkat@email.com",       preferred_language="Telugu",    preferred_channel="Voice Call", credit_score=705, monthly_income=61000.0, password="password123", relationship_assessment="Consistent repayment. One missed payment in Oct 2025 due to medical emergency. Now back on track."),
        Customer(customer_id="CUST018", customer_name="Ravi Shankar",      mobile_number="9811223300",    email_id="ravi.shankar@email.com",         preferred_language="Hindi",     preferred_channel="WhatsApp",   credit_score=555, monthly_income=33000.0, password="password123", relationship_assessment="Moderate risk with increasing DPD trend. Proactive outreach recommended."),
        Customer(customer_id="CUST019", customer_name="Anita Deshmukh",    mobile_number="9922334400",    email_id="anita.deshmukh@email.com",       preferred_language="Marathi",   preferred_channel="SMS",        credit_score=670, monthly_income=52000.0, password="password123", relationship_assessment="Good payment pattern. Occasional 3-5 day delays. Low risk overall."),
        Customer(customer_id="CUST020", customer_name="Prakash Reddy",     mobile_number="9033445500",    email_id="prakash.reddy@email.com",        preferred_language="Telugu",    preferred_channel="Email",      credit_score=490, monthly_income=27000.0, password="password123", relationship_assessment="High delinquency risk. Business loan overdue by 35+ days. Urgent intervention needed."),
        Customer(customer_id="CUST021", customer_name="Swati Joshi",       mobile_number="9144556600",    email_id="swati.joshi@email.com",          preferred_language="Hindi",     preferred_channel="WhatsApp",   credit_score=715, monthly_income=67000.0, password="password123", relationship_assessment="Strong repayment record. No overdue. Prepayment interest shown in last interaction."),
        Customer(customer_id="CUST022", customer_name="Manoj Kapoor",      mobile_number="9255667700",    email_id="manoj.kapoor@email.com",         preferred_language="Hindi",     preferred_channel="Voice Call", credit_score=538, monthly_income=34000.0, password="password123", relationship_assessment="Medium-high risk. EMI delays observed in 3 of last 6 months."),
        Customer(customer_id="CUST023", customer_name="Divya Krishnan",    mobile_number="9366778800",    email_id="divya.krishnan@email.com",       preferred_language="Tamil",     preferred_channel="Email",      credit_score=745, monthly_income=84000.0, password="password123", relationship_assessment="Premium customer. Consistent payments. Recently requested loan top-up."),
        Customer(customer_id="CUST024", customer_name="Ajay Patil",        mobile_number="9477889800",    email_id="ajay.patil@email.com",           preferred_language="Marathi",   preferred_channel="WhatsApp",   credit_score=562, monthly_income=38000.0, password="password123", relationship_assessment="Moderate risk. Salary delays cited in previous interactions. Monitor closely."),
        Customer(customer_id="CUST025", customer_name="Rekha Gupta",       mobile_number="9588990000",    email_id="rekha.gupta@email.com",          preferred_language="Hindi",     preferred_channel="SMS",        credit_score=610, monthly_income=44000.0, password="password123", relationship_assessment="Borderline medium risk. Payments mostly on time with occasional short delays."),
        Customer(customer_id="CUST026", customer_name="Nitin Malhotra",    mobile_number="9699001100",    email_id="nitin.malhotra@email.com",       preferred_language="Hindi",     preferred_channel="Email",      credit_score=480, monthly_income=26000.0, password="password123", relationship_assessment="High risk. Multiple loans with overlapping overdue. Restructuring recommended."),
        Customer(customer_id="CUST027", customer_name="Preeti Sinha",      mobile_number="9700112200",    email_id="preeti.sinha@email.com",         preferred_language="Hindi",     preferred_channel="WhatsApp",   credit_score=688, monthly_income=54000.0, password="password123", relationship_assessment="Reliable borrower. Minor overdue this month. Self-cure probability high."),
        Customer(customer_id="CUST028", customer_name="Sanjay Mehrotra",   mobile_number="9811223311",    email_id="sanjay.mehrotra@email.com",      preferred_language="Hindi",     preferred_channel="Voice Call", credit_score=530, monthly_income=30000.0, password="password123", relationship_assessment="Elevated risk. Expressed financial hardship in last call. Grace period request under consideration."),
        Customer(customer_id="CUST029", customer_name="Usha Rani",         mobile_number="9922334411",    email_id="usha.rani@email.com",            preferred_language="Telugu",    preferred_channel="SMS",        credit_score=660, monthly_income=49000.0, password="password123", relationship_assessment="Mostly on-time. One partial payment in Dec 2025. Good standing maintained."),
        Customer(customer_id="CUST030", customer_name="Rohit Bansal",      mobile_number="9033445511",    email_id="rohit.bansal@email.com",         preferred_language="Hindi",     preferred_channel="Email",      credit_score=505, monthly_income=28500.0, password="password123", relationship_assessment="High risk borrower. Business downturn cited. 45+ DPD on primary loan."),
        Customer(customer_id="CUST031", customer_name="Geeta Narayanan",   mobile_number="9144556611",    email_id="geeta.narayanan@email.com",      preferred_language="Tamil",     preferred_channel="WhatsApp",   credit_score=720, monthly_income=70000.0, password="password123", relationship_assessment="Excellent payment history. No overdue. Eligible for loyalty benefits."),
        Customer(customer_id="CUST032", customer_name="Alok Shrivastava",  mobile_number="9255667711",    email_id="alok.shrivastava@email.com",     preferred_language="Hindi",     preferred_channel="Email",      credit_score=548, monthly_income=35000.0, password="password123", relationship_assessment="Moderate risk. Delay pattern observed every 3rd month. Salary irregularity suspected."),
        Customer(customer_id="CUST033", customer_name="Rani Mukherjee",    mobile_number="9366778811",    email_id="rani.mukherjee@email.com",       preferred_language="Bengali",   preferred_channel="WhatsApp",   credit_score=695, monthly_income=60000.0, password="password123", relationship_assessment="Good repayment behaviour. EMI due in 4 days. No issues noted."),
        Customer(customer_id="CUST034", customer_name="Vikas Tripathi",    mobile_number="9477889811",    email_id="vikas.tripathi@email.com",       preferred_language="Hindi",     preferred_channel="Voice Call", credit_score=472, monthly_income=24000.0, password="password123", relationship_assessment="Critical risk. Loan overdue 60+ days. Legal notice may be required."),
        Customer(customer_id="CUST035", customer_name="Nandita Choudhary", mobile_number="9588990022",    email_id="nandita.choudhary@email.com",    preferred_language="Bengali",   preferred_channel="Email",      credit_score=735, monthly_income=80000.0, password="password123", relationship_assessment="Premium profile. Consistent on-time payments. Recently requested balance transfer."),
        Customer(customer_id="CUST036", customer_name="Gaurav Mishra",     mobile_number="9699001133",    email_id="gaurav.mishra@email.com",        preferred_language="Hindi",     preferred_channel="WhatsApp",   credit_score=590, monthly_income=42000.0, password="password123", relationship_assessment="Moderate risk. Payment delays correlate with month-end. Remind on 25th of each month."),
        Customer(customer_id="CUST037", customer_name="Sangeetha Rajan",   mobile_number="9700112244",    email_id="sangeetha.rajan@email.com",      preferred_language="Tamil",     preferred_channel="SMS",        credit_score=658, monthly_income=47000.0, password="password123", relationship_assessment="Reliable. Minor delay observed once in last 12 months. Low risk."),
        Customer(customer_id="CUST038", customer_name="Harish Nambiar",    mobile_number="9811223322",    email_id="harish.nambiar@email.com",       preferred_language="Malayalam", preferred_channel="Email",      credit_score=512, monthly_income=30000.0, password="password123", relationship_assessment="High risk. Repeated short payments. Outstanding balance growing."),
        Customer(customer_id="CUST039", customer_name="Pallavi Shetty",    mobile_number="9922334422",    email_id="pallavi.shetty@email.com",       preferred_language="Kannada",   preferred_channel="WhatsApp",   credit_score=740, monthly_income=86000.0, password="password123", relationship_assessment="Excellent borrower. EMI auto-debited consistently. No manual follow-up needed."),
        Customer(customer_id="CUST040", customer_name="Dinesh Rawat",      mobile_number="9033445522",    email_id="dinesh.rawat@email.com",         preferred_language="Hindi",     preferred_channel="SMS",        credit_score=543, monthly_income=33500.0, password="password123", relationship_assessment="Medium risk. Expressed job change concerns last quarter. Monitor EMI pattern."),
        Customer(customer_id="CUST041", customer_name="Kavya Reddy",       mobile_number="9144556622",    email_id="kavya.reddy@email.com",          preferred_language="Telugu",    preferred_channel="Email",      credit_score=702, monthly_income=63000.0, password="password123", relationship_assessment="Strong payment record. Occasional early payment shows proactive behaviour."),
        Customer(customer_id="CUST042", customer_name="Sunil Pandey",      mobile_number="9255667722",    email_id="sunil.pandey@email.com",         preferred_language="Hindi",     preferred_channel="Voice Call", credit_score=467, monthly_income=23000.0, password="password123", relationship_assessment="Critical risk. 55 DPD. Emergency restructuring review recommended."),
        Customer(customer_id="CUST043", customer_name="Meghna Rao",        mobile_number="9366778822",    email_id="meghna.rao@email.com",           preferred_language="Kannada",   preferred_channel="WhatsApp",   credit_score=682, monthly_income=53000.0, password="password123", relationship_assessment="Good standing. Timely payments. Slight drop in credit score due to new loan application."),
        Customer(customer_id="CUST044", customer_name="Bharat Sharma",     mobile_number="9477889822",    email_id="bharat.sharma@email.com",        preferred_language="Hindi",     preferred_channel="Email",      credit_score=560, monthly_income=37000.0, password="password123", relationship_assessment="Moderate risk. Agricultural income pattern causes seasonal delays in Nov-Jan."),
        Customer(customer_id="CUST045", customer_name="Ananya Das",        mobile_number="9588990033",    email_id="ananya.das@email.com",           preferred_language="Bengali",   preferred_channel="SMS",        credit_score=718, monthly_income=66000.0, password="password123", relationship_assessment="Reliable borrower. All EMIs on time. Recently added a co-applicant for home loan."),
        Customer(customer_id="CUST046", customer_name="Rakesh Yadav",      mobile_number="9699001144",    email_id="rakesh.yadav@email.com",         preferred_language="Hindi",     preferred_channel="WhatsApp",   credit_score=497, monthly_income=27500.0, password="password123", relationship_assessment="High risk. EMI defaults in 4 of last 6 months. Urgent collections action required."),
        Customer(customer_id="CUST047", customer_name="Shobha Krishnan",   mobile_number="9700112255",    email_id="shobha.krishnan@email.com",      preferred_language="Tamil",     preferred_channel="Email",      credit_score=665, monthly_income=50000.0, password="password123", relationship_assessment="Moderate-low risk. Stable income. Minor delays in Q4. Self-cure likely."),
        Customer(customer_id="CUST048", customer_name="Vinod Thakur",      mobile_number="9811223333",    email_id="vinod.thakur@email.com",         preferred_language="Hindi",     preferred_channel="SMS",        credit_score=524, monthly_income=31500.0, password="password123", relationship_assessment="Medium risk. Business loan performance weaker than personal loan. Watch closely."),
        Customer(customer_id="CUST049", customer_name="Champa Devi",       mobile_number="9922334433",    email_id="champa.devi@email.com",          preferred_language="Hindi",     preferred_channel="Voice Call", credit_score=475, monthly_income=22000.0, password="password123", relationship_assessment="High risk. Elderly borrower on fixed income. Empathetic collections approach required."),
        Customer(customer_id="CUST050", customer_name="Pradeep Bose",      mobile_number="9033445533",    email_id="pradeep.bose@email.com",         preferred_language="Bengali",   preferred_channel="Email",      credit_score=755, monthly_income=92000.0, password="password123", relationship_assessment="Premium borrower. No delays in 3 years. Recently closed one loan early."),
    ]
    db.add_all(customers)
    db.flush()

    # ── Customer Preferences ──────────────────────────────────────
    pref_map = [
        ("CUST001","WhatsApp","English"),    ("CUST002","SMS","Hindi"),
        ("CUST003","Email","English"),       ("CUST004","Voice Call","Tamil"),
        ("CUST005","Email","English"),       ("CUST006","WhatsApp","Hindi"),
        ("CUST007","Email","English"),       ("CUST008","WhatsApp","Gujarati"),
        ("CUST009","SMS","Tamil"),           ("CUST010","Email","Hindi"),
        ("CUST011","WhatsApp","Marathi"),    ("CUST012","Voice Call","Hindi"),
        ("CUST013","Email","English"),       ("CUST014","SMS","Hindi"),
        ("CUST015","WhatsApp","Malayalam"),  ("CUST016","Email","Hindi"),
        ("CUST017","Voice Call","Telugu"),   ("CUST018","WhatsApp","Hindi"),
        ("CUST019","SMS","Marathi"),         ("CUST020","Email","Telugu"),
        ("CUST021","WhatsApp","Hindi"),      ("CUST022","Voice Call","Hindi"),
        ("CUST023","Email","Tamil"),         ("CUST024","WhatsApp","Marathi"),
        ("CUST025","SMS","Hindi"),           ("CUST026","Email","Hindi"),
        ("CUST027","WhatsApp","Hindi"),      ("CUST028","Voice Call","Hindi"),
        ("CUST029","SMS","Telugu"),          ("CUST030","Email","Hindi"),
        ("CUST031","WhatsApp","Tamil"),      ("CUST032","Email","Hindi"),
        ("CUST033","WhatsApp","Bengali"),    ("CUST034","Voice Call","Hindi"),
        ("CUST035","Email","Bengali"),       ("CUST036","WhatsApp","Hindi"),
        ("CUST037","SMS","Tamil"),           ("CUST038","Email","Malayalam"),
        ("CUST039","WhatsApp","Kannada"),    ("CUST040","SMS","Hindi"),
        ("CUST041","Email","Telugu"),        ("CUST042","Voice Call","Hindi"),
        ("CUST043","WhatsApp","Kannada"),    ("CUST044","Email","Hindi"),
        ("CUST045","SMS","Bengali"),         ("CUST046","WhatsApp","Hindi"),
        ("CUST047","Email","Tamil"),         ("CUST048","SMS","Hindi"),
        ("CUST049","Voice Call","Hindi"),    ("CUST050","Email","Bengali"),
    ]
    db.add_all([CustomerPreference(customer_id=c, preferred_channel=ch, preferred_language=l) for c, ch, l in pref_map])

    # ── Loans (no LOAN008) ─────────────────────────────────────────
    loans = [
        Loan(loan_id="LOAN001", customer_id="CUST001", loan_type="Personal Loan", loan_amount=300000.0,  interest_rate=12.5,  emi_amount=6800.0,  emi_due_date="2026-04-23", outstanding_balance=210000.0,  days_past_due=10, risk_segment="Medium", self_cure_probability=0.55, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN002", customer_id="CUST002", loan_type="Home Loan",     loan_amount=2500000.0, interest_rate=8.75,  emi_amount=22000.0, emi_due_date="2026-04-18", outstanding_balance=1800000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.90, recommended_channel="SMS"),
        Loan(loan_id="LOAN003", customer_id="CUST003", loan_type="Personal Loan", loan_amount=150000.0,  interest_rate=16.0,  emi_amount=4200.0,  emi_due_date="2026-02-28", outstanding_balance=120000.0,  days_past_due=15, risk_segment="High",   self_cure_probability=0.25, recommended_channel="Email"),
        Loan(loan_id="LOAN004", customer_id="CUST004", loan_type="Car Loan",      loan_amount=800000.0,  interest_rate=9.5,   emi_amount=16500.0, emi_due_date="2026-04-16", outstanding_balance=560000.0,  days_past_due=3,  risk_segment="Low",    self_cure_probability=0.80, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN005", customer_id="CUST005", loan_type="Business Loan", loan_amount=500000.0,  interest_rate=14.0,  emi_amount=11500.0, emi_due_date="2026-02-15", outstanding_balance=430000.0,  days_past_due=28, risk_segment="High",   self_cure_probability=0.15, recommended_channel="Email"),
        Loan(loan_id="LOAN006", customer_id="CUST006", loan_type="Home Loan",     loan_amount=4000000.0, interest_rate=8.25,  emi_amount=35000.0, emi_due_date="2026-04-25", outstanding_balance=3200000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.95, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN007", customer_id="CUST001", loan_type="Car Loan",      loan_amount=600000.0,  interest_rate=10.0,  emi_amount=13000.0, emi_due_date="2026-04-20", outstanding_balance=480000.0,  days_past_due=5,  risk_segment="Medium", self_cure_probability=0.60, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN009", customer_id="CUST007", loan_type="Personal Loan", loan_amount=250000.0,  interest_rate=13.5,  emi_amount=5800.0,  emi_due_date="2026-04-25", outstanding_balance=180000.0,  days_past_due=7,  risk_segment="Medium", self_cure_probability=0.65, recommended_channel="Email"),
        Loan(loan_id="LOAN010", customer_id="CUST007", loan_type="Car Loan",      loan_amount=700000.0,  interest_rate=9.75,  emi_amount=14500.0, emi_due_date="2026-04-01", outstanding_balance=520000.0,  days_past_due=0,  risk_segment="Low",    self_cure_probability=0.88, recommended_channel="Email"),
        Loan(loan_id="LOAN011", customer_id="CUST008", loan_type="Personal Loan", loan_amount=180000.0,  interest_rate=13.0,  emi_amount=4500.0,  emi_due_date="2026-04-05", outstanding_balance=140000.0,  days_past_due=8,  risk_segment="Medium", self_cure_probability=0.50, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN012", customer_id="CUST009", loan_type="Home Loan",     loan_amount=3200000.0, interest_rate=8.5,   emi_amount=28000.0, emi_due_date="2026-04-10", outstanding_balance=2600000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.92, recommended_channel="SMS"),
        Loan(loan_id="LOAN013", customer_id="CUST010", loan_type="Personal Loan", loan_amount=120000.0,  interest_rate=17.5,  emi_amount=3800.0,  emi_due_date="2026-02-20", outstanding_balance=100000.0,  days_past_due=33, risk_segment="High",   self_cure_probability=0.12, recommended_channel="Email"),
        Loan(loan_id="LOAN014", customer_id="CUST011", loan_type="Car Loan",      loan_amount=650000.0,  interest_rate=9.8,   emi_amount=14000.0, emi_due_date="2026-04-08", outstanding_balance=500000.0,  days_past_due=2,  risk_segment="Low",    self_cure_probability=0.82, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN015", customer_id="CUST012", loan_type="Business Loan", loan_amount=350000.0,  interest_rate=15.5,  emi_amount=9500.0,  emi_due_date="2026-01-31", outstanding_balance=310000.0,  days_past_due=52, risk_segment="High",   self_cure_probability=0.08, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN016", customer_id="CUST013", loan_type="Home Loan",     loan_amount=5500000.0, interest_rate=8.0,   emi_amount=46000.0, emi_due_date="2026-04-12", outstanding_balance=4800000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.97, recommended_channel="Email"),
        Loan(loan_id="LOAN017", customer_id="CUST014", loan_type="Personal Loan", loan_amount=200000.0,  interest_rate=14.0,  emi_amount=5200.0,  emi_due_date="2026-04-02", outstanding_balance=165000.0,  days_past_due=6,  risk_segment="Medium", self_cure_probability=0.55, recommended_channel="SMS"),
        Loan(loan_id="LOAN018", customer_id="CUST015", loan_type="Car Loan",      loan_amount=750000.0,  interest_rate=9.6,   emi_amount=15800.0, emi_due_date="2026-04-07", outstanding_balance=610000.0,  days_past_due=4,  risk_segment="Low",    self_cure_probability=0.75, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN019", customer_id="CUST016", loan_type="Personal Loan", loan_amount=160000.0,  interest_rate=16.5,  emi_amount=4600.0,  emi_due_date="2026-02-25", outstanding_balance=140000.0,  days_past_due=18, risk_segment="High",   self_cure_probability=0.22, recommended_channel="Email"),
        Loan(loan_id="LOAN020", customer_id="CUST017", loan_type="Home Loan",     loan_amount=2800000.0, interest_rate=8.6,   emi_amount=24500.0, emi_due_date="2026-04-15", outstanding_balance=2200000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.88, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN021", customer_id="CUST018", loan_type="Personal Loan", loan_amount=220000.0,  interest_rate=14.5,  emi_amount=5500.0,  emi_due_date="2026-04-03", outstanding_balance=185000.0,  days_past_due=9,  risk_segment="Medium", self_cure_probability=0.48, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN022", customer_id="CUST019", loan_type="Car Loan",      loan_amount=900000.0,  interest_rate=9.2,   emi_amount=18500.0, emi_due_date="2026-04-11", outstanding_balance=720000.0,  days_past_due=1,  risk_segment="Low",    self_cure_probability=0.85, recommended_channel="SMS"),
        Loan(loan_id="LOAN023", customer_id="CUST020", loan_type="Business Loan", loan_amount=600000.0,  interest_rate=14.8,  emi_amount=13800.0, emi_due_date="2026-02-10", outstanding_balance=550000.0,  days_past_due=43, risk_segment="High",   self_cure_probability=0.10, recommended_channel="Email"),
        Loan(loan_id="LOAN024", customer_id="CUST021", loan_type="Home Loan",     loan_amount=3800000.0, interest_rate=8.3,   emi_amount=33000.0, emi_due_date="2026-04-20", outstanding_balance=3100000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.93, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN025", customer_id="CUST022", loan_type="Personal Loan", loan_amount=190000.0,  interest_rate=15.0,  emi_amount=4900.0,  emi_due_date="2026-04-06", outstanding_balance=155000.0,  days_past_due=11, risk_segment="Medium", self_cure_probability=0.42, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN026", customer_id="CUST023", loan_type="Home Loan",     loan_amount=6200000.0, interest_rate=7.9,   emi_amount=52000.0, emi_due_date="2026-04-22", outstanding_balance=5600000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.96, recommended_channel="Email"),
        Loan(loan_id="LOAN027", customer_id="CUST024", loan_type="Personal Loan", loan_amount=210000.0,  interest_rate=13.8,  emi_amount=5300.0,  emi_due_date="2026-04-04", outstanding_balance=170000.0,  days_past_due=7,  risk_segment="Medium", self_cure_probability=0.52, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN028", customer_id="CUST025", loan_type="Car Loan",      loan_amount=550000.0,  interest_rate=10.2,  emi_amount=12200.0, emi_due_date="2026-04-09", outstanding_balance=420000.0,  days_past_due=3,  risk_segment="Low",    self_cure_probability=0.72, recommended_channel="SMS"),
        Loan(loan_id="LOAN029", customer_id="CUST026", loan_type="Business Loan", loan_amount=420000.0,  interest_rate=16.0,  emi_amount=11200.0, emi_due_date="2026-02-05", outstanding_balance=390000.0,  days_past_due=48, risk_segment="High",   self_cure_probability=0.09, recommended_channel="Email"),
        Loan(loan_id="LOAN030", customer_id="CUST027", loan_type="Personal Loan", loan_amount=280000.0,  interest_rate=12.8,  emi_amount=6500.0,  emi_due_date="2026-04-13", outstanding_balance=220000.0,  days_past_due=5,  risk_segment="Medium", self_cure_probability=0.65, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN031", customer_id="CUST028", loan_type="Car Loan",      loan_amount=480000.0,  interest_rate=11.0,  emi_amount=10800.0, emi_due_date="2026-04-01", outstanding_balance=380000.0,  days_past_due=12, risk_segment="Medium", self_cure_probability=0.38, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN032", customer_id="CUST029", loan_type="Home Loan",     loan_amount=2200000.0, interest_rate=8.9,   emi_amount=19800.0, emi_due_date="2026-04-17", outstanding_balance=1750000.0, days_past_due=2,  risk_segment="Low",    self_cure_probability=0.80, recommended_channel="SMS"),
        Loan(loan_id="LOAN033", customer_id="CUST030", loan_type="Business Loan", loan_amount=700000.0,  interest_rate=15.2,  emi_amount=15500.0, emi_due_date="2026-02-01", outstanding_balance=650000.0,  days_past_due=52, risk_segment="High",   self_cure_probability=0.07, recommended_channel="Email"),
        Loan(loan_id="LOAN034", customer_id="CUST031", loan_type="Home Loan",     loan_amount=4500000.0, interest_rate=8.1,   emi_amount=38500.0, emi_due_date="2026-04-21", outstanding_balance=3800000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.95, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN035", customer_id="CUST032", loan_type="Personal Loan", loan_amount=175000.0,  interest_rate=14.2,  emi_amount=4700.0,  emi_due_date="2026-04-05", outstanding_balance=145000.0,  days_past_due=10, risk_segment="Medium", self_cure_probability=0.47, recommended_channel="Email"),
        Loan(loan_id="LOAN036", customer_id="CUST033", loan_type="Car Loan",      loan_amount=720000.0,  interest_rate=9.4,   emi_amount=15200.0, emi_due_date="2026-04-14", outstanding_balance=570000.0,  days_past_due=2,  risk_segment="Low",    self_cure_probability=0.83, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN037", customer_id="CUST034", loan_type="Personal Loan", loan_amount=130000.0,  interest_rate=18.0,  emi_amount=4100.0,  emi_due_date="2026-01-20", outstanding_balance=115000.0,  days_past_due=64, risk_segment="High",   self_cure_probability=0.05, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN038", customer_id="CUST035", loan_type="Home Loan",     loan_amount=5000000.0, interest_rate=8.2,   emi_amount=43000.0, emi_due_date="2026-04-23", outstanding_balance=4400000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.94, recommended_channel="Email"),
        Loan(loan_id="LOAN039", customer_id="CUST036", loan_type="Personal Loan", loan_amount=260000.0,  interest_rate=13.2,  emi_amount=6200.0,  emi_due_date="2026-04-08", outstanding_balance=210000.0,  days_past_due=6,  risk_segment="Medium", self_cure_probability=0.58, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN040", customer_id="CUST037", loan_type="Car Loan",      loan_amount=620000.0,  interest_rate=9.7,   emi_amount=13500.0, emi_due_date="2026-04-16", outstanding_balance=490000.0,  days_past_due=1,  risk_segment="Low",    self_cure_probability=0.79, recommended_channel="SMS"),
        Loan(loan_id="LOAN041", customer_id="CUST038", loan_type="Personal Loan", loan_amount=145000.0,  interest_rate=16.8,  emi_amount=4300.0,  emi_due_date="2026-02-22", outstanding_balance=125000.0,  days_past_due=21, risk_segment="High",   self_cure_probability=0.20, recommended_channel="Email"),
        Loan(loan_id="LOAN042", customer_id="CUST039", loan_type="Home Loan",     loan_amount=5800000.0, interest_rate=7.8,   emi_amount=49000.0, emi_due_date="2026-04-25", outstanding_balance=5200000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.97, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN043", customer_id="CUST040", loan_type="Personal Loan", loan_amount=230000.0,  interest_rate=14.6,  emi_amount=5700.0,  emi_due_date="2026-04-09", outstanding_balance=190000.0,  days_past_due=8,  risk_segment="Medium", self_cure_probability=0.50, recommended_channel="SMS"),
        Loan(loan_id="LOAN044", customer_id="CUST041", loan_type="Home Loan",     loan_amount=3500000.0, interest_rate=8.4,   emi_amount=30500.0, emi_due_date="2026-04-19", outstanding_balance=2900000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.90, recommended_channel="Email"),
        Loan(loan_id="LOAN045", customer_id="CUST042", loan_type="Business Loan", loan_amount=450000.0,  interest_rate=16.2,  emi_amount=12000.0, emi_due_date="2026-01-25", outstanding_balance=415000.0,  days_past_due=59, risk_segment="High",   self_cure_probability=0.06, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN046", customer_id="CUST043", loan_type="Car Loan",      loan_amount=830000.0,  interest_rate=9.3,   emi_amount=17200.0, emi_due_date="2026-04-11", outstanding_balance=670000.0,  days_past_due=3,  risk_segment="Low",    self_cure_probability=0.78, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN047", customer_id="CUST044", loan_type="Personal Loan", loan_amount=195000.0,  interest_rate=13.6,  emi_amount=4900.0,  emi_due_date="2026-04-07", outstanding_balance=160000.0,  days_past_due=9,  risk_segment="Medium", self_cure_probability=0.49, recommended_channel="Email"),
        Loan(loan_id="LOAN048", customer_id="CUST045", loan_type="Home Loan",     loan_amount=4200000.0, interest_rate=8.15,  emi_amount=36200.0, emi_due_date="2026-04-18", outstanding_balance=3650000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.91, recommended_channel="SMS"),
        Loan(loan_id="LOAN049", customer_id="CUST046", loan_type="Personal Loan", loan_amount=170000.0,  interest_rate=17.0,  emi_amount=4600.0,  emi_due_date="2026-02-12", outstanding_balance=155000.0,  days_past_due=41, risk_segment="High",   self_cure_probability=0.11, recommended_channel="WhatsApp"),
        Loan(loan_id="LOAN050", customer_id="CUST047", loan_type="Car Loan",      loan_amount=580000.0,  interest_rate=10.0,  emi_amount=12800.0, emi_due_date="2026-04-14", outstanding_balance=455000.0,  days_past_due=4,  risk_segment="Low",    self_cure_probability=0.74, recommended_channel="Email"),
        Loan(loan_id="LOAN051", customer_id="CUST048", loan_type="Business Loan", loan_amount=380000.0,  interest_rate=15.8,  emi_amount=10200.0, emi_due_date="2026-04-06", outstanding_balance=335000.0,  days_past_due=13, risk_segment="Medium", self_cure_probability=0.35, recommended_channel="SMS"),
        Loan(loan_id="LOAN052", customer_id="CUST049", loan_type="Personal Loan", loan_amount=110000.0,  interest_rate=17.8,  emi_amount=3600.0,  emi_due_date="2026-02-08", outstanding_balance=98000.0,   days_past_due=45, risk_segment="High",   self_cure_probability=0.08, recommended_channel="Voice Call"),
        Loan(loan_id="LOAN053", customer_id="CUST050", loan_type="Home Loan",     loan_amount=6000000.0, interest_rate=7.95,  emi_amount=51000.0, emi_due_date="2026-04-24", outstanding_balance=5400000.0, days_past_due=0,  risk_segment="Low",    self_cure_probability=0.97, recommended_channel="Email"),
    ]
    db.add_all(loans)
    db.flush()

    # ── Payment History ────────────────────────────────────────────
    payments = [
        PaymentHistory(loan_id="LOAN001", payment_date="2026-02-23", payment_amount=6800.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN001", payment_date="2026-01-25", payment_amount=6800.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN001", payment_date="2025-12-28", payment_amount=6800.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN001", payment_date="2025-11-30", payment_amount=6800.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN001", payment_date="2025-10-23", payment_amount=6800.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN007", payment_date="2026-03-15", payment_amount=13000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN007", payment_date="2026-02-18", payment_amount=13000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN007", payment_date="2026-01-19", payment_amount=13000.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN002", payment_date="2026-03-01", payment_amount=22000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN002", payment_date="2026-02-01", payment_amount=22000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN002", payment_date="2026-01-02", payment_amount=22000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN002", payment_date="2025-12-01", payment_amount=22000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN002", payment_date="2025-11-01", payment_amount=22000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN003", payment_date="2026-01-10", payment_amount=4200.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN003", payment_date="2025-12-15", payment_amount=2100.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN003", payment_date="2025-11-20", payment_amount=4200.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN003", payment_date="2025-10-18", payment_amount=4200.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN004", payment_date="2026-03-10", payment_amount=16500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN004", payment_date="2026-02-10", payment_amount=16500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN004", payment_date="2026-01-12", payment_amount=16500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN004", payment_date="2025-12-10", payment_amount=16500.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN005", payment_date="2026-01-05", payment_amount=11500.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN005", payment_date="2025-11-20", payment_amount=5750.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN005", payment_date="2025-10-15", payment_amount=11500.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN006", payment_date="2026-03-05", payment_amount=35000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN006", payment_date="2026-02-05", payment_amount=35000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN006", payment_date="2026-01-05", payment_amount=35000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN006", payment_date="2025-12-05", payment_amount=35000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN006", payment_date="2025-11-05", payment_amount=35000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN009", payment_date="2026-02-25", payment_amount=5800.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN009", payment_date="2026-01-24", payment_amount=5800.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN009", payment_date="2025-12-26", payment_amount=5800.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN010", payment_date="2026-03-01", payment_amount=14500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN010", payment_date="2026-02-01", payment_amount=14500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN010", payment_date="2026-01-02", payment_amount=14500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN011", payment_date="2026-03-02", payment_amount=4500.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN011", payment_date="2026-01-28", payment_amount=4500.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN011", payment_date="2025-12-20", payment_amount=4500.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN012", payment_date="2026-03-10", payment_amount=28000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN012", payment_date="2026-02-10", payment_amount=28000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN012", payment_date="2026-01-10", payment_amount=28000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN012", payment_date="2025-12-10", payment_amount=28000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN013", payment_date="2026-01-08", payment_amount=3800.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN013", payment_date="2025-11-15", payment_amount=1900.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN013", payment_date="2025-10-10", payment_amount=3800.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN014", payment_date="2026-03-05", payment_amount=14000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN014", payment_date="2026-02-06", payment_amount=14000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN014", payment_date="2026-01-07", payment_amount=14000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN015", payment_date="2025-12-20", payment_amount=9500.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN015", payment_date="2025-11-15", payment_amount=4750.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN015", payment_date="2025-10-10", payment_amount=9500.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN016", payment_date="2026-03-12", payment_amount=46000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN016", payment_date="2026-02-12", payment_amount=46000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN016", payment_date="2026-01-12", payment_amount=46000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN016", payment_date="2025-12-12", payment_amount=46000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN017", payment_date="2026-03-08", payment_amount=5200.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN017", payment_date="2026-02-07", payment_amount=5200.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN017", payment_date="2026-01-10", payment_amount=5200.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN018", payment_date="2026-03-03", payment_amount=15800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN018", payment_date="2026-02-04", payment_amount=15800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN018", payment_date="2026-01-05", payment_amount=15800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN019", payment_date="2026-01-20", payment_amount=4600.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN019", payment_date="2025-12-10", payment_amount=2300.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN019", payment_date="2025-11-08", payment_amount=4600.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN020", payment_date="2026-03-15", payment_amount=24500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN020", payment_date="2026-02-15", payment_amount=24500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN020", payment_date="2026-01-15", payment_amount=24500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN020", payment_date="2025-12-15", payment_amount=24500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN021", payment_date="2026-03-01", payment_amount=5500.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN021", payment_date="2026-01-25", payment_amount=5500.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN021", payment_date="2025-12-22", payment_amount=5500.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN022", payment_date="2026-03-10", payment_amount=18500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN022", payment_date="2026-02-11", payment_amount=18500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN022", payment_date="2026-01-12", payment_amount=18500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN023", payment_date="2026-01-05", payment_amount=13800.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN023", payment_date="2025-11-20", payment_amount=6900.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN023", payment_date="2025-10-08", payment_amount=13800.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN024", payment_date="2026-03-20", payment_amount=33000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN024", payment_date="2026-02-20", payment_amount=33000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN024", payment_date="2026-01-20", payment_amount=33000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN024", payment_date="2025-12-20", payment_amount=33000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN025", payment_date="2026-02-28", payment_amount=4900.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN025", payment_date="2026-01-20", payment_amount=4900.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN025", payment_date="2025-12-18", payment_amount=4900.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN026", payment_date="2026-03-22", payment_amount=52000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN026", payment_date="2026-02-22", payment_amount=52000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN026", payment_date="2026-01-22", payment_amount=52000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN026", payment_date="2025-12-22", payment_amount=52000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN027", payment_date="2026-03-01", payment_amount=5300.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN027", payment_date="2026-01-28", payment_amount=5300.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN027", payment_date="2025-12-24", payment_amount=5300.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN028", payment_date="2026-03-07", payment_amount=12200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN028", payment_date="2026-02-08", payment_amount=12200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN028", payment_date="2026-01-08", payment_amount=12200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN029", payment_date="2025-12-28", payment_amount=11200.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN029", payment_date="2025-11-10", payment_amount=5600.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN029", payment_date="2025-10-05", payment_amount=11200.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN030", payment_date="2026-03-10", payment_amount=6500.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN030", payment_date="2026-02-09", payment_amount=6500.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN030", payment_date="2026-01-11", payment_amount=6500.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN031", payment_date="2026-02-20", payment_amount=10800.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN031", payment_date="2026-01-15", payment_amount=10800.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN031", payment_date="2025-12-12", payment_amount=10800.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN032", payment_date="2026-03-15", payment_amount=19800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN032", payment_date="2026-02-16", payment_amount=19800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN032", payment_date="2026-01-16", payment_amount=19800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN033", payment_date="2025-12-15", payment_amount=15500.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN033", payment_date="2025-11-05", payment_amount=7750.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN033", payment_date="2025-10-01", payment_amount=15500.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN034", payment_date="2026-03-21", payment_amount=38500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN034", payment_date="2026-02-21", payment_amount=38500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN034", payment_date="2026-01-21", payment_amount=38500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN034", payment_date="2025-12-21", payment_amount=38500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN035", payment_date="2026-02-26", payment_amount=4700.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN035", payment_date="2026-01-22", payment_amount=4700.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN035", payment_date="2025-12-19", payment_amount=4700.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN036", payment_date="2026-03-12", payment_amount=15200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN036", payment_date="2026-02-13", payment_amount=15200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN036", payment_date="2026-01-14", payment_amount=15200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN037", payment_date="2025-12-10", payment_amount=4100.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN037", payment_date="2025-10-20", payment_amount=2050.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN037", payment_date="2025-09-18", payment_amount=4100.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN038", payment_date="2026-03-23", payment_amount=43000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN038", payment_date="2026-02-23", payment_amount=43000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN038", payment_date="2026-01-23", payment_amount=43000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN038", payment_date="2025-12-23", payment_amount=43000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN039", payment_date="2026-03-03", payment_amount=6200.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN039", payment_date="2026-02-02", payment_amount=6200.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN039", payment_date="2026-01-04", payment_amount=6200.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN040", payment_date="2026-03-14", payment_amount=13500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN040", payment_date="2026-02-15", payment_amount=13500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN040", payment_date="2026-01-15", payment_amount=13500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN041", payment_date="2026-01-18", payment_amount=4300.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN041", payment_date="2025-12-08", payment_amount=2150.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN041", payment_date="2025-11-05", payment_amount=4300.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN042", payment_date="2026-03-25", payment_amount=49000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN042", payment_date="2026-02-25", payment_amount=49000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN042", payment_date="2026-01-25", payment_amount=49000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN042", payment_date="2025-12-25", payment_amount=49000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN043", payment_date="2026-03-02", payment_amount=5700.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN043", payment_date="2026-01-30", payment_amount=5700.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN043", payment_date="2025-12-28", payment_amount=5700.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN044", payment_date="2026-03-19", payment_amount=30500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN044", payment_date="2026-02-19", payment_amount=30500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN044", payment_date="2026-01-19", payment_amount=30500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN044", payment_date="2025-12-19", payment_amount=30500.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN045", payment_date="2025-12-18", payment_amount=12000.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN045", payment_date="2025-11-10", payment_amount=6000.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN045", payment_date="2025-10-05", payment_amount=12000.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN046", payment_date="2026-03-09", payment_amount=17200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN046", payment_date="2026-02-10", payment_amount=17200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN046", payment_date="2026-01-10", payment_amount=17200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN047", payment_date="2026-02-28", payment_amount=4900.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN047", payment_date="2026-01-25", payment_amount=4900.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN047", payment_date="2025-12-20", payment_amount=4900.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN048", payment_date="2026-03-18", payment_amount=36200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN048", payment_date="2026-02-18", payment_amount=36200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN048", payment_date="2026-01-18", payment_amount=36200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN048", payment_date="2025-12-18", payment_amount=36200.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN049", payment_date="2026-01-02", payment_amount=4600.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN049", payment_date="2025-11-18", payment_amount=2300.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN049", payment_date="2025-10-12", payment_amount=4600.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN050", payment_date="2026-03-12", payment_amount=12800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN050", payment_date="2026-02-13", payment_amount=12800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN050", payment_date="2026-01-13", payment_amount=12800.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN051", payment_date="2026-02-24", payment_amount=10200.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN051", payment_date="2026-01-21", payment_amount=10200.0, payment_method="UPI"),
        PaymentHistory(loan_id="LOAN051", payment_date="2025-12-17", payment_amount=10200.0, payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN052", payment_date="2025-12-20", payment_amount=3600.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN052", payment_date="2025-11-08", payment_amount=1800.0,  payment_method="UPI"),
        PaymentHistory(loan_id="LOAN052", payment_date="2025-10-02", payment_amount=3600.0,  payment_method="Bank Transfer"),
        PaymentHistory(loan_id="LOAN053", payment_date="2026-03-24", payment_amount=51000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN053", payment_date="2026-02-24", payment_amount=51000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN053", payment_date="2026-01-24", payment_amount=51000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN053", payment_date="2025-12-24", payment_amount=51000.0, payment_method="NEFT"),
        PaymentHistory(loan_id="LOAN053", payment_date="2025-11-24", payment_amount=51000.0, payment_method="NEFT"),
    ]
    db.add_all(payments)

    # ── Interaction History ────────────────────────────────────────
    interactions = [
        InteractionHistory(interaction_id="INT001", customer_id="CUST001", interaction_type="Call",  interaction_time="2026-03-05 10:30:00", conversation_text="Customer called to inquire about grace period options due to salary delay.",                   sentiment_score=0.2,  tonality_score="Neutral",  interaction_summary="Customer requested grace period due to temporary salary delay."),
        InteractionHistory(interaction_id="INT002", customer_id="CUST001", interaction_type="Chat",  interaction_time="2026-03-10 14:00:00", conversation_text="Customer asked about EMI schedule and outstanding balance.",                                   sentiment_score=0.3,  tonality_score="Positive", interaction_summary="Customer inquired about EMI schedule. Provided loan details and next due date."),
        InteractionHistory(interaction_id="INT003", customer_id="CUST003", interaction_type="Call",  interaction_time="2026-03-01 09:00:00", conversation_text="Customer expressed frustration about high EMI amount. Requested restructuring.",             sentiment_score=-0.6, tonality_score="Negative", interaction_summary="Customer highly stressed about repayment burden. Expressed interest in restructuring."),
        InteractionHistory(interaction_id="INT004", customer_id="CUST003", interaction_type="Email", interaction_time="2026-03-08 11:30:00", conversation_text="Customer sent email requesting information about restructuring eligibility.",                 sentiment_score=-0.3, tonality_score="Neutral",  interaction_summary="Customer submitted written request for restructuring information."),
        InteractionHistory(interaction_id="INT005", customer_id="CUST005", interaction_type="Call",  interaction_time="2026-03-02 16:00:00", conversation_text="Customer mentioned business downturn and inability to pay EMI for next 2 months.",          sentiment_score=-0.8, tonality_score="Negative", interaction_summary="Customer in financial distress due to business losses. Requested emergency support."),
        InteractionHistory(interaction_id="INT006", customer_id="CUST005", interaction_type="SMS",   interaction_time="2026-03-10 08:00:00", conversation_text="Customer replied to SMS reminder saying they need more time.",                              sentiment_score=-0.4, tonality_score="Negative", interaction_summary="Customer acknowledged EMI overdue and requested extended time."),
        InteractionHistory(interaction_id="INT007", customer_id="CUST002", interaction_type="Chat",  interaction_time="2026-03-09 12:00:00", conversation_text="Customer asked about prepayment options and interest savings.",                              sentiment_score=0.7,  tonality_score="Positive", interaction_summary="Customer interested in prepayment. Provided details on prepayment charges and savings."),
        InteractionHistory(interaction_id="INT008", customer_id="CUST004", interaction_type="Call",  interaction_time="2026-03-11 10:00:00", conversation_text="Customer called to confirm EMI due date and payment method.",                                sentiment_score=0.5,  tonality_score="Positive", interaction_summary="Customer proactively confirmed EMI due date. Updated preferred payment method."),
        InteractionHistory(interaction_id="INT009", customer_id="CUST010", interaction_type="Call",  interaction_time="2026-03-03 11:00:00", conversation_text="Customer unable to pay EMI due to job loss. Requesting grace period.",                      sentiment_score=-0.9, tonality_score="Negative", interaction_summary="Customer in severe financial distress. Job loss reported. Grace request required."),
        InteractionHistory(interaction_id="INT010", customer_id="CUST012", interaction_type="Call",  interaction_time="2026-03-01 09:30:00", conversation_text="Customer unresponsive initially then acknowledged overdue. No commitment given.",            sentiment_score=-0.7, tonality_score="Negative", interaction_summary="Non-cooperative customer. Legal escalation may be needed."),
        InteractionHistory(interaction_id="INT011", customer_id="CUST013", interaction_type="Chat",  interaction_time="2026-03-12 15:00:00", conversation_text="Customer enquired about home loan top-up eligibility.",                                      sentiment_score=0.8,  tonality_score="Positive", interaction_summary="Premium customer interested in loan top-up. Provided eligibility criteria."),
        InteractionHistory(interaction_id="INT012", customer_id="CUST016", interaction_type="Email", interaction_time="2026-03-07 10:00:00", conversation_text="Customer requested restructuring citing salary reduction.",                                  sentiment_score=-0.5, tonality_score="Negative", interaction_summary="Restructuring request submitted due to income reduction."),
        InteractionHistory(interaction_id="INT013", customer_id="CUST020", interaction_type="Call",  interaction_time="2026-03-04 14:00:00", conversation_text="Customer stated business is closed and unable to pay. Seeking OTS settlement.",             sentiment_score=-0.9, tonality_score="Negative", interaction_summary="Business closed. Customer seeking OTS settlement. Escalate to senior officer."),
        InteractionHistory(interaction_id="INT014", customer_id="CUST023", interaction_type="Chat",  interaction_time="2026-03-13 11:00:00", conversation_text="Customer asked about balance transfer to another bank for better interest rate.",             sentiment_score=0.6,  tonality_score="Positive", interaction_summary="Customer exploring balance transfer. Retain with competitive offer."),
        InteractionHistory(interaction_id="INT015", customer_id="CUST026", interaction_type="Call",  interaction_time="2026-03-02 10:00:00", conversation_text="Customer asked for extension. Multiple loan obligations making it difficult.",               sentiment_score=-0.6, tonality_score="Negative", interaction_summary="Customer over-leveraged with multiple loans. Restructuring discussion needed."),
        InteractionHistory(interaction_id="INT016", customer_id="CUST028", interaction_type="Call",  interaction_time="2026-03-06 09:00:00", conversation_text="Customer expressed hardship due to medical emergency. Requesting grace period.",             sentiment_score=-0.7, tonality_score="Negative", interaction_summary="Grace period requested due to medical emergency. Empathetic handling required."),
        InteractionHistory(interaction_id="INT017", customer_id="CUST030", interaction_type="SMS",   interaction_time="2026-03-08 07:30:00", conversation_text="Customer replied to overdue reminder asking for 15 more days.",                             sentiment_score=-0.5, tonality_score="Neutral",  interaction_summary="Customer acknowledged overdue. Requested 15-day extension."),
        InteractionHistory(interaction_id="INT018", customer_id="CUST034", interaction_type="Call",  interaction_time="2026-02-28 16:00:00", conversation_text="No response. Call went unanswered 3 times. SMS sent.",                                       sentiment_score=-0.1, tonality_score="Neutral",  interaction_summary="Customer unreachable. SMS reminder sent. Legal notice consideration."),
        InteractionHistory(interaction_id="INT019", customer_id="CUST038", interaction_type="Email", interaction_time="2026-03-05 12:00:00", conversation_text="Customer disputed EMI calculation. Claims interest overcharged.",                             sentiment_score=-0.4, tonality_score="Negative", interaction_summary="Customer disputed interest calculation. Account review required."),
        InteractionHistory(interaction_id="INT020", customer_id="CUST042", interaction_type="Call",  interaction_time="2026-03-01 10:00:00", conversation_text="Customer stated business revenue down 60%. Unable to service EMIs. Requesting OTS.",        sentiment_score=-0.9, tonality_score="Negative", interaction_summary="Severe distress. OTS request made. Senior officer review needed."),
        InteractionHistory(interaction_id="INT021", customer_id="CUST046", interaction_type="Call",  interaction_time="2026-03-03 11:30:00", conversation_text="Customer in default. Threatening to abandon loan. Needs immediate intervention.",             sentiment_score=-1.0, tonality_score="Negative", interaction_summary="Critical case. Customer threatening loan abandonment. Escalate immediately."),
        InteractionHistory(interaction_id="INT022", customer_id="CUST049", interaction_type="Call",  interaction_time="2026-03-07 10:00:00", conversation_text="Elderly customer confused about EMI amount. Son confirmed family hardship.",                 sentiment_score=-0.6, tonality_score="Negative", interaction_summary="Elderly customer with family hardship. Empathetic collections approach required."),
    ]
    db.add_all(interactions)

    # ── Grace Requests ─────────────────────────────────────────────
    grace_requests = [
        GraceRequest(request_id="GR001", loan_id="LOAN001", customer_id="CUST001", request_status="Pending",  decision_comment=None,                                                           request_date="2026-03-10", approved_by=None,     decision_date=None),
        GraceRequest(request_id="GR002", loan_id="LOAN003", customer_id="CUST003", request_status="Rejected", decision_comment="Grace not allowed due to repeated EMI delays beyond 30 days.", request_date="2026-03-05", approved_by="920532", decision_date="2026-03-07"),
        GraceRequest(request_id="GR003", loan_id="LOAN005", customer_id="CUST005", request_status="Approved", decision_comment="Grace granted for 7 days considering business hardship.",     request_date="2026-03-08", approved_by="920614", decision_date="2026-03-09"),
        GraceRequest(request_id="GR004", loan_id="LOAN013", customer_id="CUST010", request_status="Pending",  decision_comment=None,                                                           request_date="2026-03-12", approved_by=None,     decision_date=None),
        GraceRequest(request_id="GR005", loan_id="LOAN019", customer_id="CUST016", request_status="Pending",  decision_comment=None,                                                           request_date="2026-03-11", approved_by=None,     decision_date=None),
        GraceRequest(request_id="GR006", loan_id="LOAN031", customer_id="CUST028", request_status="Approved", decision_comment="Grace of 10 days approved due to medical emergency.",          request_date="2026-03-09", approved_by="820654", decision_date="2026-03-10"),
        GraceRequest(request_id="GR007", loan_id="LOAN049", customer_id="CUST046", request_status="Rejected", decision_comment="Multiple defaults. Grace not permissible at this stage.",      request_date="2026-03-06", approved_by="910488", decision_date="2026-03-08"),
    ]
    db.add_all(grace_requests)

    # ── Restructure Requests ───────────────────────────────────────
    restructure_requests = [
        RestructureRequest(request_id="RR001", loan_id="LOAN003", customer_id="CUST003", request_status="Pending",  decision_comment=None,                                                       request_date="2026-03-09", approved_by=None,     decision_date=None),
        RestructureRequest(request_id="RR002", loan_id="LOAN005", customer_id="CUST005", request_status="Pending",  decision_comment=None,                                                       request_date="2026-03-11", approved_by=None,     decision_date=None),
        RestructureRequest(request_id="RR003", loan_id="LOAN019", customer_id="CUST016", request_status="Pending",  decision_comment=None,                                                       request_date="2026-03-12", approved_by=None,     decision_date=None),
        RestructureRequest(request_id="RR004", loan_id="LOAN023", customer_id="CUST020", request_status="Approved", decision_comment="Tenure extended by 18 months. EMI reduced to Rs.9,800.",  request_date="2026-03-05", approved_by="920532", decision_date="2026-03-08"),
        RestructureRequest(request_id="RR005", loan_id="LOAN029", customer_id="CUST026", request_status="Pending",  decision_comment=None,                                                       request_date="2026-03-13", approved_by=None,     decision_date=None),
        RestructureRequest(request_id="RR006", loan_id="LOAN033", customer_id="CUST030", request_status="Pending",  decision_comment=None,                                                       request_date="2026-03-10", approved_by=None,     decision_date=None),
        RestructureRequest(request_id="RR007", loan_id="LOAN045", customer_id="CUST042", request_status="Pending",  decision_comment=None,                                                       request_date="2026-03-11", approved_by=None,     decision_date=None),
    ]
    db.add_all(restructure_requests)

    # ── Chat Sessions & Messages ───────────────────────────────────
    chat_sessions = [
        ChatSession(session_id="SESS001", customer_id="CUST001", session_title="EMI Payment Query",       created_at="2026-03-10 14:00:00", last_updated="2026-03-10 14:15:00"),
        ChatSession(session_id="SESS002", customer_id="CUST001", session_title="Grace Request Discussion", created_at="2026-03-11 09:00:00", last_updated="2026-03-11 09:20:00"),
        ChatSession(session_id="SESS003", customer_id="CUST003", session_title="Loan Restructure Query",   created_at="2026-03-08 11:00:00", last_updated="2026-03-08 11:30:00"),
    ]
    db.add_all(chat_sessions)
    db.flush()

    chat_messages = [
        ChatMessage(session_id="SESS001", role="user",      message_text="What is my next EMI amount?",                                    timestamp="2026-03-10 14:01:00"),
        ChatMessage(session_id="SESS001", role="assistant", message_text="Your next EMI of Rs.6,800 is due on 23rd April 2026 for LOAN001.", timestamp="2026-03-10 14:01:30"),
        ChatMessage(session_id="SESS001", role="user",      message_text="Can I get a grace period?",                                      timestamp="2026-03-10 14:02:00"),
        ChatMessage(session_id="SESS001", role="assistant", message_text="Based on your account, you may be eligible for a grace period of up to 7 days. Would you like me to submit a request?", timestamp="2026-03-10 14:02:30"),
        ChatMessage(session_id="SESS002", role="user",      message_text="I submitted a grace request. What is its status?",               timestamp="2026-03-11 09:01:00"),
        ChatMessage(session_id="SESS002", role="assistant", message_text="Your grace request GR001 is currently Pending review by the bank officer.", timestamp="2026-03-11 09:01:30"),
        ChatMessage(session_id="SESS003", role="user",      message_text="I want to restructure my loan. What are my options?",            timestamp="2026-03-08 11:01:00"),
        ChatMessage(session_id="SESS003", role="assistant", message_text="Based on your outstanding balance of Rs.1,20,000, restructuring options include extending tenure by 12-24 months or reducing EMI by adjusting the interest rate. Would you like me to submit a request?", timestamp="2026-03-08 11:01:45"),
        ChatMessage(session_id="SESS003", role="user",      message_text="Yes, please submit a request.",                                  timestamp="2026-03-08 11:02:00"),
        ChatMessage(session_id="SESS003", role="assistant", message_text="Your restructure request has been submitted. A bank officer will review it within 2 business days.", timestamp="2026-03-08 11:02:30"),
    ]
    db.add_all(chat_messages)

    # ═════════════════════════════════════════════════════════════════
    # BOUNCE PREVENTION & PAYMENT ASSURANCE SEED DATA
    # ═════════════════════════════════════════════════════════════════
    
    print("Seeding bounce prevention data...")
    
    # Import the calculator for generating risk profiles
    from analytics.bounce_predictor import calculate_bounce_risk, predict_bounce_date
    from datetime import datetime, timedelta
    import json
    
    # Generate bounce risk profiles for all loans
    all_loans = db.query(Loan).all()
    bounce_profiles = []
    
    for loan in all_loans:
        # Fetch payment history for this loan
        payments = db.query(PaymentHistory).filter(PaymentHistory.loan_id == loan.loan_id).all()
        
        # Calculate risk
        risk_data = calculate_bounce_risk(loan, payments, None)
        
        # Mock bounce counts based on risk level
        if risk_data['level'] == 'High':
            bounce_6m = 3
            bounce_12m = 5
        elif risk_data['level'] == 'Medium':
            bounce_6m = 1
            bounce_12m = 2
        else:
            bounce_6m = 0
            bounce_12m = 0
        
        profile = BounceRiskProfile(
            loan_id=loan.loan_id,
            customer_id=loan.customer_id,
            risk_score=risk_data['score'],
            risk_level=risk_data['level'],
            risk_factors=json.dumps(risk_data['factors']),
            bounce_count_3m=bounce_6m // 2,
            bounce_count_6m=bounce_6m,
            bounce_count_12m=bounce_12m,
            last_bounce_date=datetime.now() - timedelta(days=45) if bounce_6m > 0 else None,
            next_emi_bounce_probability=risk_data['next_emi_bounce_probability'],
            predicted_bounce_date=predict_bounce_date(loan, risk_data['next_emi_bounce_probability']),
            calculated_at=datetime.now(),
            updated_at=datetime.now()
        )
        bounce_profiles.append(profile)
    
    db.add_all(bounce_profiles)
    db.flush()
    
    # Create auto-pay mandates for some low-risk customers (mock)
    auto_pay_mandates = [
        AutoPayMandate(loan_id="LOAN002", customer_id="CUST002", status="Active",  mandate_type="e-NACH", bank_account_number="XXXX5678", ifsc_code="HDFC0001234", max_amount=8500.0,  activated_at=datetime.now() - timedelta(days=30), activated_by="customer", activation_channel="app",      first_debit_date="2026-05-01", expiry_date="2027-05-01", last_success_date=datetime.now() - timedelta(days=5)),
        AutoPayMandate(loan_id="LOAN006", customer_id="CUST006", status="Active",  mandate_type="e-NACH", bank_account_number="XXXX9012", ifsc_code="ICIC0002345", max_amount=7200.0,  activated_at=datetime.now() - timedelta(days=60), activated_by="customer", activation_channel="whatsapp", first_debit_date="2026-04-23", expiry_date="2027-04-23", last_success_date=datetime.now() - timedelta(days=10)),
        AutoPayMandate(loan_id="LOAN009", customer_id="CUST009", status="Active",  mandate_type="UPI AutoPay", bank_account_number="XXXX3456", ifsc_code="SBIN0003456", max_amount=6500.0,  activated_at=datetime.now() - timedelta(days=15), activated_by="customer", activation_channel="app",      first_debit_date="2026-05-10", expiry_date="2027-05-10"),
        AutoPayMandate(loan_id="LOAN013", customer_id="CUST013", status="Active",  mandate_type="e-NACH", bank_account_number="XXXX7890", ifsc_code="AXIS0004567", max_amount=9500.0,  activated_at=datetime.now() - timedelta(days=90), activated_by="officer",  activation_channel="branch",   first_debit_date="2026-04-15", expiry_date="2027-04-15", last_success_date=datetime.now() - timedelta(days=2)),
        AutoPayMandate(loan_id="LOAN025", customer_id="CUST005", status="Pending", mandate_type="e-NACH", bank_account_number="XXXX2345", ifsc_code="HDFC0005678", max_amount=5500.0,  activated_at=None,             activated_by=None,       activation_channel=None,       first_debit_date="2026-05-20", expiry_date="2027-05-20"),
    ]
    db.add_all(auto_pay_mandates)
    db.flush()
    
    # Create some bounce prevention actions (mock campaigns)
    prevention_actions = [
        BouncePreventionAction(loan_id="LOAN003", customer_id="CUST003", action_type="whatsapp",      risk_level_at_trigger="High",   recommended_by="AI", message_content="Enable auto-pay to avoid penalties", triggered_at=datetime.now() - timedelta(days=2), executed_at=datetime.now() - timedelta(days=2), status="sent",      customer_response="opened",  bounce_prevented=0),
        BouncePreventionAction(loan_id="LOAN005", customer_id="CUST005", action_type="voice_call",    risk_level_at_trigger="High",   recommended_by="AI", message_content="Officer call regarding EMI bounce risk", triggered_at=datetime.now() - timedelta(days=5), executed_at=datetime.now() - timedelta(days=5), status="delivered", customer_response="enrolled", bounce_prevented=1, response_time_hours=12.5),
        BouncePreventionAction(loan_id="LOAN012", customer_id="CUST012", action_type="auto_pay_link", risk_level_at_trigger="High",   recommended_by="AI", message_content="Click here to enable auto-pay: https://...", triggered_at=datetime.now() - timedelta(days=7), executed_at=datetime.now() - timedelta(days=7), status="sent",      customer_response="clicked", bounce_prevented=0),
        BouncePreventionAction(loan_id="LOAN018", customer_id="CUST018", action_type="sms",           risk_level_at_trigger="Medium", recommended_by="AI", message_content="Reminder: EMI due in 3 days. Enable auto-pay?", triggered_at=datetime.now() - timedelta(days=1), executed_at=datetime.now() - timedelta(days=1), status="delivered", customer_response="ignored",  bounce_prevented=0),
        BouncePreventionAction(loan_id="LOAN027", customer_id="CUST027", action_type="whatsapp",      risk_level_at_trigger="Medium", recommended_by="Officer", message_content="We noticed your payment pattern. Would you like auto-pay?", triggered_at=datetime.now() - timedelta(days=10), executed_at=datetime.now() - timedelta(days=10), status="sent",      customer_response="enrolled", bounce_prevented=1, response_time_hours=24.0),
    ]
    db.add_all(prevention_actions)

    print(f"✅ Bounce prevention data seeded: {len(bounce_profiles)} risk profiles, {len(auto_pay_mandates)} mandates, {len(prevention_actions)} actions")

    db.commit()
    db.close()
    print("✅ Database seeded successfully with 50 customers, 5 officers, 53 loans.")


if __name__ == "__main__":
    seed()
