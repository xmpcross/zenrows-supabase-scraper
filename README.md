# 🏡 Smart Home Electronics Price Comparison System (ZenRows + Supabase)

An automated product extraction, price tracking, and price comparison system built using **ZenRows API** (anti-bot bypass, JavaScript rendering, regional rotating proxies) and **Supabase** (PostgreSQL with automated SQL triggers and views).

Powers two smart home price comparison platforms:
1. 🇦🇺 **`nxtsmarthome.com.au`**: Australian market (fetching strictly from Australian stores: Amazon AU, JB Hi-Fi, Harvey Norman, The Good Guys, eBay AU, Bunnings).
2. 🌐 **`nxtsmart.homes`**: International market (fetching from US, UK, Canada, and Europe: Amazon US/UK/CA/DE, Best Buy, Walmart, Target, Currys).
3. ✨ **`www.bestlooking.skin`**: International Beauty, Skincare & Youth-Promoting Supplements *(US, UK, CA, EU, AU, NZ: Sephora, Ulta, iHerb, Amazon, eBay, Boots, Mecca, Adore Beauty, Lookfantastic, Chemist Warehouse)*.

> [!IMPORTANT]
> **Core Business Rule - Minimum 3 Offers**:
> No canonical product will be displayed on any of the 3 sites unless it has **at least 3 valid retailer offers** within that site's target region. Enforced automatically at the database level via SQL views (`v_au_smart_home_comparisons`, `v_intl_smart_home_comparisons`, and `v_beauty_skincare_comparisons`).

---

## 📐 System Architecture

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

## 📁 Project Structure

```
zenrows-supabase-scraper/
├── config.py                      # Environment configuration loader (.env parser)
├── main.py                        # CLI Orchestrator & Execution Runner
├── demo_seed.py                   # Offline test runner & sample HTML fixtures
├── schema.sql                     # Supabase database schema, 3-offer views & SQL triggers
├── requirements.txt               # Project dependencies (zenrows, supabase, bs4, etc.)
├── .gitignore                     # Excludes secrets & virtual environments from git
├── .env.example                   # Template environment file
├── db/
│   └── supabase_client.py         # Supabase manager & 3-offer comparison query layer
├── scrapers/
│   ├── zenrows_client.py          # ZenRows API client with regional proxies (au, us, gb, ca, de)
│   └── marketplace_scrapers.py    # Parsers for AU (JB Hi-Fi, Harvey Norman, etc.) & Intl stores
└── services/
    ├── price_tracker.py           # Auto price update & price drop detector
    └── smart_home_matcher.py      # Brand/Model parser, canonical product matcher & 3-offer finder
```

---

## ⚡ Quick Start & Installation

### 1. Clone & Navigate to Project Directory
```bash
cd E:\1Kspellman\antigravity-ide\zenrows-supabase-scraper
```

### 2. Install Dependencies
```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```env
# ZenRows API Key (from https://app.zenrows.com)
ZENROWS_API_KEY=your_zenrows_api_key

# Supabase Credentials (from Project Settings -> API)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_service_role_or_anon_key

# Scraper Defaults
DEFAULT_JS_RENDER=false
DEFAULT_PREMIUM_PROXY=false
DEFAULT_ANTIBOT=true
```

### 4. Set Up Supabase Database Schema
Copy the contents of [`schema.sql`](schema.sql) into your **[Supabase SQL Editor](https://supabase.com/dashboard/project/your-project-id/sql)** and click **Run**. This creates:
- `canonical_products` (master catalog for Ring, Nest, Philips Hue, Eufy, Arlo, etc.)
- `marketplace_products` (retailer listings with `region` tags)
- `v_au_smart_home_comparisons` (SQL View for `nxtsmarthome.com.au` with $\ge 3$ AU offers)
- `v_intl_smart_home_comparisons` (SQL View for `nxtsmart.homes` with $\ge 3$ Intl offers)
- **Automated SQL Trigger** (`trg_marketplace_products_price_change`): Appends price history snapshots whenever product prices change.

---

## 🚀 Usage & CLI Commands

### 1. Run Offline Test Demo
```bash
python main.py --demo
```

### 2. Run Smart Home Scraper & Offer Matcher for Australia (`nxtsmarthome.com.au`)
```bash
python main.py --site au --smarthome
```

### 3. Run Smart Home Scraper & Offer Matcher for International (`nxtsmart.homes`)
```bash
python main.py --site intl --smarthome
```

### 4. Query Valid 3+ Offer Comparisons for Frontend Platforms
```bash
# View comparisons for Australian site (nxtsmarthome.com.au)
python main.py --site au --compare

# View comparisons for International site (nxtsmart.homes)
python main.py --site intl --compare
```

---

## 🛡️ Geo-Proxy Scraping Strategies in ZenRows

| Store / Retailer | Region | `proxy_country` | `js_render` | `antibot` | Target Site |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Amazon AU** | AU | `au` | `true` | `true` | nxtsmarthome.com.au |
| **JB Hi-Fi** | AU | `au` | `true` | `true` | nxtsmarthome.com.au |
| **Harvey Norman** | AU | `au` | `true` | `true` | nxtsmarthome.com.au |
| **The Good Guys** | AU | `au` | `true` | `true` | nxtsmarthome.com.au |
| **eBay AU** | AU | `au` | `true` | `true` | nxtsmarthome.com.au |
| **Amazon US** | US | `us` | `true` | `true` | nxtsmart.homes |
| **Best Buy US** | US | `us` | `true` | `true` | nxtsmart.homes |
| **Walmart** | US | `us` | `true` | `true` | nxtsmart.homes |
| **Target** | US | `us` | `true` | `true` | nxtsmart.homes |
| **Currys UK** | UK | `gb` | `true` | `true` | nxtsmart.homes |
| **Amazon UK** | UK | `gb` | `true` | `true` | nxtsmart.homes |
| **MediaMarkt DE** | DE | `de` | `true` | `true` | nxtsmart.homes |

---

## 🔒 Security Best Practices

- Real API keys belong **only** in `.env`.
- `.env` is listed in `.gitignore` to prevent accidental pushes to public repositories.
- Use `.env.example` as a template when deploying to production environments.

