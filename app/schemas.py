from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============================================================
# BASE
# ============================================================
class TimestampMixin(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================
# USERS
# ============================================================
class UserCreate(BaseModel):
    email: str
    phone: Optional[str] = None
    password: str = Field(min_length=6)
    first_name: str
    last_name: str
    role: str = "stylist"
    commission_rate: Optional[Decimal] = Decimal("40.00")
    color: Optional[str] = "#6366F1"


class UserUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    commission_rate: Optional[Decimal] = None
    color: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    phone: Optional[str] = None
    first_name: str
    last_name: str
    full_name: str
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    color: Optional[str] = None
    commission_rate: Optional[Decimal] = None
    bio: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# CLIENTS
# ============================================================
class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    preferences: Optional[dict] = None
    allergies: Optional[List[str]] = None
    referral_source: Optional[str] = None


class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    preferences: Optional[dict] = None
    allergies: Optional[List[str]] = None
    is_vip: Optional[bool] = None


class ClientResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    preferences: Optional[Any] = None
    allergies: Optional[List[str]] = None
    is_vip: bool
    total_visits: int
    total_spent: Decimal
    last_visit_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# SERVICES
# ============================================================
class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    duration_min: int
    price: Decimal
    color: Optional[str] = "#8B5CF6"
    requires_deposit: Optional[bool] = False
    deposit_amount: Optional[Decimal] = None


class ServiceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    duration_min: int
    price: Decimal
    is_active: bool
    color: Optional[str] = None
    requires_deposit: bool
    deposit_amount: Optional[Decimal] = None

    class Config:
        from_attributes = True


# ============================================================
# APPOINTMENTS
# ============================================================
class AppointmentCreate(BaseModel):
    client_id: UUID
    stylist_id: UUID
    service_id: UUID
    start_time: datetime
    notes: Optional[str] = None
    is_walk_in: Optional[bool] = False


class AppointmentReschedule(BaseModel):
    start_time: datetime


class AppointmentResponse(BaseModel):
    id: UUID
    client_id: UUID
    stylist_id: UUID
    service_id: UUID
    start_time: datetime
    end_time: datetime
    status: str
    notes: Optional[str] = None
    is_walk_in: bool
    is_recurring: bool
    source: Optional[str] = None
    cancel_reason: Optional[str] = None
    client: Optional[ClientResponse] = None
    stylist: Optional[UserResponse] = None
    service: Optional[ServiceResponse] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# VISIT NOTES
# ============================================================
class FormulaDetail(BaseModel):
    brand: Optional[str] = None
    color_code: Optional[str] = None
    formula_name: Optional[str] = None
    developer_vol: Optional[str] = None
    processing_time: Optional[int] = None
    formula_details: Optional[dict] = None
    hair_condition: Optional[str] = None
    allergy_test: Optional[bool] = False


class VisitNoteCreate(FormulaDetail):
    appointment_id: UUID
    client_id: UUID
    stylist_id: UUID
    service_id: UUID
    observations: Optional[str] = None
    products_used: Optional[List[dict]] = None
    follow_up_date: Optional[date] = None


class VisitNoteResponse(BaseModel):
    id: UUID
    appointment_id: UUID
    client_id: UUID
    stylist_id: UUID
    service_id: UUID
    formula_name: Optional[str] = None
    brand: Optional[str] = None
    color_code: Optional[str] = None
    formula_details: Optional[Any] = None
    developer_vol: Optional[str] = None
    processing_time: Optional[int] = None
    hair_condition: Optional[str] = None
    observations: Optional[str] = None
    products_used: Optional[Any] = None
    follow_up_date: Optional[date] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# PHOTOS
# ============================================================
class PhotoCreate(BaseModel):
    client_id: UUID
    appointment_id: Optional[UUID] = None
    visit_note_id: Optional[UUID] = None
    photo_url: str
    photo_type: str
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class PhotoResponse(BaseModel):
    id: UUID
    client_id: UUID
    photo_url: str
    thumbnail_url: Optional[str] = None
    photo_type: str
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# TRANSACTIONS (PAYMENTS)
# ============================================================
class TransactionItemCreate(BaseModel):
    item_type: str
    item_id: Optional[UUID] = None
    item_name: str
    quantity: int = 1
    unit_price: Decimal
    stylist_id: Optional[UUID] = None


class TransactionCreate(BaseModel):
    appointment_id: Optional[UUID] = None
    client_id: UUID
    transaction_type: str
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    tip_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    payment_method: str = "cash"
    card_last_four: Optional[str] = None
    notes: Optional[str] = None
    items: List[TransactionItemCreate] = []
    tip_distributions: Optional[List[dict]] = None


class TransactionResponse(BaseModel):
    id: UUID
    appointment_id: Optional[UUID] = None
    client_id: UUID
    transaction_type: str
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    tip_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    payment_method: str
    notes: Optional[str] = None
    items: Optional[List[Any]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# GIFT CARDS
# ============================================================
class GiftCardCreate(BaseModel):
    client_id: Optional[UUID] = None
    initial_balance: Decimal
    expires_at: Optional[date] = None


class GiftCardResponse(BaseModel):
    id: UUID
    code: str
    client_id: Optional[UUID] = None
    original_balance: Decimal
    current_balance: Decimal
    is_active: bool
    expires_at: Optional[date] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# INVENTORY
# ============================================================
class InventoryItemCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    cost_price: Decimal
    retail_price: Decimal
    current_stock: int = 0
    reorder_point: int = 5
    reorder_quantity: int = 20
    unit: str = "unit"
    barcode: Optional[str] = None


class InventoryItemResponse(BaseModel):
    id: UUID
    name: str
    brand: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    cost_price: Decimal
    retail_price: Decimal
    current_stock: int
    reorder_point: int
    reorder_quantity: int
    unit: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# COMMISSION
# ============================================================
class CommissionResponse(BaseModel):
    id: UUID
    stylist_id: UUID
    service_amount: Decimal
    retail_amount: Decimal
    tip_amount: Decimal
    service_earned: Decimal
    retail_earned: Decimal
    tip_earned: Decimal
    total_earned: Decimal
    is_paid: bool

    class Config:
        from_attributes = True


# ============================================================
# DASHBOARD
# ============================================================
class DashboardSummary(BaseModel):
    total_revenue_today: Decimal
    total_appointments_today: int
    appointments_by_status: dict
    active_clients: int
    new_clients_this_month: int
    top_stylist: Optional[str] = None
    low_stock_items: int
    upcoming_appointments: List[AppointmentResponse] = []
    revenue_by_service_category: List[dict] = []
    weekly_revenue: List[dict] = []


# ============================================================
# AUTH
# ============================================================
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================
# PAYMENT SYSTEM SPECIFIC SCHEMAS
# ============================================================
class SplitPaymentInput(BaseModel):
    transaction_id: UUID
    splits: List[dict]


class RefundInput(BaseModel):
    transaction_id: UUID
    amount: Optional[Decimal] = None
    reason: str


class TipDistributionInput(BaseModel):
    transaction_id: UUID
    stylist_id: UUID
    amount: Decimal
    percentage: Optional[Decimal] = None


class ProcessPaymentRequest(BaseModel):
    client_id: UUID
    appointment_id: Optional[UUID] = None
    items: List[TransactionItemCreate]
    tip_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    payment_method: str = "cash"
    card_last_four: Optional[str] = None
    tip_split: Optional[List[dict]] = None
    gift_card_code: Optional[str] = None
    gift_card_amount: Optional[Decimal] = None
