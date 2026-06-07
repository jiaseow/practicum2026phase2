from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    database_url: str = Field(default="", alias="DATABASE_URL")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    whisper_model: str = Field(default="whisper-1", alias="WHISPER_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    agents_model: str = Field(default="gpt-5-nano", alias="AGENTS_MODEL")
    chunk_target_tokens: int = Field(default=300, alias="CHUNK_TARGET_TOKENS")
    chunk_overlap_tokens: int = Field(default=50, alias="CHUNK_OVERLAP_TOKENS")

    default_project_id: str = Field(default="", alias="DEFAULT_PROJECT_ID")
    default_repo_url: str = Field(default="", alias="DEFAULT_REPO_URL")
    default_video_path: str = Field(default="", alias="DEFAULT_VIDEO_PATH")
    default_transcript_path: str = Field(default="", alias="DEFAULT_TRANSCRIPT_PATH")
    default_readme_path: str = Field(default="", alias="DEFAULT_README_PATH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
