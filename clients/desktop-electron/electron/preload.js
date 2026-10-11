import { contextBridge, ipcRenderer, webUtils } from 'electron';
var api = {
    ping: function () { return ipcRenderer.invoke('daemon:ping'); },
    getNotes: function () { return ipcRenderer.invoke('daemon:get_notes'); },
    getPendingSignals: function () { return ipcRenderer.invoke('daemon:get_pending_signals'); },
    resolveSignal: function (signalId, action) {
        return ipcRenderer.invoke('daemon:resolve_signal', { signalId: signalId, action: action });
    },
    submitPrompt: function (prompt) { return ipcRenderer.invoke('daemon:submit_prompt', prompt); },
    ingestFile: function (filePath) { return ipcRenderer.invoke('daemon:ingest_file', filePath); },
    getDroppedFilePath: function (file) {
        try {
            return webUtils.getPathForFile(file);
        }
        catch (err) {
            console.error('[Preload] Échec webUtils.getPathForFile:', err);
            return '';
        }
    },
    closeWindow: function () { return ipcRenderer.invoke('window:close'); },
    resizeWindow: function (width, height) { return ipcRenderer.invoke('window:resize', { width: width, height: height }); },
    onPromptChunk: function (callback) {
        var handler = function (_event, chunk) { return callback(chunk); };
        ipcRenderer.on('daemon:prompt_chunk', handler);
        return function () {
            ipcRenderer.removeListener('daemon:prompt_chunk', handler);
        };
    },
};
contextBridge.exposeInMainWorld('ekkoAPI', api);
