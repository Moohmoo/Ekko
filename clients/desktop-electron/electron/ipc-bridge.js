import net from 'node:net';
var DEFAULT_SOCKET_PATH = '/tmp/ekko.sock';
/**
 * Send single request to the Ekko UNIX domain socket and await single response.
 */
export function sendJsonRpc(method, params, socketPath) {
    if (params === void 0) { params = {}; }
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    return new Promise(function (resolve, reject) {
        var client = net.createConnection(socketPath);
        var payload = JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: Date.now(),
        }) + '\n';
        var buffer = '';
        client.on('connect', function () {
            client.write(payload);
        });
        client.on('data', function (data) {
            buffer += data.toString();
            if (buffer.includes('\n')) {
                var line = buffer.split('\n')[0];
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
        client.on('error', function () {
            reject(new Error('DAEMON_OFFLINE'));
        });
    });
}
/**
 * Stream prompt execution over UNIX domain socket, invoking chunk and completion callbacks.
 */
export function streamPrompt(prompt, onChunk, onComplete, onError, socketPath) {
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    var client = net.createConnection(socketPath);
    var fullText = '';
    var buffer = '';
    var payload = JSON.stringify({
        jsonrpc: '2.0',
        method: 'submit_prompt',
        params: { prompt: prompt, session_id: 'desktop_electron' },
        id: Date.now(),
    }) + '\n';
    client.on('connect', function () {
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
                // ignore parse fragment
            }
        }
    });
    client.on('end', function () {
        if (fullText) {
            onComplete(fullText);
        }
    });
    client.on('error', function () {
        onError('DAEMON_OFFLINE');
    });
}
