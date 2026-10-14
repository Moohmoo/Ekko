"""System domain IPC contracts for configuration, sources, and environment status."""

from pydantic import BaseModel, ConfigDict, Field


class UserContextConfig(BaseModel):
    """User-specific settings and radar topics decoupled from source code."""

    model_config = ConfigDict(populate_by_name=True)

    language: str = Field(
        default="fr",
        validation_alias="preferred_language",
        description="Primary interaction and distillation language",
    )
    topics: list[str] = Field(
        default_factory=list,
        validation_alias="preferences",
        description="Priority topics and domains of interest for radar and distillation",
    )
    user_name: str | None = Field(default=None, description="Legacy optional display name (deprecated)")
    custom_instructions: str | None = Field(default=None, description="Legacy optional instructions (deprecated)")

    @property
    def preferred_language(self) -> str:
        return self.language

    @property
    def preferences(self) -> list[str]:
        return self.topics

    def model_dump(self, *args: object, **kwargs: object) -> dict[str, object]:
        data = super().model_dump(*args, **kwargs)
        if "language" in data and "preferred_language" not in data:
            data["preferred_language"] = data["language"]
        if "topics" in data and "preferences" not in data:
            data["preferences"] = data["topics"]
        return data


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
