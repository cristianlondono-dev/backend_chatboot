from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "Enterprise Chatbot"

    ENVIRONMENT: str = "development"

    DATABASE_URL: str

    ALEMBIC_DATABASE_URL: str

    OPENAI_API_KEY: str

    SUPABASE_URL: str = ""

    SUPABASE_SERVICE_KEY: str = ""

    SUPABASE_BUCKET_NAME: str = "documents"

    class Config:
        env_file = ".env"


settings = Settings()