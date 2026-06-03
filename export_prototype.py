#!/usr/bin/env python3
"""Generate standalone offline prototype HTML files for mobile demo."""
import os, shutil
from datetime import datetime, date, timedelta
from decimal import Decimal
from types import SimpleNamespace

TEMPLATE_DIR = "app/templates"
CSS_PATH = "app/static/css/style.css"
JS_PATH = "app/static/js/app.js"
OUTPUT_DIR = "prototype_export"

def load_file(path):
    with open(path) as f:
        return f.read()

CSS_CONTENT = load_file(CSS_PATH)
# Replace Google Fonts import with system font fallback
CSS_CONTENT = CSS_CONTENT.replace(
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');",
    ""
)
CSS_CONTENT = CSS_CONTENT.replace(
    "font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;",
    "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;"
)

JS_CONTENT = load_file(JS_PATH)

def obj(**kwargs):
    return SimpleNamespace(**kwargs)

def mock_user(first, last, role, color, email):
    return obj(
        first_name=first, last_name=last,
        full_name=f"{first} {last}",
        email=email, phone="+91-9876543200",
        color=color,
        role=obj(value=role),
        is_active=True,
        commission_rate=Decimal("45.00"),
        bio=f"Professional {role}",
        shifts=[obj()],
        appointments=[obj()],
        id="usr-001",
    )

def mock_service(name, cat, dur, price, color):
    return obj(
        id=f"svc-{name.lower().replace(' ', '-')}",
        name=name, category=cat, duration_min=dur,
        price=Decimal(str(price)), color=color,
        is_active=True,
    )

def mock_client(fname, lname, phone, email, is_vip=False):
    return obj(
        id=f"cli-{fname.lower()}",
        first_name=fname, last_name=lname,
        full_name=f"{fname} {lname}",
        phone=phone, email=email, is_vip=is_vip,
        total_visits=12, total_spent=Decimal("34000.00"),
        last_visit_at=datetime.now() - timedelta(days=7),
    )

def mock_appt(client, service, stylist, start, status):
    return obj(
        id=f"apt-{start.strftime('%H%M')}",
        client=client,
        service=service,
        stylist=stylist,
        start_time=start,
        end_time=start + timedelta(minutes=service.duration_min),
        status=obj(value=status),
        notes="",
    )

def mock_txn(client, stylist, service, subtotal, tip, total, method, ttype, status, when=None):
    return obj(
        id=f"txn-{id(obj)}",
        client=client,
        created_at=when or datetime.now(),
        transaction_type=obj(value=ttype),
        payment_method=obj(value=method),
        subtotal=Decimal(str(subtotal)),
        tip_amount=Decimal(str(tip)),
        discount_amount=Decimal("0"),
        total=Decimal(str(total)),
        status=obj(value=status),
    )

# ============================================================
# MOCK DATA
# ============================================================
now = datetime.now()
today = date.today()

active_user = mock_user("Sarah", "Johnson", "owner", "#8B5CF6", "owner@salonos.com")

services = [
    mock_service("Women's Haircut", "cut", 60, 750, "#EC4899"),
    mock_service("Men's Haircut", "cut", 30, 450, "#6366F1"),
    mock_service("Full Balayage", "color", 150, 4500, "#8B5CF6"),
    mock_service("Partial Highlights", "color", 90, 2800, "#A78BFA"),
    mock_service("Root Touch-Up", "color", 60, 1800, "#C084FC"),
    mock_service("Keratin Treatment", "treatment", 120, 4000, "#F59E0B"),
    mock_service("Deep Conditioning", "treatment", 30, 900, "#34D399"),
    mock_service("Blowout", "styling", 30, 1000, "#F472B6"),
    mock_service("Bridal Updo", "styling", 90, 3500, "#FB7185"),
    mock_service("Balayage + Cut", "package", 180, 5500, "#8B5CF6"),
]

stylists = [
    mock_user("Maya", "Rodriguez", "stylist", "#EC4899", "maya@salonos.com"),
    mock_user("James", "Chen", "stylist", "#6366F1", "james@salonos.com"),
    mock_user("Lena", "Park", "stylist", "#F59E0B", "lena@salonos.com"),
]
stylists[0].bio = "Specializing in balayage and creative color."
stylists[1].bio = "Expert in precision cuts and men's grooming."
stylists[2].bio = "Keratin treatments and bridal styling specialist."

clients = [
    mock_client("Emma", "Thompson", "+91-9876543210", "emma@example.com"),
    mock_client("Olivia", "Martinez", "+91-9876543211", "olivia@example.com"),
    mock_client("Sophia", "Williams", "+91-9876543212", "sophia@example.com"),
    mock_client("Priya", "Sharma", "+91-9876543213", "priya@example.com", is_vip=True),
    mock_client("Ananya", "Verma", "+91-9876543214", "ananya@example.com"),
]

staff = stylists + [
    mock_user("Alex", "Rivera", "receptionist", "#10B981", "alex@salonos.com"),
    active_user,
]

appts_today = [
    mock_appt(clients[0], services[0], stylists[0], now.replace(hour=9, minute=0, second=0), "confirmed"),
    mock_appt(clients[1], services[2], stylists[2], now.replace(hour=10, minute=0, second=0), "confirmed"),
    mock_appt(clients[2], services[1], stylists[1], now.replace(hour=11, minute=30, second=0), "checked_in"),
    mock_appt(clients[3], services[8], stylists[0], now.replace(hour=13, minute=0, second=0), "in_progress"),
    mock_appt(clients[4], services[6], stylists[2], now.replace(hour=15, minute=0, second=0), "confirmed"),
]

appts_upcoming = appts_today + [
    mock_appt(clients[0], services[4], stylists[1], now.replace(hour=16, minute=0, second=0) + timedelta(days=1), "confirmed"),
    mock_appt(clients[1], services[0], stylists[0], now.replace(hour=10, minute=0, second=0) + timedelta(days=1), "confirmed"),
    mock_appt(clients[3], services[3], stylists[2], now.replace(hour=14, minute=0, second=0) + timedelta(days=1), "pending"),
]

transactions = [
    mock_txn(clients[0], stylists[0], services[0], 750, 150, 900, "card", "service", "completed", now - timedelta(hours=2)),
    mock_txn(clients[1], stylists[2], services[2], 4500, 500, 5000, "card", "service", "completed", now - timedelta(hours=1)),
    mock_txn(clients[2], stylists[1], services[1], 450, 50, 500, "cash", "service", "completed", now - timedelta(minutes=30)),
    mock_txn(clients[0], active_user, services[0], 2000, 0, 2000, "card", "gift_card_sale", "completed", now - timedelta(days=1)),
    mock_txn(clients[3], stylists[0], services[8], 3500, 700, 4200, "digital_wallet", "service", "completed", now - timedelta(days=2)),
]

today_revenue = sum(float(t.total) for t in transactions if t.created_at.date() == today)
today_appointments_count = sum(1 for a in appts_today if a.start_time.date() == today)
active_clients_count = 5
gift_cards_count = 1

appointments_by_status = {"confirmed": 3, "checked_in": 1, "in_progress": 1}

weekly_revenue_data = []
for i in range(7):
    day = today - timedelta(days=6-i)
    weekly_revenue_data.append({"date": day.isoformat(), "revenue": float(2000 + i * 800 + hash(str(day)) % 1500)})

# Calendar events (for FullCalendar mockup)
calendar_events = []
for a in appts_today + appts_upcoming:
    calendar_events.append({
        "id": a.id, "title": f"{a.client.full_name} - {a.service.name}",
        "start": a.start_time.isoformat(), "end": a.end_time.isoformat(),
        "backgroundColor": a.service.color, "borderColor": a.service.color,
        "textColor": "#fff",
        "extendedProps": {
            "client": a.client.full_name, "service": a.service.name,
            "stylist": a.stylist.full_name, "status": a.status.value, "notes": "",
        },
    })

# ============================================================
# RENDER ENGINE
# ============================================================
os.makedirs(OUTPUT_DIR, exist_ok=True)

def inline_css(html):
    """Inline CSS into HTML head."""
    css_tag = '<link href="/static/css/style.css" rel="stylesheet">'
    inline = f"<style>\n{CSS_CONTENT}\n</style>"
    html = html.replace(css_tag, inline)
    html = html.replace(
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">',
        ""
    )
    # Remove FullCalendar CDN CSS
    html = html.replace(
        '<link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.css" rel="stylesheet">',
        ""
    )
    return html

def inline_js(html):
    """Inline JS into HTML."""
    js_tag = '<script src="/static/js/app.js"></script>'
    inline = f"<script>\n{JS_CONTENT}\n</script>"
    html = html.replace(js_tag, inline)
    # Remove FullCalendar CDN JS
    html = html.replace(
        '<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js"></script>',
        ""
    )
    return html

def fix_links(html, page_name):
    """Fix sidebar links to point to local HTML files."""
    links = {
        'href="/"': f'href="dashboard.html"',
        'href="/calendar"': 'href="calendar.html"',
        'href="/appointments"': 'href="appointments.html"',
        'href="/payments"': 'href="payments.html"',
        'href="/staff"': 'href="staff.html"',
        'href="/login"': 'href="login.html"',
        'href="/logout"': '#',
        'href="/book"': 'href="book.html"',
    }
    for old, new in links.items():
        html = html.replace(old, new)
    # Fix form actions
    html = html.replace('action="/login"', 'action="#"')
    html = html.replace('action="/api/staff"', 'action="#"')
    return html

def render_template(template_name, **context):
    """Simple Jinja2-like template renderer for the specific variables used."""
    content = load_file(f"{TEMPLATE_DIR}/{template_name}")
    variables = {}

    # Render with Python string formatting for simple cases
    # But we need Jinja2 - let's use it
    from jinja2 import Environment, FileSystemLoader, Template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    # Simulate request
    template = env.get_template(template_name)
    
    # Create request mock
    request = obj(url=obj(path=f"/{template_name.replace('.html', '')}"))
    
    full_context = dict(context, request=request)
    return template.render(**full_context)

def render_and_save(template_name, output_name, **context):
    print(f"  Rendering {template_name}...")
    html = render_template(template_name, **context)
    html = inline_css(html)
    html = fix_links(html, output_name)
    
    # Inline JS for pages that use app.js (not login/book)
    if template_name != "login.html" and template_name != "book.html":
        html = inline_js(html)
    
    with open(f"{OUTPUT_DIR}/{output_name}", "w") as f:
        f.write(html)
    print(f"    -> {OUTPUT_DIR}/{output_name}")

# ============================================================
# GENERATE PAGES
# ============================================================
# ============================================================
# GENERATE STATIC CALENDAR VIEW
# ============================================================
def render_calendar_page():
    """Render calendar page replacing FullCalendar with static week view."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("calendar.html")
    request = obj(url=obj(path="/calendar"))
    
    html = template.render(
        request=request, user=active_user,
        stylists=stylists, clients=clients, services=services,
    )
    html = inline_css(html)
    html = inline_js(html)
    html = fix_links(html, "calendar.html")
    
    # Replace FullCalendar div with a static weekly calendar table
    week_start = today - timedelta(days=today.weekday())
    time_slots = [f"{h:02d}:00" for h in range(9, 19)]
    
    cal_html = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px;min-width:700px">'
    cal_html += '<thead><tr style="background:#1E1B2E;color:white">'
    cal_html += '<th style="padding:10px 8px;text-align:center;width:60px;font-size:11px;font-weight:600">Time</th>'
    
    days_headers = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, dname in enumerate(days_headers):
        d = week_start + timedelta(days=i)
        cls = 'today' if d == today else ''
        style = 'background:rgba(139,92,246,0.15)' if d == today else ''
        cal_html += f'<th style="padding:10px 4px;text-align:center;font-size:11px;font-weight:600;{style}"><div style="font-size:10px;text-transform:uppercase;opacity:0.7">{dname}</div><div style="font-size:16px;font-weight:800">{d.day}</div></th>'
    cal_html += '</tr></thead><tbody>'
    
    for slot in time_slots:
        hour = int(slot.split(":")[0])
        cal_html += f'<tr><td style="padding:10px 8px;text-align:center;font-size:11px;color:#6B7280;font-weight:600;border-bottom:1px solid #F3F4F6">{slot}</td>'
        for di in range(7):
            d = week_start + timedelta(days=di)
            cell_appts = [a for a in appts_today + appts_upcoming
                         if a.start_time.hour == hour and a.start_time.date() == d]
            if cell_appts:
                for a in cell_appts:
                    bg = a.service.color or "#8B5CF6"
                    cal_html += f'<td style="padding:2px 4px;border-bottom:1px solid #F3F4F6;vertical-align:top"><div style="background:{bg};color:white;border-radius:6px;padding:4px 6px;font-size:11px;font-weight:600;margin:1px 0"><div style="font-size:10px;opacity:0.9">{a.start_time.strftime("%I:%M")}</div><div>{a.client.full_name}</div><div style="font-size:9px;opacity:0.8">{a.service.name}</div></div></td>'
            else:
                cal_html += '<td style="border-bottom:1px solid #F3F4F6"></td>'
        cal_html += '</tr>'
    
    cal_html += '</tbody></table></div>'
    cal_html += '<div style="text-align:center;padding:16px;color:#9CA3AF;font-size:12px">📱 Static view for offline demo — drag & drop not available</div>'
    
    html = html.replace('<div id="fullCalendar"></div>', cal_html)
    
    # Remove initCalendar call
    html = html.replace(
        "if (document.getElementById('calendar-page')) initCalendar();",
        "// Calendar: static view (offline prototype)"
    )
    
    # Remove FullCalendar init JS function
    import re
    html = re.sub(
        r'function initCalendar\(\)\s*\{[^}]+\}[^}]*\}',
        'function initCalendar() { /* static view */ }',
        html
    )
    
    with open(f"{OUTPUT_DIR}/calendar.html", "w") as f:
        f.write(html)
    print(f"  Rendering calendar.html (static view)...")
    print(f"    -> {OUTPUT_DIR}/calendar.html")

print("\n=== Generating offline prototype ===\n")

# Login (no user ctx needed)
render_and_save("login.html", "login.html", user=None)

# Dashboard
render_and_save("dashboard.html", "dashboard.html",
    user=active_user,
    today_revenue=today_revenue,
    today_appointments=today_appointments_count,
    active_clients=active_clients_count,
    upcoming=appts_upcoming[:5],
    appointments_by_status=appointments_by_status,
    weekly_revenue=weekly_revenue_data,
)

# Appointments
render_and_save("appointments.html", "appointments.html",
    user=active_user,
    appointments=appts_today + appts_upcoming,
    clients=clients,
    stylists=stylists,
    services=services,
)

# Calendar - overwrite with static calendar view
render_calendar_page()

# Payments
render_and_save("payments.html", "payments.html",
    user=active_user,
    transactions=transactions,
    clients=clients,
    services=services,
    stylists=stylists,
    gift_cards=gift_cards_count,
)

# Staff
render_and_save("staff.html", "staff.html",
    user=active_user,
    staff=staff,
)

# Book (public, no user)
appointments_json = [{
    "stylist_id": a.stylist.id,
    "start_time": a.start_time.isoformat(),
    "end_time": a.end_time.isoformat(),
    "service_id": a.service.id,
    "client_id": a.client.id,
    "status": a.status.value,
} for a in appts_today + appts_upcoming]

render_and_save("book.html", "book.html",
    services=services,
    stylists=stylists,
    appointments=appointments_json,
)

print("\n=== Done! ===")
print(f"\nFiles created in '{OUTPUT_DIR}/':")
for f in sorted(os.listdir(OUTPUT_DIR)):
    size = os.path.getsize(f"{OUTPUT_DIR}/{f}")
    print(f"  {f} ({size/1024:.1f} KB)")

print(f"\n📱 Transfer '{OUTPUT_DIR}/' folder to your phone")
print("   and open files in browser (no internet needed!)")
