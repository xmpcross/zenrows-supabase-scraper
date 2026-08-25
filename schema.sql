-- ===================================================
-- ZenRows + Supabase Multi-Marketplace Scraper Schema
-- Smart Home Price Comparison System
-- Supports:
-- 1. nxtsmarthome.com.au (AU Region, AU Retailers)
-- 2. nxtsmart.homes (International: US, UK, CA, EU)
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

-- Seed Default Smart Home Categories
INSERT INTO public.categories (name, slug) VALUES
('Smart Security & Access', 'smart-security'),
('Smart Lighting & Ambiance', 'smart-lighting'),
('Smart Climate & Energy', 'smart-climate'),
('Smart Hubs & Controllers', 'smart-hubs'),
('Robot Vacuums & Appliances', 'robot-vacuums'),
('Smart Audio & Entertainment', 'smart-audio')
ON CONFLICT (slug) DO NOTHING;

-- 2. Canonical Smart Home Products (Master Product Records)
CREATE TABLE IF NOT EXISTS public.canonical_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    gtin_upc_ean TEXT UNIQUE,
    category TEXT NOT NULL DEFAULT 'Smart Home',
    image_url TEXT,
    description TEXT,
    specifications JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_canonical_brand ON public.canonical_products(brand);
CREATE INDEX IF NOT EXISTS idx_canonical_category ON public.canonical_products(category);

-- 3. Marketplace Products / Retailer Offers Table
CREATE TABLE IF NOT EXISTS public.marketplace_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_product_id UUID REFERENCES public.canonical_products(id) ON DELETE SET NULL,
    region VARCHAR(10) NOT NULL DEFAULT 'AU', -- 'AU', 'US', 'UK', 'CA', 'EU'
    marketplace VARCHAR(50) NOT NULL,        -- 'amazon_au', 'jbhifi', 'harveynorman', 'amazon_us', 'bestbuy', 'walmart', 'currys', etc.
    external_id TEXT,                        -- ASIN, SKU, Item ID
    title TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    current_price NUMERIC(12, 2),
    original_price NUMERIC(12, 2),
    discount_percent NUMERIC(5, 2),
    currency VARCHAR(10) DEFAULT 'AUD',      -- 'AUD', 'USD', 'GBP', 'CAD', 'EUR'
    rank_position INTEGER,
    rating NUMERIC(3, 2),
    review_count INTEGER DEFAULT 0,
    seller_name TEXT,
    coupon_text TEXT,
    coupon_code TEXT,
    short_description TEXT,
    description TEXT,
    is_available BOOLEAN DEFAULT true,
    product_url TEXT UNIQUE NOT NULL,
    image_url TEXT,
    images TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mkp_products_canonical ON public.marketplace_products(canonical_product_id);
CREATE INDEX IF NOT EXISTS idx_mkp_products_region ON public.marketplace_products(region);
CREATE INDEX IF NOT EXISTS idx_mkp_products_marketplace ON public.marketplace_products(marketplace);
CREATE INDEX IF NOT EXISTS idx_mkp_products_url ON public.marketplace_products(product_url);
CREATE INDEX IF NOT EXISTS idx_mkp_products_external_id ON public.marketplace_products(marketplace, external_id);
CREATE INDEX IF NOT EXISTS idx_mkp_products_category ON public.marketplace_products(category);

-- 4. Price History Snapshots Table
CREATE TABLE IF NOT EXISTS public.price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID NOT NULL REFERENCES public.marketplace_products(id) ON DELETE CASCADE,
    price NUMERIC(12, 2) NOT NULL,
    original_price NUMERIC(12, 2),
    currency VARCHAR(10) DEFAULT 'AUD',
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_listing ON public.price_history(listing_id);
CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON public.price_history(recorded_at DESC);

-- 5. Product Comparison Groups (Legacy Compatibility)
CREATE TABLE IF NOT EXISTS public.product_comparison_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    normalized_title TEXT,
    gtin_upc_ean TEXT,
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

-- 6. Scrape Run Logs Table
CREATE TABLE IF NOT EXISTS public.scrape_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_url TEXT NOT NULL,
    marketplace VARCHAR(50),
    target_type TEXT NOT NULL,
    status TEXT NOT NULL,
    items_count INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scrape_logs_status ON public.scrape_logs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_created_at ON public.scrape_logs(created_at DESC);

-- 7. Trigger Function: Log Price Changes to price_history
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

-- 8. Views for 3+ Offers Rule Enforcement

-- View for nxtsmarthome.com.au (Australian Site)
-- Returns canonical products that have AT LEAST 3 active Australian retailer offers
CREATE OR REPLACE VIEW public.v_au_smart_home_comparisons AS
SELECT 
    cp.id AS canonical_product_id,
    cp.title AS canonical_title,
    cp.brand,
    cp.model,
    cp.category,
    cp.image_url AS canonical_image,
    COUNT(mp.id) AS active_offers_count,
    MIN(mp.current_price) AS lowest_price_aud,
    MAX(mp.current_price) AS highest_price_aud,
    json_agg(
        json_build_object(
            'offer_id', mp.id,
            'marketplace', mp.marketplace,
            'retailer_name', UPPER(mp.marketplace),
            'price', mp.current_price,
            'original_price', mp.original_price,
            'currency', mp.currency,
            'coupon_text', mp.coupon_text,
            'product_url', mp.product_url,
            'image_url', mp.image_url,
            'rating', mp.rating,
            'is_available', mp.is_available
        ) ORDER BY mp.current_price ASC
    ) AS offers
FROM public.canonical_products cp
JOIN public.marketplace_products mp ON cp.id = mp.canonical_product_id
WHERE mp.region = 'AU' AND mp.is_available = true AND mp.current_price IS NOT NULL
GROUP BY cp.id, cp.title, cp.brand, cp.model, cp.category, cp.image_url
HAVING COUNT(mp.id) >= 3;

-- View for nxtsmart.homes (International Site)
-- Returns canonical products that have AT LEAST 3 active International retailer offers
CREATE OR REPLACE VIEW public.v_intl_smart_home_comparisons AS
SELECT 
    cp.id AS canonical_product_id,
    cp.title AS canonical_title,
    cp.brand,
    cp.model,
    cp.category,
    cp.image_url AS canonical_image,
    COUNT(mp.id) AS active_offers_count,
    MIN(mp.current_price) AS lowest_price,
    MAX(mp.current_price) AS highest_price,
    json_agg(
        json_build_object(
            'offer_id', mp.id,
            'region', mp.region,
            'marketplace', mp.marketplace,
            'retailer_name', UPPER(mp.marketplace),
            'price', mp.current_price,
            'original_price', mp.original_price,
            'currency', mp.currency,
            'coupon_text', mp.coupon_text,
            'product_url', mp.product_url,
            'image_url', mp.image_url,
            'rating', mp.rating,
            'is_available', mp.is_available
        ) ORDER BY mp.current_price ASC
    ) AS offers
FROM public.canonical_products cp
JOIN public.marketplace_products mp ON cp.id = mp.canonical_product_id
WHERE mp.region IN ('US', 'UK', 'CA', 'EU') AND mp.is_available = true AND mp.current_price IS NOT NULL
GROUP BY cp.id, cp.title, cp.brand, cp.model, cp.category, cp.image_url
HAVING COUNT(mp.id) >= 3;

-- Row Level Security (RLS) policies
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.canonical_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.marketplace_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_comparison_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comparison_group_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scrape_logs ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read categories" ON public.categories FOR SELECT USING (true);
CREATE POLICY "Allow public read canonical_products" ON public.canonical_products FOR SELECT USING (true);
CREATE POLICY "Allow public read marketplace_products" ON public.marketplace_products FOR SELECT USING (true);
CREATE POLICY "Allow public read price_history" ON public.price_history FOR SELECT USING (true);
CREATE POLICY "Allow public read comparison_groups" ON public.product_comparison_groups FOR SELECT USING (true);
CREATE POLICY "Allow public read comparison_items" ON public.comparison_group_items FOR SELECT USING (true);

-- Allow full write access for scraper service
CREATE POLICY "Allow write categories" ON public.categories FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write canonical_products" ON public.canonical_products FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write marketplace_products" ON public.marketplace_products FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write price_history" ON public.price_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write comparison_groups" ON public.product_comparison_groups FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write comparison_items" ON public.comparison_group_items FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow write scrape_logs" ON public.scrape_logs FOR ALL USING (true) WITH CHECK (true);

