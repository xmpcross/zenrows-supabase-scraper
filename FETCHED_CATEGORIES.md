# 📊 Fetched Categories & Scraped Products Log

This document tracks all e-commerce categories, product counts, marketplaces, and sample listings currently stored in your **Supabase Database**.

---

## 📈 Executive Summary

- **Total Tracked Products in DB**: `136 listings`
- **Total Unique Categories**: `12 categories`
- **Supported Marketplaces Ingested**: `Amazon`, `eBay`, `Best Buy`, `Walmart`, `Target`, `Newegg`, `AliExpress`

---

## 🗂️ Fetched Categories Breakdown

| Category Name | Total Items | Marketplaces Scraped | Status / Last Fetched |
| :--- | :---: | :--- | :--- |
| **Computers & Hardware** | 43 | Amazon, Best Buy, eBay | ✅ Scraped |
| **Daily Deals & Deal of the Day** | 37 | eBay, Best Buy | ✅ Scraped |
| **Electronics > Audio & Headphones** | 13 | Amazon, Best Buy, eBay, Target, Newegg, AliExpress | ✅ Scraped |
| **Electronics & TV/Video** | 12 | Walmart, Amazon | ✅ Scraped |
| **Home & Kitchen** | 11 | Amazon, Best Buy | ✅ Scraped |
| **Toys, Games & Collectibles** | 8 | Amazon, eBay | ✅ Scraped |
| **Apparel & Accessories** | 6 | Amazon, eBay | ✅ Scraped |
| **Gaming Laptops** | 3 | Amazon | ✅ Scraped |
| **Sports & Outdoors** | 2 | Amazon | ✅ Scraped |
| **Beauty & Personal Care** | 1 | Amazon | ✅ Scraped |

---

## 🔍 Detailed Category Logs & Sample Products

### 1. 💻 Computers & Hardware (43 Products)
- **Marketplaces**: eBay, Amazon, Best Buy
- **Sample Listings**:
  - *ASUS CX34 14" FHD Chromebook Plus Laptop (Intel Core 5)* — Best Buy
  - *Lenovo IdeaPad Slim 3 15.6" Full HD Laptop (AMD Ryzen 5)* — Best Buy
  - *YEYIAN Spark Series 2000 Blue Switch Wired Gaming Keyboard* — Best Buy
  - *Acer Aspire Go 15 AI Ready Laptop 15.6"* — Amazon

### 2. ⚡ Daily Deals & Deal of the Day (37 Products)
- **Marketplaces**: eBay, Best Buy
- **Sample Listings**:
  - *Pursonic Portable Mini Massage Gun* — Best Buy
  - *Sony WH-1000XM5 Wireless Noise-Canceling Headphones* — eBay Deals
  - *Apple AirPods Pro (2nd Generation) MagSafe* — eBay Deals

### 3. 🎧 Electronics > Audio & Headphones (13 Products)
- **Marketplaces**: Amazon, Best Buy, eBay, Target, Newegg, AliExpress
- **Sample Listings**:
  - *Apple AirPods Pro (2nd Generation) Wireless Earbuds* — Amazon ($199.00)
  - *Apple AirPods Pro 2nd Gen with USB-C* — Walmart ($194.00)
  - *Sony WH-1000XM5 Wireless Headphones Black* — Newegg ($339.99)
  - *Original Silicone Case for AirPods Pro 2* — AliExpress ($4.99)

### 4. 📺 Electronics & TV/Video (12 Products)
- **Marketplaces**: Walmart, Amazon
- **Sample Listings**:
  - *Roku Express 4K+ Streaming Media Player* — Walmart
  - *Insignia 32-inch Class F20 Series Smart HD Fire TV* — Amazon

### 5. 🏠 Home & Kitchen (11 Products)
- **Marketplaces**: Amazon, Best Buy
- **Sample Listings**:
  - *Keurig K-Express Single Serve K-Cup Pod Coffee Maker* — Amazon
  - *Ninja Air Fryer Pro 4-in-1* — Best Buy

### 6. 🎮 Toys, Games & Collectibles (8 Products)
- **Marketplaces**: Amazon, eBay
- **Sample Listings**:
  - *LEGO Star Wars Mandalorian Helmet Set* — Amazon
  - *Pokemon TCG Booster Pack Bundle* — eBay

---

## 🛠️ How to Refresh Category Data

To run an automated price update and refresh all existing tracked products in Supabase:

```bash
# Refresh prices for all tracked categories
python main.py --price-check
```
