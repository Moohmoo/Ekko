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
import { spawn } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { DEFAULT_SOCKET_PATH } from './transport/socket-client';
var daemonProcess = null;
var isManagedDaemon = false;
/**
 * Check if the daemon UNIX socket is actively listening and responsive.
 */
export function isSocketAlive(socketPath) {
    if (socketPath === void 0) { socketPath = DEFAULT_SOCKET_PATH; }
    return new Promise(function (resolve) {
        var client = net.createConnection(socketPath);
        var timer = setTimeout(function () {
            client.destroy();
            resolve(false);
        }, 400);
        client.on('connect', function () {
            clearTimeout(timer);
            client.end();
            resolve(true);
        });
        client.on('error', function () {
            clearTimeout(timer);
            resolve(false);
        });
    });
}
/**
 * Find the repository root containing pyproject.toml.
 */
export function findRepoRoot() {
    var currentFileDir = path.dirname(fileURLToPath(import.meta.url));
    var startPaths = [
        process.cwd(),
        currentFileDir,
    ];
    for (var _i = 0, startPaths_1 = startPaths; _i < startPaths_1.length; _i++) {
        var start = startPaths_1[_i];
        var curr = path.resolve(start);
        for (var i = 0; i < 5; i++) {
            if (fs.existsSync(path.join(curr, 'pyproject.toml'))) {
                return curr;
            }
            var parent_1 = path.dirname(curr);
            if (parent_1 === curr)
                break;
            curr = parent_1;
        }
    }
    return process.cwd();
}
/**
 * Ensure the Python daemon is running.
 * If already active, adopts it (no-op).
 * If absent, spawns `uv run ekko daemon` and polls until socket accepts connections.
 */
export function ensureDaemonRunning() {
    return __awaiter(this, arguments, void 0, function (options) {
        var socketPath, maxWaitMs, retryIntervalMs, repoRoot, alreadyRunning, homeDir, customPath, uvBin, start, alive;
        var _a, _b;
        if (options === void 0) { options = {}; }
        return __generator(this, function (_c) {
            switch (_c.label) {
                case 0:
                    socketPath = options.socketPath || DEFAULT_SOCKET_PATH;
                    maxWaitMs = options.maxWaitMs || 5000;
                    retryIntervalMs = options.retryIntervalMs || 150;
                    repoRoot = options.repoRoot || findRepoRoot();
                    return [4 /*yield*/, isSocketAlive(socketPath)];
                case 1:
                    alreadyRunning = _c.sent();
                    if (alreadyRunning) {
                        console.log('[DaemonManager] Daemon préexistant détecté et actif sur', socketPath);
                        isManagedDaemon = false;
                        return [2 /*return*/, true];
                    }
                    // Clean stale socket file if process is dead
                    if (fs.existsSync(socketPath)) {
                        try {
                            fs.unlinkSync(socketPath);
                        }
                        catch (_d) {
                            // ignore
                        }
                    }
                    console.log('[DaemonManager] Démarrage automatique du daemon Ekko depuis', repoRoot);
                    homeDir = process.env.HOME || '/home/mohamed';
                    customPath = "".concat(homeDir, "/.local/bin:").concat(process.env.PATH || '');
                    uvBin = 'uv';
                    if (fs.existsSync("".concat(homeDir, "/.local/bin/uv"))) {
                        uvBin = "".concat(homeDir, "/.local/bin/uv");
                    }
                    daemonProcess = spawn(uvBin, ['run', 'ekko', 'daemon'], {
                        cwd: repoRoot,
                        env: __assign(__assign({}, process.env), { PATH: customPath }),
                        stdio: ['ignore', 'pipe', 'pipe'],
                    });
                    isManagedDaemon = true;
                    (_a = daemonProcess.stdout) === null || _a === void 0 ? void 0 : _a.on('data', function (data) {
                        var lines = data.toString().split('\n');
                        for (var _i = 0, lines_1 = lines; _i < lines_1.length; _i++) {
                            var line = lines_1[_i];
                            if (line.trim()) {
                                console.log("[ekko-daemon] ".concat(line));
                            }
                        }
                    });
                    (_b = daemonProcess.stderr) === null || _b === void 0 ? void 0 : _b.on('data', function (data) {
                        var lines = data.toString().split('\n');
                        for (var _i = 0, lines_2 = lines; _i < lines_2.length; _i++) {
                            var line = lines_2[_i];
                            if (line.trim()) {
                                console.error("[ekko-daemon:ERR] ".concat(line));
                            }
                        }
                    });
                    daemonProcess.on('error', function (err) {
                        console.error('[DaemonManager:ERR] Erreur lors du lancement du processus daemon:', err);
                        daemonProcess = null;
                        isManagedDaemon = false;
                    });
                    daemonProcess.on('exit', function (code, signal) {
                        console.log("[DaemonManager] Processus daemon termin\u00E9 (code: ".concat(code, ", signal: ").concat(signal, ")"));
                        daemonProcess = null;
                        isManagedDaemon = false;
                    });
                    start = Date.now();
                    _c.label = 2;
                case 2:
                    if (!(Date.now() - start < maxWaitMs)) return [3 /*break*/, 5];
                    return [4 /*yield*/, new Promise(function (res) { return setTimeout(res, retryIntervalMs); })];
                case 3:
                    _c.sent();
                    return [4 /*yield*/, isSocketAlive(socketPath)];
                case 4:
                    alive = _c.sent();
                    if (alive) {
                        console.log("[DaemonManager] Daemon op\u00E9rationnel et socket connect\u00E9 apr\u00E8s ".concat(Date.now() - start, "ms"));
                        return [2 /*return*/, true];
                    }
                    return [3 /*break*/, 2];
                case 5:
                    console.warn("[DaemonManager:WARN] Timeout (".concat(maxWaitMs, "ms) en attente du socket daemon."));
                    return [2 /*return*/, false];
            }
        });
    });
}
/**
 * Graceful termination of the managed daemon.
 * Sends SIGTERM, waits, and forces SIGKILL after timeout.
 */
export function stopDaemonIfManaged() {
    return __awaiter(this, void 0, void 0, function () {
        var proc;
        return __generator(this, function (_a) {
            if (!isManagedDaemon || !daemonProcess || daemonProcess.killed) {
                return [2 /*return*/];
            }
            console.log('[DaemonManager] Arrêt gracieux du daemon managé (SIGTERM)...');
            proc = daemonProcess;
            daemonProcess = null;
            isManagedDaemon = false;
            return [2 /*return*/, new Promise(function (resolve) {
                    var killTimer = null;
                    var onExit = function () {
                        if (killTimer)
                            clearTimeout(killTimer);
                        resolve();
                    };
                    proc.once('exit', onExit);
                    // Fallback SIGKILL after 3000ms
                    killTimer = setTimeout(function () {
                        console.warn('[DaemonManager:WARN] Forçage de l\'arrêt du daemon (SIGKILL)...');
                        try {
                            proc.kill('SIGKILL');
                        }
                        catch (_a) {
                            // ignore
                        }
                        resolve();
                    }, 3000);
                    try {
                        proc.kill('SIGTERM');
                    }
                    catch (_a) {
                        resolve();
                    }
                })];
        });
    });
}
