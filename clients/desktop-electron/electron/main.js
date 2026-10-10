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
import { app, BrowserWindow, ipcMain, screen } from 'electron';
import path from 'node:path';
import { sendJsonRpc, streamPrompt } from './ipc-bridge';
process.env.DIST = path.join(__dirname, '../dist');
process.env.VITE_PUBLIC = app.isPackaged
    ? process.env.DIST
    : path.join(__dirname, '../public');
var win = null;
var VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL'];
function createWindow() {
    var primaryDisplay = screen.getPrimaryDisplay();
    var screenWidth = primaryDisplay.workAreaSize.width;
    var podWidth = 440;
    var podHeight = 560;
    // Position anchored in top right with 20px margins
    var posX = Math.max(20, screenWidth - podWidth - 20);
    var posY = 30;
    win = new BrowserWindow({
        width: podWidth,
        height: podHeight,
        x: posX,
        y: posY,
        resizable: false,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: false,
        hasShadow: true,
        backgroundColor: '#00000000',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
    });
    if (VITE_DEV_SERVER_URL) {
        win.loadURL(VITE_DEV_SERVER_URL);
    }
    else {
        win.loadFile(path.join(process.env.DIST, 'index.html'));
    }
    // Auto-hide on blur (optional click outside dismiss)
    win.on('blur', function () {
        // Keep window visible or allow user to toggle
    });
}
// IPC Handlers
ipcMain.handle('daemon:ping', function () { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('ping')];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:get_notes', function () { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, sendJsonRpc('scan_inbox', { limit: 20 })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:ingest_file', function (_event, filePath) { return __awaiter(void 0, void 0, void 0, function () {
    var prompt;
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                prompt = "Analyse et indexe ce document d\u00E9pos\u00E9 : ".concat(filePath);
                return [4 /*yield*/, new Promise(function (resolve, reject) {
                        streamPrompt(prompt, function () { }, function (res) { return resolve(res); }, function (err) { return reject(new Error(err)); });
                    })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('daemon:submit_prompt', function (event, prompt) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0: return [4 /*yield*/, new Promise(function (resolve, reject) {
                    streamPrompt(prompt, function (chunk) {
                        event.sender.send('daemon:prompt_chunk', chunk);
                    }, function (full) {
                        resolve(full);
                    }, function (err) {
                        reject(new Error(err));
                    });
                })];
            case 1: return [2 /*return*/, _a.sent()];
        }
    });
}); });
ipcMain.handle('window:close', function () {
    if (win) {
        win.close();
    }
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
});
app.whenReady().then(createWindow);
