# Architecture Frontend Desktop Ekko (Electron + React 19)

Ce document établit les principes d'ingénierie logicielle, l'organisation par couches et la gouvernance de l'état pour les clients graphiques d'Ekko.

---

## 1. Philosophie & Principes Directeurs
- **Couplage lâche, contrat strict :** Le renderer React ne communique JAMAIS directement avec le système d'exploitation ou le réseau. Tout transit passe par le pont typé du Preload (`window.ekkoAPI`).
- **Source de vérité unique (SSOT) :** Interdiction absolue de disperser les états réseau ou de santé du daemon dans des `useState` locaux au sein des composants visuels. Tout état partagé est centralisé dans des stores Zustand dédiés.
- **Observabilité & Traçabilité :** Tout échange IPC ou socket UNIX doit être tracé avec des préfixes explicites (`[IPC:REQ]`, `[IPC:RES]`, `[IPC:ERR]`) pour faciliter le diagnostic sans outil intrusif.
- **Zéro Mock :** L'interface doit refléter fidèlement l'état réel de l'infrastructure locale (`/tmp/ekko.sock`). En cas de déconnexion, l'UI bascule immédiatement en mode dégradé avec un feedback transparent pour l'utilisateur.

---

## 2. Découpage par Couches

```
clients/desktop-electron/
├── electron/                         # COUCHE SYSTÈME & TRANSPORT (Node.js)
│   ├── main.ts                       # Orchestration de la fenêtre BrowserWindow & cycle OS
│   ├── preload.ts                    # Isolation de contexte & contrat d'API typé CJS
│   └── transport/
│       └── socket-client.ts          # Client UNIX Socket délimité par \n vers /tmp/ekko.sock
│
└── src/                              # COUCHE PRÉSENTATION & MÉTIER (React 19)
    ├── core/                         # Logique transverse & états globaux
    │   ├── stores/                   # Stores Zustand (useDaemonStore)
    │   ├── hooks/                    # Hooks de cycle de vie (useDaemonHeartbeat)
    │   └── types/                    # Définitions TypeScript canoniques
    ├── design-system/                # Design tokens & constantes d'animation (Framer Motion)
    ├── features/                     # Modules fonctionnels découpés
    │   ├── home/                     # Vue d'accueil, mascotte & zone Drop & Forget
    │   ├── assistant/                # Chat, streaming ReAct & fil de discussion
    │   └── echo/                     # Vue des fiches distillées (PKM)
    ├── components/                   # Composants UI partagés (Header, Badges)
    ├── App.tsx                       # Racine de composition
    └── main.tsx                      # Point de montage DOM
```

---

## 3. Couche Système & Transport (`electron/`)
1. **`main.ts` (Main Process) :**
   - Responsable unique de la gestion des fenêtres (`BrowserWindow`), du positionnement géométrique sur l'écran et des raccourcis système.
   - Écoute les requêtes IPC envoyées par le renderer via `ipcMain.handle`.
2. **`transport/socket-client.ts` :**
   - Encapsule le module `node:net` pour dialoguer en JSON-RPC 2.0 sur le socket UNIX `/tmp/ekko.sock`.
   - Garantit la délimitation stricte par saut de ligne (`\n`) et l'accumulation résiliente des fragments réseau.
   - Applique des timeouts défensifs (3s pour les requêtes synchrones, 60s pour les flux de streaming).
3. **`preload.ts` (Preload Bridge) :**
   - Compilé obligatoirement au format **CommonJS (`.cjs`)** pour compatibilité avec l'isolation de contexte d'Electron.
   - Expose une interface immuable et strictement typée sur `window.ekkoAPI`.

---

## 4. Gestion d'État Centralisée (Zustand)

Toutes les données partagées et l'état de santé du daemon résident dans `useDaemonStore` :

- **État (`DaemonState`) :**
  - `isOnline: boolean` (état de liaison au socket UNIX)
  - `lastPingTimestamp: string | null` (horodatage du dernier battement de cœur)
  - `vramUsageMb: number` (télémétrie GPU)
  - `niceness: string` (priorité CPU, typiquement `nice +10`)
  - `isChecking: boolean` (indicateur de transition réseau)

- **Système de Heartbeat (`useDaemonHeartbeat`) :**
  - Un hook racine actif interroge périodiquement le daemon toutes les **2 000 ms** via `window.ekkoAPI.ping()`.
  - La bascule d'état `online` $\leftrightarrow$ `offline` est atomique et propagée instantanément à l'ensemble de l'arbre React via Zustand.
