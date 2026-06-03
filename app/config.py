from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SalonOS"
    app_version: str = "1.0.0"
    debug: bool = True

    database_url: str = "sqlite:///./salonos.db"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-me-in-production-salonos-secret-2024"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    smtp_host: str = "smtp.sendgrid.net"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_email: str = "noreply@salonos.com"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone: str = ""

    s3_bucket: str = "salonos-assets"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    openai_api_key: str = ""


settings = Settings()
