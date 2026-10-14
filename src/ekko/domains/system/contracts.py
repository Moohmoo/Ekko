"""System domain IPC contracts for configuration, sources, and environment status."""

from pydantic import BaseModel, Field


class UserContextConfig(BaseModel):
    """User-specific settings and preferences decoupled from source code."""

    user_name: str | None = Field(default=None, description="Preferred user display name")
    preferred_language: str = Field(default="fr", description="Primary interaction language")
    preferences: list[str] = Field(
        default_factory=list,
        description="User habits, preferences, and environment facts",
    )
    custom_instructions: str | None = Field(
        default=None,
        description="Specific instructions provided by the user",
    )


class SourceConfig(BaseModel):
    """Configuration model for an individual declarative ingestion source."""

    id: str
    type: str
    url: str | None = None
    path: str | None = None
    interval: str = "30m"
    max_items: int = 20
    params: dict[str, str | int | float | bool] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    json_items_path: str | None = None
    field_mapping: dict[str, str] = Field(default_factory=dict)


class SourcesCatalogConfig(BaseModel):
    """Collection catalog of all active ingestion sources."""

    sources: list[SourceConfig] = Field(default_factory=list)


class SystemStatusInfo(BaseModel):
    """System runtime environment information."""

    llm_provider: str
    active_model: str
    sqlite_db_path: str
    ipc_socket_path: str
    status: str = "online"


class SystemSettingsResponse(BaseModel):
    """Contract payload returned by get_system_settings endpoint."""

    status: str = "ok"
    user_context: UserContextConfig
    sources: SourcesCatalogConfig
    system: SystemStatusInfo
