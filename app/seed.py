"""Seed the database with sample data for demo."""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import engine, Base, SessionLocal
from app.models import (
    User, Client, Service, Appointment, AppointmentStatus,
    Transaction, TransactionStatus, TransactionType, PaymentMethod,
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(User).count() > 0:
    print("Database already seeded, skipping")
    db.close()
    exit(0)

# ============================================================
# USERS
# ============================================================
owner = User(
    id=uuid.uuid4(), email='owner@salonos.com', password_hash='password123',
    first_name='Sarah', last_name='Johnson', role='owner', color='#8B5CF6',
)
stylist1 = User(
    id=uuid.uuid4(), email='maya@salonos.com', password_hash='password123',
    first_name='Maya', last_name='Rodriguez', role='stylist', color='#EC4899',
    commission_rate=Decimal('45.00'), bio='Specializing in balayage and creative color.',
)
stylist2 = User(
    id=uuid.uuid4(), email='james@salonos.com', password_hash='password123',
    first_name='James', last_name='Chen', role='stylist', color='#6366F1',
    commission_rate=Decimal('50.00'), bio='Expert in precision cuts and men\'s grooming.',
)
stylist3 = User(
    id=uuid.uuid4(), email='lena@salonos.com', password_hash='password123',
    first_name='Lena', last_name='Park', role='stylist', color='#F59E0B',
    commission_rate=Decimal('40.00'), bio='Keratin treatments and bridal styling specialist.',
)
reception = User(
    id=uuid.uuid4(), email='alex@salonos.com', password_hash='password123',
    first_name='Alex', last_name='Rivera', role='receptionist', color='#10B981',
)
users = [owner, stylist1, stylist2, stylist3, reception]
for u in users:
    db.add(u)
db.flush()

# ============================================================
# SERVICES
# ============================================================
services_data = [
    Service(name="Women's Haircut", category='cut', duration_min=60, price=Decimal('750.00'), color='#EC4899'),
    Service(name="Men's Haircut", category='cut', duration_min=30, price=Decimal('450.00'), color='#6366F1'),
    Service(name='Full Balayage', category='color', duration_min=150, price=Decimal('4500.00'), color='#8B5CF6'),
    Service(name='Partial Highlights', category='color', duration_min=90, price=Decimal('2800.00'), color='#A78BFA'),
    Service(name='Root Touch-Up', category='color', duration_min=60, price=Decimal('1800.00'), color='#C084FC'),
    Service(name='Keratin Treatment', category='treatment', duration_min=120, price=Decimal('4000.00'), color='#F59E0B'),
    Service(name='Deep Conditioning', category='treatment', duration_min=30, price=Decimal('900.00'), color='#34D399'),
    Service(name='Blowout', category='styling', duration_min=30, price=Decimal('1000.00'), color='#F472B6'),
    Service(name='Bridal Updo', category='styling', duration_min=90, price=Decimal('3500.00'), color='#FB7185'),
    Service(name='Balayage + Cut', category='package', duration_min=180, price=Decimal('5500.00'), color='#8B5CF6'),
]
for s in services_data:
    db.add(s)
db.flush()

# ============================================================
# CLIENTS
# ============================================================
clients_data = [
    Client(first_name='Emma', last_name='Thompson', phone='+91-9876543210', email='emma@example.com',
           preferences='{"style": "beachy waves", "products": ["Olaplex"]}',
           notes='Allergic to PPD. Prefers quiet appointments.', total_visits=24, total_spent=Decimal('84000.00'),
           last_visit_at=datetime.now() - timedelta(days=14)),
    Client(first_name='Olivia', last_name='Martinez', phone='+91-9876543211', email='olivia@example.com',
           preferences='{"style": "bold colors", "products": ["Redken"]}',
           notes='Always 10 min late. Has 2 kids.', total_visits=18, total_spent=Decimal('62000.00'),
           last_visit_at=datetime.now() - timedelta(days=3)),
    Client(first_name='Sophia', last_name='Williams', phone='+91-9876543212', email='sophia@example.com',
           preferences='{"style": "blunt bob", "products": ["K18"]}',
           notes='Very detail-oriented.', total_visits=12, total_spent=Decimal('36000.00'),
           last_visit_at=datetime.now() - timedelta(days=35)),
    Client(first_name='Priya', last_name='Sharma', phone='+91-9876543213', email='priya@example.com',
           is_vip=True, notes='Bridal package booked for Dec 2025.', total_visits=8, total_spent=Decimal('19000.00'),
           last_visit_at=datetime.now() - timedelta(days=60)),
    Client(first_name='Ananya', last_name='Verma', phone='+91-9876543214', email='ananya@example.com',
           preferences='{"style": "trendy", "products": ["Drugstore"]}',
           notes='College student. Budget-conscious.', total_visits=6, total_spent=Decimal('6400.00'),
           last_visit_at=datetime.now() - timedelta(days=30)),
]
for c in clients_data:
    db.add(c)
db.flush()

# ============================================================
# TRANSACTIONS (for revenue data only - no fake appointments)
# ============================================================
transactions_data = [
    Transaction(
        client_id=clients_data[0].id, processed_by=stylist1.id,
        transaction_type=TransactionType.service, status=TransactionStatus.completed,
        subtotal=Decimal('750.00'), tip_amount=Decimal('150.00'), total=Decimal('900.00'),
        payment_method=PaymentMethod.card,
    ),
    Transaction(
        client_id=clients_data[1].id, processed_by=stylist2.id,
        transaction_type=TransactionType.service, status=TransactionStatus.completed,
        subtotal=Decimal('4500.00'), tip_amount=Decimal('500.00'), total=Decimal('5000.00'),
        payment_method=PaymentMethod.card,
    ),
    Transaction(
        client_id=clients_data[0].id, processed_by=reception.id,
        transaction_type=TransactionType.gift_card_sale, status=TransactionStatus.completed,
        subtotal=Decimal('2000.00'), total=Decimal('2000.00'),
        payment_method=PaymentMethod.card,
    ),
]
for t in transactions_data:
    db.add(t)

# ============================================================
# APPOINTMENTS (sample for demo)
# ============================================================
from datetime import datetime as dt, timedelta as tdelta
today_start = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
tomorrow_start = today_start + tdelta(days=1)

sample_appointments = [
    Appointment(
        client_id=clients_data[0].id, stylist_id=stylist1.id, service_id=services_data[0].id,
        start_time=today_start + tdelta(hours=9), end_time=today_start + tdelta(hours=10),
        status=AppointmentStatus.confirmed, notes="Regular haircut",
    ),
    Appointment(
        client_id=clients_data[1].id, stylist_id=stylist3.id, service_id=services_data[2].id,
        start_time=today_start + tdelta(hours=10), end_time=today_start + tdelta(hours=12, minutes=30),
        status=AppointmentStatus.confirmed, notes="Full balayage touch up",
    ),
    Appointment(
        client_id=clients_data[2].id, stylist_id=stylist2.id, service_id=services_data[1].id,
        start_time=today_start + tdelta(hours=11, minutes=30), end_time=today_start + tdelta(hours=12),
        status=AppointmentStatus.checked_in, notes="",
    ),
    Appointment(
        client_id=clients_data[3].id, stylist_id=stylist1.id, service_id=services_data[8].id,
        start_time=today_start + tdelta(hours=13), end_time=today_start + tdelta(hours=14, minutes=30),
        status=AppointmentStatus.in_progress, notes="Bridal trial",
    ),
    Appointment(
        client_id=clients_data[0].id, stylist_id=stylist2.id, service_id=services_data[4].id,
        start_time=tomorrow_start + tdelta(hours=10), end_time=tomorrow_start + tdelta(hours=11),
        status=AppointmentStatus.confirmed, notes="Root touch up",
    ),
    Appointment(
        client_id=clients_data[1].id, stylist_id=stylist1.id, service_id=services_data[0].id,
        start_time=tomorrow_start + tdelta(hours=14), end_time=tomorrow_start + tdelta(hours=15),
        status=AppointmentStatus.confirmed, notes="",
    ),
]
for a in sample_appointments:
    db.add(a)
db.flush()

db.commit()
db.close()
print("Database seeded successfully!")
print(f"  - {len(users)} users")
print(f"  - {len(services_data)} services")
print(f"  - {len(clients_data)} clients")
print(f"  - {len(transactions_data)} transactions")
print(f"  - {len(sample_appointments)} appointments")
