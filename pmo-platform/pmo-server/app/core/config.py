"""应用配置。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "dev"
    DATABASE_URL: str = "sqlite:///./pmo.db"
    JWT_SECRET: str = "pmo-dev-secret-change-me-please-2026"
    JWT_EXPIRE_MIN: int = 480
    SECRECY_EXPORT_WATERMARK: str = "PMO 平台 机密文件 仅限内部使用"

    # 外部集成（P1 留空，不强制）
    LDAP_URI: str = ""
    WECOM_CORP_ID: str = ""
    WECOM_SECRET: str = ""
    WECOM_AGENT_ID: str = ""
    AI_PROXY_URL: str = ""
    AI_API_KEY_A: str = ""
    AI_API_KEY_B: str = ""


settings = Settings()
