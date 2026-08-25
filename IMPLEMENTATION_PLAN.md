# 🛍️ Multi-Niche Price Comparison Platform Implementation Plan

Comprehensive architecture, database design, ZenRows + DataForSEO scraping pipeline, product matching engine, and 3-offer validation strategy powering 3 specialized niche comparison platforms:

1. 🇦🇺 **`nxtsmarthome.com.au`**: Australian Smart Home Electronics *(Amazon AU, JB Hi-Fi, Harvey Norman, The Good Guys, eBay AU, Bunnings)*
2. 🌐 **`nxtsmart.homes`**: International Smart Home Electronics *(US, UK, CA, EU: Amazon, Best Buy, Walmart, Target, Currys, MediaMarkt)*
3. ✨ **`www.bestlooking.skin`**: International Beauty, Skincare & Anti-Aging Supplements *(US, UK, CA, EU, AU, NZ: Sephora, Ulta, iHerb, Amazon, eBay, Boots, Mecca, Adore Beauty, Lookfantastic, Chemist Warehouse)*

---

## 🎯 Executive Summary & Data Ingestion Hybrid Architecture

The system architecture supports multi-tenant niche platforms sharing a unified backend infrastructure powered by **Dual Data Providers**:

- **DataForSEO Merchant & Google Shopping API (Primary Aggregator)**:
  - Fast, pre-parsed JSON offer retrieval.
  - Automatically fetches 3 to 10 merchant offers per product in a single request (~$0.002/req).
  - Built-in geo-targeting for AU, US, UK, CA, EU, and NZ.

- **ZenRows Direct Web Scraper Engine (Direct Store Backup)**:
  - Direct HTML scraping with anti-bot bypass, JavaScript rendering, and residential proxies.
  - Used for deep specification parsing, live hidden promo code extraction, and direct store crawling.

- **Site 1: `nxtsmarthome.com.au` (AU Smart Home)**
  - Scope: `niche = 'smart_home'`, `region = 'AU'`, currency `AUD`.

- **Site 2: `nxtsmart.homes` (International Smart Home)**
  - Scope: `niche = 'smart_home'`, `region IN ('US', 'UK', 'CA', 'EU')`, currencies `USD`, `GBP`, `CAD`, `EUR`.

- **Site 3: `www.bestlooking.skin` (International Beauty, Skincare & Skin-Youth Supplements)**
  - Scope: `niche = 'beauty_skincare'`, `region IN ('US', 'UK', 'CA', 'EU', 'AU', 'NZ')`, currencies `USD`, `GBP`, `CAD`, `EUR`, `AUD`, `NZD`.

- **Core Business Rule - Minimum 3 Offers**:
  No canonical product will be displayed on any of the 3 sites unless it has **at least 3 active retailer offers** within that site's target region.

---

## 📐 System Architecture Diagram

```
                                    +-----------------------+           +-----------------------+
                                    |     DataForSEO API    |           |     ZenRows API       |
                                    | (Google Shopping SERP)|           | (Anti-Bot, JS, Proxy) |
                                    +-----------+-----------+           +-----------+-----------+
                                                |                                   |
        +---------------------------------------+-----------------------------------+
        |                                       |                                   |
        v                                       v                                   v
+-----------------------+               +-----------------------+           +-----------------------+
|  AU Smart Home Pipeline|               | Intl Smart Home Pipeline|           | Beauty & Youth Supplements|
|  Retailers:           |               |  Regions: US, UK, CA, EU|           |  Regions: US/UK/CA/EU/AU/NZ|
|  - Amazon AU, JB Hi-Fi|               |  Retailers:           |           |  Retailers:           |
|  - Harvey Norman      |               |  - Amazon, Best Buy   |           |  - iHerb, Amazon, eBay|
|  - The Good Guys      |               |  - Walmart, Target    |           |  - Sephora, Ulta      |
+-----------+-----------+               +-----------+-----------+           +-----------+-----------+
            |                                       |                                   |
            +---------------------------------------+-----------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
|                              Smart Matcher & Gemini 2.5 Flash Rewriter                            |
|  - Generates Unique SEO Titles, 3 Key Feature Bullets, and Engaging Summaries via Gemini API       |
|  - Normalizes Brand, Volume/Count, Dosage, Shade, GTIN/UPC/EAN                                    |
|  - Enforces Rule: Active Retailer Offers Count >= 3 per Region & Niche                            |
+---------------------------------------------------+-----------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
|                                       Supabase DB                                                 |
|  - canonical_products (Master Smart Home & Beauty/Supplement Catalog with niche tags)             |
|  - marketplace_products (Scraped retailer listings from DataForSEO / ZenRows)                    |
|  - price_history (Automated price change snapshots via PostgreSQL trigger)                        |
|  - v_au_smart_home_comparisons (View for nxtsmarthome.com.au: AU Smart Home & >= 3 offers)         |
|  - v_intl_smart_home_comparisons (View for nxtsmart.homes: Intl Smart Home & >= 3 offers)         |
|  - v_beauty_skincare_comparisons (View for www.bestlooking.skin: Beauty & Supplements >= 3 offers) |
+---------------------------------------------------------------------------------------------------+
```

---

## 🔑 Environment Configuration (`.env`)

```env
# DataForSEO Credentials (from https://dataforseo.com/register)
DATAFORSEO_LOGIN=your_dataforseo_login_email
DATAFORSEO_PASSWORD=your_dataforseo_api_password

# ZenRows API Key (from https://app.zenrows.com)
ZENROWS_API_KEY=your_zenrows_api_key_here

# Google Gemini API Key (from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_google_gemini_api_key_here

# Supabase Credentials (from Project Settings -> API)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_role_key_here
```

---

## 🚀 Execution CLI Commands

### 1. View Comparisons (Min 3 Offers)
```bash
python main.py --site au --compare
python main.py --site intl --compare
python main.py --site beauty --compare
```

### 2. Discover & Index via DataForSEO or ZenRows
```bash
# Ingest via DataForSEO (Google Shopping API)
python main.py --site au --smarthome --provider dataforseo

# Ingest via ZenRows (Direct Web Scraper)
python main.py --site au --smarthome --provider zenrows
```
