# 🛍️ ZenRows + Supabase Multi-Marketplace Product Scraper & Price Tracker

An automated product extraction, price tracking, and price comparison system built using **ZenRows API** (anti-bot bypass, JavaScript rendering, premium rotating proxies) and **Supabase** (PostgreSQL with automated SQL triggers).

Supports scraping top/trending products across **7 major e-commerce marketplaces**:
- 🛒 **Amazon**: Best Sellers & Today's Deals (Goldbox)
- 🏷️ **eBay**: Trending & popular listings
- 🏪 **Walmart**: Category rankings & best sellers
- 🟡 **Best Buy**: Top deals & tech rankings
- 🎯 **Target**: Best sellers & trending items
- 🥚 **Newegg**: Hardware & tech deals
- 📦 **AliExpress**: Hot-selling products & order counts

---

## 📐 System Architecture

```
                                    +-----------------------+
                                    |     ZenRows API       |
                                    | (Anti-Bot, JS, Proxy) |
                                    +-----------+-----------+
                                                |
                                                v
+---------------------------------------------------------------------------------------+
|                              Multi-Marketplace Scrapers                               |
|                                                                                       |
|  +-------------------+  +------------------+  +-------------------+                   |
|  |  Amazon Scraper   |  |   eBay Scraper   |  |  Walmart Scraper  |                   |
|  |  (Deals/Bestseller|  |   (Trending)     |  |  (Category Rank)  |                   |
|  +-------------------+  +------------------+  +-------------------+                   |
|  +-------------------+  +------------------+  +-------------------+  +----------------+ |
|  |  Best Buy Scraper |  |  Target Scraper  |  |  Newegg Scraper   |  | AliExpress Scp | |
|  |  (Top Deals)      |  |  (Best Sellers)  |  |  (Hardware Deals) |  | (Hot Selling)  | |
|  +-------------------+  +------------------+  +-------------------+  +----------------+ |
+---------------------------------------+-----------------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------------+
|                          Data Processing & Comparison Engine                          |
|  - Normalizes product titles, prices, stock, ratings & seller details                 |
|  - Extracts Coupons & Savings Badges ("Save $20", "Save 15%")                         |
|  - Parses Top Highlights, Technical Specifications & Item Details                     |
|  - Clusters identical items across marketplaces into comparison groups                 |
+---------------------------------------+-----------------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------------+
|                                    Supabase DB                                        |
|  - marketplace_products (Multi-Marketplace catalog & image links)                     |
|  - price_history (Automated price change snapshots via PostgreSQL trigger)            |
|  - product_comparison_groups (Cross-marketplace matching)                             |
|  - scrape_logs & categories                                                           |
+---------------------------------------------------------------------------------------+
```

---

## 📁 Project Structure

```
zenrows-supabase-scraper/
├── config.py                      # Environment configuration loader (.env parser)
├── main.py                        # CLI Orchestrator & Execution Runner
├── demo_seed.py                   # Offline test runner & sample HTML fixtures
├── schema.sql                     # Supabase database schema & automated SQL triggers
├── requirements.txt               # Project dependencies (zenrows, supabase, bs4, etc.)
├── .gitignore                     # Excludes secrets & virtual environments from git
├── .env.example                   # Template environment file
├── db/
│   └── supabase_client.py         # Supabase client manager & price history queries
├── scrapers/
│   ├── zenrows_client.py          # ZenRows API client with marketplace presets
│   └── marketplace_scrapers.py    # Parsers for Amazon, eBay, Walmart, Best Buy, Target, Newegg, & AliExpress
└── services/
    └── price_tracker.py           # Auto price update, price drop detector & comparison matrix
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
- `marketplace_products` (catalog for products, coupons, images, and descriptions)
- `price_history` (historic price change snapshots)
- `product_comparison_groups` & `comparison_group_items` (cross-marketplace price matching)
- **Automated SQL Trigger** (`trg_marketplace_products_price_change`): Appends a record to `price_history` whenever product prices update.

---

## 🚀 Usage & CLI Commands

### Run Offline Test Demo (No API Credits Required)
```bash
python main.py --demo
```

### Scrape Live Products from a Specific Marketplace
```bash
# Scrape Amazon Today's Deals (Goldbox)
python main.py --marketplace amazon --category "Today's Deals"

# Scrape Best Buy Top Deals
python main.py --marketplace bestbuy --category Electronics

# Scrape Target Best Sellers
python main.py --marketplace target --category Electronics

# Scrape Newegg Tech Deals
python main.py --marketplace newegg --category Computers

# Scrape Walmart Category Rankings
python main.py --marketplace walmart --category Electronics
```

### Scrape All 7 Marketplaces at Once
```bash
# Scrape all 7 marketplaces at once (Amazon, eBay, Walmart, Best Buy, Target, Newegg, AliExpress)
python main.py --marketplace all
```

### Run Automated Price History Refresh (Price Check)
```bash
# Re-check prices for existing tracked products and log price drops to price_history
python main.py --price-check
```

### Display Cross-Marketplace Price Comparison Matrix
```bash
# Print cross-marketplace price comparison table
python main.py --compare
```

---

## 🛡️ Marketplace Scraping Strategies in ZenRows

| Marketplace | `antibot` | `js_render` | `premium_proxy` | Description / Strategy |
| :--- | :---: | :---: | :---: | :--- |
| **Amazon** | `true` | `true` | `true` | Solves Amazon CAPTCHAs & parses Best Seller & Goldbox Deals grid faceouts |
| **Walmart** | `true` | `true` | `true` | Bypasses Akamai WAF and extracts `__NEXT_DATA__` JSON |
| **Best Buy** | `true` | `true` | `true` | Bypasses Akamai IP locks & extracts SKU product cards |
| **Target** | `true` | `true` | `true` | Solves Target RedSky / PerimeterX bot protections |
| **Newegg** | `true` | `true` | `true` | Bypasses Incapsula & parses item containers |
| **AliExpress** | `true` | `true` | `true` | Renders dynamic React SPAs & parses `_INITIAL_DATA_` |
| **eBay** | `true` | `false` | `false` | Fast DOM parsing of eBay search & category listings |

---

## 📊 Extracted Product Schema

Each scraped listing includes the following fields in Supabase:

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `marketplace` | `VARCHAR(50)` | Marketplace source (`amazon`, `ebay`, `walmart`, `bestbuy`, `target`, `newegg`, `aliexpress`) |
| `external_id` | `TEXT` | Listing ID (ASIN, Item ID, SKU, TCIN) |
| `title` | `TEXT` | Clean Product Name |
| `current_price` | `NUMERIC(12,2)` | Active selling price |
| `original_price` | `NUMERIC(12,2)` | Regular / List price before discount |
| `coupon_text` | `TEXT` | Coupon badge text (e.g. *"Save $20 with coupon"*, *"Save 15%"*) |
| `coupon_code` | `TEXT` | Savings promotional code |
| `short_description` | `TEXT` | Key feature bullet points / Top Highlights summary |
| `description` | `TEXT` | Detailed product specifications & overview |
| `rank_position` | `INTEGER` | Category ranking position (e.g. `#1`, `#2`) |
| `rating` | `NUMERIC(3,2)` | Customer review rating score (out of 5) |
| `review_count` | `INTEGER` | Total number of reviews |
| `image_url` | `TEXT` | High-res primary thumbnail link |
| `product_url` | `TEXT` | Direct listing URL |
| `metadata` | `JSONB` | Extracted top highlights & specifications dictionary |

---

## 🔒 Security Best Practices

- Real API keys belong **only** in `.env`.
- `.env` is listed in `.gitignore` to prevent accidental pushes to public repositories.
- Use `.env.example` as a template when cloning or deploying to new environments.
