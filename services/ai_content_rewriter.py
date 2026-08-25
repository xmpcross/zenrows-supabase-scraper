import os
import re
import json
import logging
from typing import Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)

class AIContentRewriter:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.client = None

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Successfully initialized Gemini AI Content Rewriter client.")
            except ImportError:
                logger.warning("google-genai library not installed. Install with 'pip install google-genai'. Falling back to rule-based rewriter.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini AI client: {e}")
        else:
            logger.info("GEMINI_API_KEY not configured in .env. Operating in rule-based fallback rewriter mode.")

    def rewrite_product_content(
        self,
        title: str,
        brand: Optional[str] = None,
        category: str = "General",
        raw_description: Optional[str] = None,
        niche: str = "smart_home"
    ) -> Dict[str, Any]:
        """
        Rewrites product titles, short descriptions, and full descriptions
        into SEO-friendly, unique, high-converting content for comparison platforms.
        """
        # If Gemini Client is available, run LLM enrichment
        if self.client:
            try:
                prompt = f"""You are an expert e-commerce SEO copywriter for a top price comparison website.
Your task is to rewrite the product details below into clean, engaging, 100% unique SEO content.

Target Niche: {niche}
Product Category: {category}
Raw Title: {title}
Brand: {brand or 'Unknown'}
Raw Description / Features: {raw_description or 'N/A'}

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "seo_title": "Clean, engaging title (Max 70 chars, including Brand)",
  "short_description": "2-3 bullet points highlighting key benefits and value",
  "summary_description": "2 engaging sentences explaining why consumers compare and buy this product"
}}"""

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                
                text = response.text or ""
                json_match = re.search(r"\{[\s\S]*\}", text)
                if json_match:
                    res_json = json.loads(json_match.group(0))
                    logger.info(f"AI Rewriter Success for product: '{res_json.get('seo_title')}'")
                    short_desc_raw = res_json.get("short_description", title)
                    if isinstance(short_desc_raw, list):
                        short_desc = "\n".join(f"- {item}" for item in short_desc_raw)
                    else:
                        short_desc = str(short_desc_raw)

                    return {
                        "seo_title": res_json.get("seo_title", title),
                        "short_description": short_desc,
                        "description": res_json.get("summary_description", title),
                        "is_ai_generated": True
                    }
            except Exception as e:
                logger.warning(f"Gemini AI API call failed or rate limited: {e}. Falling back to rule-based rewriter.")

        # Rule-based fallback rewriter (Instant & Free)
        return self._rule_based_fallback(title, brand, category, raw_description, niche)

    def _rule_based_fallback(
        self,
        title: str,
        brand: Optional[str] = None,
        category: str = "General",
        raw_description: Optional[str] = None,
        niche: str = "smart_home"
    ) -> Dict[str, Any]:
        """Fast rule-based text cleaner for zero-latency fallback."""
        clean_t = " ".join(title.split()[:12])
        b = brand or (clean_t.split()[0] if clean_t.split() else "Top Brand")

        if niche == "beauty_skincare":
            short_desc = f"- Premium {category} by {b}.\n- Formulated for radiant, healthy, youthful-looking skin.\n- Compare prices across Sephora, Ulta, iHerb, Amazon & leading retailers."
            full_desc = f"Discover best price deals on {clean_t}. Compare multi-retailer offers and save on your daily skincare and wellness routine."
        else:
            short_desc = f"- Authentic {category} device by {b}.\n- High-performance smart connectivity and automated controls.\n- Compare prices across top authorized tech retailers."
            full_desc = f"Find the best prices and live deal comparisons for {clean_t}. Save on your smart home setup across verified stores."

        return {
            "seo_title": clean_t,
            "short_description": short_desc,
            "description": full_desc,
            "is_ai_generated": False
        }
