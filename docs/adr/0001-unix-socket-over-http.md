# ADR 0001: UNIX Domain Socket Over HTTP for Local IPC

## Status
Accepted

## Context
The Ekko desktop experience requires low-latency, bidirectional communication between the Electron frontend (Node.js/React) and the Python background daemon. Traditional approaches use an HTTP REST server or WebSockets on a local loopback port (`127.0.0.1:port`).

However, local HTTP servers introduce notable drawbacks for an ambient desktop utility:
1. **TCP Port Collisions**: Static ports clash with other developer tooling or instances. Dynamic ports require complex discovery files.
2. **Security Vulnerability**: Any unprivileged browser tab or local script running under the user session can probe and issue requests to `localhost:port`.
3. **Overhead**: Full TCP handshake and HTTP header parsing add latency to real-time drag-and-drop feedback and streaming token rendering.

## Decision
We utilize a local UNIX domain socket at `/tmp/ekko.sock` with JSON-RPC 2.0 framing and newline-delimited JSON (NDJSON) streaming.

## Consequences
### Positive
- **Sub-millisecond Latency**: Eliminates TCP stack overhead; streaming tokens and events arrive immediately.
- **File System Permissions**: Access is restricted strictly to the operating system user account owning the socket file.
- **Collision-Free**: No TCP port allocations or firewalls involved.
- **Connection Health**: Disconnections and socket unlinks provide immediate, definitive lifecycle events without polling TCP keep-alives.

### Negative
- **Platform Specificity**: Windows requires Named Pipes (`\\\\.\\pipe\\ekko`) instead of POSIX domain sockets. An abstraction layer is maintained in the socket transport.
