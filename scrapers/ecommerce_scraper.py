import json
import re
import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

def extract_top_highlights(soup: BeautifulSoup) -> List[str]:
    """
    Extracts 'Top highlights' bullet points from Amazon side-peek & feature bullet sections
    (#feature-bullets, div[data-feature-name='topHighlights'], div#productOverview_feature_div)
    """
    highlights = []
    
    # 1. Feature bullets list
    for li in soup.select("#feature-bullets ul li span.a-list-item, div[data-feature-name='topHighlights'] li span"):
        text = " ".join(li.get_text(strip=True).split())
        if text and len(text) > 5 and not text.startswith("Make sure this fits") and text not in highlights:
            highlights.append(text)

    # 2. Product overview rows (Key Highlights table)
    for row in soup.select("#productOverview_feature_div tr, div.po-row"):
        label_elem = row.select_one("td.a-span3 span, span.po-break-word")
        val_elem = row.select_one("td.a-span9 span, span.po-break-word:nth-child(2)")
        if label_elem and val_elem:
            k = " ".join(label_elem.get_text(strip=True).split())
            v = " ".join(val_elem.get_text(strip=True).split())
            if k and v:
                line = f"{k}: {v}"
                if line not in highlights:
                    highlights.append(line)

    return highlights

def extract_product_specifications(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extracts key-value product specifications from Amazon detail sections & side-peek panels
    (#productDetails_techSpec_section_1, table.a-keyvalue, #detailBullets_feature_div, etc.)
    """
    specs = {}
    # 1. Table rows (th / td pairs or td.label / td.value pairs)
    for table in soup.select("table.a-keyvalue, #productDetails_techSpec_section_1, #productDetails_db_sections, table[class*='spec']"):
        for row in table.find_all("tr"):
            th = row.find(["th", "td"], class_=re.compile(r"(label|name|head)", re.I)) or row.find("th")
            td = row.find("td", class_=re.compile(r"(value|attr)", re.I)) or row.find_all("td")[-1] if row.find_all("td") else None
            if th and td:
                k = " ".join(th.get_text(strip=True).split())
                v = " ".join(td.get_text(strip=True).split())
                if k and v and len(k) < 60:
                    specs[k] = v

    # 2. Bullet list specifications (#detailBullets_feature_div)
    for li in soup.select("#detailBullets_feature_div li, div.product-facts-detail"):
        text = li.get_text(strip=True)
        if ":" in text:
            parts = text.split(":", 1)
            k = " ".join(parts[0].replace("\u200e", "").replace("\u200f", "").split())
            v = " ".join(parts[1].split())
            if k and v and len(k) < 60:
                specs[k] = v

    return specs

def parse_product_page(html_content: str, url: str) -> Dict[str, Any]:
    """
    Parses HTML content of an e-commerce product page into a structured schema.
    Uses JSON-LD Product microdata, OpenGraph meta tags, and BeautifulSoup heuristics.
    """
    soup = BeautifulSoup(html_content, "lxml")

    name = None
    price = None
    original_price = None
    currency = "USD"
    sku = None
    brand = None
    category = None
    availability = "InStock"
    rating = None
    review_count = 0
    image_url = None
    images: List[str] = []
    description = None
    metadata = {}

    # 1. Attempt JSON-LD Schema.org Product parsing
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                data = data[0] if data else {}
            
            graph = data.get("@graph", [])
            items_to_check = [data] + (graph if isinstance(graph, list) else [])

            for item in items_to_check:
                item_type = str(item.get("@type", "")).lower()
                if "product" in item_type:
                    name = item.get("name")
                    sku = item.get("sku") or item.get("mpn") or item.get("gtin13")
                    description = item.get("description")
                    
                    # Brand
                    brand_obj = item.get("brand")
                    if isinstance(brand_obj, dict):
                        brand = brand_obj.get("name")
                    elif isinstance(brand_obj, str):
                        brand = brand_obj
                        
                    # Images
                    img = item.get("image")
                    if isinstance(img, list):
                        images = img
                        image_url = img[0] if img else None
                    elif isinstance(img, str):
                        image_url = img
                        images = [img]

                    # Offers / Price
                    offers = item.get("offers")
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    if isinstance(offers, dict):
                        raw_price = offers.get("price")
                        if raw_price is not None:
                            try:
                                price = float(str(raw_price).replace(",", "").replace("$", ""))
                            except ValueError:
                                pass
                        currency = offers.get("priceCurrency") or currency
                        avail_str = str(offers.get("availability", ""))
                        if "outofstock" in avail_str.lower():
                            availability = "OutOfStock"
                            
                    # Rating
                    agg_rating = item.get("aggregateRating")
                    if isinstance(agg_rating, dict):
                        try:
                            rating = float(agg_rating.get("ratingValue"))
                            review_count = int(agg_rating.get("reviewCount") or agg_rating.get("ratingCount") or 0)
                        except (ValueError, TypeError):
                            pass

                    metadata["json_ld"] = item
                    break
        except Exception:
            continue

    # 2. OpenGraph / Meta Tag Fallbacks
    if not name:
        og_name = soup.find("meta", property="og:title")
        if og_name:
            name = og_name.get("content")

    if not image_url:
        og_img = soup.find("meta", property="og:image")
        if og_img:
            image_url = og_img.get("content")
            if image_url and image_url not in images:
                images.append(image_url)

    if not price:
        og_price = soup.find("meta", property="product:price:amount") or soup.find("meta", attrs={"name": "price"})
        if og_price:
            try:
                price = float(og_price.get("content"))
            except (ValueError, TypeError):
                pass

    # 3. DOM / HTML Element Fallbacks
    if not name:
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)

    if not price:
        # Search for common price class patterns
        price_elem = soup.find(class_=re.compile(r"(price|amount)", re.I))
        if price_elem:
            price_match = re.search(r"[\$\€\£]?\s*(\d+[\.,]\d{2})", price_elem.get_text())
            if price_match:
                try:
                    price = float(price_match.group(1).replace(",", ""))
                except ValueError:
                    pass

    # 4. Extract Top Highlights & Specifications
    top_highlights = extract_top_highlights(soup)
    specifications = extract_product_specifications(soup)

    metadata["top_highlights"] = top_highlights
    metadata["specifications"] = specifications

    short_description = " | ".join(top_highlights[:3]) if top_highlights else None

    name = name or "Unknown Product"

    return {
        "url": url,
        "sku": sku,
        "name": name,
        "price": price,
        "original_price": original_price,
        "currency": currency,
        "brand": brand,
        "category": category,
        "availability": availability,
        "rating": rating,
        "review_count": review_count,
        "image_url": image_url,
        "images": images,
        "short_description": short_description,
        "description": description,
        "metadata": metadata
    }
