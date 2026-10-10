import net from 'node:net';

const DEFAULT_SOCKET_PATH = '/tmp/ekko.sock';

export interface JSONRPCResponse<T = unknown> {
  jsonrpc: '2.0';
  result?: T;
  error?: {
    code: number;
    message: string;
  };
  id?: number | string;
}

/**
 * Send single request to the Ekko UNIX domain socket with robust buffering, timeout, and logging.
 */
export function sendJsonRpc<T = unknown>(
  method: string,
  params: Record<string, unknown> = {},
  socketPath: string = DEFAULT_SOCKET_PATH
): Promise<T> {
  return new Promise((resolve, reject) => {
    console.log(`[IPC] Connecting to ${socketPath} for method '${method}'...`);
    const client = net.createConnection(socketPath);
    const payload = JSON.stringify({
      jsonrpc: '2.0',
      method,
      params,
      id: Date.now(),
    }) + '\n';

    let buffer = '';

    client.setTimeout(3000);

    client.on('connect', () => {
      console.log(`[IPC] Connected to socket! Sending request: ${method}`);
      client.write(payload);
    });

    client.on('data', (chunk) => {
      buffer += chunk.toString();
      if (buffer.includes('\n')) {
        const line = buffer.split('\n')[0];
        console.log(`[IPC] Received response line for ${method}: ${line.slice(0, 100)}...`);
        client.end();
        try {
          const parsed = JSON.parse(line) as JSONRPCResponse<T>;
          if (parsed.error) {
            reject(new Error(parsed.error.message));
          } else {
            resolve(parsed.result as T);
          }
        } catch (err) {
          reject(err);
        }
      }
    });

    client.on('timeout', () => {
      console.warn(`[IPC] Timeout (3s) waiting for socket response to '${method}'`);
      client.destroy();
      reject(new Error('TIMEOUT'));
    });

    client.on('error', (err) => {
      console.warn(`[IPC] Socket error for '${method}':`, err.message);
      reject(new Error('DAEMON_OFFLINE'));
    });
  });
}

/**
 * Stream prompt execution over UNIX domain socket, invoking chunk and completion callbacks.
 */
export function streamPrompt(
  prompt: string,
  onChunk: (chunk: string) => void,
  onComplete: (fullText: string) => void,
  onError: (error: string) => void,
  socketPath: string = DEFAULT_SOCKET_PATH
): void {
  console.log(`[IPC] Streaming prompt to ${socketPath}...`);
  const client = net.createConnection(socketPath);
  let fullText = '';
  let buffer = '';

  client.setTimeout(60000);

  const payload = JSON.stringify({
    jsonrpc: '2.0',
    method: 'submit_prompt',
    params: { prompt, session_id: 'desktop_electron' },
    id: Date.now(),
  }) + '\n';

  client.on('connect', () => {
    console.log('[IPC] Connected for streamPrompt, writing payload');
    client.write(payload);
  });

  client.on('data', (data) => {
    buffer += data.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const evt = JSON.parse(line);
        if (evt.error) {
          onError(evt.error.message || 'Moteur indisponible');
          client.end();
          return;
        }

        const type = evt.type;
        if (type === 'token_chunk') {
          fullText += evt.delta || '';
          onChunk(evt.delta || '');
        } else if (type === 'turn_completed' || type === 'TurnCompleted') {
          const finalAns = evt.response || fullText;
          onComplete(finalAns);
          client.end();
          return;
        } else if (type === 'engine_error' || type === 'EngineError') {
          onError(evt.message || 'Erreur moteur');
          client.end();
          return;
        }
      } catch {
        // partial line
      }
    }
  });

  client.on('end', () => {
    console.log('[IPC] Stream completed, total length:', fullText.length);
    if (fullText) {
      onComplete(fullText);
    }
  });

  client.on('timeout', () => {
    console.warn('[IPC] Stream timeout');
    client.destroy();
    onError('TIMEOUT');
  });

  client.on('error', (err) => {
    console.warn('[IPC] Stream socket error:', err.message);
    onError('DAEMON_OFFLINE');
  });
}
