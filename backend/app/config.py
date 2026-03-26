import json
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "dodge_ai_2024"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    data_dir: str = "data/raw"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8501",
        "http://localhost:8502",
        "*",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
