You are absolutely right. In the affiliate world, missing, incomplete, or incorrect product identifiers (GTIN/UPC/EAN) are one of the biggest technical challenges. While electronics and smart home devices usually have reliable **MPNs (Manufacturer Part Numbers)**, beauty and skincare products frequently lack public barcodes on retailer sites, or merchants simply omit them from their product pages to prevent easy price comparison.  
To solve this, we cannot rely on GTINs alone. Instead, we should implement a **"Matching Waterfall" pipeline** in your ingestion layer.  
Here is how we make this possible, starting with changes to your database schema and ending with a programmatic matching strategy.

### 1\. Database Schema Updates (Adding Fallback Identifiers)

To support multiple ways of identifying a product, we need to make gtin nullable, add an asin field (highly valuable since Amazon is your primary retailer), and create indexes that support "fuzzy" search.  
You would modify your products table in Supabase like this:  
\-- Enable PostgreSQL Trigram Extension for fuzzy title/brand matching  
CREATE EXTENSION IF NOT EXISTS pg\_trgm;

ALTER TABLE products   
  ALTER COLUMN gtin DROP NOT NULL, \-- Make GTIN optional  
  ADD COLUMN mpn TEXT,             \-- Manufacturer Part Number  
  ADD COLUMN asin TEXT,            \-- Amazon Standard Identification Number  
  ADD COLUMN normalized\_title TEXT; \-- Lowercase, punctuation-stripped title

\-- Create indexes for fast lookup and similarity searches  
CREATE INDEX idx\_products\_gtin ON products(gtin) WHERE gtin IS NOT NULL;  
CREATE INDEX idx\_products\_asin ON products(asin) WHERE asin IS NOT NULL;  
CREATE INDEX idx\_products\_brand\_mpn ON products(brand, mpn) WHERE brand IS NOT NULL AND mpn IS NOT NULL;  
CREATE INDEX idx\_products\_trgm\_title ON products USING gin (normalized\_title gin\_trgm\_ops);

### 2\. The Programmatic "Matching Waterfall"

When your scrapper or DataForSEO finds a new offer from eBay, iHerb, or Walmart, your ingestion worker should run through this prioritized "waterfall" logic to find an existing product in your database before giving up and creating a new one:  
                  ┌──────────────────────────────┐  
                  │      Incoming Raw Offer      │  
                  └──────────────┬───────────────┘  
                                 │  
                     \[1. Has GTIN/UPC/EAN?\]  
                                 │  
                    ┌────────────┴────────────┐  
                 YES│                       NO│  
                    ▼                         ▼  
         Match in \`products.gtin\`    \[2. Has Amazon ASIN?\]  
         ┌──────────┴──────────┐              │  
         ▼                     ▼          ┌───┴───┐  
     \[Match found\]       \[No Match\]    YES│     NO│  
     Link offer          Check next       ▼       ▼  
                         tier         Match in \`products.asin\`  
                                      ┌───┴───┐  
                                      ▼       ▼  
                                  \[Match\]   \[3. Has Brand \+ MPN?\]  
                                  Link        │  
                                           ┌───┴───┐  
                                        YES│     NO│  
                                           ▼       ▼  
                                       Match in \`products.brand\_mpn\`  
                                       ┌───┴───┐  
                                       ▼       ▼  
                                   \[Match\]   \[4. Title Similarity Search\]  
                                   Link        │ (PostgreSQL Trigram \> 85%)  
                                               ▼  
                                            ┌──────────────────────┐  
                                            │  \[No Match Found\]    │  
                                            │  Insert new product  │  
                                            │  or send to Queue    │  
                                            └──────────────────────┘

#### Tier 1: Exact GTIN Match (Gold Standard)

If the scraped offer has a GTIN/UPC/EAN, search your database. If it exists, link the offer immediately.

#### Tier 2: Amazon ASIN Match

Since you are scraping Amazon and using it as a primary catalog source, ASINs are incredibly stable. If an offer contains an ASIN, query your database's asin column. If a match is found, link it.

#### Tier 3: Brand \+ MPN Match

Highly effective for **NXTSmartHome** and **nxtsmart.homes**. Electronics almost always have a Manufacturer Part Number (e.g., *Philips Hue smart bulb MPN: 929002226601*). Matching UPPER(brand) \+ UPPER(mpn) is practically as bulletproof as a GTIN.

#### Tier 4: Fuzzy Title \+ Brand Match (The AI/Algorithmic Fallback)

When scraping skincare on iHerb or eBay, identifiers are usually missing. You must compare text.

1. **Normalize the titles** on both sides: Convert to lowercase, remove punctuation, strip common volume metrics (e.g., "100ml", "3.4 oz"), and remove packaging words (e.g., "pack of 2", "with box").  
2. Run a **trigram similarity search** in Supabase to find products by the same brand with extremely similar titles:  
3. SELECT id, title, similarity(normalized\_title, 'normalized\_scraped\_title') AS score  
4. FROM products  
5. WHERE brand \= 'Brand Name'  
6. AND normalized\_title % 'normalized\_scraped\_title' \-- % means "meets similarity threshold"  
7. ORDER BY score DESC  
8. LIMIT 1;  
9. If the similarity score is high (e.g., **\> 85%**), link the offer to that product.

### 3\. Human-in-the-Loop "Merge Queue" (Admin Dashboard)

For matches that fall into a "gray area" (e.g., a similarity score between **65% and 85%**), you shouldn't auto-link them, as this can corrupt your pricing tables (e.g., matching a "50ml moisturizer" with a "100ml moisturizer").

* **How to build it**: Set up a simple review page in your Strapi admin panel or a custom Supabase-backed React table.  
* **How it works**: Any incoming offer that fails to match perfectly, but has a moderate fuzzy match, is saved to an unmatched\_queue table.  
* **The Action**: Once a week, you spend 10 minutes looking at this queue. The UI shows:  
* *Scraped Offer*: "CeraVe Moisturizing Cream 1.89 Liters" (eBay)  
* *Best DB Suggestion*: "CeraVe Moisturizing Cream 454g" (No Match) or "CeraVe Moisturizing Cream 1.89L" (Match\!)  
* You click **"Merge"** or **"Create New"**. When you click Merge, the database saves the relationship, and future scrapes will auto-match perfectly.

📝 I can update your centralized-affiliate-blueprint.md to version 2 (centralized-affiliate-blueprint-v2.md), incorporating these exact schema updates, the PostgreSQL trigram similarity queries, and the waterfall matching logic so you have it saved in your documentation. Let me know if you'd like to do that\!  
