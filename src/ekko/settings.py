"""12-factor application settings loaded from environment and .env."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration keeping infrastructure concerns decoupled."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = Field(default="gemini")
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash")

    local_llm_url: str = Field(default="http://localhost:11434")
    local_llm_model: str = Field(default="llama3.1")

    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    log_level: str = Field(default="INFO")
    log_file: str | None = Field(default="logs/ekko.log")
    config_dir: str = Field(default="config")
    sqlite_db_path: str = Field(default="data/ekko.db")
    ipc_socket_path: str = Field(default="/tmp/ekko.sock")

    @property
    def active_model(self) -> str:
        """Return the active model identifier based on selected provider."""
        return self.local_llm_model if self.llm_provider == "local" else self.gemini_model



