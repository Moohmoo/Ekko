"""Daemon package providing scheduling, hardware confinement, and IPC server."""

from ekko.daemon.ipc_client import IPCClient, IPCClientError
from ekko.daemon.resources import ResourceManager
from ekko.daemon.scheduler import IngestionCoordinator
from ekko.daemon.server import DEFAULT_SOCKET_PATH, IPCServer
from ekko.daemon.service import run_daemon

__all__ = [
    "DEFAULT_SOCKET_PATH",
    "IPCClient",
    "IPCClientError",
    "IPCServer",
    "IngestionCoordinator",
    "ResourceManager",
    "run_daemon",
]
