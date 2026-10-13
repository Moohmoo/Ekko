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
import { app, BrowserWindow, globalShortcut, ipcMain, Menu, screen, shell, Tray } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sendJsonRpc, streamPrompt, subscribeDaemonEvents } from './transport/socket-client';
import { ensureDaemonRunning, stopDaemonIfManaged } from './daemon-manager';
import fs from 'node:fs';
var __dirname = path.dirname(fileURLToPath(import.meta.url));
process.env.DIST = path.join(__dirname, '../dist');
process.env.VITE_PUBLIC = app.isPackaged
    ? process.env.DIST
    : path.join(__dirname, '../public');
// Hardware acceleration & GPU rasterization optimizations for Linux/Chromium
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
var win = null;
var tray = null;
var isQuitting = false;
var VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL'];
function getPreloadPath() {
    // 1. Production / compiled path (same directory as main.js)
    var prodPath = path.join(__dirname, 'preload.cjs');
    if (fs.existsSync(prodPath)) {
        console.log('[Main] Using production preload path:', prodPath);
        return prodPath;
    }
    // 2. Dev path relative to electron/ source directory
    var devPath = path.join(__dirname, '../dist-electron/preload.cjs');
    if (fs.existsSync(devPath)) {
        console.log('[Main] Using dev relative preload path:', devPath);
        return devPath;
    }
    // 3. Absolute project root fallback
    var fallbackPath = path.resolve(app.getAppPath(), 'dist-electron/preload.cjs');
    console.log('[Main] Using fallback preload path:', fallbackPath);
    return fallbackPath;
}
function getCenteredTopBounds(width, height) {
    var primaryDisplay = screen.getPrimaryDisplay();
    var _a = primaryDisplay.workArea, workX = _a.x, workY = _a.y, workWidth = _a.width;
    return {
        x: Math.round(workX + (workWidth - width) / 2),
        y: workY, // Anchored to top work area (under panel on Linux/GNOME, y=0 on Windows)
        width: width,
        height: height,
    };
}
function toggleWindow() {
    if (!win || win.isDestroyed())
        return;
    if (win.isVisible()) {
        win.hide();
    }
    else {
        // Re-verify centering in case display geometry changed while hidden
        var _a = win.getSize(), currentWidth = _a[0], currentHeight = _a[1];
        var bounds = getCenteredTopBounds(currentWidth, currentHeight);
        win.setPosition(bounds.x, bounds.y);
        win.show();
        win.focus();
    }
}
function getTrayIconPath(state) {
    var publicDir = process.env.VITE_PUBLIC || path.join(__dirname, '../public');
    switch (state) {
        case 'ingesting':
            return path.join(publicDir, 'assets/tray-ingest.png');
        case 'alert':
            return path.join(publicDir, 'assets/tray-alert.png');
        case 'offline':
            return path.join(publicDir, 'assets/tray-offline.png');
        case 'idle':
        default:
            return path.join(publicDir, 'assets/tray-idle.png');
    }
}
function updateTrayIcon(state) {
    if (!tray || tray.isDestroyed())
        return;
    var iconPath = getTrayIconPath(state);
    if (fs.existsSync(iconPath)) {
        tray.setImage(iconPath);
    }
}
function createTray() {
    var iconPath = getTrayIconPath('idle');
    tray = new Tray(iconPath);
    tray.setToolTip('Ekko - Ambient Cognitive Buffer');
    var contextMenu = Menu.buildFromTemplate([
        {
            label: 'Afficher / Masquer Ekko',
            click: function () { return toggleWindow(); },
        },
        { type: 'separator' },
        {
            label: 'Quitter Ekko',
            click: function () {
                isQuitting = true;
                app.quit();
            },
        },
    ]);
    tray.setContextMenu(contextMenu);
    tray.on('click', function () { return toggleWindow(); });
}
function createWindow() {
    var windowWidth = 660; // 620px notch core + 2x20px transparent side margin for fillets
    var podHeight = 230;
    var initialBounds = getCenteredTopBounds(windowWidth, podHeight);
    var preloadPath = getPreloadPath();
    win = new BrowserWindow({
        width: initialBounds.width,
        height: initialBounds.height,
        x: initialBounds.x,
        y: initialBounds.y,
        resizable: false,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        hasShadow: true,
        backgroundColor: '#00000000',
        webPreferences: {
            preload: preloadPath,
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: false, // Essential to allow require('electron') in preload.cjs
        },
    });
    // Explicit preload-error listener for terminal observability
    win.webContents.on('preload-error', function (_event, preloadErrPath, error) {
        console.error('[Main:FATAL] Preload execution error in:', preloadErrPath);
        console.error(error);
    });
    // Native keyboard shortcuts: Escape to hide, Ctrl+Q to quit
    win.webContents.on('before-input-event', function (_event, input) {
        if (input.key === 'Escape') {
            win === null || win === void 0 ? void 0 : win.hide();
        }
        else if (input.control && input.key.toLowerCase() === 'q') {
            console.log('[Main] Ctrl+Q pressed, quitting application.');
            isQuitting = true;
            app.quit();
        }
    });
    // Hide rather than destroy window when user closes it
    win.on('close', function (event) {
        if (!isQuitting) {
            event.preventDefault();
            win === null || win === void 0 ? void 0 : win.hide();
        }
    });
    // Automatically open detached DevTools in dev mode (except in automated E2E tests)
    if (!process.env.E2E_TEST && (process.env.NODE_ENV !== 'production' || !app.isPackaged)) {
        win.webContents.openDevTools({ mode: 'detach' });
    }
    if (VITE_DEV_SERVER_URL) {
        console.log('[Main] Loading dev server URL:', VITE_DEV_SERVER_URL);
        win.loadURL(VITE_DEV_SERVER_URL);
    }
    else {
        console.log('[Main] Loading static index.html from:', process.env.DIST);
        win.loadFile(path.join(process.env.DIST, 'index.html'));
    }
}
// State tracker for daemon connectivity transitions
var isDaemonConnected = null;
// IPC Handlers
ipcMain.handle('daemon:ping', function () { return __awaiter(void 0, void 0, void 0, function () {
    var res, err_1;
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                _a.trys.push([0, 2, , 3]);
                return [4 /*yield*/, sendJsonRpc('ping')];
            case 1:
                res = _a.sent();
                if (isDaemonConnected !== true) {
                    isDaemonConnected = true;
                    console.log('[Daemon] Connecté au socket local /tmp/ekko.sock');
                }
                return [2 /*return*/, res];
            case 2:
                err_1 = _a.sent();
                if (isDaemonConnected !== false) {
                    isDaemonConnected = false;
                    console.warn('[Daemon:WARN] Liaison perdue avec le daemon');
                }
                return [2 /*return*/, null];
            case 3: return [2 /*return*/];
        }
    });
}); });
ipcMain.handle('daemon:get_notes', function () { return __awaiter(void 0, void 0, void 0, function () {
    var _e_1;
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                _a.trys.push([0, 2, , 4]);
                return [4 /*yield*/, sendJsonRpc('scan_notes', { limit: 50 })];
            case 1: return [2 /*return*/, _a.sent()];
            case 2:
                _e_1 = _a.sent();
                return [4 /*yield*/, sendJsonRpc('scan_inbox', { limit: 50 })];
            case 3: return [2 /*return*/, _a.sent()];
            case 4: return [2 /*return*/];
        }
    });
}); });
ipcMain.handle('daemon:search_notes', function (_event_1, _a) { return __awaiter(void 0, [_event_1, _a], void 0, function (_event, _b) {
    var query = _b.query, _c = _b.mode, mode = _c === void 0 ? 'hybrid' : _c, _d = _b.limit, limit = _d === void 0 ? 20 : _d;
    return __generator(this, function (_f) {
        switch (_f.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('search_notes', { query: query, mode: mode, limit: limit })];
            case 1: return [2 /*return*/, _f.sent()];
        }
    });
}); });
ipcMain.handle('shell:open_external', function (_event, url) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                if (!(url && (url.startsWith('http://') || url.startsWith('https://')))) return [3 /*break*/, 2];
                return [4 /*yield*/, shell.openExternal(url)];
            case 1:
                _a.sent();
                _a.label = 2;
            case 2: return [2 /*return*/];
        }
    });
}); });
var MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB
ipcMain.handle('daemon:ingest_file', function (_event, filePath) { return __awaiter(void 0, void 0, void 0, function () {
    var stats;
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                try {
                    stats = fs.statSync(filePath);
                    if (stats.size > MAX_FILE_SIZE_BYTES) {
                        return [2 /*return*/, {
                                status: 'rejected',
                                reason: 'file_too_large',
                                message: "Fichier trop volumineux (".concat(stats.size, " octets > ").concat(MAX_FILE_SIZE_BYTES, " octets max)."),
                                max_bytes: MAX_FILE_SIZE_BYTES,
                            }];
                    }
                }
                catch (err) {
                    // If stat fails, continue and let daemon return proper error
                }
                return [4 /*yield*/, sendJsonRpc('ingest_file', { file_path: filePath })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:ingest_url', function (_event, url) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('ingest_url', { url: url })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:get_pending_signals', function () { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('get_pending_signals', { limit: 20 })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:resolve_signal', function (_event_1, _a) { return __awaiter(void 0, [_event_1, _a], void 0, function (_event, _b) {
    var signalId = _b.signalId, action = _b.action;
    return __generator(this, function (_c) {
        switch (_c.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('resolve_signal', { signal_id: signalId, action: action })];
            case 1: return [2 /*return*/, _c.sent()];
        }
    });
}); });
ipcMain.handle('daemon:resolve_all_pending_signals', function (_event_1, _a) { return __awaiter(void 0, [_event_1, _a], void 0, function (_event, _b) {
    var action = _b.action;
    return __generator(this, function (_c) {
        switch (_c.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('resolve_all_pending_signals', { action: action })];
            case 1: return [2 /*return*/, _c.sent()];
        }
    });
}); });
ipcMain.handle('daemon:submit_prompt', function (event, prompt, sessionId) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, new Promise(function (resolve, reject) {
                    streamPrompt(prompt, function (chunk) {
                        event.sender.send('daemon:prompt_chunk', chunk);
                    }, function (full) {
                        resolve(full);
                    }, function (err) {
                        reject(new Error(err));
                    }, function (toolEvent) {
                        event.sender.send('daemon:tool_event', toolEvent);
                    }, sessionId || 'desktop_electron');
                })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('chat:send_message', function (event_1, _a) { return __awaiter(void 0, [event_1, _a], void 0, function (event, _b) {
    var prompt = _b.prompt;
    return __generator(this, function (_c) {
        switch (_c.label) {
            case 0: return [4 /*yield*/, new Promise(function (resolve, reject) {
                    streamPrompt(prompt, function (chunk) {
                        event.sender.send('chat:token', chunk);
                    }, function (full) {
                        event.sender.send('chat:done');
                        resolve(full);
                    }, function (err) {
                        event.sender.send('chat:error', err);
                        reject(new Error(err));
                    }, undefined, 'desktop_chat');
                })];
            case 1: return [2 /*return*/, _c.sent()];
        }
    });
}); });
ipcMain.handle('daemon:get_system_settings', function () { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('get_system_settings')];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:update_user_context', function (_event, context) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('update_user_context', context)];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:update_sources', function (_event, sources) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('update_sources', { sources: sources })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('tray:set_state', function (_event, state) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        updateTrayIcon(state);
        return [2 /*return*/];
    });
}); });
ipcMain.handle('window:close', function () {
    if (win && !win.isDestroyed()) {
        win.hide();
    }
});
ipcMain.handle('window:resize', function (_event_1, _a) { return __awaiter(void 0, [_event_1, _a], void 0, function (_event, _b) {
    var bounds;
    var width = _b.width, height = _b.height;
    return __generator(this, function (_c) {
        if (win && !win.isDestroyed()) {
            bounds = getCenteredTopBounds(width, height);
            win.setBounds(bounds);
        }
        return [2 /*return*/];
    });
}); });
ipcMain.on('dev:test_mascot_emotion', function (_event, emotion) {
    if (win && !win.isDestroyed()) {
        win.webContents.send('dev:set_mascot_emotion', emotion);
    }
});
app.on('before-quit', function (event) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                if (isQuitting)
                    return [2 /*return*/];
                isQuitting = true;
                event.preventDefault();
                _a.label = 1;
            case 1:
                _a.trys.push([1, , 3, 4]);
                return [4 /*yield*/, stopDaemonIfManaged()];
            case 2:
                _a.sent();
                return [3 /*break*/, 4];
            case 3:
                app.quit();
                return [7 /*endfinally*/];
            case 4: return [2 /*return*/];
        }
    });
}); });
app.on('will-quit', function () {
    globalShortcut.unregisterAll();
});
app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        app.quit();
        win = null;
    }
});
app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
    else if (win) {
        win.show();
        win.focus();
    }
});
app.whenReady().then(function () { return __awaiter(void 0, void 0, void 0, function () {
    var err_2, shortcutRegistered;
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                _a.trys.push([0, 2, , 3]);
                return [4 /*yield*/, ensureDaemonRunning()];
            case 1:
                _a.sent();
                return [3 /*break*/, 3];
            case 2:
                err_2 = _a.sent();
                console.error('[Main:ERR] Erreur lors de l\'initialisation du daemon:', err_2);
                return [3 /*break*/, 3];
            case 3:
                createWindow();
                createTray();
                // Subscribe to daemon push notifications (e.g. instant note completion)
                subscribeDaemonEvents(function (method, params) {
                    if (win && !win.isDestroyed()) {
                        win.webContents.send(method, params);
                    }
                });
                shortcutRegistered = globalShortcut.register('CommandOrControl+Shift+Space', function () {
                    toggleWindow();
                });
                if (!shortcutRegistered) {
                    console.warn('[Main:WARN] Global shortcut CommandOrControl+Shift+Space registration failed.');
                }
                // Recalculate notch position if display resolution or work area changes
                screen.on('display-metrics-changed', function () {
                    if (win && !win.isDestroyed()) {
                        var _a = win.getSize(), width = _a[0], height = _a[1];
                        var bounds = getCenteredTopBounds(width, height);
                        win.setPosition(bounds.x, bounds.y);
                    }
                });
                return [2 /*return*/];
        }
    });
}); });
