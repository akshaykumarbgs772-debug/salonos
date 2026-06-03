import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import (
    Appointment, AppointmentStatus, Client,
    Service, Shift, Transaction, TransactionItem,
    TransactionStatus, TransactionType, User, UserRole,
    VisitNote,
)
from app.payment_service import PaymentProcessor
from app.schemas import (
    AppointmentCreate, ProcessPaymentRequest,
    ServiceCreate, VisitNoteCreate,
)

app = FastAPI(title="SalonOS", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        return db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    except (ValueError, Exception):
        return None


# ============================================================
# AUTH ROUTES
# ============================================================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.password_hash != password:
        return templates.TemplateResponse(request, "login.html", {
            "error": "Invalid email or password"
        })
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie(key="user_id", value=str(user.id), max_age=86400 * 30)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("user_id")
    return resp


# ============================================================
# PAGE ROUTES
# ============================================================
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    today = date.today()

    today_appts = db.query(Appointment).filter(
        func.date(Appointment.start_time) == today
    ).count()

    today_revenue = db.query(func.coalesce(func.sum(Transaction.total), 0)).filter(
        func.date(Transaction.created_at) == today,
        Transaction.status == TransactionStatus.completed,
        Transaction.transaction_type != TransactionType.refund,
    ).scalar()

    upcoming = db.query(Appointment).filter(
        Appointment.start_time >= datetime.now(),
        Appointment.status.in_([AppointmentStatus.confirmed, AppointmentStatus.pending]),
    ).order_by(Appointment.start_time).limit(10).all()

    active_clients = db.query(func.count(Client.id)).filter(
        Client.last_visit_at >= datetime.now() - timedelta(days=90)
    ).scalar()

    appointments_by_status = {}
    for status in AppointmentStatus:
        count = db.query(Appointment).filter(
            func.date(Appointment.start_time) == today,
            Appointment.status == status,
        ).count()
        if count > 0:
            appointments_by_status[status.value] = count

    weekly_revenue = []
    for i in range(7):
        day = today - timedelta(days=i)
        rev = db.query(func.coalesce(func.sum(Transaction.total), 0)).filter(
            func.date(Transaction.created_at) == day,
            Transaction.status == TransactionStatus.completed,
        ).scalar()
        weekly_revenue.append({"date": day.isoformat(), "revenue": float(rev)})
    weekly_revenue.reverse()

    total_revenue_today = float(today_revenue)

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "today_appointments": today_appts,
        "today_revenue": total_revenue_today,
        "active_clients": active_clients,
        "upcoming": upcoming,
        "appointments_by_status": appointments_by_status,
        "weekly_revenue": weekly_revenue,
    })





@app.get("/appointments", response_class=HTMLResponse)
def appointments_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    appts = db.query(Appointment).order_by(Appointment.start_time.desc()).limit(50).all()
    stylists = db.query(User).filter(User.role.in_([UserRole.stylist, UserRole.owner])).all()
    clients = db.query(Client).order_by(Client.first_name).all()
    services = db.query(Service).filter(Service.is_active == True).all()
    return templates.TemplateResponse(request, "appointments.html", {
        "user": user, "appointments": appts,
        "stylists": stylists, "clients": clients, "services": services,
    })


@app.get("/calendar", response_class=HTMLResponse)
def calendar_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    stylists = db.query(User).filter(User.role.in_([UserRole.stylist, UserRole.owner])).all()
    clients = db.query(Client).order_by(Client.first_name).all()
    services = db.query(Service).filter(Service.is_active == True).all()
    return templates.TemplateResponse(request, "calendar.html", {
        "user": user, "stylists": stylists,
        "clients": clients, "services": services,
    })


@app.get("/payments", response_class=HTMLResponse)
def payments_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    transactions = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(50).all()
    clients = db.query(Client).order_by(Client.first_name).all()
    services = db.query(Service).filter(Service.is_active == True).all()
    stylists = db.query(User).filter(User.role == UserRole.stylist).all()
    gift_cards = db.query(Transaction).filter(
        Transaction.transaction_type == TransactionType.gift_card_sale
    ).count()
    return templates.TemplateResponse(request, "payments.html", {
        "user": user, "transactions": transactions,
        "clients": clients, "services": services, "stylists": stylists,
        "gift_cards": gift_cards,
    })





@app.get("/staff", response_class=HTMLResponse)
def staff_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    staff = db.query(User).order_by(User.first_name).all()
    return templates.TemplateResponse(request, "staff.html", {
        "user": user, "staff": staff,
    })


# ============================================================
# API ROUTES
# ============================================================

@app.post("/api/services")
def api_create_service(data: ServiceCreate, db: Session = Depends(get_db)):
    service = Service(**data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return {"success": True, "service": {"id": str(service.id), "name": service.name}}


@app.get("/api/services")
def api_list_services(db: Session = Depends(get_db)):
    services = db.query(Service).filter(Service.is_active == True).all()
    return [{
        "id": str(s.id), "name": s.name, "category": s.category,
        "duration": s.duration_min, "price": float(s.price),
        "color": s.color,
    } for s in services]


@app.post("/api/appointments")
def api_create_appointment(data: AppointmentCreate, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == data.service_id).first()
    if not service:
        raise HTTPException(400, "Service not found")
    end_time = data.start_time + timedelta(minutes=service.duration_min)
    conflict = db.query(Appointment).filter(
        Appointment.stylist_id == data.stylist_id,
        Appointment.start_time < end_time,
        Appointment.end_time > data.start_time,
        Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.no_show]),
    ).first()
    if conflict:
        raise HTTPException(409, "Stylist is not available at this time")
    appt = Appointment(
        client_id=data.client_id,
        stylist_id=data.stylist_id,
        service_id=data.service_id,
        start_time=data.start_time,
        end_time=end_time,
        notes=data.notes,
        is_walk_in=data.is_walk_in,
        status=AppointmentStatus.confirmed,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return {"success": True, "appointment": {"id": str(appt.id)}}


@app.put("/api/appointments/{appt_id}/status")
def api_update_appointment_status(appt_id: str, status: str = Form(...), db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(Appointment.id == uuid.UUID(appt_id)).first()
    if not appt:
        raise HTTPException(404)
    appt.status = AppointmentStatus(status)
    db.commit()
    return {"success": True}


@app.get("/api/appointments/calendar")
def api_calendar_appointments(
    start: str = Query(...), end: str = Query(...),
    stylist_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Appointment).filter(
        Appointment.start_time >= datetime.fromisoformat(start),
        Appointment.end_time <= datetime.fromisoformat(end),
        Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.no_show]),
    )
    if stylist_id:
        query = query.filter(Appointment.stylist_id == uuid.UUID(stylist_id))

    results = []
    for a in query.all():
        client = db.query(Client).filter(Client.id == a.client_id).first()
        service = db.query(Service).filter(Service.id == a.service_id).first()
        stylist = db.query(User).filter(User.id == a.stylist_id).first()
        results.append({
            "id": str(a.id),
            "title": f"{client.full_name if client else 'Unknown'} - {service.name if service else ''}",
            "start": a.start_time.isoformat(),
            "end": a.end_time.isoformat(),
            "backgroundColor": service.color if service else "#8B5CF6",
            "borderColor": service.color if service else "#8B5CF6",
            "textColor": "#fff",
            "extendedProps": {
                "client": client.full_name if client else "",
                "service": service.name if service else "",
                "stylist": stylist.full_name if stylist else "",
                "status": a.status.value,
                "notes": a.notes or "",
            },
        })
    return results


@app.post("/api/visit-notes")
def api_create_visit_note(data: VisitNoteCreate, db: Session = Depends(get_db)):
    note = VisitNote(**data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"success": True, "note": {"id": str(note.id)}}


@app.post("/api/payments/process")
def api_process_payment(data: ProcessPaymentRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401)
    processor = PaymentProcessor(db)
    try:
        txn = processor.process_payment(
            client_id=data.client_id,
            processed_by=user.id,
            transaction_type="service",
            items=[i.model_dump() for i in data.items],
            payment_method=data.payment_method,
            tip_amount=data.tip_amount,
            discount_amount=data.discount_amount,
            card_last_four=data.card_last_four,
            appointment_id=data.appointment_id,
            gift_card_code=data.gift_card_code,
            gift_card_amount=data.gift_card_amount,
            tip_split=[dict(s) for s in (data.tip_split or [])],
        )
        if txn.tip_amount > 0 and data.tip_split:
            processor.distribute_tips(txn.id, [dict(s) for s in data.tip_split])
        if txn.payment_method != "cash":
            processor.calculate_commission(txn.id)
        return {"success": True, "transaction": {
            "id": str(txn.id),
            "total": float(txn.total),
            "subtotal": float(txn.subtotal),
            "tip": float(txn.tip_amount),
            "status": txn.status.value,
        }}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/payments/refund")
def api_refund_payment(
    transaction_id: str = Form(...),
    reason: str = Form(...),
    amount: Optional[float] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401)
    processor = PaymentProcessor(db)
    try:
        refund = processor.process_refund(
            transaction_id=uuid.UUID(transaction_id),
            processed_by=user.id,
            amount=Decimal(str(amount)) if amount else None,
            reason=reason,
        )
        return {"success": True, "refund": {
            "id": str(refund.id), "amount": float(abs(refund.total)),
        }}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/payments/gift-card")
def api_issue_gift_card(
    client_id: str = Form(...),
    amount: float = Form(...),
    db: Session = Depends(get_db),
):
    processor = PaymentProcessor(db)
    try:
        card = processor.issue_gift_card(
            initial_balance=Decimal(str(amount)),
            client_id=uuid.UUID(client_id),
        )
        return {"success": True, "gift_card": {
            "code": card.code, "balance": float(card.current_balance),
        }}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/payments/history")
def api_payment_history(client_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(50)
    if client_id:
        query = query.filter(Transaction.client_id == uuid.UUID(client_id))
    results = []
    for t in query.all():
        client = db.query(Client).filter(Client.id == t.client_id).first()
        results.append({
            "id": str(t.id),
            "client": client.full_name if client else "",
            "type": t.transaction_type.value,
            "method": t.payment_method.value,
            "subtotal": float(t.subtotal),
            "tip": float(t.tip_amount),
            "total": float(t.total),
            "status": t.status.value,
            "date": t.created_at.isoformat() if t.created_at else "",
        })
    return results


@app.post("/api/staff")
def api_create_staff(
    first_name: str = Form(...), last_name: str = Form(...),
    email: str = Form(...), phone: str = Form(""),
    role: str = Form("stylist"), commission_rate: float = Form(40.0),
    bio: str = Form(""),
    db: Session = Depends(get_db),
):
    staff = User(
        email=email, phone=phone,
        password_hash="$2b$12$placeholder",
        first_name=first_name, last_name=last_name,
        role=UserRole(role),
        commission_rate=Decimal(str(commission_rate)),
        bio=bio,
    )
    db.add(staff)
    db.commit()
    return {"success": True, "staff": {"id": str(staff.id), "name": staff.full_name}}


@app.get("/api/stats/revenue-by-stylist")
def api_revenue_by_stylist(db: Session = Depends(get_db)):
    rows = db.query(
        User.id, User.first_name, User.last_name,
        func.coalesce(func.sum(Transaction.total), 0).label("revenue"),
    ).join(Transaction, Transaction.processed_by == User.id).filter(
        func.date(Transaction.created_at) >= date.today() - timedelta(days=30),
        Transaction.status == TransactionStatus.completed,
    ).group_by(User.id).all()
    return [{
        "name": f"{r.first_name} {r.last_name}",
        "revenue": float(r.revenue),
    } for r in rows]


@app.get("/api/stats/revenue-by-category")
def api_revenue_by_category(db: Session = Depends(get_db)):
    rows = db.query(
        Service.category,
        func.coalesce(func.sum(TransactionItem.total_price), 0).label("revenue"),
    ).join(TransactionItem, TransactionItem.item_id == Service.id).filter(
        TransactionItem.item_type == "service",
    ).group_by(Service.category).all()
    return [{"category": r.category, "revenue": float(r.revenue)} for r in rows]


@app.get("/api/stats/summary")
def api_stats_summary(db: Session = Depends(get_db)):
    today = date.today()
    return {
        "today_revenue": float(db.query(func.coalesce(func.sum(Transaction.total), 0)).filter(
            func.date(Transaction.created_at) == today,
            Transaction.status == TransactionStatus.completed,
        ).scalar()),
        "today_appointments": db.query(Appointment).filter(
            func.date(Appointment.start_time) == today
        ).count(),
        "active_clients": db.query(Client).filter(
            Client.last_visit_at >= datetime.now() - timedelta(days=90)
        ).count(),
        "pending_appointments": db.query(Appointment).filter(
            Appointment.status == AppointmentStatus.pending
        ).count(),
        "today_checkins": db.query(Appointment).filter(
            func.date(Appointment.start_time) == today,
            Appointment.status == AppointmentStatus.checked_in,
        ).count(),
    }


# ============================================================
# PUBLIC BOOKING (client-facing)
# ============================================================
@app.get("/book", response_class=HTMLResponse)
def public_booking_page(request: Request, db: Session = Depends(get_db)):
    services = db.query(Service).filter(Service.is_active == True).order_by(Service.category, Service.name).all()
    stylists = db.query(User).filter(User.role.in_([UserRole.stylist, UserRole.owner])).order_by(User.first_name).all()
    # Fetch upcoming appointments for 14 days to show booked slots
    from datetime import timedelta as td
    upcoming_appts = db.query(Appointment).filter(
        Appointment.start_time >= datetime.now(),
        Appointment.start_time < datetime.now() + td(days=14),
        Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.no_show]),
    ).order_by(Appointment.start_time).all()
    appointments_json = [{
        "stylist_id": str(a.stylist_id),
        "start_time": a.start_time.isoformat(),
        "end_time": a.end_time.isoformat(),
        "service_id": str(a.service_id),
        "client_id": str(a.client_id),
        "status": a.status.value,
    } for a in upcoming_appts]
    return templates.TemplateResponse(request, "book.html", {
        "services": services, "stylists": stylists,
        "appointments": appointments_json,
    })


class PublicBookingInput(BaseModel):
    client_name: str
    client_phone: str
    client_email: Optional[str] = None
    stylist_id: str
    service_id: str
    start_time: str
    notes: Optional[str] = None


@app.post("/api/public/book")
def api_public_booking(data: PublicBookingInput, db: Session = Depends(get_db)):
    from datetime import datetime as dt

    try:
        try:
            service_uuid = uuid.UUID(data.service_id)
        except ValueError:
            raise HTTPException(400, f"Invalid service ID format: {data.service_id}")
        service = db.query(Service).filter(Service.id == service_uuid).first()
        if not service:
            raise HTTPException(400, f"Service not found (ID: {data.service_id})")
        try:
            stylist_uuid = uuid.UUID(data.stylist_id)
        except ValueError:
            raise HTTPException(400, f"Invalid stylist ID format: {data.stylist_id}")
        stylist = db.query(User).filter(User.id == stylist_uuid).first()
        if not stylist:
            raise HTTPException(400, f"Stylist not found (ID: {data.stylist_id})")

        start = dt.fromisoformat(data.start_time.replace('Z', '+00:00'))
        end = start + timedelta(minutes=service.duration_min)

        conflict = db.query(Appointment).filter(
            Appointment.stylist_id == stylist.id,
            Appointment.start_time < end,
            Appointment.end_time > start,
            Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.no_show]),
        ).first()
        if conflict:
            raise HTTPException(409, "This time slot is no longer available")

        client = db.query(Client).filter(Client.phone == data.client_phone).first()
        if not client:
            client = Client(
                first_name=data.client_name.split(' ')[0] if ' ' in data.client_name else data.client_name,
                last_name=data.client_name.split(' ')[-1] if ' ' in data.client_name else '',
                phone=data.client_phone,
                email=data.client_email or '',
            )
            db.add(client)
            db.flush()

        appt = Appointment(
            client_id=client.id,
            stylist_id=stylist.id,
            service_id=service.id,
            start_time=start,
            end_time=end,
            status=AppointmentStatus.confirmed,
            notes=data.notes or '',
            source='online',
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)

        return {"success": True, "booking_id": str(appt.id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/appointments")
def api_list_appointments(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401)
    appts = db.query(Appointment).order_by(Appointment.start_time.desc()).limit(100).all()
    results = []
    for a in appts:
        client = db.query(Client).filter(Client.id == a.client_id).first()
        service = db.query(Service).filter(Service.id == a.service_id).first()
        stylist = db.query(User).filter(User.id == a.stylist_id).first()
        results.append({
            "id": str(a.id),
            "client": client.full_name if client else "",
            "client_id": str(a.client_id),
            "service": service.name if service else "",
            "service_id": str(a.service_id),
            "stylist": stylist.full_name if stylist else "",
            "stylist_id": str(a.stylist_id),
            "start_time": a.start_time.isoformat(),
            "end_time": a.end_time.isoformat(),
            "duration": service.duration_min if service else 0,
            "status": a.status.value,
            "notes": a.notes or "",
        })
    return results


@app.get("/api/staff")
def api_list_staff(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401)
    staff = db.query(User).order_by(User.first_name).all()
    return [{
        "id": str(s.id), "name": s.full_name, "email": s.email,
        "phone": s.phone or "", "role": s.role.value,
        "is_active": s.is_active, "color": s.color,
        "commission_rate": float(s.commission_rate) if s.commission_rate else 0,
        "bio": s.bio or "",
    } for s in staff]


@app.get("/api/clients")
def api_list_clients(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401)
    clients = db.query(Client).order_by(Client.first_name).all()
    return [{
        "id": str(c.id), "name": c.full_name, "phone": c.phone or "",
        "email": c.email or "", "is_vip": c.is_vip,
        "total_visits": c.total_visits, "total_spent": float(c.total_spent or 0),
        "last_visit": c.last_visit_at.isoformat() if c.last_visit_at else None,
    } for c in clients]


@app.get("/api/waitlist")
def api_waitlist(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401)
    from app.models import WaitlistEntry
    entries = db.query(WaitlistEntry).filter(
        WaitlistEntry.status == "waiting"
    ).order_by(WaitlistEntry.created_at).all()
    results = []
    for e in entries:
        client = db.query(Client).filter(Client.id == e.client_id).first()
        results.append({
            "id": str(e.id),
            "client": client.full_name if client else "",
            "phone": client.phone if client else "",
            "preferred_date": e.preferred_date.isoformat() if e.preferred_date else "",
            "preferred_time": str(e.preferred_time) if e.preferred_time else "",
            "created_at": e.created_at.isoformat() if e.created_at else "",
        })
    return results
