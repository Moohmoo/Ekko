"""Integration test verifying end-to-end daemon lifecycle, IPC responsiveness, and graceful shutdown."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from ekko.daemon.ipc_client import IPCClient
from ekko.daemon.service import main, parse_args, run_daemon
from ekko.core.settings import Settings


@pytest.mark.asyncio
async def test_daemon_lifecycle_start_ping_and_graceful_stop(tmp_path: Path) -> None:
    """Ensure run_daemon starts services, answers IPC ping, and cleans up on stop_event."""
    sock_path = tmp_path / "test_lifecycle.sock"
    db_file = tmp_path / "test_lifecycle.db"
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        sqlite_db_path=str(db_file),
        config_dir=str(config_dir),
        ipc_socket_path=str(sock_path),
        _env_file=None,
    )

    stop_event = asyncio.Event()

    daemon_task = asyncio.create_task(
        run_daemon(
            settings=settings,
            socket_path=sock_path,
            poll_interval=1.0,
            stop_event=stop_event,
        )
    )

    # Wait briefly for socket creation
    for _ in range(50):
        if sock_path.exists():
            break
        await asyncio.sleep(0.05)

    assert sock_path.exists(), "IPC socket file was not created by daemon"

    # Connect client and verify IPC communication
    async with IPCClient(socket_path=sock_path) as client:
        ping_resp = await client.ping()
        assert ping_resp.get("status") == "ok"

        inbox_resp = await client.scan_inbox(limit=5)
        assert isinstance(inbox_resp, list)

    # Signal shutdown
    stop_event.set()
    await daemon_task

    # Verify graceful cleanup
    assert not sock_path.exists(), "IPC socket file must be deleted upon graceful stop"


def test_cli_daemon_subcommand_parsing() -> None:
    """Ensure CLI parses daemon subcommand and options accurately."""
    args = parse_args(["daemon", "--interval", "30.0"])
    assert args.command == "daemon"
    assert args.interval == 30.0


def test_cli_main_dispatches_daemon_command() -> None:
    """Ensure main() delegates to run_daemon when daemon command is supplied."""
    with patch("ekko.daemon.service.run_daemon", new_callable=AsyncMock) as mock_daemon:
        with patch("sys.argv", ["ekko", "daemon", "--interval", "15.0"]):
            main()
            mock_daemon.assert_awaited_once_with(poll_interval=15.0)
