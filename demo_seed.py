"""
Demo / Seed Script for ZenRows Multi-Marketplace Product Scraper & Supabase Price Tracker.
Demonstrates scraping & price tracking on sample product fixtures for Amazon, eBay, Walmart, BestBuy, Target, Newegg, and AliExpress.
"""

import sys
import logging
from scrapers.marketplace_scrapers import parse_marketplace_page
from services.price_tracker import PriceTrackerEngine
from db.supabase_client import SupabaseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("demo_seed")

# 1. SAMPLE FIXTURE HTML CONTENT FOR 7 MARKETPLACES
MOCK_AMAZON_HTML = """
<html>
<body>
  <div class="zg-grid-general-faceout" data-asin="B0B9356M39">
    <span class="zg-bdg-text">#1</span>
    <a href="/dp/B0B9356M39?tag=test"><img alt="Apple AirPods Pro (2nd Generation) Wireless Earbuds" src="https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1500_.jpg"/></a>
    <div class="_cDE12_p13n-sc-css-line-clamp-1_1597W">Apple AirPods Pro (2nd Generation) Wireless Earbuds</div>
    <i class="a-icon-star"><span class="a-icon-alt">4.7 out of 5 stars</span></i>
    <span class="a-size-small">54,321 ratings</span>
    <span class="p13n-sc-price">$199.00</span>
  </div>
  <div class="zg-grid-general-faceout" data-asin="B0BDHWDR12">
    <span class="zg-bdg-text">#2</span>
    <a href="/dp/B0BDHWDR12"><img alt="Sony WH-1000XM5 Wireless Headphones" src="https://m.media-amazon.com/images/I/51SKmu2B5FL._AC_SL1200_.jpg"/></a>
    <div class="_cDE12_p13n-sc-css-line-clamp-1_1597W">Sony WH-1000XM5 Wireless Headphones</div>
    <i class="a-icon-star"><span class="a-icon-alt">4.6 out of 5 stars</span></i>
    <span class="a-size-small">12,450 ratings</span>
    <span class="p13n-sc-price">$348.00</span>
  </div>
</body>
</html>
"""

MOCK_EBAY_HTML = """
<html>
<body>
  <div class="srp-results">
    <div class="s-item">
      <a class="s-item__link" href="https://www.ebay.com/itm/123456789012">
        <h3 class="s-item__title">Apple AirPods Pro (2nd Generation) MagSafe Charging Case</h3>
      </a>
      <span class="s-item__price">$189.99</span>
      <span class="s-item__seller-info">TopRatedSeller99</span>
      <div class="s-item__image-img"><img src="https://i.ebayimg.com/thumbs/images/g/test/s-l300.jpg"/></div>
    </div>
    <div class="s-item">
      <a class="s-item__link" href="https://www.ebay.com/itm/987654321098">
        <h3 class="s-item__title">Sony WH-1000XM5 Noise Canceling Headphones Black</h3>
      </a>
      <span class="s-item__price">$329.50</span>
      <span class="s-item__seller-info">AudioTechPro</span>
      <div class="s-item__image-img"><img src="https://i.ebayimg.com/thumbs/images/g/sony/s-l300.jpg"/></div>
    </div>
  </div>
</body>
</html>
"""

MOCK_WALMART_HTML = """
<html>
<body>
  <script id="__NEXT_DATA__" type="application/json">
  {
    "props": {
      "pageProps": {
        "initialData": {
          "searchResult": {
            "itemStacks": [
              {
                "items": [
                  {
                    "usItemId": "554433221",
                    "title": "Apple AirPods Pro 2nd Gen with USB-C",
                    "brand": "Apple",
                    "priceInfo": { "currentPrice": { "price": 194.00 } },
                    "canonicalUrl": "/ip/Apple-AirPods-Pro-2nd-Gen/554433221",
                    "imageInfo": { "thumbnailUrl": "https://i5.walmartimages.com/asr/airpods.jpg" },
                    "rating": { "averageRating": 4.8, "numberOfReviews": 8900 }
                  },
                  {
                    "usItemId": "998877665",
                    "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
                    "brand": "Sony",
                    "priceInfo": { "currentPrice": { "price": 349.99 } },
                    "canonicalUrl": "/ip/Sony-WH-1000XM5/998877665",
                    "imageInfo": { "thumbnailUrl": "https://i5.walmartimages.com/asr/sony.jpg" },
                    "rating": { "averageRating": 4.7, "numberOfReviews": 3400 }
                  }
                ]
              }
            ]
          }
        }
      }
    }
  }
  </script>
</body>
</html>
"""

MOCK_BESTBUY_HTML = """
<html>
<body>
  <li class="sku-item" data-sku-id="6501045">
    <div class="sku-title"><a href="/site/apple-airpods-pro-2nd-generation-with-magsafe-case/6501045.p">Apple - AirPods Pro (2nd generation) with MagSafe Case (USB-C) - White</a></div>
    <div class="priceView-customer-price"><span>$199.99</span></div>
    <p class="c-review-average">4.8</p>
    <span class="c-total-reviews">(14,500)</span>
    <img class="sku-image" src="https://pisces.bbystatic.com/image2/BestBuy_US/images/products/6501/6501045_sd.jpg"/>
  </li>
  <li class="sku-item" data-sku-id="6505727">
    <div class="sku-title"><a href="/site/sony-wh-1000xm5-wireless-noise-canceling-over-the-ear-headphones-black/6505727.p">Sony - WH-1000XM5 Wireless Noise-Canceling Over-the-Ear Headphones - Black</a></div>
    <div class="priceView-customer-price"><span>$349.99</span></div>
    <p class="c-review-average">4.7</p>
    <span class="c-total-reviews">(4,200)</span>
    <img class="sku-image" src="https://pisces.bbystatic.com/image2/BestBuy_US/images/products/6505/6505727_sd.jpg"/>
  </li>
</body>
</html>
"""

MOCK_TARGET_HTML = """
<html>
<body>
  <div data-test="product-card">
    <a data-test="product-title" href="/p/apple-airpods-pro-2nd-generation/-/A-86718520">Apple AirPods Pro (2nd generation) with MagSafe Case (USB-C)</a>
    <span data-test="current-price">$199.99</span>
    <span data-test="rating-count">4.8</span>
    <picture><img src="https://target.scene7.com/is/image/Target/GUEST_airpods"/></picture>
  </div>
</body>
</html>
"""

MOCK_NEWEGG_HTML = """
<html>
<body>
  <div class="item-container">
    <a class="item-title" href="https://www.newegg.com/p/N82E16875113001">Sony WH-1000XM5 Wireless Headphones Black</a>
    <li class="price-current">$339.99</li>
    <a class="item-rating" title="4.6 out of 5 stars"></a>
    <span class="item-rating-num">(85)</span>
    <a class="item-img"><img src="https://c1.neweggimages.com/ProductImage/sony.jpg"/></a>
  </div>
</body>
</html>
"""

MOCK_ALIEXPRESS_HTML = """
<html>
<body>
  <div class="multi--container--1cn2G07">
    <a href="https://www.aliexpress.com/item/1005006677889900.html" title="Original Silicone Case for AirPods Pro 2">
      <div class="title">Original Silicone Case for AirPods Pro 2</div>
      <div class="price">$4.99</div>
      <img src="//ae01.alicdn.com/kf/S123456789.jpg"/>
    </a>
  </div>
</body>
</html>
"""

def run_demo():
    print("=" * 75)
    print(" ZENROWS MULTI-MARKETPLACE PRODUCT SCRAPER & PRICE TRACKER DEMO")
    print(" (Supporting Amazon, eBay, Walmart, BestBuy, Target, Newegg, AliExpress)")
    print("=" * 75 + "\n")

    supabase = SupabaseManager()
    tracker = PriceTrackerEngine(supabase=supabase)

    all_products = []

    # 1. Amazon
    logger.info("Parsing Amazon Best Sellers...")
    amz_items = parse_marketplace_page(MOCK_AMAZON_HTML, "https://www.amazon.com/gp/bestsellers/electronics", "amazon", "Electronics")
    all_products.extend(amz_items)
    print(f" -> Amazon Extracted: {len(amz_items)} products.")

    # 2. eBay
    logger.info("Parsing eBay Trending Listings...")
    ebay_items = parse_marketplace_page(MOCK_EBAY_HTML, "https://www.ebay.com/b/Headphones/112529", "ebay", "Electronics")
    all_products.extend(ebay_items)
    print(f" -> eBay Extracted: {len(ebay_items)} products.")

    # 3. Walmart
    logger.info("Parsing Walmart Best Sellers...")
    wm_items = parse_marketplace_page(MOCK_WALMART_HTML, "https://www.walmart.com/browse/electronics/headphones", "walmart", "Electronics")
    all_products.extend(wm_items)
    print(f" -> Walmart Extracted: {len(wm_items)} products.")

    # 4. BestBuy
    logger.info("Parsing BestBuy Top Deals...")
    bb_items = parse_marketplace_page(MOCK_BESTBUY_HTML, "https://www.bestbuy.com/site/electronics/top-deals/pcmcat1563299784494.c", "bestbuy", "Electronics")
    all_products.extend(bb_items)
    print(f" -> BestBuy Extracted: {len(bb_items)} products.")

    # 5. Target
    logger.info("Parsing Target Best Sellers...")
    tgt_items = parse_marketplace_page(MOCK_TARGET_HTML, "https://www.target.com/c/electronics/-/N-5xtg6", "target", "Electronics")
    all_products.extend(tgt_items)
    print(f" -> Target Extracted: {len(tgt_items)} products.")

    # 6. Newegg
    logger.info("Parsing Newegg Today's Deals...")
    egg_items = parse_marketplace_page(MOCK_NEWEGG_HTML, "https://www.newegg.com/todays-deals", "newegg", "Electronics")
    all_products.extend(egg_items)
    print(f" -> Newegg Extracted: {len(egg_items)} products.")

    # 7. AliExpress
    logger.info("Parsing AliExpress Hot Selling Products...")
    ali_items = parse_marketplace_page(MOCK_ALIEXPRESS_HTML, "https://www.aliexpress.com/popular/airpods-pro.html", "aliexpress", "Electronics")
    all_products.extend(ali_items)
    print(f" -> AliExpress Extracted: {len(ali_items)} products.")

    print("\n" + "-" * 75)
    print(f" TOTAL EXTRACTED MARKETPLACE PRODUCTS: {len(all_products)}")
    print("-" * 75)

    # Render Price Comparison Matrix
    print("\nCROSS-MARKETPLACE PRICE COMPARISON TABLE:")
    tracker.print_price_comparison(all_products)

    if supabase.is_connected():
        logger.info("Supabase is connected! Upserting items into 'marketplace_products' table...")
        supabase.upsert_marketplace_products_batch(all_products)
        tracker.auto_create_comparison_groups()
    else:
        logger.info("Supabase credentials not configured yet. (Set SUPABASE_URL and SUPABASE_KEY in .env to enable DB persistence)")

    print("\n" + "=" * 75)
    print(" DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    run_demo()
