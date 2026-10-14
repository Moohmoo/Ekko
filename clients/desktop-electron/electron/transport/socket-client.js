import net from 'node:net';
export var DEFAULT_SOCKET_PATH = '/tmp/ekko.sock';
/**
 * Send a single JSON-RPC 2.0 request over the UNIX domain socket.
 * Accumulates buffer until newline and logs operations with [IPC:REQ], [IPC:RES], [IPC:ERR].
 */
export function sendJsonRpc(method, params, socketPath) {
    if (params === void 0) { params = {}; }
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    var isSilent = method === 'ping' || method === 'scan_notes' || method === 'get_pending_signals';
    return new Promise(function (resolve, reject) {
        if (!isSilent) {
            console.log("[IPC:REQ] Connecting to ".concat(socketPath, " -> ").concat(method));
        }
        var client = net.createConnection(socketPath);
        var payload = JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: Date.now(),
        }) + '\n';
        var buffer = '';
        // Contextual timeouts: 5s for ping, 30s for business actions
        var timeoutMs = method === 'ping' ? 5000 : 30000;
        client.setTimeout(timeoutMs);
        client.on('connect', function () {
            if (!isSilent) {
                console.log("[IPC:REQ] Connected. Writing payload for ".concat(method));
            }
            client.write(payload);
        });
        client.on('data', function (chunk) {
            buffer += chunk.toString();
            if (buffer.includes('\n')) {
                var line = buffer.split('\n')[0];
                if (!isSilent) {
                    console.log("[IPC:RES] ".concat(method, " returned: ").concat(line.slice(0, 120)));
                }
                client.end();
                try {
                    var parsed = JSON.parse(line);
                    if (parsed.error) {
                        console.error("[IPC:ERR] JSON-RPC Error in ".concat(method, ":"), parsed.error.message);
                        reject(new Error(parsed.error.message));
                    }
                    else {
                        resolve(parsed.result);
                    }
                }
                catch (err) {
                    console.error("[IPC:ERR] Parse error in ".concat(method, ":"), err);
                    reject(err);
                }
            }
        });
        client.on('timeout', function () {
            console.error("[IPC:ERR] Timeout (".concat(timeoutMs, "ms) waiting for ").concat(method));
            client.destroy();
            reject(new Error('TIMEOUT'));
        });
        client.on('error', function (err) {
            if (method !== 'ping') {
                console.error("[IPC:ERR] Socket connection error for ".concat(method, ":"), err.message);
            }
            reject(new Error('DAEMON_OFFLINE'));
        });
    });
}
/**
 * Stream prompt execution over UNIX domain socket line-by-line (NDJSON EngineEvents).
 */
export function streamPrompt(prompt, onChunk, onComplete, onError, onToolEvent, sessionId, socketPath) {
    if (sessionId === void 0) { sessionId = 'desktop_electron'; }
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    console.log("[IPC:REQ] streamPrompt started on ".concat(socketPath, " (session: ").concat(sessionId, ")"));
    var client = net.createConnection(socketPath);
    var fullText = '';
    var buffer = '';
    // Streaming timeout: 120s safety margin for multi-turn ReAct
    client.setTimeout(120000);
    var payload = JSON.stringify({
        jsonrpc: '2.0',
        method: 'submit_prompt',
        params: { prompt: prompt, session_id: sessionId || 'desktop_electron' },
        id: Date.now(),
    }) + '\n';
    client.on('connect', function () {
        console.log('[IPC:REQ] Connected for streamPrompt, transmitting payload');
        client.write(payload);
    });
    client.on('data', function (data) {
        buffer += data.toString();
        var lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (var _i = 0, lines_1 = lines; _i < lines_1.length; _i++) {
            var line = lines_1[_i];
            if (!line.trim())
                continue;
            try {
                var evt = JSON.parse(line);
                if (evt.error) {
                    console.error('[IPC:ERR] Engine reported error:', evt.error.message);
                    onError(evt.error.message || 'Moteur indisponible');
                    client.end();
                    return;
                }
                var type = evt.type;
                if (type === 'token_chunk') {
                    fullText += evt.delta || '';
                    onChunk(evt.delta || '');
                }
                else if (type === 'tool_call_started' || type === 'ToolCallStarted') {
                    onToolEvent === null || onToolEvent === void 0 ? void 0 : onToolEvent({
                        type: 'tool_call_started',
                        tool_call_id: evt.tool_call_id,
                        tool_name: evt.tool_name,
                        arguments: evt.arguments,
                    });
                }
                else if (type === 'tool_call_completed' || type === 'ToolCallCompleted') {
                    onToolEvent === null || onToolEvent === void 0 ? void 0 : onToolEvent({
                        type: 'tool_call_completed',
                        tool_call_id: evt.tool_call_id,
                        tool_name: evt.tool_name,
                        success: evt.success,
                        summary: evt.summary,
                        duration_ms: evt.duration_ms,
                    });
                }
                else if (type === 'turn_completed' || type === 'TurnCompleted') {
                    var finalAns = evt.response || fullText;
                    console.log("[IPC:RES] streamPrompt completed (".concat(finalAns.length, " chars)"));
                    onComplete(finalAns);
                    client.end();
                    return;
                }
                else if (type === 'engine_error' || type === 'EngineError') {
                    console.error('[IPC:ERR] EngineError:', evt.message);
                    onError(evt.message || 'Erreur moteur');
                    client.end();
                    return;
                }
            }
            catch (_a) {
                // Line was fragmented, will be completed on next chunk
            }
        }
    });
    client.on('end', function () {
        if (fullText) {
            onComplete(fullText);
        }
    });
    client.on('timeout', function () {
        console.warn('[IPC:ERR] Stream prompt timeout (60s)');
        client.destroy();
        onError('TIMEOUT');
    });
    client.on('error', function (err) {
        console.warn('[IPC:ERR] Stream prompt socket error:', err.message);
        onError('DAEMON_OFFLINE');
    });
}
/**
 * Long-lived connection listening for server-pushed JSON-RPC notifications (e.g. daemon:note_created).
 * Features automatic silent reconnection with exponential backoff if daemon restarts.
 */
export function subscribeDaemonEvents(onEvent, socketPath) {
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    var isClosed = false;
    var client = null;
    var reconnectTimer = null;
    var buffer = '';
    var connect = function () {
        if (isClosed)
            return;
        client = net.createConnection(socketPath);
        client.on('connect', function () {
            console.log("[IPC:EVENT] Connected to ".concat(socketPath, " for daemon push notifications"));
        });
        client.on('data', function (chunk) {
            buffer += chunk.toString();
            var lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (var _i = 0, lines_2 = lines; _i < lines_2.length; _i++) {
                var line = lines_2[_i];
                if (!line.trim())
                    continue;
                try {
                    var parsed = JSON.parse(line);
                    if (parsed && typeof parsed.method === 'string') {
                        onEvent(parsed.method, parsed.params || {});
                    }
                }
                catch (_a) {
                    // Line fragmentation or malformed JSON
                }
            }
        });
        client.on('error', function () {
            // Suppress noisy logs while daemon is restarting
        });
        client.on('close', function () {
            client = null;
            if (!isClosed) {
                reconnectTimer = setTimeout(connect, 2000);
            }
        });
    };
    connect();
    return function () {
        isClosed = true;
        if (reconnectTimer)
            clearTimeout(reconnectTimer);
        if (client) {
            client.destroy();
            client = null;
        }
    };
}
