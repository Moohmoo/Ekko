"""Asynchronous terminal input handler with persistent history and slash commands."""

import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

CLI_STYLE = Style.from_dict({
    "bottom-toolbar": "noinherit #777777 bg:default",
    "prompt": "bold #00bcbc",
})
DEFAULT_PROMPT: AnyFormattedText = [("class:prompt", "> ")]


class CommandType(str, Enum):
    """Types of commands emitted from user terminal input."""

    USER_PROMPT = "user_prompt"
    CLEAR = "clear"
    EXIT = "exit"
    HELP = "help"
    INTERRUPT = "interrupt"


@dataclass(frozen=True)
class UserInput:
    """Structured representation of intercepted or standard user input."""

    command: CommandType
    text: str = ""


@dataclass(frozen=True)
class ToolbarMetadata:
    """Dynamic contextual metadata rendered in the bottom status toolbar."""

    model_name: str = ""
    session_id: str = ""
    workspace: str = ""


def parse_slash_command(text: str) -> CommandType | None:
    """Parse local control slash commands without sending them to the LLM."""
    clean = text.strip()
    if clean in ("/exit", "/quit", "/q"):
        return CommandType.EXIT
    if clean == "/clear":
        return CommandType.CLEAR
    if clean in ("/help", "?"):
        return CommandType.HELP
    return None


def format_bottom_toolbar(metadata: ToolbarMetadata) -> list[tuple[str, str]]:
    """Format dynamic status toolbar tokens for prompt_toolkit rendering."""
    left = "? for shortcuts"
    right_items = [
        item for item in (metadata.model_name, metadata.session_id, metadata.workspace) if item
    ]
    right = " • ".join(right_items)

    cols = shutil.get_terminal_size(fallback=(80, 24)).columns
    padding = max(2, cols - len(left) - len(right) - 4)
    summary = f" {left}{' ' * padding}{right} " if right else f" {left} "
    return [("class:bottom-toolbar", summary)]


class CLIInputHandler:
    """Manages asynchronous interactive input, persistent history, and signal handling."""

    def __init__(
        self,
        history_file: str | Path = "data/.ekko_history",
        metadata: ToolbarMetadata | None = None,
        session: Any = None,
    ) -> None:
        self.history_file = Path(history_file)
        self.metadata = metadata or ToolbarMetadata()
        self._ensure_history_directory()
        self.session = session or PromptSession(
            history=FileHistory(str(self.history_file)),
            bottom_toolbar=self._get_toolbar,
            style=CLI_STYLE,
        )

    def _ensure_history_directory(self) -> None:
        """Create parent directory for history storage if non-existent."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def _get_toolbar(self) -> AnyFormattedText:
        """Return formatted bottom toolbar representation."""
        return format_bottom_toolbar(self.metadata)

    def set_metadata(self, metadata: ToolbarMetadata) -> None:
        """Update dynamic runtime metadata displayed in the status toolbar."""
        self.metadata = metadata

    def _print_separator(self) -> None:
        """Print discreet dimmed separator line above prompt."""
        cols = min(shutil.get_terminal_size(fallback=(80, 24)).columns, 80)
        print(f"\033[90m{'─' * cols}\033[0m")

    async def get_input(self, prompt_text: AnyFormattedText | None = None) -> UserInput:
        """Prompt user asynchronously and handle interrupts or local slash commands."""
        self._print_separator()
        active_prompt = prompt_text if prompt_text is not None else DEFAULT_PROMPT
        try:
            raw_input = await self.session.prompt_async(active_prompt)
        except KeyboardInterrupt:
            return UserInput(command=CommandType.INTERRUPT, text="")
        except EOFError:
            return UserInput(command=CommandType.EXIT, text="")

        command = parse_slash_command(raw_input)
        if command is not None:
            return UserInput(command=command, text=raw_input.strip())

        return UserInput(command=CommandType.USER_PROMPT, text=raw_input.strip())
