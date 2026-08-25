import json
import re
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def clean_price(price_str: Optional[str]) -> Optional[float]:
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d\.]", "", price_str.replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None

KNOWN_BRANDS = [
    # Top Smart Home & Electronics Brands
    "Ring", "Nest", "Google Nest", "Philips Hue", "Hue", "Eufy", "Arlo", "Ecobee",
    "Roborock", "Aqara", "TP-Link", "Kasa", "Tapo", "Sonos", "Eve", "Nanoleaf",
    "Blink", "Yale", "SwitchBot", "August", "Sensibo", "Netatmo", "Belkin", "Wemo",
    "Reolink", "Dyson", "iRobot", "Roomba", "Dreame", "Ecovacs", "Wyze", "Leviton",
    
    # Top Beauty, Skincare & Youth Supplement Brands
    "The Ordinary", "CeraVe", "La Roche-Posay", "Paula's Choice", "Glow Recipe",
    "SkinCeuticals", "Drunk Elephant", "Estée Lauder", "Clinique", "Laneige",
    "COSRX", "Supergoop!", "Sunday Riley", "Kiehl's", "Tatcha", "Youth to the People",
    "Sol de Janeiro", "Fenty Skin", "NARS", "Charlotte Tilbury", "Urban Decay", "MAC",
    "Olaplex", "Dermalogica", "Vital Proteins", "Codeage", "Sports Research", "Solgar",
    "Thorne", "Garden of Life", "NOW Foods", "Reserveage", "NeoCell", "HUM Nutrition",
    "OLLY", "Life Extension", "Nature's Bounty", "Swisse", "Blackmores",
    "Sennheiser", "Bose", "Sony", "Apple", "Samsung", "LG", "Logitech", "Anker", "JBL"
]

def clean_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    ascii_clean = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_clean.split())

def extract_brand(title: Optional[str], card: Optional[BeautifulSoup] = None) -> Optional[str]:
    if not title:
        return None
    
    # 1. Check DOM card for explicit brand element
    if card:
        brand_elem = card.select_one(".byline-info, [data-brand], a#bylineInfo, .brand-name, span.brand")
        if brand_elem:
            raw_b = brand_elem.get_text(strip=True).replace("Brand:", "").replace("by ", "").replace("Visit the ", "").replace(" Store", "")
            if raw_b and len(raw_b) < 30:
                return clean_text(raw_b)

    # 2. Check title against known brands list
    for b in KNOWN_BRANDS:
        if re.search(r'\b' + re.escape(b) + r'\b', title, re.I):
            return b

    # 3. Fallback: First word of title if valid brand candidate
    words = title.split()
    if words and len(words[0]) >= 2 and words[0].isalpha() and words[0].lower() not in ["new", "sponsored", "sale", "the", "official", "pack"]:
        return words[0].title()

    return None

# ==========================================
# 1. AMAZON BEST SELLERS PARSER
# ==========================================
def parse_amazon_bestsellers(html_content: str, category: str = "General") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []

    card_elements = soup.select(".zg-grid-general-faceout, #gridItemRoot, div[id^='post-'], div[data-deal-id], div[class*='DealCard'], div[data-testid*='deal-card']")
    if not card_elements:
        card_elements = soup.select("div.zg-carousel-general-faceout, div[data-asin], div.a-section[class*='Deal']")
    if not card_elements:
        card_elements = [a.find_parent("div") for a in soup.select("a[href*='/dp/'], a[href*='/deal/']") if a.find_parent("div")]

    logger.info(f"Amazon Parser: Found {len(card_elements)} candidate product cards.")

    rank = 1
    seen_urls = set()
    for card in card_elements:
        asin = card.get("data-asin") or card.get("data-deal-id")
        link_elem = card.select_one("a[href*='/dp/'], a[href*='/deal/'], a[href*='/gp/product/']")
        product_url = ""
        if link_elem:
            href = link_elem.get("href", "")
            if href.startswith("/"):
                product_url = f"https://www.amazon.com{href.split('?')[0]}"
            else:
                product_url = href.split("?")[0]
            if not asin:
                asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", product_url)
                if asin_match:
                    asin = asin_match.group(1)

        if product_url in seen_urls:
            continue
        if product_url:
            seen_urls.add(product_url)

        rank_elem = card.select_one(".zg-bdg-text, .zg-badge-text, span.zg-badge-body")
        rank_pos = rank
        if rank_elem:
            rank_match = re.search(r"\d+", rank_elem.get_text())
            if rank_match:
                rank_pos = int(rank_match.group(0))

        title_elem = card.select_one("div._cDE12_p13n-sc-css-line-clamp-1_1597W, div[class*='p13n-sc-css-line-clamp'], span.zg-text-js-truncate, img[alt]")
        title = None
        if title_elem:
            title = title_elem.get("alt") if title_elem.name == "img" else title_elem.get_text(strip=True)
        if not title and link_elem:
            title = link_elem.get_text(strip=True)

        price_elem = card.select_one("span._cDE12_price_1bkM5, span.p13n-sc-price, span.a-price span.a-offscreen, span.a-color-price")
        current_price = clean_price(price_elem.get_text()) if price_elem else None

        orig_price_elem = card.select_one("span.a-text-price span.a-offscreen, span.basisPrice span.a-offscreen, span[data-a-strike='true'] span.a-offscreen, span.a-price[data-a-strike='true']")
        original_price = clean_price(orig_price_elem.get_text()) if orig_price_elem else None

        discount_percent = None
        if current_price and original_price and original_price > current_price:
            discount_percent = round(((original_price - current_price) / original_price) * 100, 2)

        rating_elem = card.select_one("i.a-icon-star, span.a-icon-alt")
        rating = None
        if rating_elem:
            rating_match = re.search(r"(\d+(?:\.\d+)?)", rating_elem.get_text())
            if rating_match:
                rating = float(rating_match.group(1))

        review_elem = card.select_one("a[href*='#customerReviews'] span, span.a-size-small")
        review_count = 0
        if review_elem:
            rev_match = re.search(r"[\d,]+", review_elem.get_text())
            if rev_match:
                review_count = int(rev_match.group(0).replace(",", ""))

        img_elem = card.select_one("img[src*='images-I'], img[src*='media-amazon']")
        image_url = img_elem.get("src") if img_elem else None

        # Extract Coupon / Savings Badge
        coupon_elem = card.select_one("span.s-coupon-unclipped, span.a-color-discount, span[id*='coupon']")
        coupon_text = clean_text(coupon_elem.get_text()) if coupon_elem else None
        coupon_code = None

        if title and (product_url or asin):
            products.append({
                "marketplace": "amazon",
                "external_id": asin,
                "title": clean_text(title),
                "brand": extract_brand(title, card),
                "category": category,
                "current_price": current_price,
                "original_price": original_price,
                "discount_percent": discount_percent,
                "currency": "USD",
                "rank_position": rank_pos,
                "rating": rating,
                "review_count": review_count,
                "seller_name": "Amazon",
                "coupon_text": coupon_text,
                "coupon_code": coupon_code,
                "short_description": clean_text(title),
                "description": None,
                "is_available": True,
                "product_url": product_url or f"https://www.amazon.com/dp/{asin}",
                "image_url": image_url,
                "images": [image_url] if image_url else [],
                "metadata": {"asin": asin, "category": category}
            })
            rank += 1

    return products


# ==========================================
# 2. EBAY TRENDING LISTINGS PARSER
# ==========================================
def parse_ebay_trending(html_content: str, category: str = "General") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []

    card_elements = soup.select(".dne-itemcard, div.ebayui-dne-item-card, .srp-results .s-item, .b-list__items_nofooter .s-item, ul.b-list__items_nofooter > li")
    if not card_elements:
        item_links = soup.select("a[href*='/itm/'], a[href*='/p/']")
        card_elements = []
        for a in item_links:
            parent = a.find_parent(class_=re.compile(r"(card|item|col|grid|wrapper)", re.I)) or a.parent
            if parent and parent not in card_elements:
                card_elements.append(parent)

    logger.info(f"eBay Parser: Found {len(card_elements)} product cards.")

    rank = 1
    seen_urls = set()

    for card in card_elements:
        link_elem = card.select_one("a[href*='/itm/'], a[href*='/p/'], a.dne-itemcard-title, a.s-item__link, a.b-tile__link") or (card if card.name == "a" else None)
        if not link_elem:
            continue
        product_url = link_elem.get("href", "").split("?")[0]
        if not product_url or product_url in seen_urls:
            continue

        title_elem = card.select_one("span[title], h3, h2, span.title, .dne-itemcard-title, .s-item__title, img[alt]") or a
        title = title_elem.get("alt") if title_elem and title_elem.name == "img" else title_elem.get_text(strip=True)

        if not title or len(title) < 5 or "Shop on eBay" in title:
            continue

        seen_urls.add(product_url)

        item_id = None
        id_match = re.search(r"/itm/(\d+)", product_url)
        if id_match:
            item_id = id_match.group(1)

        price_elem = card.select_one("span[class*='price' i], div[class*='price' i], span.first-price, .dne-itemcard-price, .s-item__price")
        current_price = clean_price(price_elem.get_text()) if price_elem else None

        orig_price_elem = card.select_one(".dne-itemcard-original-price, .item-tile__price-original, span[class*='original' i]")
        orig_price = clean_price(orig_price_elem.get_text()) if orig_price_elem else None

        badge_elem = card.select_one(".dne-itemcard-hotness, .dne-itemcard-discount, .s-item__discount, span[class*='discount' i]")
        coupon_text = clean_text(badge_elem.get_text()) if badge_elem else None

        img_elem = card.select_one("img[src*='ebayimg'], img[data-src], img")
        image_url = img_elem.get("src") or img_elem.get("data-src") if img_elem else None

        seller_elem = card.select_one(".s-item__seller-info")
        seller_name = seller_elem.get_text(strip=True) if seller_elem else "eBay Seller"

        products.append({
            "marketplace": "ebay",
            "external_id": item_id,
            "title": clean_text(title),
            "brand": None,
            "category": category,
            "current_price": current_price,
            "original_price": orig_price,
            "discount_percent": None,
            "currency": "USD",
            "rank_position": rank,
            "rating": None,
            "review_count": 0,
            "seller_name": seller_name,
            "coupon_text": coupon_text,
            "coupon_code": None,
            "short_description": None,
            "description": None,
            "is_available": True,
            "product_url": product_url,
            "image_url": image_url,
            "images": [image_url] if image_url else [],
            "metadata": {"ebay_item_id": item_id}
        })
        rank += 1

    return products


# ==========================================
# 3. WALMART BEST SELLERS PARSER
# ==========================================
def parse_walmart_bestsellers(html_content: str, category: str = "General") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []

    script_next = soup.find("script", id="__NEXT_DATA__")
    if script_next and script_next.string:
        try:
            json_data = json.loads(script_next.string)
            props = json_data.get("props", {}).get("pageProps", {})
            search_res = props.get("initialData", {}).get("searchResult", {}).get("itemStacks", [])
            
            rank = 1
            for stack in search_res:
                items = stack.get("items", [])
                for item in items:
                    name = item.get("name") or item.get("title")
                    if not name:
                        continue
                    
                    price_info = item.get("priceInfo", {}).get("currentPrice", {})
                    current_price = price_info.get("price")
                    us_item_id = str(item.get("usItemId") or item.get("id"))
                    canonical_url = item.get("canonicalUrl") or f"/ip/{us_item_id}"
                    full_url = f"https://www.walmart.com{canonical_url}"
                    image_url = item.get("imageInfo", {}).get("thumbnailUrl")
                    rating_val = item.get("rating", {}).get("averageRating")

                    products.append({
                        "marketplace": "walmart",
                        "external_id": us_item_id,
                        "title": clean_text(name),
                        "brand": item.get("brand"),
                        "category": category,
                        "current_price": float(current_price) if current_price else None,
                        "original_price": None,
                        "discount_percent": None,
                        "currency": "USD",
                        "rank_position": rank,
                        "rating": float(rating_val) if rating_val else None,
                        "review_count": int(item.get("rating", {}).get("numberOfReviews") or 0),
                        "seller_name": item.get("sellerName", "Walmart"),
                        "is_available": True,
                        "product_url": full_url,
                        "image_url": image_url,
                        "images": [image_url] if image_url else [],
                        "metadata": {"walmart_item_id": us_item_id}
                    })
                    rank += 1
            if products:
                logger.info(f"Walmart Parser: Extracted {len(products)} items from __NEXT_DATA__ JSON.")
                return products
        except Exception as e:
            logger.warning(f"Walmart NEXT_DATA JSON parse failed: {e}")

    cards = soup.select("div[data-item-id], [data-testimonial-id]")
    rank = 1
    for card in cards:
        item_id = card.get("data-item-id")
        title_elem = card.select_one("span.w_iU, [data-automation-id='product-title'], a span")
        title = title_elem.get_text(strip=True) if title_elem else None
        
        link_elem = card.select_one("a[href*='/ip/']")
        product_url = f"https://www.walmart.com{link_elem.get('href')}" if link_elem else ""

        price_elem = card.select_one("div[data-automation-id='product-price'], div.aria-hidden")
        price = clean_price(price_elem.get_text()) if price_elem else None

        img_elem = card.select_one("img[data-testimonial-id='product-image'], img")
        image_url = img_elem.get("src") if img_elem else None

        if title and product_url:
            products.append({
                "marketplace": "walmart",
                "external_id": item_id,
                "title": clean_text(title),
                "brand": extract_brand(title, card),
                "category": category,
                "current_price": price,
                "original_price": None,
                "discount_percent": None,
                "currency": "USD",
                "rank_position": rank,
                "rating": None,
                "review_count": 0,
                "seller_name": "Walmart",
                "is_available": True,
                "product_url": product_url,
                "image_url": image_url,
                "images": [image_url] if image_url else [],
                "metadata": {"item_id": item_id}
            })
            rank += 1

    return products


# ==========================================
# 4. BEST BUY BEST SELLERS PARSER
# ==========================================
def parse_bestbuy_bestsellers(html_content: str, category: str = "General") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []

    card_elements = soup.select("div.dotd-product-offer, div.offer-position-1, div[class*='offer' i], div[class*='dotd' i], li.sku-item, div.sku-item, div[data-sku-id]")
    if not card_elements:
        card_elements = [a.find_parent("div") for a in soup.select("a[href*='/site/'], a[href*='/product/'], a[href*='/combo/']") if a.find_parent("div")]

    logger.info(f"BestBuy Parser: Found {len(card_elements)} candidate product cards.")

    rank = 1
    seen_urls = set()

    for card in card_elements:
        title_elem = card.select_one("h1 a, h2 a, h3 a, h4 a, .heading-5 a, .heading-4 a, a[href*='/site/'], a[href*='/product/']")
        if not title_elem:
            title_elem = card.select_one("h1, h2, h3, h4, .heading-5, .heading-4")
        if not title_elem:
            continue
        
        title = title_elem.get_text(strip=True)
        if not title or len(title) < 5 or "See Deal of the Day" in title or "Best Buy" in title:
            continue

        link_elem = title_elem if title_elem.name == "a" else card.select_one("a[href*='/site/'], a[href*='/product/'], a[href*='/combo/']")
        if not link_elem:
            continue

        href = link_elem.get("href", "")
        if not href or href in seen_urls:
            continue

        product_url = f"https://www.bestbuy.com{href.split('?')[0]}" if href.startswith("/") else href.split("?")[0]
        seen_urls.add(href)
        seen_urls.add(product_url)

        sku_id = None
        sku_match = re.search(r"/(?:product|site|combo)/.*?/([A-Z0-9]{6,12}|\d{7})", product_url)
        if sku_match:
            sku_id = sku_match.group(1)

        price_elem = card.select_one("span.customer-price, div.priceView-customer-price span, [class*='price' i]")
        price = clean_price(price_elem.get_text()) if price_elem else None

        orig_price_elem = card.select_one("div.pricing-price__regular-price, span.pricing-price__regular-price-value, [class*='regular' i]")
        orig_price = clean_price(orig_price_elem.get_text()) if orig_price_elem else None

        img_elem = card.select_one("img.product-image, img.sku-image, img")
        image_url = img_elem.get("src") if img_elem else None

        products.append({
            "marketplace": "bestbuy",
            "external_id": sku_id,
            "title": clean_text(title),
            "brand": extract_brand(title, card),
            "category": category,
            "current_price": price,
            "original_price": orig_price,
            "discount_percent": None,
            "currency": "USD",
            "rank_position": rank,
            "rating": None,
            "review_count": 0,
            "seller_name": "Best Buy",
            "coupon_text": None,
            "coupon_code": None,
            "short_description": None,
            "description": None,
            "is_available": True,
            "product_url": product_url,
            "image_url": image_url,
            "images": [image_url] if image_url else [],
            "metadata": {"sku_id": sku_id}
        })
        rank += 1

    return products


# ==========================================
# 5. TARGET BEST SELLERS PARSER
# ==========================================
def parse_target_bestsellers(html_content: str, category: str = "General") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []

    for script in soup.find_all("script"):
        script_str = script.string or ""
        if "__TGT_DATA__" in script_str or "redsky" in script_str:
            try:
                json_match = re.search(r"window\.__TGT_DATA__\s*=\s*(\{.*?\});", script_str, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                    search_res = data.get("deepRedsky", {}).get("search", {}).get("products", [])
                    rank = 1
                    for item in search_res:
                        tcin = item.get("tcin")
                        item_info = item.get("item", {}).get("product_description", {})
                        title = item_info.get("title")
                        price_info = item.get("price", {})
                        price = price_info.get("current_retail")
                        orig_price = price_info.get("reg_retail")
                        img_url = item.get("item", {}).get("enrichment", {}).get("images", {}).get("primary_image_url")
                        rating = item.get("ratings_and_reviews", {}).get("statistics", {}).get("rating", {}).get("average")

                        if title and tcin:
                            products.append({
                                "marketplace": "target",
                                "external_id": str(tcin),
                                "title": clean_text(title),
                                "brand": item.get("item", {}).get("product_classification", {}).get("brand_name"),
                                "category": category,
                                "current_price": float(price) if price else None,
                                "original_price": float(orig_price) if orig_price else None,
                                "discount_percent": None,
                                "currency": "USD",
                                "rank_position": rank,
                                "rating": float(rating) if rating else None,
                                "review_count": int(item.get("ratings_and_reviews", {}).get("statistics", {}).get("review_count") or 0),
                                "seller_name": "Target",
                                "is_available": True,
                                "product_url": f"https://www.target.com/p/-/A-{tcin}",
                                "image_url": img_url,
                                "images": [img_url] if img_url else [],
                                "metadata": {"tcin": tcin}
                            })
                            rank += 1
                    if products:
                        return products
            except Exception as e:
                logger.warning(f"Target JSON parse failed: {e}")

    card_elements = soup.select("div[data-test='@web/site-top-of-funnel/ProductCardWrapper'], div[data-test='product-card']")
    logger.info(f"Target Parser: Found {len(card_elements)} DOM product cards.")

    rank = 1
    for card in card_elements:
        title_elem = card.select_one("a[data-test='product-title'], a.styles__StyledTitleLink-sc-1kk2044-0")
        title = title_elem.get_text(strip=True) if title_elem else None

        link_elem = title_elem or card.select_one("a[href*='/p/']")
        product_url = f"https://www.target.com{link_elem.get('href').split('?')[0]}" if link_elem else ""

        tcin = None
        tcin_match = re.search(r"/A-(\d+)", product_url)
        if tcin_match:
            tcin = tcin_match.group(1)

        price_elem = card.select_one("span[data-test='current-price'], div[data-test='current-price']")
        price = clean_price(price_elem.get_text()) if price_elem else None

        rating_elem = card.select_one("span[data-test='rating-count']")
        rating = clean_price(rating_elem.get_text()) if rating_elem else None

        img_elem = card.select_one("picture img, img")
        image_url = img_elem.get("src") if img_elem else None

        if title and product_url:
            products.append({
                "marketplace": "target",
                "external_id": tcin,
                "title": clean_text(title),
                "brand": extract_brand(title, card),
                "category": category,
                "current_price": price,
                "original_price": None,
                "discount_percent": None,
                "currency": "USD",
                "rank_position": rank,
                "rating": rating,
                "review_count": 0,
                "seller_name": "Target",
                "is_available": True,
                "product_url": product_url,
                "image_url": image_url,
                "images": [image_url] if image_url else [],
                "metadata": {"tcin": tcin}
            })
            rank += 1

    return products


# ==========================================
# 6. NEWEGG BEST SELLERS PARSER
# ==========================================
def parse_newegg_bestsellers(html_content: str, category: str = "General") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []

    card_elements = soup.select("div.item-cells-wrap div.item-cell, div.item-container")
    logger.info(f"Newegg Parser: Found {len(card_elements)} item containers.")

    rank = 1
    for card in card_elements:
        title_elem = card.select_one("a.item-title")
        if not title_elem:
            continue
        title = title_elem.get_text(strip=True)
        product_url = title_elem.get("href", "").split("?")[0]

        item_id = None
        id_match = re.search(r"/(?:p|Item)/([A-Z0-9]{12,15}|N82E\d+)", product_url, re.I)
        if id_match:
            item_id = id_match.group(1)

        price_elem = card.select_one("li.price-current, ul.price li.price-current")
        price = clean_price(price_elem.get_text()) if price_elem else None

        was_price_elem = card.select_one("li.price-was, span.price-was-data")
        orig_price = clean_price(was_price_elem.get_text()) if was_price_elem else None

        rating_elem = card.select_one("a.item-rating, i.rating")
        rating = None
        if rating_elem:
            title_rating = rating_elem.get("title") or rating_elem.get("aria-label") or ""
            r_match = re.search(r"(\d+(?:\.\d+)?)", title_rating)
            if r_match:
                rating = float(r_match.group(1))

        review_elem = card.select_one("span.item-rating-num")
        review_count = 0
        if review_elem:
            rev_match = re.search(r"\d+", review_elem.get_text())
            if rev_match:
                review_count = int(rev_match.group(0))

        img_elem = card.select_one("a.item-img img, img")
        image_url = img_elem.get("src") if img_elem else None

        if title and product_url:
            products.append({
                "marketplace": "newegg",
                "external_id": item_id,
                "title": clean_text(title),
                "brand": extract_brand(title, card),
                "category": category,
                "current_price": price,
                "original_price": orig_price,
                "discount_percent": None,
                "currency": "USD",
                "rank_position": rank,
                "rating": rating,
                "review_count": review_count,
                "seller_name": "Newegg",
                "is_available": True,
                "product_url": product_url,
                "image_url": image_url,
                "images": [image_url] if image_url else [],
                "metadata": {"newegg_item_id": item_id}
            })
            rank += 1

    return products


# ==========================================
# 7. ALIEXPRESS HOT SELLING PARSER
# ==========================================
def parse_aliexpress_hotselling(html_content: str, category: str = "General") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []

    for script in soup.find_all("script"):
        script_str = script.string or ""
        if "_INITIAL_DATA_" in script_str or "__AEP_DATA__" in script_str:
            try:
                json_match = re.search(r"window\._INITIAL_DATA_\s*=\s*(\{[\s\S]*?\n\s*\});?", script_str)
                if not json_match:
                    json_match = re.search(r"window\._INITIAL_DATA_\s*=\s*(\{[\s\S]*\});?", script_str)
                if json_match:
                    raw_json = json_match.group(1).strip().rstrip(";")
                    data = json.loads(raw_json)
                    items = data.get("data", {}).get("root", {}).get("fields", {}).get("mods", {}).get("itemList", {}).get("content", [])
                    rank = 1
                    for item in items:
                        title = item.get("title", {}).get("displayTitle")
                        prod_id = item.get("productId")
                        price = item.get("prices", {}).get("salePrice", {}).get("minPrice")
                        orig_price = item.get("prices", {}).get("originalPrice", {}).get("minPrice")
                        image = item.get("image", {}).get("imgUrl")
                        orders = item.get("trade", {}).get("tradeDesc")

                        if title and prod_id:
                            products.append({
                                "marketplace": "aliexpress",
                                "external_id": str(prod_id),
                                "title": clean_text(title),
                                "brand": None,
                                "category": category,
                                "current_price": float(price) if price else None,
                                "original_price": float(orig_price) if orig_price else None,
                                "discount_percent": None,
                                "currency": "USD",
                                "rank_position": rank,
                                "rating": float(item.get("evaluation", {}).get("starRating") or 0),
                                "review_count": 0,
                                "seller_name": "AliExpress Seller",
                                "is_available": True,
                                "product_url": f"https://www.aliexpress.com/item/{prod_id}.html",
                                "image_url": f"https:{image}" if image and image.startswith("//") else image,
                                "images": [],
                                "metadata": {"orders_sold": orders}
                            })
                            rank += 1
                    if products:
                        return products
            except Exception as e:
                logger.warning(f"AliExpress JSON script parse failed: {e}")

    cards = soup.select("a[href*='/item/'], div.multi--container--1cn2G07")
    logger.info(f"AliExpress Parser: Found {len(cards)} candidate cards.")

    rank = 1
    for card in cards:
        href = card.get("href", "")
        if not href and card.name != "a":
            a_tag = card.select_one("a[href*='/item/']")
            href = a_tag.get("href", "") if a_tag else ""

        prod_id = None
        id_match = re.search(r"/item/(\d+)\.html", href)
        if id_match:
            prod_id = id_match.group(1)

        title_elem = card.select_one("h1, h3, div[class*='title']")
        title = title_elem.get_text(strip=True) if title_elem else card.get("title")

        price_elem = card.select_one("div[class*='price'], span[class*='price']")
        price = clean_price(price_elem.get_text()) if price_elem else None

        img_elem = card.select_one("img")
        image_url = img_elem.get("src") if img_elem else None

        if title and prod_id:
            products.append({
                "marketplace": "aliexpress",
                "external_id": prod_id,
                "title": clean_text(title),
                "brand": None,
                "category": category,
                "current_price": price,
                "original_price": None,
                "discount_percent": None,
                "currency": "USD",
                "rank_position": rank,
                "rating": None,
                "review_count": 0,
                "seller_name": "AliExpress Seller",
                "is_available": True,
                "product_url": f"https://www.aliexpress.com/item/{prod_id}.html",
                "image_url": image_url,
                "images": [image_url] if image_url else [],
                "metadata": {"item_id": prod_id}
            })
            rank += 1

    return products


# ==========================================
# 8. AUSTRALIAN RETAILERS (nxtsmarthome.com.au)
# ==========================================
def parse_jbhifi(html_content: str, category: str = "Smart Home") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []
    card_elements = soup.select("a[href*='/products/'], div[data-testid='product-card'], div[class*='ProductCard']")
    rank = 1
    seen = set()

    for card in card_elements:
        href = card.get("href", "") if card.name == "a" else (card.select_one("a[href*='/products/']") or {}).get("href", "")
        if not href or href in seen:
            continue
        product_url = f"https://www.jbhifi.com.au{href.split('?')[0]}" if href.startswith("/") else href.split("?")[0]
        seen.add(product_url)

        title_elem = card.select_one("h3, h4, span[class*='title' i], p[class*='title' i]") or card
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title or len(title) < 5 or "JB Hi-Fi" in title:
            continue

        price_elem = card.select_one("span[class*='price' i], div[class*='price' i]")
        price = clean_price(price_elem.get_text()) if price_elem else None
        img_elem = card.select_one("img")
        img_url = img_elem.get("src") if img_elem else None

        products.append({
            "marketplace": "jbhifi",
            "region": "AU",
            "external_id": href.split("/")[-1],
            "title": clean_text(title),
            "brand": extract_brand(title, card),
            "category": category,
            "current_price": price,
            "original_price": None,
            "discount_percent": None,
            "currency": "AUD",
            "rank_position": rank,
            "rating": None,
            "review_count": 0,
            "seller_name": "JB Hi-Fi Australia",
            "is_available": True,
            "product_url": product_url,
            "image_url": img_url,
            "images": [img_url] if img_url else [],
            "metadata": {"store": "jbhifi"}
        })
        rank += 1
    return products

def parse_harveynorman(html_content: str, category: str = "Smart Home") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []
    card_elements = soup.select("div.product-item, div[class*='product-card' i], div[data-product-id]")
    rank = 1
    seen = set()

    for card in card_elements:
        link_elem = card.select_one("a.product-title, a[href*='.html']")
        if not link_elem:
            continue
        href = link_elem.get("href", "")
        if not href or href in seen:
            continue
        product_url = f"https://www.harveynorman.com.au{href.split('?')[0]}" if href.startswith("/") else href.split("?")[0]
        seen.add(product_url)

        title = link_elem.get_text(strip=True)
        price_elem = card.select_one("span.price, div.price-box, [class*='price' i]")
        price = clean_price(price_elem.get_text()) if price_elem else None
        img_elem = card.select_one("img")
        img_url = img_elem.get("src") if img_elem else None

        products.append({
            "marketplace": "harveynorman",
            "region": "AU",
            "external_id": card.get("data-product-id") or href.split("/")[-1],
            "title": clean_text(title),
            "brand": extract_brand(title, card),
            "category": category,
            "current_price": price,
            "original_price": None,
            "discount_percent": None,
            "currency": "AUD",
            "rank_position": rank,
            "rating": None,
            "review_count": 0,
            "seller_name": "Harvey Norman Australia",
            "is_available": True,
            "product_url": product_url,
            "image_url": img_url,
            "images": [img_url] if img_url else [],
            "metadata": {"store": "harveynorman"}
        })
        rank += 1
    return products

def parse_thegoodguys(html_content: str, category: str = "Smart Home") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []
    card_elements = soup.select("div.product-tile, div[class*='productCard' i]")
    rank = 1
    seen = set()

    for card in card_elements:
        link_elem = card.select_one("a[href*='/p/'], a.product-tile-title")
        if not link_elem:
            continue
        href = link_elem.get("href", "")
        if not href or href in seen:
            continue
        product_url = f"https://www.thegoodguys.com.au{href.split('?')[0]}" if href.startswith("/") else href.split("?")[0]
        seen.add(product_url)

        title = link_elem.get_text(strip=True)
        price_elem = card.select_one("span.pricepoint-price, div.price, [class*='price' i]")
        price = clean_price(price_elem.get_text()) if price_elem else None
        img_elem = card.select_one("img")
        img_url = img_elem.get("src") if img_elem else None

        products.append({
            "marketplace": "thegoodguys",
            "region": "AU",
            "external_id": href.split("/")[-1],
            "title": clean_text(title),
            "brand": extract_brand(title, card),
            "category": category,
            "current_price": price,
            "original_price": None,
            "discount_percent": None,
            "currency": "AUD",
            "rank_position": rank,
            "rating": None,
            "review_count": 0,
            "seller_name": "The Good Guys Australia",
            "is_available": True,
            "product_url": product_url,
            "image_url": img_url,
            "images": [img_url] if img_url else [],
            "metadata": {"store": "thegoodguys"}
        })
        rank += 1
    return products


# ==========================================
# 9. IHERB PARSER (Beauty & Supplements)
# ==========================================
def parse_iherb(html_content: str, category: str = "Beauty & Supplements") -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "lxml")
    products = []
    card_elements = soup.select("div.product-cell, div.absolute-link-wrapper, div[class*='product-card' i]")
    rank = 1
    seen = set()

    for card in card_elements:
        link_elem = card.select_one("a.product-link, a[href*='/pr/']")
        if not link_elem:
            continue
        href = link_elem.get("href", "")
        if not href or href in seen:
            continue
        product_url = f"https://www.iherb.com{href.split('?')[0]}" if href.startswith("/") else href.split("?")[0]
        seen.add(product_url)

        title_elem = card.select_one("div.product-title, span.product-title, .product-name") or link_elem
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title or len(title) < 5:
            continue

        price_elem = card.select_one("span.price, div.price, [class*='price' i]")
        price = clean_price(price_elem.get_text()) if price_elem else None
        
        rating_elem = card.select_one("a.rating-count, span.rating, [aria-label*='stars']")
        rating = None
        if rating_elem:
            r_match = re.search(r"(\d+(?:\.\d+)?)", rating_elem.get_text() or rating_elem.get("aria-label", ""))
            if r_match:
                rating = float(r_match.group(1))

        img_elem = card.select_one("img")
        img_url = img_elem.get("src") or img_elem.get("data-src") if img_elem else None

        pid = href.split("/")[-1]

        products.append({
            "marketplace": "iherb",
            "region": "US",
            "external_id": pid,
            "title": clean_text(title),
            "brand": extract_brand(title, card),
            "category": category,
            "current_price": price,
            "original_price": None,
            "discount_percent": None,
            "currency": "USD",
            "rank_position": rank,
            "rating": rating,
            "review_count": 0,
            "seller_name": "iHerb",
            "is_available": True,
            "product_url": product_url,
            "image_url": img_url,
            "images": [img_url] if img_url else [],
            "metadata": {"store": "iherb"}
        })
        rank += 1
    return products


# ==========================================
# UNIFIED ROUTER (AU + INTL MARKETPLACES)
# ==========================================
def parse_marketplace_page(html_content: str, url: str, marketplace: str, category: str = "Smart Home") -> List[Dict[str, Any]]:
    m = marketplace.lower()
    if m in ["amazon", "amazon_us"]:
        items = parse_amazon_bestsellers(html_content, category)
        for item in items:
            item["region"] = "US"
            item["currency"] = "USD"
        return items
    elif m == "amazon_au":
        items = parse_amazon_bestsellers(html_content, category)
        for item in items:
            item["marketplace"] = "amazon_au"
            item["region"] = "AU"
            item["currency"] = "AUD"
            item["seller_name"] = "Amazon Australia"
            if "amazon.com" in item["product_url"] and "amazon.com.au" not in item["product_url"]:
                item["product_url"] = item["product_url"].replace("amazon.com", "amazon.com.au")
        return items
    elif m == "amazon_uk":
        items = parse_amazon_bestsellers(html_content, category)
        for item in items:
            item["marketplace"] = "amazon_uk"
            item["region"] = "UK"
            item["currency"] = "GBP"
            item["seller_name"] = "Amazon UK"
        return items
    elif m in ["ebay", "ebay_us"]:
        items = parse_ebay_trending(html_content, category)
        for item in items:
            item["region"] = "US"
            item["currency"] = "USD"
        return items
    elif m == "ebay_au":
        items = parse_ebay_trending(html_content, category)
        for item in items:
            item["marketplace"] = "ebay_au"
            item["region"] = "AU"
            item["currency"] = "AUD"
        return items
    elif m == "jbhifi":
        return parse_jbhifi(html_content, category)
    elif m == "harveynorman":
        return parse_harveynorman(html_content, category)
    elif m == "thegoodguys":
        return parse_thegoodguys(html_content, category)
    elif m == "iherb":
        return parse_iherb(html_content, category)
    elif m == "walmart":
        items = parse_walmart_bestsellers(html_content, category)
        for item in items:
            item["region"] = "US"
            item["currency"] = "USD"
        return items
    elif m in ["bestbuy", "bestbuy_us"]:
        items = parse_bestbuy_bestsellers(html_content, category)
        for item in items:
            item["region"] = "US"
            item["currency"] = "USD"
        return items
    elif m == "target":
        items = parse_target_bestsellers(html_content, category)
        for item in items:
            item["region"] = "US"
            item["currency"] = "USD"
        return items
    elif m == "newegg":
        items = parse_newegg_bestsellers(html_content, category)
        for item in items:
            item["region"] = "US"
            item["currency"] = "USD"
        return items
    elif m == "aliexpress":
        return parse_aliexpress_hotselling(html_content, category)
    else:
        # Fallback to amazon parsing logic if unknown
        logger.warning(f"Unknown marketplace '{marketplace}', attempting Amazon parser fallback.")
        return parse_amazon_bestsellers(html_content, category)


