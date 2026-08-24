import re
from typing import Optional, Dict

# Standardized taxonomy mapping
CATEGORY_PATTERNS: Dict[str, str] = {
    r"\b(airpods|headphone|headphones|earbud|earbuds|headset|soundcore|earphone|audio|speaker|subwoofer)\b": "Electronics > Audio & Headphones",
    r"\b(laptop|desktop|mini pc|computer|ram|ssd|keyboard|mouse|switch|ethernet|router|monitor|gpu)\b": "Computers & Hardware",
    r"\b(tv|television|projector|soundbar|home theater)\b": "Electronics > TV & Video",
    r"\b(iphone|samsung|galaxy|cell phone|smartphone|charger|case|power bank)\b": "Cell Phones & Accessories",
    r"\b(dehumidifier|air fryer|stand mixer|dresser|chair|patio|vacuum|appliance|furniture)\b": "Home & Kitchen",
    r"\b(slippers|boots|shoes|wallet|tote|backpack|bag|jacket|hoodie|clothing|apparel)\b": "Apparel & Accessories",
    r"\b(pokemon|mtg|booster|board game|toy|plush|bounce house)\b": "Toys, Games & Collectibles",
    r"\b(skincare|serum|cream|moisturizer|makeup|cosmetics|balm)\b": "Beauty & Personal Care",
    r"\b(tent|scooter|camping|atv|ride on|fitness|sports)\b": "Sports & Outdoors"
}

def classify_product_category(title: str, raw_category: Optional[str] = None) -> str:
    """
    Classifies a product into a standardized taxonomy based on title and raw marketplace category tags.
    """
    combined_text = f"{title} {raw_category or ''}".lower()

    for pattern, std_category in CATEGORY_PATTERNS.items():
        if re.search(pattern, combined_text, re.I):
            return std_category

    if raw_category and raw_category.lower() not in ["general", "deals", "today's deals", "top deals"]:
        return raw_category.title()

    return "General / Uncategorized"
