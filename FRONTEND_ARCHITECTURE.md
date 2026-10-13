# Architecture Frontend Desktop Ekko (Beta v0.1.0 — Electron + React 19)

Ce document établit les principes d'ingénierie logicielle, l'organisation par couches et la gouvernance de l'état pour les clients graphiques d'Ekko conformes au Design System Coucou.

---

## 1. Philosophie & Principes Directeurs
- **Couplage lâche, contrat strict :** Le renderer React ne communique JAMAIS directement avec le système d'exploitation ou le réseau. Tout transit passe par le pont typé du Preload (`window.ekkoAPI`).
- **Source de vérité unique (SSOT) :** Interdiction absolue de disperser les états réseau, de navigation ou de glisser-déposer dans des `useState` locaux disparates. Tout état partagé est centralisé dans des stores Zustand dédiés (`useDaemonStore`, `useDropStore`, `useEchoStore`, `useViewStore`).
- **Sérénité cognitive & Absorption In-Place :** Le glisser-déposer d'un document ne vole jamais le focus et n'entraîne aucune redirection disruptive vers le chat. L'opération s'exécute silencieusement in-place sur sa tuile Bento dédiée.
- **Observabilité & Traçabilité :** Tout échange IPC ou socket UNIX doit être tracé avec des préfixes explicites (`[IPC:REQ]`, `[IPC:RES]`, `[IPC:ERR]`) pour faciliter le diagnostic sans outil intrusif.
- **Zéro Mock :** L'interface doit refléter fidèlement l'état réel de l'infrastructure locale (`/tmp/ekko.sock`). En cas de déconnexion, l'UI bascule immédiatement en mode dégradé avec un feedback transparent pour l'utilisateur.

---

## 2. Découpage par Couches

```
clients/desktop-electron/
├── electron/                         # COUCHE SYSTÈME & TRANSPORT (Node.js)
│   ├── main.ts                       # Orchestration de BrowserWindow, redimensionnement & cycle OS
│   ├── preload.ts                    # Isolation de contexte & contrat d'API typé CJS (resizeWindow, ping, etc.)
│   └── transport/
│       └── socket-client.ts          # Client UNIX Socket délimité par \n vers /tmp/ekko.sock
│
└── src/                              # COUCHE PRÉSENTATION & MÉTIER (React 19)
    ├── core/                         # Logique transverse & états globaux
    │   ├── stores/                   # Stores Zustand (useDaemonStore, useDropStore, useEchoStore, useViewStore)
    │   ├── hooks/                    # Hooks de cycle de vie (useDaemonHeartbeat, useWindowResize)
    │   └── types/                    # Définitions TypeScript canoniques
    ├── design-system/                # Design tokens & constantes d'animation (Framer Motion)
    ├── features/                     # Modules fonctionnels découpés
    │   ├── welcome/                  # Amorce 1,8s & animation coucou mascotte
    │   ├── home/                     # Grille Bento (Drop in-place, veilleurs, dernier écho, télémétrie)
    │   ├── assistant/                # Chat, streaming ReAct & fil conversationnel
    │   ├── echo/                     # Consultation détaillée des fiches PKM
    │   └── settings/                 # Réglages, profils BYOM, état du daemon
    ├── components/                   # Composants UI partagés (Header, Badges, Tuiles)
    ├── App.tsx                       # Racine de composition & machine d'état des vues
    └── main.tsx                      # Point de montage DOM
```

---

## 3. Couche Système & Transport (`electron/`)

1. **`main.ts` (Main Process & Window Management) :**
   - Responsable unique de la gestion de `BrowserWindow`, du positionnement ancré en haut à droite (marge de 20px) et des raccourcis clavier natifs (`Escape`, `Ctrl+Q`).
   - Gestionnaire IPC `window:resize` : ajuste atomiquement les dimensions de la fenêtre (`win.setSize(width, height, true)`) lors des transitions de vues (Compact 620×230 px $\leftrightarrow$ Étendu 620×460 px) sans saccade ni scintillement.
   - Écoute les requêtes IPC envoyées par le renderer via `ipcMain.handle`.
2. **`transport/socket-client.ts` :**
   - Encapsule le module `node:net` pour dialoguer en JSON-RPC 2.0 sur le socket UNIX `/tmp/ekko.sock`.
   - Silence complet sur les pings nominaux pour éviter tout flood de terminal.
   - Applique des timeouts défensifs (3s pour les requêtes synchrones, 60s pour les flux de streaming).
3. **`preload.ts` (Preload Bridge) :**
   - Compilé obligatoirement au format **CommonJS (`.cjs`)** avec `sandbox: false`.
   - Expose l'interface typée `window.ekkoAPI` comprenant :
     - `resizeWindow: (width: number, height: number) => Promise<void>`
     - `ping: () => Promise<{ status: string; timestamp: string } | null>`
     - `getNotes: () => Promise<unknown[]>`
     - `submitPrompt: (prompt: string) => Promise<string>`
     - `ingestFile: (filePath: string) => Promise<string>`
     - `closeWindow: () => Promise<void>`
     - `onPromptChunk: (callback: (chunk: string) => void) => () => void`

---

## 4. Machine d'États des Vues & Navigation

L'état global de navigation est orchestré par un store dédié ou géré au niveau racine (`useViewStore`) :

```typescript
export type ViewMode = 'welcome' | 'home' | 'chat' | 'echo' | 'settings';
```

### 4.1 Séquence d'Amorce (Welcome Sequence)
1. Au lancement de l'application, l'interface s'initialise en mode `welcome` avec la géométrie Compacte (620×230 px).
2. La mascotte joue son animation de bienvenue (`welcome` : coucou avec la main satellite droite et regard chaleureux).
3. Après **1 800 ms** (`WELCOME_DURATION_MS`), transition fluide vers le mode `home` (Grille Bento).

### 4.2 Redimensionnement Dynamique de la Fenêtre
Lors de tout changement de `viewMode`, l'application pilote de concert le conteneur React (via les transitions spring de Framer Motion) et la fenêtre native :
- **Mode Compact (620×230 px) :** Activé pour `'welcome'` et `'home'`.
- **Mode Étendu (620×460 px) :** Déclenché automatiquement lors de la sélection des onglets `'chat'`, `'echo'` ou `'settings'`.
- La synchronisation s'effectue via l'appel IPC `window.ekkoAPI.resizeWindow(width, height)`.

---

## 5. Cycle de Vie "Drop & Forget" In-Place (`useDropStore`)

Le glisser-déposer de fichiers ou documents respecte strictement la règle de non-disruption du flux utilisateur. Il est formellement interdit de rediriger l'utilisateur vers l'onglet Chat lors d'un drop.

### Machine d'État de la Tuile Drop
```
[ idle ] ── (dragover) ──> [ hover ]
   ▲                            │ (drop)
   │                            ▼
   └─── (1,5s) ── [ success ] ◄── [ distilling ] ◄── [ uploading (jauge %) ]
```
- `idle` : Affichage du cadre en pointillés invitant au dépôt.
- `hover` : Mascotte en émotion `hover_drop`, contour illuminé `#38bdf8`.
- `uploading` : Progression locale du transfert avec barre de pourcentage animée in-place.
- `distilling` : Badge de distillation en tâche de fond (la mascotte passe en émotion `ingesting`).
- `success` : Confirmation visuelle avec badge émeraude (`ready`), puis retour silencieux à `idle` après 1,5 s.

---

## 6. Connexion des Tuiles Bento aux Stores Globaux

Dans la vue Home, les 4 tuiles de la grille Bento sont connectées à des sources de vérité uniques et découplées :

1. **Tuile Drop & Forget :** Connectée à `useDropStore` (gestion de la jauge et des étapes in-place).
2. **Tuile Veilleurs :** Connectée à `useDaemonStore` (statut des connecteurs déclarés dans `sources.yaml` : arXiv, HackerNews, RSS).
3. **Tuile Dernier Écho :** Connectée à `useEchoStore` (écoute du dernier item présent dans la base PKM `knowledge_notes`).
4. **Tuile Télémétrie & Santé :** Connectée à `useDaemonStore` (affichage réactif de `vramUsageMb`, `niceness` et `isOnline`).
