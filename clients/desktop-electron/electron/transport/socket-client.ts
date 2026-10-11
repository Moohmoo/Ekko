import net from 'node:net';

export const DEFAULT_SOCKET_PATH = '/tmp/ekko.sock';

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
 * Send a single JSON-RPC 2.0 request over the UNIX domain socket.
 * Accumulates buffer until newline and logs operations with [IPC:REQ], [IPC:RES], [IPC:ERR].
 */
export function sendJsonRpc<T = unknown>(
  method: string,
  params: Record<string, unknown> = {},
  socketPath: string = DEFAULT_SOCKET_PATH
): Promise<T> {
  const isPing = method === 'ping';

  return new Promise((resolve, reject) => {
    if (!isPing) {
      console.log(`[IPC:REQ] Connecting to ${socketPath} -> ${method}`);
    }
    const client = net.createConnection(socketPath);
    const payload = JSON.stringify({
      jsonrpc: '2.0',
      method,
      params,
      id: Date.now(),
    }) + '\n';

    let buffer = '';

    // Contextual timeouts: 5s for ping, 30s for business actions
    const timeoutMs = isPing ? 5000 : 30000;
    client.setTimeout(timeoutMs);

    client.on('connect', () => {
      if (!isPing) {
        console.log(`[IPC:REQ] Connected. Writing payload for ${method}`);
      }
      client.write(payload);
    });

    client.on('data', (chunk) => {
      buffer += chunk.toString();
      if (buffer.includes('\n')) {
        const line = buffer.split('\n')[0];
        if (!isPing) {
          console.log(`[IPC:RES] ${method} returned: ${line.slice(0, 120)}`);
        }
        client.end();
        try {
          const parsed = JSON.parse(line) as JSONRPCResponse<T>;
          if (parsed.error) {
            console.error(`[IPC:ERR] JSON-RPC Error in ${method}:`, parsed.error.message);
            reject(new Error(parsed.error.message));
          } else {
            resolve(parsed.result as T);
          }
        } catch (err) {
          console.error(`[IPC:ERR] Parse error in ${method}:`, err);
          reject(err);
        }
      }
    });

    client.on('timeout', () => {
      console.error(`[IPC:ERR] Timeout (${timeoutMs}ms) waiting for ${method}`);
      client.destroy();
      reject(new Error('TIMEOUT'));
    });

    client.on('error', (err) => {
      if (!isPing) {
        console.error(`[IPC:ERR] Socket connection error for ${method}:`, err.message);
      }
      reject(new Error('DAEMON_OFFLINE'));
    });
  });
}

/**
 * Stream prompt execution over UNIX domain socket line-by-line (NDJSON EngineEvents).
 */
export function streamPrompt(
  prompt: string,
  onChunk: (chunk: string) => void,
  onComplete: (fullText: string) => void,
  onError: (error: string) => void,
  socketPath: string = DEFAULT_SOCKET_PATH
): void {
  console.log(`[IPC:REQ] streamPrompt started on ${socketPath}`);
  const client = net.createConnection(socketPath);
  let fullText = '';
  let buffer = '';

  // Streaming timeout: 120s safety margin for multi-turn ReAct
  client.setTimeout(120000);

  const payload = JSON.stringify({
    jsonrpc: '2.0',
    method: 'submit_prompt',
    params: { prompt, session_id: 'desktop_electron' },
    id: Date.now(),
  }) + '\n';

  client.on('connect', () => {
    console.log('[IPC:REQ] Connected for streamPrompt, transmitting payload');
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
          console.error('[IPC:ERR] Engine reported error:', evt.error.message);
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
          console.log(`[IPC:RES] streamPrompt completed (${finalAns.length} chars)`);
          onComplete(finalAns);
          client.end();
          return;
        } else if (type === 'engine_error' || type === 'EngineError') {
          console.error('[IPC:ERR] EngineError:', evt.message);
          onError(evt.message || 'Erreur moteur');
          client.end();
          return;
        }
      } catch {
        // Line was fragmented, will be completed on next chunk
      }
    }
  });

  client.on('end', () => {
    if (fullText) {
      onComplete(fullText);
    }
  });

  client.on('timeout', () => {
    console.warn('[IPC:ERR] Stream prompt timeout (60s)');
    client.destroy();
    onError('TIMEOUT');
  });

  client.on('error', (err) => {
    console.warn('[IPC:ERR] Stream prompt socket error:', err.message);
    onError('DAEMON_OFFLINE');
  });
}
