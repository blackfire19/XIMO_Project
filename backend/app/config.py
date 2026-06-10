from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    UPLOAD_DIR: str = "./uploads"
    COOKIE_SECURE: bool = False  # 生产环境 HTTPS 时在 .env 设置为 True

    class Config:
        env_file = ".env"


settings = Settings()
