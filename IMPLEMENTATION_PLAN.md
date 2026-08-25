# 🛍️ Multi-Niche Price Comparison Platform Implementation Plan

Comprehensive architecture, database design, ZenRows scraping pipeline, product matching engine, and 3-offer validation strategy powering 3 specialized niche comparison platforms:

1. 🇦🇺 **`nxtsmarthome.com.au`**: Australian Smart Home Electronics *(Amazon AU, JB Hi-Fi, Harvey Norman, The Good Guys, eBay AU, Bunnings)*
2. 🌐 **`nxtsmart.homes`**: International Smart Home Electronics *(US, UK, CA, EU: Amazon, Best Buy, Walmart, Target, Currys, MediaMarkt)*
3. ✨ **`www.bestlooking.skin`**: International Beauty & Skincare *(US, UK, CA, EU, AU, NZ: Sephora, Ulta, Boots, Mecca, Adore Beauty, Lookfantastic, Chemist Warehouse)*

---

## 🎯 Executive Summary & Objectives

The system architecture supports multi-tenant niche platforms sharing a unified backend infrastructure:

- **Site 1: `nxtsmarthome.com.au` (AU Smart Home)**
  - Scope: `niche = 'smart_home'`, `region = 'AU'`, currency `AUD`.
  - Target Retailers: Amazon AU, JB Hi-Fi, Harvey Norman, The Good Guys, eBay AU, Bunnings.

- **Site 2: `nxtsmart.homes` (International Smart Home)**
  - Scope: `niche = 'smart_home'`, `region IN ('US', 'UK', 'CA', 'EU')`, currencies `USD`, `GBP`, `CAD`, `EUR`.
  - Target Retailers: Amazon US/UK/CA/DE, Best Buy US/CA, Walmart, Target, Currys UK, MediaMarkt DE.

- **Site 3: `www.bestlooking.skin` (International Beauty & Skincare)**
  - Scope: `niche = 'beauty_skincare'`, `region IN ('US', 'UK', 'CA', 'EU', 'AU', 'NZ')`, currencies `USD`, `GBP`, `CAD`, `EUR`, `AUD`, `NZD`.
  - Target Retailers: Sephora (US/CA/UK/EU/AU), Ulta Beauty (US), Boots (UK), Mecca (AU/NZ), Adore Beauty (AU), Chemist Warehouse (AU/NZ), Dermstore, Lookfantastic, Cult Beauty, Amazon.

- **Core Rule - Minimum 3 Offers**:
  No canonical product will be displayed on any of the 3 sites unless it has **at least 3 active retailer offers** within that site's target region and niche.

---

## 📐 System Architecture Diagram

```
                                    +-----------------------+
                                    |     ZenRows API       |
                                    | (Anti-Bot, JS, Proxy) |
                                    +-----------+-----------+
                                                |
        +---------------------------------------+---------------------------------------+
        |                                       |                                       |
        v                                       v                                       v
+-----------------------+               +-----------------------+               +-----------------------+
|  AU Smart Home Pipeline|               | Intl Smart Home Pipeline|               |  Beauty & Skincare Pipeline|
|  Retailers:           |               |  Regions: US, UK, CA, EU|               |  Regions: US/UK/CA/EU/AU/NZ|
|  - Amazon AU          |               |  Retailers:           |               |  Retailers:           |
|  - JB Hi-Fi           |               |  - Amazon (US/UK/CA/DE|               |  - Sephora, Ulta      |
|  - Harvey Norman      |               |  - Best Buy, Walmart  |               |  - Boots UK, Mecca AU |
|  - The Good Guys      |               |  - Target, Currys     |               |  - Adore Beauty       |
+-----------+-----------+               +-----------+-----------+               +-----------+-----------+
            |                                       |                                       |
            +---------------------------------------+---------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
|                              Smart Matcher & Multi-Offer Engine                                   |
|  - Classifies into Smart Home Taxonomy or Beauty & Skincare Taxonomy                              |
|  - Normalizes Brand, Volume/Size, Shade, GTIN/UPC/EAN                                             |
|  - Enforces Rule: Active Retailer Offers Count >= 3 per Region & Niche                            |
+---------------------------------------------------+-----------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
|                                       Supabase DB                                                 |
|  - canonical_products (Master Smart Home & Beauty Catalog with niche tags)                        |
|  - marketplace_products (Scraped retailer listings with region & currency tags)                   |
|  - price_history (Automated price change snapshots via PostgreSQL trigger)                        |
|  - v_au_smart_home_comparisons (View for nxtsmarthome.com.au: AU Smart Home & >= 3 offers)         |
|  - v_intl_smart_home_comparisons (View for nxtsmart.homes: Intl Smart Home & >= 3 offers)         |
|  - v_beauty_skincare_comparisons (View for www.bestlooking.skin: Beauty & >= 3 offers)             |
+---------------------------------------------------------------------------------------------------+
```

---

## 💄 Beauty & Skincare Category Taxonomy & Brands

### 1. Categories
- 🧴 **Cleansers & Toners**: Gel Cleansers, Cleansing Oils, Micellar Waters, Exfoliating Toners, Essences.
- 💧 **Serums & Treatments**: Vitamin C, Retinol / Bakuchiol, Hyaluronic Acid, Niacinamide, AHA/BHA Acids, Eye Serums.
- 🧴 **Moisturizers & Creams**: Night Creams, Gel Moisturizers, Barrier Repair Creams, Face Oils.
- ☀️ **Sunscreen & Sun Care**: Mineral Sunscreens, Chemical Sunscreens, Tinted SPFs.
- 🎭 **Face Masks & Peels**: Clay Masks, Sheet Masks, Overnight Masks, Chemical Peels.
- 👁️ **Eye & Lip Care**: Eye Creams, Dark Circle Treatments, Lip Sleeping Masks, Lip Balms.
- 💆 **Hair & Body Care**: Scalp Treatments, Hair Oils, Body Scrubs, Body Lotions.

### 2. Top Brands
The Ordinary, CeraVe, La Roche-Posay, Paula's Choice, Glow Recipe, SkinCeuticals, Drunk Elephant, Estée Lauder, Clinique, Laneige, COSRX, Supergoop!, Sunday Riley, Kiehl's, Tatcha, Youth to the People, Sol de Janeiro, Fenty Skin, Dyson Beauty, NARS, Charlotte Tilbury, Urban Decay, MAC, Olaplex, Dermalogica, Biossance, Murad.

---

## 🗄️ Database Schema & SQL Views

### 1. Canonical Products Table (`canonical_products`)
- `id` (UUID Primary Key)
- `niche` (`'smart_home'`, `'beauty_skincare'`)
- `title` (Master product name)
- `brand` (e.g. *The Ordinary, CeraVe, La Roche-Posay, SkinCeuticals, Ring, Nest*)
- `variant` (e.g. *30ml, 50ml, 100ml, Shade / Option*)
- `gtin_upc_ean` (Universal product identifier)
- `category` (Niche taxonomy)

### 2. SQL View for `www.bestlooking.skin` (`v_beauty_skincare_comparisons`)
```sql
CREATE OR REPLACE VIEW public.v_beauty_skincare_comparisons AS
SELECT 
    cp.id AS canonical_product_id,
    cp.title AS canonical_title,
    cp.brand,
    cp.variant,
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
            'currency', mp.currency,
            'product_url', mp.product_url,
            'image_url', mp.image_url,
            'rating', mp.rating,
            'is_available', mp.is_available
        ) ORDER BY mp.current_price ASC
    ) AS offers
FROM public.canonical_products cp
JOIN public.marketplace_products mp ON cp.id = mp.canonical_product_id
WHERE cp.niche = 'beauty_skincare' 
  AND mp.region IN ('US', 'UK', 'CA', 'EU', 'AU', 'NZ') 
  AND mp.is_available = true 
  AND mp.current_price IS NOT NULL
GROUP BY cp.id, cp.title, cp.brand, cp.variant, cp.category, cp.image_url
HAVING COUNT(mp.id) >= 3;
```

---

## 🛡️ ZenRows Regional Presets for Beauty & Skincare Stores

| Retailer / Store | Region | `proxy_country` | `js_render` | `antibot` | Target Site |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Sephora US** | US | `us` | `true` | `true` | `www.bestlooking.skin` |
| **Ulta Beauty** | US | `us` | `true` | `true` | `www.bestlooking.skin` |
| **Dermstore** | US | `us` | `true` | `true` | `www.bestlooking.skin` |
| **Boots UK** | UK | `gb` | `true` | `true` | `www.bestlooking.skin` |
| **Lookfantastic UK** | UK | `gb` | `true` | `true` | `www.bestlooking.skin` |
| **Cult Beauty UK** | UK | `gb` | `true` | `true` | `www.bestlooking.skin` |
| **Sephora CA** | CA | `ca` | `true` | `true` | `www.bestlooking.skin` |
| **Shoppers Drug Mart** | CA | `ca` | `true` | `true` | `www.bestlooking.skin` |
| **Mecca AU** | AU | `au` | `true` | `true` | `www.bestlooking.skin` |
| **Adore Beauty AU** | AU | `au` | `true` | `true` | `www.bestlooking.skin` |
| **Chemist Warehouse** | AU/NZ | `au` | `true` | `true` | `www.bestlooking.skin` |
| **Sephora EU** | FR/DE | `fr` | `true` | `true` | `www.bestlooking.skin` |

---

## 🚀 Execution CLI Commands

### 1. View Comparisons for `www.bestlooking.skin` (Min 3 Offers)
```bash
python main.py --site beauty --compare
```

### 2. Discover & Index Skincare Products
```bash
python main.py --site beauty --skincare
```

### 3. Smart Home Platforms
```bash
# Australian Smart Home site (nxtsmarthome.com.au)
python main.py --site au --compare

# International Smart Home site (nxtsmart.homes)
python main.py --site intl --compare
```
