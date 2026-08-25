# 🛍️ Multi-Niche Price Comparison Platform Implementation Plan

Comprehensive architecture, database design, ZenRows scraping pipeline, product matching engine, and 3-offer validation strategy powering 3 specialized niche comparison platforms:

1. 🇦🇺 **`nxtsmarthome.com.au`**: Australian Smart Home Electronics *(Amazon AU, JB Hi-Fi, Harvey Norman, The Good Guys, eBay AU, Bunnings)*
2. 🌐 **`nxtsmart.homes`**: International Smart Home Electronics *(US, UK, CA, EU: Amazon, Best Buy, Walmart, Target, Currys, MediaMarkt)*
3. ✨ **`www.bestlooking.skin`**: International Beauty, Skincare & Anti-Aging Supplements *(US, UK, CA, EU, AU, NZ: Sephora, Ulta, iHerb, Amazon, eBay, Boots, Mecca, Adore Beauty, Lookfantastic, Chemist Warehouse)*

---

## 🎯 Executive Summary & Objectives

The system architecture supports multi-tenant niche platforms sharing a unified backend infrastructure:

- **Site 1: `nxtsmarthome.com.au` (AU Smart Home)**
  - Scope: `niche = 'smart_home'`, `region = 'AU'`, currency `AUD`.
  - Target Retailers: Amazon AU, JB Hi-Fi, Harvey Norman, The Good Guys, eBay AU, Bunnings.

- **Site 2: `nxtsmart.homes` (International Smart Home)**
  - Scope: `niche = 'smart_home'`, `region IN ('US', 'UK', 'CA', 'EU')`, currencies `USD`, `GBP`, `CAD`, `EUR`.
  - Target Retailers: Amazon US/UK/CA/DE, Best Buy US/CA, Walmart, Target, Currys UK, MediaMarkt DE.

- **Site 3: `www.bestlooking.skin` (International Beauty, Skincare & Skin-Youth Supplements)**
  - Scope: `niche = 'beauty_skincare'`, `region IN ('US', 'UK', 'CA', 'EU', 'AU', 'NZ')`, currencies `USD`, `GBP`, `CAD`, `EUR`, `AUD`, `NZD`.
  - Target Retailers: **iHerb**, **Amazon**, **eBay**, Sephora (US/CA/UK/EU/AU), Ulta Beauty (US), Boots (UK), Mecca (AU/NZ), Adore Beauty (AU), Chemist Warehouse (AU/NZ), Dermstore, Lookfantastic, Cult Beauty.

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
|  AU Smart Home Pipeline|               | Intl Smart Home Pipeline|               | Beauty & Youth Supplements|
|  Retailers:           |               |  Regions: US, UK, CA, EU|               |  Regions: US/UK/CA/EU/AU/NZ|
|  - Amazon AU          |               |  Retailers:           |               |  Retailers:           |
|  - JB Hi-Fi           |               |  - Amazon (US/UK/CA/DE|               |  - iHerb, Amazon, eBay|
|  - Harvey Norman      |               |  - Best Buy, Walmart  |               |  - Sephora, Ulta      |
|  - The Good Guys      |               |  - Target, Currys     |               |  - Boots UK, Mecca AU |
+-----------+-----------+               +-----------+-----------+               +-----------+-----------+
            |                                       |                                       |
            +---------------------------------------+---------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
|                              Smart Matcher & Multi-Offer Engine                                   |
|  - Classifies into Smart Home Taxonomy or Beauty & Skincare & Youth Supplement Taxonomy           |
|  - Normalizes Brand, Volume/Count, Dosage, Shade, GTIN/UPC/EAN                                    |
|  - Enforces Rule: Active Retailer Offers Count >= 3 per Region & Niche                            |
+---------------------------------------------------+-----------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
|                                       Supabase DB                                                 |
|  - canonical_products (Master Smart Home & Beauty/Supplement Catalog with niche tags)             |
|  - marketplace_products (Scraped retailer listings from iHerb, Amazon, eBay, Sephora, etc.)       |
|  - price_history (Automated price change snapshots via PostgreSQL trigger)                        |
|  - v_au_smart_home_comparisons (View for nxtsmarthome.com.au: AU Smart Home & >= 3 offers)         |
|  - v_intl_smart_home_comparisons (View for nxtsmart.homes: Intl Smart Home & >= 3 offers)         |
|  - v_beauty_skincare_comparisons (View for www.bestlooking.skin: Beauty & Supplements >= 3 offers) |
+---------------------------------------------------------------------------------------------------+
```

---

## 💄 Beauty, Skincare & Youth-Promoting Supplements Taxonomy

### 1. Skincare Categories
- 🧴 **Cleansers & Toners**: Gel Cleansers, Cleansing Oils, Micellar Waters, Exfoliating Toners, Essences.
- 💧 **Serums & Treatments**: Vitamin C, Retinol / Bakuchiol, Hyaluronic Acid, Niacinamide, AHA/BHA Acids, Eye Serums.
- 🧴 **Moisturizers & Creams**: Night Creams, Gel Moisturizers, Barrier Repair Creams, Face Oils.
- ☀️ **Sunscreen & Sun Care**: Mineral Sunscreens, Chemical Sunscreens, Tinted SPFs.
- 🎭 **Face Masks & Peels**: Clay Masks, Sheet Masks, Overnight Masks, Chemical Peels.

### 2. Youth-Promoting Skin Vitamins & Supplements Categories 💊
- 🧬 **Collagen & Peptides**: Hydrolyzed Marine Collagen, Bovine Collagen Powder, Liquid Collagen Shots.
- 💧 **Skin Hydration & Hyaluronic Acid**: Hyaluronic Acid Capsules, Phytoceramides for Skin Barrier.
- 🛡️ **Cellular Anti-Aging & Longevity**: NMN (Nicotinamide Mononucleotide), Resveratrol, CoQ10, NAD+ Boosters.
- ✨ **Skin Brightening & Antioxidants**: Glutathione, Vitamin C & E Complex, Alpha Lipoic Acid.
- 💅 **Hair, Skin & Nails Vitamins**: High-Potency Biotin, Keratin, Zinc, Hair Growth Gummies.
- 🐟 **Omega-3 & Essential Fatty Acids**: Wild Alaskan Salmon Oil, Evening Primrose Oil, Sea Buckthorn.

### 3. Top Brands (Skincare & Supplements)
- **Skincare Brands**: The Ordinary, CeraVe, La Roche-Posay, Paula's Choice, Glow Recipe, SkinCeuticals, Drunk Elephant, Estée Lauder, Clinique, Laneige, COSRX, Supergoop!, Sunday Riley, Kiehl's, Tatcha, Youth to the People, Sol de Janeiro, Fenty Skin, Dyson Beauty, NARS, Charlotte Tilbury, Urban Decay, MAC, Olaplex, Dermalogica.
- **Supplement Brands**: Vital Proteins, iHerb Exclusives, Codeage, Sports Research, Solgar, Thorne, Garden of Life, NOW Foods, Reserveage Beauty, NeoCell, HUM Nutrition, OLLY, Life Extension, Nature's Bounty, Swisse, Blackmores.

---

## 🗄️ Database Schema & SQL Views

### SQL View for `www.bestlooking.skin` (`v_beauty_skincare_comparisons`)
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

## 🛡️ ZenRows Regional Presets for Sourcing List (Including iHerb, Amazon, eBay)

| Retailer / Sourcing Store | Region | `proxy_country` | `js_render` | `antibot` | Target Site |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **iHerb** | Global (US/EU/AU) | `us` | `true` | `true` | `www.bestlooking.skin` |
| **Amazon (US, UK, CA, DE, AU)** | Global | `us` / `au` / `gb` | `true` | `true` | `www.bestlooking.skin` |
| **eBay (US, UK, AU)** | Global | `us` / `au` / `gb` | `true` | `true` | `www.bestlooking.skin` |
| **Sephora (US, CA, UK, EU, AU)** | Global | `us` / `au` / `gb` | `true` | `true` | `www.bestlooking.skin` |
| **Ulta Beauty** | US | `us` | `true` | `true` | `www.bestlooking.skin` |
| **Dermstore** | US | `us` | `true` | `true` | `www.bestlooking.skin` |
| **Boots UK** | UK | `gb` | `true` | `true` | `www.bestlooking.skin` |
| **Mecca AU / NZ** | AU/NZ | `au` | `true` | `true` | `www.bestlooking.skin` |
| **Adore Beauty AU** | AU | `au` | `true` | `true` | `www.bestlooking.skin` |
| **Chemist Warehouse** | AU/NZ | `au` | `true` | `true` | `www.bestlooking.skin` |

---

## 🚀 Execution CLI Commands

### 1. View Comparisons for `www.bestlooking.skin` (Min 3 Offers)
```bash
python main.py --site beauty --compare
```

### 2. Discover & Index Skincare & Youth Supplements
```bash
python main.py --site beauty --skincare
```
