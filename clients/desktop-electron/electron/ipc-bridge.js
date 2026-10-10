import net from 'node:net';
var DEFAULT_SOCKET_PATH = '/tmp/ekko.sock';
/**
 * Send single request to the Ekko UNIX domain socket with robust buffering, timeout, and logging.
 */
export function sendJsonRpc(method, params, socketPath) {
    if (params === void 0) { params = {}; }
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    return new Promise(function (resolve, reject) {
        console.log("[IPC] Connecting to ".concat(socketPath, " for method '").concat(method, "'..."));
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
            console.log("[IPC] Connected to socket! Sending request: ".concat(method));
            client.write(payload);
        });
        client.on('data', function (chunk) {
            buffer += chunk.toString();
            if (buffer.includes('\n')) {
                var line = buffer.split('\n')[0];
                console.log("[IPC] Received response line for ".concat(method, ": ").concat(line.slice(0, 100), "..."));
                client.end();
                try {
                    var parsed = JSON.parse(line);
                    if (parsed.error) {
                        reject(new Error(parsed.error.message));
                    }
                    else {
                        resolve(parsed.result);
                    }
                }
                catch (err) {
                    reject(err);
                }
            }
        });
        client.on('timeout', function () {
            console.warn("[IPC] Timeout (3s) waiting for socket response to '".concat(method, "'"));
            client.destroy();
            reject(new Error('TIMEOUT'));
        });
        client.on('error', function (err) {
            console.warn("[IPC] Socket error for '".concat(method, "':"), err.message);
            reject(new Error('DAEMON_OFFLINE'));
        });
    });
}
/**
 * Stream prompt execution over UNIX domain socket, invoking chunk and completion callbacks.
 */
export function streamPrompt(prompt, onChunk, onComplete, onError, socketPath) {
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    console.log("[IPC] Streaming prompt to ".concat(socketPath, "..."));
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
        console.log('[IPC] Connected for streamPrompt, writing payload');
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
                    onComplete(finalAns);
                    client.end();
                    return;
                }
                else if (type === 'engine_error' || type === 'EngineError') {
                    onError(evt.message || 'Erreur moteur');
                    client.end();
                    return;
                }
            }
            catch (_a) {
                // partial line
            }
        }
    });
    client.on('end', function () {
        console.log('[IPC] Stream completed, total length:', fullText.length);
        if (fullText) {
            onComplete(fullText);
        }
    });
    client.on('timeout', function () {
        console.warn('[IPC] Stream timeout');
        client.destroy();
        onError('TIMEOUT');
    });
    client.on('error', function (err) {
        console.warn('[IPC] Stream socket error:', err.message);
        onError('DAEMON_OFFLINE');
    });
}
