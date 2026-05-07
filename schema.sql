-- ============================================================
-- GST Billing Software — Supabase (PostgreSQL) Schema
-- Run this in: Supabase Dashboard → SQL Editor
-- ============================================================

-- ── Settings (key-value store) ───────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ── Customers ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    phone      TEXT,
    gst_number TEXT,
    address    TEXT,
    state      TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_customers_gst ON customers(gst_number);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);

-- ── Products / Stock ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    sku         TEXT UNIQUE,
    quantity    NUMERIC DEFAULT 0,
    price       NUMERIC NOT NULL DEFAULT 0,
    gst_percent NUMERIC DEFAULT 18,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_sku  ON products(sku);

-- ── Invoice header ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoices (
    id               BIGSERIAL PRIMARY KEY,
    invoice_number   TEXT UNIQUE NOT NULL,   -- e.g. INV-2024-01001
    customer_name    TEXT,
    customer_gst     TEXT,
    customer_address TEXT,
    customer_state   TEXT,
    business_state   TEXT,
    is_interstate    BOOLEAN DEFAULT FALSE,
    invoice_date     DATE,
    subtotal         NUMERIC DEFAULT 0,
    cgst             NUMERIC DEFAULT 0,
    sgst             NUMERIC DEFAULT 0,
    igst             NUMERIC DEFAULT 0,
    total            NUMERIC DEFAULT 0,
    created_at       TIMESTAMPTZ DEFAULT now()
);

-- ── Invoice line items ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoice_items (
    id           BIGSERIAL PRIMARY KEY,
    invoice_id   BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_name TEXT,
    quantity     NUMERIC,
    price        NUMERIC,
    gst_percent  NUMERIC,
    cgst_amount  NUMERIC DEFAULT 0,
    sgst_amount  NUMERIC DEFAULT 0,
    igst_amount  NUMERIC DEFAULT 0,
    line_total   NUMERIC DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);

-- ── Row-Level Security (RLS) ──────────────────────────────────
-- Enable RLS and allow authenticated users full access.
-- Adjust policies as needed for your auth setup.

ALTER TABLE settings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers     ENABLE ROW LEVEL SECURITY;
ALTER TABLE products      ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices      ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;

-- Simple policy: allow all operations for authenticated users
-- (Replace with your own auth logic if needed)
CREATE POLICY "allow_all_authenticated" ON settings
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "allow_all_authenticated" ON customers
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "allow_all_authenticated" ON products
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "allow_all_authenticated" ON invoices
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "allow_all_authenticated" ON invoice_items
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── If you're using the anon key (no auth), use this instead ─
-- DROP POLICY IF EXISTS "allow_all_authenticated" ON settings;
-- CREATE POLICY "allow_anon" ON settings FOR ALL TO anon USING (true) WITH CHECK (true);
-- (repeat for each table)
