# 🏡 Smart Home Price Comparison Implementation Plan

Architecture, database design, ZenRows scraping pipeline, product matching engine, and 3-offer validation strategy for **`nxtsmarthome.com.au`** (Australia) and **`nxtsmart.homes`** (International).

---

## 🎯 Executive Summary & Objectives

The goal of this system is to power two distinct, high-converting smart home price comparison platforms sharing a unified backend architecture:

1. **`nxtsmarthome.com.au` (Australia Platform)**:
   - Targets Australian consumers with localized currency (`AUD`).
   - Fetches products exclusively from major Australian retailers: **Amazon AU**, **JB Hi-Fi**, **Harvey Norman**, **The Good Guys**, **eBay AU**, and **Bunnings**.

2. **`nxtsmart.homes` (International Platform)**:
   - Targets North American and European consumers (`USD`, `GBP`, `CAD`, `EUR`).
   - Fetches products from international electronics giants: **Amazon (US, UK, CA, DE)**, **Best Buy (US, CA)**, **Walmart**, **Target**, **Currys UK**, and **MediaMarkt DE**.

3. **Core Business Rule: Minimum 3 Offers Requirement**:
   - To deliver genuine price comparison value and maximize trust, **no product will be displayed on either site unless it has at least 3 active retailer offers** in its respective target region.

---

## 📐 System Architecture Diagram

```
                                    +-----------------------+
                                    |     ZenRows API       |
                                    | (Anti-Bot, JS, Proxy) |
                                    +-----------+-----------+
                                                |
                 +------------------------------+------------------------------+
                 |                                                             |
                 v                                                             v
+---------------------------------+                           +----------------------------------+
|      AU Scraping Pipeline       |                           |      International Pipeline      |
|  Retailers:                     |                           |  Regions: US, UK, CA, EU         |
|  - Amazon AU (amazon.com.au)    |                           |  Retailers:                      |
|  - JB Hi-Fi (jbhifi.com.au)     |                           |  - Amazon (US, UK, CA, DE)       |
|  - Harvey Norman                |                           |  - Best Buy (US, CA)             |
|  - The Good Guys                |                           |  - Walmart & Target (US)         |
|  - eBay AU & Bunnings           |                           |  - Currys (UK) & MediaMarkt (DE) |
+----------------+----------------+                           +----------------+-----------------+
                 |                                                             |
                 +------------------------------+------------------------------+
                                                |
                                                v
+------------------------------------------------------------------------------------------------+
|                             Smart Home Matcher & Offer Engine                                  |
|  - Categorizes into Smart Home Taxonomy (Security, Lighting, Hubs, Climate, Vacuums, etc.)    |
|  - Normalizes Brand, Model, GTIN/UPC/EAN                                                       |
|  - Enforces Rule: Active Offers Count >= 3 per Region                                           |
+-----------------------------------------------+------------------------------------------------+
                                                |
                                                v
+------------------------------------------------------------------------------------------------+
|                                    Supabase DB                                                 |
|  - canonical_products (Master Smart Home Catalog)                                              |
|  - marketplace_products (Retailer listings with region tags)                                   |
|  - price_history (Automated price change snapshots via PostgreSQL trigger)                     |
|  - v_au_smart_home_comparisons (View for nxtsmarthome.com.au: AU region & >= 3 offers)         |
|  - v_intl_smart_home_comparisons (View for nxtsmart.homes: US/UK/CA/EU & >= 3 offers)          |
+------------------------------------------------------------------------------------------------+
```

---

## 🗄️ Database Schema & 3-Offer Validation Views

### 1. Canonical Products Table (`canonical_products`)
Stores master record for each unique smart home product model (*Ring Video Doorbell 4, Philips Hue Bridge v2, Google Nest Hub 2nd Gen, Roborock S8 Pro Ultra*):
- `id` (UUID Primary Key)
- `title` (Master title)
- `brand` (e.g. *Ring, Nest, Philips Hue, Eufy, Arlo, Ecobee, Roborock*)
- `model` (e.g. *Gen 4, v2, Pro, Ultra, 4K*)
- `gtin_upc_ean` (Universal Product Code index)
- `category` (Smart Home taxonomy)

### 2. Retailer Offers Table (`marketplace_products`)
Stores individual scraped retailer listings:
- `region` (`'AU'`, `'US'`, `'UK'`, `'CA'`, `'EU'`)
- `marketplace` (`'amazon_au'`, `'jbhifi'`, `'harveynorman'`, `'thegoodguys'`, `'amazon_us'`, `'bestbuy'`, etc.)
- `canonical_product_id` (Foreign key to `canonical_products.id`)
- `current_price`, `currency`, `product_url`, `is_available`, `image_url`

### 3. Automated 3-Offer SQL Views

#### View for Australia (`v_au_smart_home_comparisons`)
```sql
CREATE OR REPLACE VIEW public.v_au_smart_home_comparisons AS
SELECT 
    cp.id AS canonical_product_id,
    cp.title AS canonical_title,
    cp.brand,
    cp.category,
    COUNT(mp.id) AS active_offers_count,
    MIN(mp.current_price) AS lowest_price_aud,
    MAX(mp.current_price) AS highest_price_aud,
    json_agg(
        json_build_object(
            'offer_id', mp.id,
            'marketplace', mp.marketplace,
            'retailer_name', UPPER(mp.marketplace),
            'price', mp.current_price,
            'currency', mp.currency,
            'product_url', mp.product_url,
            'is_available', mp.is_available
        ) ORDER BY mp.current_price ASC
    ) AS offers
FROM public.canonical_products cp
JOIN public.marketplace_products mp ON cp.id = mp.canonical_product_id
WHERE mp.region = 'AU' AND mp.is_available = true AND mp.current_price IS NOT NULL
GROUP BY cp.id, cp.title, cp.brand, cp.category
HAVING COUNT(mp.id) >= 3;
```

#### View for International (`v_intl_smart_home_comparisons`)
```sql
CREATE OR REPLACE VIEW public.v_intl_smart_home_comparisons AS
SELECT 
    cp.id AS canonical_product_id,
    cp.title AS canonical_title,
    cp.brand,
    cp.category,
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
            'currency', mp.currency,
            'product_url', mp.product_url,
            'is_available', mp.is_available
        ) ORDER BY mp.current_price ASC
    ) AS offers
FROM public.canonical_products cp
JOIN public.marketplace_products mp ON cp.id = mp.canonical_product_id
WHERE mp.region IN ('US', 'UK', 'CA', 'EU') AND mp.is_available = true AND mp.current_price IS NOT NULL
GROUP BY cp.id, cp.title, cp.brand, cp.category
HAVING COUNT(mp.id) >= 3;
```

---

## 🛡️ ZenRows Proxy & Scraping Configurations

| Store / Retailer | Region | `proxy_country` | `js_render` | `antibot` | Target Website |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Amazon AU** | AU | `au` | `true` | `true` | `nxtsmarthome.com.au` |
| **JB Hi-Fi** | AU | `au` | `true` | `true` | `nxtsmarthome.com.au` |
| **Harvey Norman** | AU | `au` | `true` | `true` | `nxtsmarthome.com.au` |
| **The Good Guys** | AU | `au` | `true` | `true` | `nxtsmarthome.com.au` |
| **eBay AU** | AU | `au` | `true` | `true` | `nxtsmarthome.com.au` |
| **Amazon US** | US | `us` | `true` | `true` | `nxtsmart.homes` |
| **Best Buy US** | US | `us` | `true` | `true` | `nxtsmart.homes` |
| **Walmart** | US | `us` | `true` | `true` | `nxtsmart.homes` |
| **Target** | US | `us` | `true` | `true` | `nxtsmart.homes` |
| **Currys UK** | UK | `gb` | `true` | `true` | `nxtsmart.homes` |
| **Amazon UK** | UK | `gb` | `true` | `true` | `nxtsmart.homes` |
| **MediaMarkt DE** | DE | `de` | `true` | `true` | `nxtsmart.homes` |

---

## 🚀 Execution CLI Commands

### 1. Scrape & Match Smart Home Products for Australia
```bash
python main.py --site au --smarthome
```

### 2. Scrape & Match Smart Home Products for International
```bash
python main.py --site intl --smarthome
```

### 3. Display Valid 3+ Offer Comparisons
```bash
# Query Australian comparisons (nxtsmarthome.com.au)
python main.py --site au --compare

# Query International comparisons (nxtsmart.homes)
python main.py --site intl --compare
```
