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
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
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
    sendChatMessage: function (prompt, history) { return ipcRenderer.invoke('chat:send_message', { prompt: prompt, history: history }); },
    onChatToken: function (callback) {
        var handler = function (_event, token) { return callback(token); };
        ipcRenderer.on('chat:token', handler);
        return function () {
            ipcRenderer.removeListener('chat:token', handler);
        };
    },
    onChatDone: function (callback) {
        var handler = function () { return callback(); };
        ipcRenderer.on('chat:done', handler);
        return function () {
            ipcRenderer.removeListener('chat:done', handler);
        };
    },
    onChatError: function (callback) {
        var handler = function (_event, err) { return callback(err); };
        ipcRenderer.on('chat:error', handler);
        return function () {
            ipcRenderer.removeListener('chat:error', handler);
        };
    },
    testMascotEmotion: function (emotion) {
        ipcRenderer.send('dev:test_mascot_emotion', emotion);
    },
    cycleAllEmotions: function () { return __awaiter(void 0, void 0, void 0, function () {
        var emotions, _i, emotions_1, em;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    emotions = ['welcome', 'idle', 'hover_drop', 'ingesting', 'ready', 'alert', 'error'];
                    console.log('%c[Ekko Test Bench] Début du cycle des 7 micro-émotions de la mascotte...', 'color: #38bdf8; font-weight: bold;');
                    _i = 0, emotions_1 = emotions;
                    _a.label = 1;
                case 1:
                    if (!(_i < emotions_1.length)) return [3 /*break*/, 4];
                    em = emotions_1[_i];
                    console.log("%c[Ekko Test Bench] Emotion en test : %c".concat(em, "%c (2.5s)"), 'color: #94a3b8;', 'color: #22c55e; font-weight: bold;', 'color: #94a3b8;');
                    ipcRenderer.send('dev:test_mascot_emotion', em);
                    return [4 /*yield*/, new Promise(function (res) { return setTimeout(res, 2500); })];
                case 2:
                    _a.sent();
                    _a.label = 3;
                case 3:
                    _i++;
                    return [3 /*break*/, 1];
                case 4:
                    console.log('%c[Ekko Test Bench] Fin du cycle. Retour au mode nominal automatique.', 'color: #38bdf8; font-weight: bold;');
                    ipcRenderer.send('dev:test_mascot_emotion', null);
                    return [2 /*return*/];
            }
        });
    }); },
    onTestMascotEmotion: function (callback) {
        var handler = function (_event, emotion) { return callback(emotion); };
        ipcRenderer.on('dev:set_mascot_emotion', handler);
        return function () {
            ipcRenderer.removeListener('dev:set_mascot_emotion', handler);
        };
    },
};
contextBridge.exposeInMainWorld('ekkoAPI', api);
