-- ===================================================
-- ZenRows + Supabase Multi-Marketplace Scraper Schema
-- E-Commerce Best Sellers & Price Comparison Database
-- Run this script in your Supabase SQL Editor
-- ===================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Categories Table
CREATE TABLE IF NOT EXISTS public.categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    parent_id UUID REFERENCES public.categories(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Marketplace Products Table (Amazon, eBay, Walmart, Etsy, AliExpress)
CREATE TABLE IF NOT EXISTS public.marketplace_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    marketplace VARCHAR(50) NOT NULL, -- 'amazon', 'ebay', 'walmart', 'bestbuy', 'target', 'newegg', 'aliexpress'
    external_id TEXT,                 -- ASIN, Item ID, SKU
    title TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    current_price NUMERIC(12, 2),
    original_price NUMERIC(12, 2),
    discount_percent NUMERIC(5, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    rank_position INTEGER,             -- Category ranking (e.g. #1 Best Seller)
    rating NUMERIC(3, 2),
    review_count INTEGER DEFAULT 0,
    seller_name TEXT,
    coupon_text TEXT,                 -- e.g. "Save $20 with coupon", "Extra 10% off"
    coupon_code TEXT,                 -- e.g. "SAVE10", "SUMMER2026"
    short_description TEXT,           -- Key bullet points / summary
    description TEXT,                 -- Full detailed description
    is_available BOOLEAN DEFAULT true,
    product_url TEXT UNIQUE NOT NULL,
    image_url TEXT,
    images TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mkp_products_marketplace ON public.marketplace_products(marketplace);
CREATE INDEX IF NOT EXISTS idx_mkp_products_url ON public.marketplace_products(product_url);
CREATE INDEX IF NOT EXISTS idx_mkp_products_external_id ON public.marketplace_products(marketplace, external_id);
CREATE INDEX IF NOT EXISTS idx_mkp_products_category ON public.marketplace_products(category);
CREATE INDEX IF NOT EXISTS idx_mkp_products_rank ON public.marketplace_products(marketplace, category, rank_position);

-- 3. Price History Snapshots Table
CREATE TABLE IF NOT EXISTS public.price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID NOT NULL REFERENCES public.marketplace_products(id) ON DELETE CASCADE,
    price NUMERIC(12, 2) NOT NULL,
    original_price NUMERIC(12, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_listing ON public.price_history(listing_id);
CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON public.price_history(recorded_at DESC);

-- 4. Product Comparison Groups (Connecting same/similar products across marketplaces)
CREATE TABLE IF NOT EXISTS public.product_comparison_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,                -- e.g. "Sony WH-1000XM5 Wireless Headphones"
    normalized_title TEXT,             -- Search indexable cleaned title
    gtin_upc_ean TEXT,                 -- Standard product code for auto-matching
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.comparison_group_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID NOT NULL REFERENCES public.product_comparison_groups(id) ON DELETE CASCADE,
    listing_id UUID NOT NULL REFERENCES public.marketplace_products(id) ON DELETE CASCADE,
    matched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, listing_id)
);

-- 5. Scrape Run Logs Table
CREATE TABLE IF NOT EXISTS public.scrape_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_url TEXT NOT NULL,
    marketplace VARCHAR(50),
    target_type TEXT NOT NULL,        -- 'bestsellers', 'search', 'product_page'
    status TEXT NOT NULL,             -- 'success', 'failed', 'partial'
    items_count INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scrape_logs_status ON public.scrape_logs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_created_at ON public.scrape_logs(created_at DESC);

-- 6. Trigger Function: Automatically insert into price_history when price updates
CREATE OR REPLACE FUNCTION public.fn_log_price_history()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') OR (NEW.current_price IS DISTINCT FROM OLD.current_price) THEN
        IF NEW.current_price IS NOT NULL THEN
            INSERT INTO public.price_history (listing_id, price, original_price, currency, recorded_at)
            VALUES (NEW.id, NEW.current_price, NEW.original_price, NEW.currency, NOW());
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_marketplace_products_price_change ON public.marketplace_products;

CREATE TRIGGER trg_marketplace_products_price_change
AFTER INSERT OR UPDATE ON public.marketplace_products
FOR EACH ROW
EXECUTE FUNCTION public.fn_log_price_history();

-- Row Level Security (RLS) policies
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.marketplace_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_comparison_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comparison_group_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scrape_logs ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read categories" ON public.categories FOR SELECT USING (true);
CREATE POLICY "Allow public read marketplace_products" ON public.marketplace_products FOR SELECT USING (true);
CREATE POLICY "Allow public read price_history" ON public.price_history FOR SELECT USING (true);
CREATE POLICY "Allow public read comparison_groups" ON public.product_comparison_groups FOR SELECT USING (true);
CREATE POLICY "Allow public read comparison_items" ON public.comparison_group_items FOR SELECT USING (true);

-- Allow full write access for client applications (Service Role or Anon Ingestion)
CREATE POLICY "Allow write categories" ON public.categories FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write marketplace_products" ON public.marketplace_products FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write price_history" ON public.price_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write comparison_groups" ON public.product_comparison_groups FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write comparison_items" ON public.comparison_group_items FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write scrape_logs" ON public.scrape_logs FOR ALL USING (true) WITH CHECK (true);
