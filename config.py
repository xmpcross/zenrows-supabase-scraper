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

    DEFAULT_JS_RENDER = os.getenv("DEFAULT_JS_RENDER", "false").lower() == "true"
    DEFAULT_PREMIUM_PROXY = os.getenv("DEFAULT_PREMIUM_PROXY", "false").lower() == "true"
    DEFAULT_ANTIBOT = os.getenv("DEFAULT_ANTIBOT", "true").lower() == "true"

    @classmethod
    def validate(cls):
        missing = []
        if not cls.ZENROWS_API_KEY or cls.ZENROWS_API_KEY == "your_zenrows_api_key_here":
            missing.append("ZENROWS_API_KEY")
        if not cls.SUPABASE_URL or cls.SUPABASE_URL == "https://your-project-id.supabase.co":
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_KEY or cls.SUPABASE_KEY == "your_supabase_anon_or_service_role_key_here":
            missing.append("SUPABASE_KEY")
        
        return missing
