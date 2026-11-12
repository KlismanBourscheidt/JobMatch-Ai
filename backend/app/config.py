from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    allowed_email: str
    frontend_origin: str
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
