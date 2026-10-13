var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
import { contextBridge, ipcRenderer, webUtils } from 'electron';
var api = {
    ping: function () { return ipcRenderer.invoke('daemon:ping'); },
    getNotes: function () { return ipcRenderer.invoke('daemon:get_notes'); },
    searchNotes: function (query, options) {
        return ipcRenderer.invoke('daemon:search_notes', __assign({ query: query }, options));
    },
    getPendingSignals: function () { return ipcRenderer.invoke('daemon:get_pending_signals'); },
    resolveSignal: function (signalId, action) {
        return ipcRenderer.invoke('daemon:resolve_signal', { signalId: signalId, action: action });
    },
    resolveAllPendingSignals: function (action) {
        return ipcRenderer.invoke('daemon:resolve_all_pending_signals', { action: action });
    },
    submitPrompt: function (prompt, sessionId) {
        return ipcRenderer.invoke('daemon:submit_prompt', prompt, sessionId);
    },
    getSystemSettings: function () { return ipcRenderer.invoke('daemon:get_system_settings'); },
    updateUserContext: function (context) {
        return ipcRenderer.invoke('daemon:update_user_context', context);
    },
    updateSources: function (sources) {
        return ipcRenderer.invoke('daemon:update_sources', sources);
    },
    ingestFile: function (filePath) { return ipcRenderer.invoke('daemon:ingest_file', filePath); },
    ingestUrl: function (url) { return ipcRenderer.invoke('daemon:ingest_url', url); },
    getDroppedFilePath: function (file) {
        try {
            var p = webUtils.getPathForFile(file);
            if (p)
                return p;
        }
        catch (_a) {
            // ignore webUtils error
        }
        try {
            var legacy = file.path;
            if (typeof legacy === 'string' && legacy) {
                return legacy;
            }
        }
        catch (_b) {
            // ignore legacy error
        }
        return '';
    },
    openExternal: function (url) { return ipcRenderer.invoke('shell:open_external', url); },
    closeWindow: function () { return ipcRenderer.invoke('window:close'); },
    resizeWindow: function (width, height) { return ipcRenderer.invoke('window:resize', { width: width, height: height }); },
    setTrayState: function (state) { return ipcRenderer.invoke('tray:set_state', state); },
    onPromptChunk: function (callback) {
        var handler = function (_event, chunk) { return callback(chunk); };
        ipcRenderer.on('daemon:prompt_chunk', handler);
        return function () {
            ipcRenderer.removeListener('daemon:prompt_chunk', handler);
        };
    },
    onToolEvent: function (callback) {
        var handler = function (_event, eventData) { return callback(eventData); };
        ipcRenderer.on('daemon:tool_event', handler);
        return function () {
            ipcRenderer.removeListener('daemon:tool_event', handler);
        };
    },
    onNoteCreated: function (callback) {
        var handler = function (_event, noteData) { return callback(noteData); };
        ipcRenderer.on('daemon:note_created', handler);
        return function () {
            ipcRenderer.removeListener('daemon:note_created', handler);
        };
    },
};
contextBridge.exposeInMainWorld('ekkoAPI', api);
