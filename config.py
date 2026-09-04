import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    ZENROWS_API_KEY = os.getenv("ZENROWS_API_KEY", "")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN", "")
    DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD", "")
    PRODUCT_PROVIDER = os.getenv("PRODUCT_PROVIDER", "hybrid").lower()
    ALLOW_DEMO_DATA = os.getenv("ALLOW_DEMO_DATA", "false").lower() == "true"
    # Read-only migration source. Production product writes never use Strapi.
    LEGACY_STRAPI_URL = os.getenv("LEGACY_STRAPI_URL", "https://cms.fxnstudio.com")
    LEGACY_STRAPI_API_TOKEN = os.getenv("LEGACY_STRAPI_API_TOKEN", "")

    # Affiliate Monetization Tags
    AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "nxtbargains-20")
    EBAY_AFFILIATE_CAMPAIGN_ID = os.getenv("EBAY_AFFILIATE_CAMPAIGN_ID", "5338000000")
    WALMART_AFFILIATE_ID = os.getenv("WALMART_AFFILIATE_ID", "")
    BESTBUY_AFFILIATE_ID = os.getenv("BESTBUY_AFFILIATE_ID", "")

    DEFAULT_JS_RENDER = os.getenv("DEFAULT_JS_RENDER", "false").lower() == "true"
    DEFAULT_PREMIUM_PROXY = os.getenv("DEFAULT_PREMIUM_PROXY", "false").lower() == "true"
    DEFAULT_ANTIBOT = os.getenv("DEFAULT_ANTIBOT", "true").lower() == "true"

    @classmethod
    def validate(cls):
        """Validate shared persistence configuration only."""
        missing = []
        if not cls.SUPABASE_URL or cls.SUPABASE_URL == "https://your-project-id.supabase.co":
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_KEY or cls.SUPABASE_KEY == "your_supabase_anon_or_service_role_key_here":
            missing.append("SUPABASE_KEY")
        
        return missing

    @classmethod
    def validate_provider(cls, provider: str):
        provider = provider.lower()
        if provider not in {"zenrows", "dataforseo", "hybrid"}:
            return [f"Unsupported provider: {provider}"]
        missing = cls.validate()
        if provider in {"zenrows", "hybrid"}:
            if not cls.ZENROWS_API_KEY or cls.ZENROWS_API_KEY == "your_zenrows_api_key_here":
                missing.append("ZENROWS_API_KEY")
        if provider in {"dataforseo", "hybrid"}:
            if not cls.DATAFORSEO_LOGIN or cls.DATAFORSEO_LOGIN == "your_dataforseo_login_email":
                missing.append("DATAFORSEO_LOGIN")
            if not cls.DATAFORSEO_PASSWORD or cls.DATAFORSEO_PASSWORD == "your_dataforseo_api_password":
                missing.append("DATAFORSEO_PASSWORD")
        return sorted(set(missing))
