-- SalonOS: Complete Database Schema
-- PostgreSQL 15+

-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================
CREATE TYPE user_role AS ENUM ('owner', 'stylist', 'receptionist', 'admin');
CREATE TYPE appointment_status AS ENUM (
    'pending', 'confirmed', 'checked_in', 'in_progress',
    'completed', 'cancelled', 'no_show', 'rescheduled'
);
CREATE TYPE transaction_status AS ENUM ('pending', 'completed', 'refunded', 'partial_refund', 'failed');
CREATE TYPE transaction_type AS ENUM ('service', 'product', 'tip', 'deposit', 'refund', 'gift_card_sale', 'gift_card_redemption');
CREATE TYPE payment_method AS ENUM ('cash', 'card', 'digital_wallet', 'gift_card', 'mixed');
CREATE TYPE shift_status AS ENUM ('scheduled', 'clocked_in', 'on_break', 'clocked_out', 'absent');
CREATE TYPE inventory_action AS ENUM ('received', 'sold', 'transferred', 'adjusted', 'returned');

-- ============================================================
-- USERS (staff: owners, stylists, receptionists)
-- ============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    role            user_role NOT NULL DEFAULT 'stylist',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    avatar_url      VARCHAR(500),
    color           VARCHAR(7) DEFAULT '#6366F1',
    commission_rate DECIMAL(5,2) DEFAULT 40.00,
    hourly_rate     DECIMAL(10,2),
    pin_code        VARCHAR(6),
    bio             TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================
-- CLIENTS
-- ============================================================
CREATE TABLE clients (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255),
    phone           VARCHAR(20),
    birthday        DATE,
    gender          VARCHAR(20),
    notes           TEXT,
    preferences     JSONB DEFAULT '{}',
    allergies       TEXT[] DEFAULT '{}',
    is_vip          BOOLEAN DEFAULT FALSE,
    referral_source VARCHAR(100),
    referred_by     UUID REFERENCES clients(id),
    total_visits    INTEGER DEFAULT 0,
    total_spent     DECIMAL(12,2) DEFAULT 0.00,
    last_visit_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clients_phone ON clients(phone);
CREATE INDEX idx_clients_email ON clients(email);
CREATE INDEX idx_clients_last_visit ON clients(last_visit_at);

-- ============================================================
-- SERVICES (catalog of what the salon offers)
-- ============================================================
CREATE TABLE services (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    category        VARCHAR(100) NOT NULL,
    duration_min    INTEGER NOT NULL,
    price           DECIMAL(10,2) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    color           VARCHAR(7) DEFAULT '#8B5CF6',
    commissionable  BOOLEAN DEFAULT TRUE,
    requires_deposit BOOLEAN DEFAULT FALSE,
    deposit_amount  DECIMAL(10,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_services_category ON services(category);

-- ============================================================
-- APPOINTMENTS
-- ============================================================
CREATE TABLE appointments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id       UUID NOT NULL REFERENCES clients(id),
    stylist_id      UUID NOT NULL REFERENCES users(id),
    service_id      UUID NOT NULL REFERENCES services(id),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    status          appointment_status NOT NULL DEFAULT 'pending',
    notes           TEXT,
    is_walk_in      BOOLEAN DEFAULT FALSE,
    is_recurring    BOOLEAN DEFAULT FALSE,
    recurring_rule  VARCHAR(100),
    source          VARCHAR(50) DEFAULT 'online',
    confirmation_token VARCHAR(100),
    cancelled_at    TIMESTAMPTZ,
    cancel_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_appointments_stylist_date ON appointments(stylist_id, start_time);
CREATE INDEX idx_appointments_client ON appointments(client_id);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_appointments_date ON appointments(start_time);

-- ============================================================
-- VISIT NOTES (formulas, photos, observations for each visit)
-- ============================================================
CREATE TABLE visit_notes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id  UUID NOT NULL REFERENCES appointments(id),
    client_id       UUID NOT NULL REFERENCES clients(id),
    stylist_id      UUID NOT NULL REFERENCES users(id),
    service_id      UUID NOT NULL REFERENCES services(id),

    -- Color Formula
    formula_name    VARCHAR(200),
    brand           VARCHAR(100),
    color_code      VARCHAR(100),
    formula_details JSONB DEFAULT '{}',
    developer_vol   VARCHAR(10),
    processing_time INTEGER,
    hair_condition  TEXT,
    allergy_test    BOOLEAN DEFAULT FALSE,

    -- General
    observations    TEXT,
    products_used   JSONB DEFAULT '[]',
    follow_up_date  DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_visit_notes_client ON visit_notes(client_id);
CREATE INDEX idx_visit_notes_appointment ON visit_notes(appointment_id);

-- ============================================================
-- PHOTOS (before/after, formula references)
-- ============================================================
CREATE TABLE photos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id       UUID NOT NULL REFERENCES clients(id),
    appointment_id  UUID REFERENCES appointments(id),
    visit_note_id   UUID REFERENCES visit_notes(id),
    uploaded_by     UUID REFERENCES users(id),
    photo_url       VARCHAR(500) NOT NULL,
    thumbnail_url   VARCHAR(500),
    photo_type      VARCHAR(20) NOT NULL CHECK (photo_type IN ('before', 'after', 'formula', 'inspiration', 'other')),
    tags            TEXT[] DEFAULT '{}',
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_photos_client ON photos(client_id);

-- ============================================================
-- TRANSACTIONS (payments, tips, refunds)
-- ============================================================
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id  UUID REFERENCES appointments(id),
    client_id       UUID NOT NULL REFERENCES clients(id),
    processed_by    UUID NOT NULL REFERENCES users(id),
    transaction_type transaction_type NOT NULL,
    status          transaction_status NOT NULL DEFAULT 'completed',
    subtotal        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tax_amount      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tip_amount      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total           DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    payment_method  payment_method NOT NULL DEFAULT 'cash',
    card_last_four  VARCHAR(4),
    stripe_payment_id VARCHAR(255),
    notes           TEXT,
    refund_of_id    UUID REFERENCES transactions(id),
    refund_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_client ON transactions(client_id);
CREATE INDEX idx_transactions_appointment ON transactions(appointment_id);
CREATE INDEX idx_transactions_date ON transactions(created_at);

-- ============================================================
-- TRANSACTION LINE ITEMS
-- ============================================================
CREATE TABLE transaction_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id  UUID NOT NULL REFERENCES transactions(id),
    item_type       VARCHAR(50) NOT NULL,
    item_id         UUID,
    item_name       VARCHAR(200) NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1,
    unit_price      DECIMAL(10,2) NOT NULL,
    total_price     DECIMAL(10,2) NOT NULL,
    stylist_id      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TIP DISTRIBUTION
-- ============================================================
CREATE TABLE tip_distributions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id  UUID NOT NULL REFERENCES transactions(id),
    stylist_id      UUID NOT NULL REFERENCES users(id),
    amount          DECIMAL(10,2) NOT NULL,
    percentage      DECIMAL(5,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- GIFT CARDS
-- ============================================================
CREATE TABLE gift_cards (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(50) NOT NULL UNIQUE,
    client_id       UUID REFERENCES clients(id),
    original_balance DECIMAL(10,2) NOT NULL,
    current_balance DECIMAL(10,2) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    expires_at      DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gift_cards_code ON gift_cards(code);

-- ============================================================
-- INVENTORY
-- ============================================================
CREATE TABLE inventory_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    brand           VARCHAR(100),
    sku             VARCHAR(100) UNIQUE,
    category        VARCHAR(100),
    cost_price      DECIMAL(10,2) NOT NULL,
    retail_price    DECIMAL(10,2) NOT NULL,
    current_stock   INTEGER NOT NULL DEFAULT 0,
    reorder_point   INTEGER DEFAULT 5,
    reorder_quantity INTEGER DEFAULT 20,
    unit            VARCHAR(20) DEFAULT 'unit',
    is_active       BOOLEAN DEFAULT TRUE,
    barcode         VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inventory_sku ON inventory_items(sku);

-- ============================================================
-- INVENTORY TRANSACTIONS
-- ============================================================
CREATE TABLE inventory_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id         UUID NOT NULL REFERENCES inventory_items(id),
    quantity_change INTEGER NOT NULL,
    action          inventory_action NOT NULL,
    reference_id    UUID,
    reference_type  VARCHAR(50),
    notes           TEXT,
    performed_by    UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TIME CLOCK / SHIFTS
-- ============================================================
CREATE TABLE shifts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id),
    date            DATE NOT NULL,
    scheduled_start TIMESTAMPTZ,
    scheduled_end   TIMESTAMPTZ,
    clock_in_at     TIMESTAMPTZ,
    clock_out_at    TIMESTAMPTZ,
    break_start     TIMESTAMPTZ,
    break_end       TIMESTAMPTZ,
    status          shift_status NOT NULL DEFAULT 'scheduled',
    total_hours     DECIMAL(5,2),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_shifts_user_date ON shifts(user_id, date);

-- ============================================================
-- COMMISSIONS
-- ============================================================
CREATE TABLE commissions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stylist_id      UUID NOT NULL REFERENCES users(id),
    transaction_id  UUID NOT NULL REFERENCES transactions(id),
    appointment_id  UUID REFERENCES appointments(id),
    service_amount  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    retail_amount   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tip_amount      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    service_rate    DECIMAL(5,2) NOT NULL,
    retail_rate     DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    service_earned  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    retail_earned   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tip_earned      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    bonus_amount    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_earned    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    is_paid         BOOLEAN DEFAULT FALSE,
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- WAITLIST
-- ============================================================
CREATE TABLE waitlist (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id       UUID NOT NULL REFERENCES clients(id),
    service_id      UUID REFERENCES services(id),
    preferred_date DATE,
    preferred_time TIME,
    notified_at     TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'waiting',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- NOTIFICATIONS LOG
-- ============================================================
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_type  VARCHAR(20) NOT NULL CHECK (recipient_type IN ('client', 'staff')),
    recipient_id    UUID NOT NULL,
    channel         VARCHAR(20) NOT NULL CHECK (channel IN ('sms', 'email', 'push')),
    template        VARCHAR(100),
    subject         VARCHAR(200),
    body            TEXT,
    sent_at         TIMESTAMPTZ,
    read_at         TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'pending',
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- AUDIT LOG
-- ============================================================
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    entity_type     VARCHAR(100),
    entity_id       UUID,
    old_values      JSONB,
    new_values      JSONB,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);

-- ============================================================
-- TRIGGER: automatically update updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_services_updated_at BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_appointments_updated_at BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_inventory_updated_at BEFORE UPDATE ON inventory_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_shifts_updated_at BEFORE UPDATE ON shifts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- SEED DATA
-- ============================================================
INSERT INTO users (email, password_hash, first_name, last_name, role, color, commission_rate)
VALUES
    ('owner@salonos.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0', 'Sarah', 'Johnson', 'owner', '#8B5CF6', 0),
    ('stylist1@salonos.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0', 'Maya', 'Rodriguez', 'stylist', '#EC4899', 45.00),
    ('stylist2@salonos.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0', 'James', 'Chen', 'stylist', '#6366F1', 50.00),
    ('stylist3@salonos.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0', 'Lena', 'Park', 'stylist', '#F59E0B', 40.00),
    ('reception@salonos.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0Qm0', 'Alex', 'Rivera', 'receptionist', '#10B981', 0);

INSERT INTO services (name, description, category, duration_min, price, color)
VALUES
    ('Women''s Haircut', 'Wash, cut, blow-dry and style', 'cut', 60, 75.00, '#EC4899'),
    ('Men''s Haircut', 'Precision cut with clipper & scissor finish', 'cut', 30, 45.00, '#6366F1'),
    ('Full Balayage', 'Hand-painted highlights for a natural sun-kissed look', 'color', 150, 220.00, '#8B5CF6'),
    ('Partial Highlights', 'Foiling on top/crown section only', 'color', 90, 150.00, '#A78BFA'),
    ('Root Touch-Up', 'Single-process color application to roots', 'color', 60, 95.00, '#C084FC'),
    ('Keratin Treatment', 'Smoothing treatment for frizz-free straight hair', 'treatment', 120, 200.00, '#F59E0B'),
    ('Deep Conditioning', 'Intensive moisture treatment for damaged hair', 'treatment', 30, 45.00, '#34D399'),
    ('Blowout', 'Wash and blow-dry with round brush styling', 'styling', 30, 50.00, '#F472B6'),
    ('Bridal Updo', 'Consultation + trial + day-of styling', 'styling', 90, 175.00, '#FB7185'),
    ('Balayage + Cut', 'Full balayage with haircut and style', 'package', 180, 275.00, '#8B5CF6');

INSERT INTO clients (first_name, last_name, email, phone, birthday, notes, preferences, total_visits, total_spent, last_visit_at)
VALUES
    ('Emma', 'Thompson', 'emma@example.com', '+15551234567', '1992-03-15', 'Prefers quiet appointments, no small talk. Allergic to PPD.', '{"style": "beachy waves", "products": ["Olaplex"]}', 24, 4200.00, NOW() - INTERVAL '2 weeks'),
    ('Olivia', 'Martinez', 'olivia@example.com', '+15552345678', '1988-07-22', 'Always 10 min late. Has 2 kids. Loves trying new colors.', '{"style": "bold colors", "products": ["Redken"]}', 18, 3100.00, NOW() - INTERVAL '3 days'),
    ('Sophia', 'Williams', 'sophia@example.com', '+15553456789', '1995-11-08', 'Very detail-oriented. Brings inspiration photos.', '{"style": "blunt bob", "products": ["K18"]}', 12, 1800.00, NOW() - INTERVAL '5 weeks'),
    ('Isabella', 'Brown', 'isabella@example.com', '+15554567890', '1990-05-30', 'Getting married June 2025. Booking trial soon.', '{"style": "bridal", "products": ["Wella"]}', 8, 950.00, NOW() - INTERVAL '2 months'),
    ('Mia', 'Garcia', 'mia@example.com', '+15555678901', '2000-01-14', 'College student. Budget-conscious. Loves trendy cuts.', '{"style": "trendy", "products": ["Drugstore"]}', 6, 320.00, NOW() - INTERVAL '1 month');
