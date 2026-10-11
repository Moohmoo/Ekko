import net from 'node:net';
export var DEFAULT_SOCKET_PATH = '/tmp/ekko.sock';
/**
 * Send a single JSON-RPC 2.0 request over the UNIX domain socket.
 * Accumulates buffer until newline and logs operations with [IPC:REQ], [IPC:RES], [IPC:ERR].
 */
export function sendJsonRpc(method, params, socketPath) {
    if (params === void 0) { params = {}; }
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    return new Promise(function (resolve, reject) {
        console.log("[IPC:REQ] Connecting to ".concat(socketPath, " -> ").concat(method));
        var client = net.createConnection(socketPath);
        var payload = JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: Date.now(),
        }) + '\n';
        var buffer = '';
        client.setTimeout(3000);
        client.on('connect', function () {
            console.log("[IPC:REQ] Connected. Writing payload for ".concat(method));
            client.write(payload);
        });
        client.on('data', function (chunk) {
            buffer += chunk.toString();
            if (buffer.includes('\n')) {
                var line = buffer.split('\n')[0];
                console.log("[IPC:RES] ".concat(method, " returned: ").concat(line.slice(0, 120)));
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
            console.warn("[IPC:ERR] Timeout (3000ms) waiting for ".concat(method));
            client.destroy();
            reject(new Error('TIMEOUT'));
        });
        client.on('error', function (err) {
            console.warn("[IPC:ERR] Socket connection error for ".concat(method, ":"), err.message);
            reject(new Error('DAEMON_OFFLINE'));
        });
    });
}
/**
 * Stream prompt execution over UNIX domain socket line-by-line (NDJSON EngineEvents).
 */
export function streamPrompt(prompt, onChunk, onComplete, onError, socketPath) {
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    console.log("[IPC:REQ] streamPrompt started on ".concat(socketPath));
    var client = net.createConnection(socketPath);
    var fullText = '';
    var buffer = '';
    client.setTimeout(60000);
    var payload = JSON.stringify({
        jsonrpc: '2.0',
        method: 'submit_prompt',
        params: { prompt: prompt, session_id: 'desktop_electron' },
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
