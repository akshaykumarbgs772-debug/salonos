import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Enum, ForeignKey,
    Index, Integer, JSON, Numeric, String, Text, Time, Uuid,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, enum.Enum):
    owner = "owner"
    stylist = "stylist"
    receptionist = "receptionist"
    admin = "admin"


class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    checked_in = "checked_in"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"
    rescheduled = "rescheduled"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    refunded = "refunded"
    partial_refund = "partial_refund"
    failed = "failed"


class TransactionType(str, enum.Enum):
    service = "service"
    product = "product"
    tip = "tip"
    deposit = "deposit"
    refund = "refund"
    gift_card_sale = "gift_card_sale"
    gift_card_redemption = "gift_card_redemption"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    card = "card"
    digital_wallet = "digital_wallet"
    gift_card = "gift_card"
    mixed = "mixed"


class ShiftStatus(str, enum.Enum):
    scheduled = "scheduled"
    clocked_in = "clocked_in"
    on_break = "on_break"
    clocked_out = "clocked_out"
    absent = "absent"


class PhotoType(str, enum.Enum):
    before = "before"
    after = "after"
    formula = "formula"
    inspiration = "inspiration"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.stylist)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(500))
    color = Column(String(7), default="#6366F1")
    commission_rate = Column(Numeric(5, 2), default=Decimal("40.00"))
    hourly_rate = Column(Numeric(10, 2))
    pin_code = Column(String(6))
    bio = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    appointments = relationship("Appointment", foreign_keys="Appointment.stylist_id", back_populates="stylist")
    shifts = relationship("Shift", back_populates="user")
    commissions = relationship("Commission", back_populates="stylist")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Client(Base):
    __tablename__ = "clients"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(20))
    birthday = Column(Date)
    gender = Column(String(20))
    notes = Column(Text)
    preferences = Column(JSON, default=dict)
    allergies = Column(JSON, default=list)
    is_vip = Column(Boolean, default=False)
    referral_source = Column(String(100))
    referred_by = Column(Uuid, ForeignKey("clients.id"))
    total_visits = Column(Integer, default=0)
    total_spent = Column(Numeric(12, 2), default=Decimal("0.00"))
    last_visit_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    appointments = relationship("Appointment", back_populates="client")
    visit_notes = relationship("VisitNote", back_populates="client")
    photos = relationship("Photo", back_populates="client")
    transactions = relationship("Transaction", back_populates="client")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if self.birthday:
            today = date.today()
            return today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))
        return None


class Service(Base):
    __tablename__ = "services"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)
    duration_min = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    color = Column(String(7), default="#8B5CF6")
    commissionable = Column(Boolean, default=True)
    requires_deposit = Column(Boolean, default=False)
    deposit_amount = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    appointments = relationship("Appointment", back_populates="service")
    visit_notes = relationship("VisitNote", back_populates="service")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id = Column(Uuid, ForeignKey("clients.id"), nullable=False)
    stylist_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    service_id = Column(Uuid, ForeignKey("services.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.pending)
    notes = Column(Text)
    is_walk_in = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    recurring_rule = Column(String(100))
    source = Column(String(50), default="online")
    confirmation_token = Column(String(100))
    cancelled_at = Column(DateTime(timezone=True))
    cancel_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="appointments")
    stylist = relationship("User", foreign_keys=[stylist_id], back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    visit_notes = relationship("VisitNote", back_populates="appointment")
    photos = relationship("Photo", back_populates="appointment")
    transactions = relationship("Transaction", back_populates="appointment")

    __table_args__ = (
        Index("idx_appointments_stylist_date", stylist_id, start_time),
    )


class VisitNote(Base):
    __tablename__ = "visit_notes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    appointment_id = Column(Uuid, ForeignKey("appointments.id"), nullable=False)
    client_id = Column(Uuid, ForeignKey("clients.id"), nullable=False)
    stylist_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    service_id = Column(Uuid, ForeignKey("services.id"), nullable=False)

    formula_name = Column(String(200))
    brand = Column(String(100))
    color_code = Column(String(100))
    formula_details = Column(JSON, default=dict)
    developer_vol = Column(String(10))
    processing_time = Column(Integer)
    hair_condition = Column(Text)
    allergy_test = Column(Boolean, default=False)

    observations = Column(Text)
    products_used = Column(JSON, default=list)
    follow_up_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    appointment = relationship("Appointment", back_populates="visit_notes")
    client = relationship("Client", back_populates="visit_notes")
    service = relationship("Service", back_populates="visit_notes")
    photos = relationship("Photo", back_populates="visit_note")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id = Column(Uuid, ForeignKey("clients.id"), nullable=False)
    appointment_id = Column(Uuid, ForeignKey("appointments.id"))
    visit_note_id = Column(Uuid, ForeignKey("visit_notes.id"))
    uploaded_by = Column(Uuid, ForeignKey("users.id"))
    photo_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    photo_type = Column(String(20), nullable=False)
    tags = Column(JSON, default=list)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("photo_type IN ('before', 'after', 'formula', 'inspiration', 'other')"),
    )

    client = relationship("Client", back_populates="photos")
    appointment = relationship("Appointment", back_populates="photos")
    visit_note = relationship("VisitNote", back_populates="photos")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    appointment_id = Column(Uuid, ForeignKey("appointments.id"))
    client_id = Column(Uuid, ForeignKey("clients.id"), nullable=False)
    processed_by = Column(Uuid, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.completed)
    subtotal = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    tax_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    tip_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    discount_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    payment_method = Column(Enum(PaymentMethod), nullable=False, default=PaymentMethod.cash)
    card_last_four = Column(String(4))
    stripe_payment_id = Column(String(255))
    notes = Column(Text)
    refund_of_id = Column(Uuid, ForeignKey("transactions.id"))
    refund_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    appointment = relationship("Appointment", back_populates="transactions")
    client = relationship("Client", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction")
    tip_distributions = relationship("TipDistribution", back_populates="transaction")
    commissions = relationship("Commission", back_populates="transaction")


class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id = Column(Uuid, ForeignKey("transactions.id"), nullable=False)
    item_type = Column(String(50), nullable=False)
    item_id = Column(Uuid)
    item_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    stylist_id = Column(Uuid, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="items")


class TipDistribution(Base):
    __tablename__ = "tip_distributions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id = Column(Uuid, ForeignKey("transactions.id"), nullable=False)
    stylist_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    percentage = Column(Numeric(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="tip_distributions")


class GiftCard(Base):
    __tablename__ = "gift_cards"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True)
    client_id = Column(Uuid, ForeignKey("clients.id"))
    original_balance = Column(Numeric(10, 2), nullable=False)
    current_balance = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    brand = Column(String(100))
    sku = Column(String(100), unique=True)
    category = Column(String(100))
    cost_price = Column(Numeric(10, 2), nullable=False)
    retail_price = Column(Numeric(10, 2), nullable=False)
    current_stock = Column(Integer, nullable=False, default=0)
    reorder_point = Column(Integer, default=5)
    reorder_quantity = Column(Integer, default=20)
    unit = Column(String(20), default="unit")
    is_active = Column(Boolean, default=True)
    barcode = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id = Column(Uuid, ForeignKey("inventory_items.id"), nullable=False)
    quantity_change = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)
    reference_id = Column(Uuid)
    reference_type = Column(String(50))
    notes = Column(Text)
    performed_by = Column(Uuid, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    scheduled_start = Column(DateTime(timezone=True))
    scheduled_end = Column(DateTime(timezone=True))
    clock_in_at = Column(DateTime(timezone=True))
    clock_out_at = Column(DateTime(timezone=True))
    break_start = Column(DateTime(timezone=True))
    break_end = Column(DateTime(timezone=True))
    status = Column(Enum(ShiftStatus), nullable=False, default=ShiftStatus.scheduled)
    total_hours = Column(Numeric(5, 2))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="shifts")


class Commission(Base):
    __tablename__ = "commissions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    stylist_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(Uuid, ForeignKey("transactions.id"), nullable=False)
    appointment_id = Column(Uuid, ForeignKey("appointments.id"))
    service_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    retail_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    tip_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    service_rate = Column(Numeric(5, 2), nullable=False)
    retail_rate = Column(Numeric(5, 2), nullable=False, default=Decimal("10.00"))
    service_earned = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    retail_earned = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    tip_earned = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    bonus_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_earned = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stylist = relationship("User", back_populates="commissions")
    transaction = relationship("Transaction", back_populates="commissions")


class WaitlistEntry(Base):
    __tablename__ = "waitlist"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id = Column(Uuid, ForeignKey("clients.id"), nullable=False)
    service_id = Column(Uuid, ForeignKey("services.id"))
    preferred_date = Column(Date)
    preferred_time = Column(Time)
    notified_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="waiting")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    recipient_type = Column(String(20), nullable=False)
    recipient_id = Column(Uuid, nullable=False)
    channel = Column(String(20), nullable=False)
    template = Column(String(100))
    subject = Column(String(200))
    body = Column(Text)
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("recipient_type IN ('client', 'staff')"),
        CheckConstraint("channel IN ('sms', 'email', 'push')"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(Uuid)
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
