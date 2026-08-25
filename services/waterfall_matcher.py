"""
Waterfall Product Matching Engine for Multi-Marketplace Affiliate Price Tracking.

Implements the 4-Tier Matching Strategy from strategy-docs:
  Tier 1: Exact GTIN / UPC / EAN Match (Gold Standard)
  Tier 2: Amazon ASIN Match
  Tier 3: Brand + MPN (Manufacturer Part Number) Match
  Tier 4: Fuzzy Title + Brand Trigram Similarity Match
          - Score >= 85%: Auto-link to canonical product
          - Score 65% - 84%: Route to human-in-the-loop 'unmatched_queue'
          - Score < 65%: Create new canonical product
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from db.supabase_client import SupabaseManager

logger = logging.getLogger(__name__)

def normalize_title(title: str) -> str:
    """
    Normalizes a product title by lowercasing, stripping punctuation,
    and removing filler noise words for reliable string comparison.
    """
    if not title:
        return ""
    t = title.lower()
    # Replace punctuation with spaces
    t = re.sub(r"[^\w\s]", " ", t)
    # Remove extra whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t

def generate_trigrams(text: str) -> set:
    """
    Generates 3-character (trigram) substrings from normalized text,
    matching PostgreSQL pg_trgm behavior.
    """
    padded = f"  {text} "
    trigrams = set()
    for i in range(len(padded) - 2):
        trigrams.add(padded[i:i+3])
    return trigrams

def calculate_trigram_similarity(title1: str, title2: str) -> float:
    """
    Computes trigram (Dice / Jaccard similarity) between two titles.
    Returns float score between 0.0 (no match) and 1.0 (identical).
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
        
    t1 = generate_trigrams(norm1)
    t2 = generate_trigrams(norm2)
    
    if not t1 or not t2:
        return 0.0
        
    intersection = t1.intersection(t2)
    # Dice coefficient: 2 * |t1 n t2| / (|t1| + |t2|)
    return (2.0 * len(intersection)) / (len(t1) + len(t2))

def extract_asin_from_url(url: str) -> Optional[str]:
    """
    Extracts Amazon ASIN (e.g. B0B9356M39) from product URL if present.
    """
    if not url:
        return None
    match = re.search(r"/(?:dp|gp/product|asin)/([A-Z0-9]{10})", url, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


class WaterfallMatcher:
    def __init__(
        self,
        supabase: Optional[SupabaseManager] = None,
        auto_link_threshold: float = 0.85,
        gray_area_threshold: float = 0.65
    ):
        self.supabase = supabase or SupabaseManager()
        self.auto_link_threshold = auto_link_threshold
        self.gray_area_threshold = gray_area_threshold

    def match_offer(
        self,
        raw_offer: Dict[str, Any],
        local_catalog: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes the 4-Tier Matching Waterfall on an incoming marketplace offer.
        
        Returns dictionary with:
          - canonical_product_id: UUID or mock ID of matched/created canonical product
          - match_tier: 'tier1_gtin', 'tier2_asin', 'tier3_brand_mpn', 'tier4_trigram', 'queued_review', 'tier5_new_canonical'
          - confidence_score: float score (0.0 to 1.0)
          - details: Explanation of match rationale
        """
        title = raw_offer.get("title", "")
        brand = raw_offer.get("brand", "")
        gtin = raw_offer.get("gtin") or raw_offer.get("gtin_upc_ean") or raw_offer.get("upc") or raw_offer.get("ean")
        asin = raw_offer.get("asin") or extract_asin_from_url(raw_offer.get("product_url", ""))
        mpn = raw_offer.get("mpn") or raw_offer.get("model")
        niche = raw_offer.get("niche") or ("beauty_skincare" if "skin" in title.lower() or "cream" in title.lower() or "serum" in title.lower() else "smart_home")
        category = raw_offer.get("category", "General")

        logger.info(f"[Waterfall Matcher] Evaluating offer: '{title}' (Brand: {brand}, GTIN: {gtin}, ASIN: {asin}, MPN: {mpn})")

        # ---------------------------------------------------------------------
        # TIER 1: Exact GTIN / UPC / EAN Match
        # ---------------------------------------------------------------------
        if gtin:
            matched = self.supabase.find_canonical_by_gtin(gtin) if self.supabase.is_connected() else None
            if not matched and local_catalog:
                matched = next((c for c in local_catalog if c.get("gtin_upc_ean") == gtin), None)
            
            if matched:
                logger.info(f"   ► TIER 1 MATCH (GTIN: {gtin}) -> Canonical ID: {matched.get('id')}")
                return {
                    "canonical_product_id": matched.get("id"),
                    "match_tier": "tier1_gtin",
                    "confidence_score": 1.0,
                    "canonical": matched,
                    "details": f"Exact GTIN match on {gtin}"
                }

        # ---------------------------------------------------------------------
        # TIER 2: Amazon ASIN Match
        # ---------------------------------------------------------------------
        if asin:
            matched = self.supabase.find_canonical_by_asin(asin) if self.supabase.is_connected() else None
            if not matched and local_catalog:
                matched = next((c for c in local_catalog if c.get("asin") == asin), None)
                
            if matched:
                logger.info(f"   ► TIER 2 MATCH (ASIN: {asin}) -> Canonical ID: {matched.get('id')}")
                return {
                    "canonical_product_id": matched.get("id"),
                    "match_tier": "tier2_asin",
                    "confidence_score": 1.0,
                    "canonical": matched,
                    "details": f"Exact ASIN match on {asin}"
                }

        # ---------------------------------------------------------------------
        # TIER 3: Brand + MPN Match
        # ---------------------------------------------------------------------
        if brand and mpn:
            matched = self.supabase.find_canonical_by_brand_mpn(brand, mpn) if self.supabase.is_connected() else None
            if not matched and local_catalog:
                matched = next((c for c in local_catalog if 
                                str(c.get("brand", "")).upper() == str(brand).upper() and 
                                str(c.get("mpn", c.get("model", ""))).upper() == str(mpn).upper()), None)
                                
            if matched:
                logger.info(f"   ► TIER 3 MATCH (Brand+MPN: {brand} / {mpn}) -> Canonical ID: {matched.get('id')}")
                return {
                    "canonical_product_id": matched.get("id"),
                    "match_tier": "tier3_brand_mpn",
                    "confidence_score": 0.98,
                    "canonical": matched,
                    "details": f"Exact Brand+MPN match on {brand} / {mpn}"
                }

        # ---------------------------------------------------------------------
        # TIER 4: Trigram Fuzzy Title & Brand Match
        # ---------------------------------------------------------------------
        candidates = []
        if self.supabase.is_connected():
            norm_t = normalize_title(title)
            candidates = self.supabase.find_canonical_by_trigram(norm_t, brand=brand) or []
        
        if local_catalog:
            # Merge local catalog candidates to ensure complete coverage in offline/mock testing
            existing_ids = {c.get("id") for c in candidates if c.get("id")}
            for lc in local_catalog:
                if lc.get("id") not in existing_ids:
                    candidates.append(lc)

        best_match: Optional[Dict[str, Any]] = None
        best_score: float = 0.0

        for candidate in candidates:
            cand_title = candidate.get("title", "")
            cand_brand = candidate.get("brand", "")
            
            # Skip if brands are explicitly different
            if brand and cand_brand and brand.lower() not in cand_brand.lower() and cand_brand.lower() not in brand.lower():
                continue

            score = calculate_trigram_similarity(title, cand_title)
            if score > best_score:
                best_score = score
                best_match = candidate

        # Decision based on similarity thresholds
        if best_match and best_score >= self.auto_link_threshold:
            logger.info(f"   ► TIER 4 MATCH (Trigram Score: {best_score*100:.1f}%) -> Canonical ID: {best_match.get('id')}")
            return {
                "canonical_product_id": best_match.get("id"),
                "match_tier": "tier4_trigram",
                "confidence_score": round(best_score, 4),
                "canonical": best_match,
                "details": f"Trigram title similarity {best_score*100:.1f}% >= threshold {self.auto_link_threshold*100:.0f}%"
            }
        elif best_match and best_score >= self.gray_area_threshold:
            logger.warning(f"   ► GRAY AREA MATCH ({best_score*100:.1f}%) -> Queuing in 'unmatched_queue'")
            self.supabase.insert_unmatched_queue(
                raw_offer=raw_offer,
                suggested_canonical_id=best_match.get("id"),
                similarity_score=best_score
            )
            return {
                "canonical_product_id": None,
                "match_tier": "queued_review",
                "confidence_score": round(best_score, 4),
                "suggested_canonical_id": best_match.get("id"),
                "details": f"Gray area similarity {best_score*100:.1f}% routed to human-in-the-loop unmatched_queue"
            }

        # ---------------------------------------------------------------------
        # TIER 5: No Match Found -> Create New Canonical Product
        # ---------------------------------------------------------------------
        logger.info(f"   ► TIER 5: No existing match found (Best Score: {best_score*100:.1f}%). Creating new canonical product.")
        new_canonical_payload = {
            "niche": niche,
            "title": title,
            "brand": brand,
            "model": mpn or raw_offer.get("model"),
            "mpn": mpn,
            "asin": asin,
            "normalized_title": normalize_title(title),
            "gtin_upc_ean": gtin,
            "category": category,
            "image_url": raw_offer.get("image_url")
        }

        res = self.supabase.upsert_canonical_product(new_canonical_payload)
        new_id = res.get("data", {}).get("id") or f"mock-canonical-{hash(title) & 0xffffffff:x}"

        return {
            "canonical_product_id": new_id,
            "match_tier": "tier5_new_canonical",
            "confidence_score": 0.0,
            "canonical": new_canonical_payload,
            "details": f"Created new canonical product record with ID {new_id}"
        }
