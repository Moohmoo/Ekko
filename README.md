# Ekko (Beta v0.1.0)

> **Tampon cognitif ambiant & local-first pour développeurs et chercheurs.**  
> Veille autonome, absorption silencieuse de documents et mémoire hybride pérenne.

---

## 1. Présentation

Ekko s'interpose comme une couche de sérénité cognitive entre le flux continu d'informations et votre session de travail :
- **Discrétion Ambiante :** Une encoche de bureau (*Desktop Notch*) ancrée en haut d'écran, ergonomique et non intrusive (hauteur compacte de **230 px**, extensible avec fluidité à **460 px** sans vol de focus ni fuite de clic).
- **Mascotte Vivante :** Une goutte d'eau vectorielle animée incarnant l'état du système à travers **7 micro-émotions réactives** (*idle*, *welcome*, *hover_drop*, *ingesting*, *ready*, *alert*, *error*).
- **Drop & Forget In-Place :** Déposez un document (`.pdf`, `.md`, `.txt`) ou une URL directement sur l'encoche. L'absorption s'effectue silencieusement in-place sans jamais interrompre votre tâche en cours.
- **Distillation Autonome :** Un daemon d'arrière-plan résilient extrait, compresse et synthétise les connaissances via un LLM local (Ollama `qwen2.5:7b` avec confinement VRAM et TTL de rétention de 5 minutes).
- **Mémoire Hybride Locale :** Stockage unifié sous SQLite en mode WAL combinant recherche textuelle FTS5 (BM25), recherche dense vectorielle `sqlite-vec` (embeddings FastEmbed ONNX 384d), fusion par rangs réciproques (**RRF** $k=60$) et fiches synchronisées au format Markdown Obsidian.
- **Orchestration Unifiée :** Démarrage direct en une seule commande : le processus Electron supervise et lance automatiquement le daemon Python en tâche de fond s'il n'est pas déjà actif, et l'éteint proprement à la fermeture.

---

## 2. Architecture Technique

```text
+-----------------------------------------------------------------------------------+
|                            Couche Présentation                                   |
|   +----------------------------------+     +----------------------------------+   |
|   |            CLI Rich              |     |     Client Desktop Electron      |   |
|   |  (REPL, prompt_toolkit, Live)    |     |   (React 19, TS, Tailwind, Notch) |   |
|   +-----------------+----------------+     +-----------------+----------------+   |
|                     |                                        |                    |
+---------------------|----------------------------------------|--------------------+
                      |                                        |
                      v                                        v
+-----------------------------------------------------------------------------------+
|               Driving Adapter IPC (Socket UNIX Local / JSON-RPC 2.0)              |
|   Socket : /tmp/ekko.sock | Push : daemon:note_created | Streaming : NDJSON       |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                               Cœur de Domaine (Core)                             |
|  - Architecture Hexagonale stricte (Ports & Adaptateurs, zéro dépendance infra)   |
|  - Modèles : Message, Turn, ModelResponse, ToolCall, Signal, Note                |
|  - Engine : Boucle ReAct, circuit-breaker & dispatch asynchrone                   |
+--------------------+---------------------+--------------------+-------------------+
                     |                     |                    |
   +-----------------+                     |                    +-----------------+
   v                                       v                                      v
+-----------------------+  +-------------------------------+  +-------------------------+
| Adaptateurs Inférence |  |    Couche Mémoire Hybride     |  | Pipeline d'Ingestion    |
| (providers/)          |  |    (SQLite + FTS5 + Vec)      |  | (ingestion/)            |
| - LiteLLMProvider     |  | - Table source_states         |  | - sources.yaml          |
| - Ollama (qwen2.5:7b) |  | - Table raw_signals           |  | - ResilientHttpClient   |
|   keep_alive: "5m"    |  | - Table knowledge_notes       |  |   (ETag, Token Bucket,  |
| - Confinement VRAM &  |  | - Index FTS5 (Lexical BM25)   |  |    Jitter, Anti-SSRF)   |
|   priorité nice +10   |  | - Index sqlite-vec (FastEmbed)|  | - Ingestion Drop & Push |
|                       |  | - Fusion Hybride RRF (k=60)   |  | - SignalDistiller       |
+-----------------------+  +-------------------------------+  +-------------------------+
```

---

## 3. Guide de Démarrage Rapide

### Prérequis
- **Système d'Exploitation :** Linux (Ubuntu/Debian, Arch, Fedora) avec serveur d'affichage X11 ou Wayland (support transparence).
- **Python :** Version 3.14+ avec gestionnaire de paquets [`uv`](https://github.com/astral-sh/uv).
- **Node.js :** Version 20+ avec `npm`.
- **Modèle Local :** [Ollama](https://ollama.com/) en cours d'exécution avec le modèle `qwen2.5:7b` :
  ```bash
  ollama pull qwen2.5:7b
  ```

### Installation

1. Cloner le dépôt :
   ```bash
   git clone https://github.com/your-username/Ekko.git
   cd Ekko
   ```

2. Installer les dépendances Python et synchroniser l'environnement virtuel :
   ```bash
   uv sync
   ```

3. Installer les dépendances du client Desktop Electron :
   ```bash
   cd clients/desktop-electron
   npm install
   ```

### Lancement Unifié (Recommandé)

Démarrez l'application d'une seule traite :
```bash
cd clients/desktop-electron
npm run dev
```

> **Supervision automatique intégrée :**  
> Electron vérifie immédiatement la présence du socket UNIX `/tmp/ekko.sock`. Si le daemon Python n'est pas déjà actif, Electron démarre automatiquement `uv run ekko daemon` en sous-processus managé, attend activement que le socket accepte les connexions, puis ouvre l'encoche de bureau. À la fermeture de l'application (`Ctrl+Q`), le daemon supervisé est éteint proprement par signal `SIGTERM`.

### Mode Développement Manuel (Deux Terminaux)

Si vous souhaitez modifier le code du daemon Python indépendamment de l'interface :
```bash
# Terminal 1 — Daemon Python avec logs directs
uv run ekko daemon

# Terminal 2 — Client graphique Electron
cd clients/desktop-electron
npm run dev
```
*(Electron détecte alors l'instance existante et s'y connecte sans relancer de sous-processus).*

---

## 4. Utilisation & Raccourcis Clavier

| Raccourci / Action | Comportement |
|---|---|
| `Ctrl+Q` | Ferme l'application et arrête proprement le daemon managé |
| `Escape` | Replie / masque la fenêtre de l'encoche sans fermer l'application |
| `CommandOrControl+Shift+Space` | Raccourci global de bascule (afficher / masquer l'encoche) |
| **Glisser-Déposer sur l'encoche** | Ingestion immédiate in-place du fichier ou de l'URL |
| **Clic Icône Goutte (Accueil)** | Vue Bento compacte (230 px) avec mascotte, Drop, veilleurs et dernier écho |
| **Clic Icône Bulle (Chat)** | Extension à 460 px avec l'assistant local et dialogue en streaming |
| **Clic Icône Éclair (Écho)** | Extension à 460 px avec le flux des notes PKM et recherche instantanée FTS5 |
| **Clic Icône Roue (Réglages)** | Statut IPC, télémétrie matérielle et gestion des sources |

---

## 5. Qualité & Banc de Tests

Le socle technique d'Ekko est couvert par une suite de validation automatisée stricte :

### Tests Python (Domaine & Daemon)
```bash
uv run pytest tests/unit tests/integration
```
- **291 tests passants** garantissant l'étanchéité de l'architecture hexagonale, la mémoire hybride, les politiques anti-SSRF, le polite polling et le cycle de vie IPC.

### Tests E2E Playwright Electron
```bash
cd clients/desktop-electron
npm run test:e2e
```
- **7 scénarios industriels** exécutés directement sur le binaire Electron natif :
  1. *Géométrie & Mur transparent* : vérification stricte de la bascule 230 px $\leftrightarrow$ 460 px et de l'étanchéité des ailes transparentes.
  2. *Cycle de vie Sentinelle* : persistance en mémoire du processus lors de la fermeture (`hide` rather than `destroy`).
  3. *Neutralité géométrique de la mascotte* : reset absolu des échelles *squash & stretch* (`scale: 1`, `scaleX: 1`, `scaleY: 1`) au retour en état `idle`/`ready`.
  4. *Continuité du regard* : suivi oculaire interactif borné ($R \le 3.5\text{px}$) et absence d'erreur lors du survol.
  5. *Fluidité 60 FPS & Zéro Long Task* : vérification via `PerformanceObserver` qu'aucun re-render parasite ou blocage $>50\text{ms}$ ne survient pendant les mouvements de souris.
  6. *Stress test de clics rapides* : alternance ultra-rapide entre onglets sans aucune désynchronisation géométrique.
  7. *Soak test mémoire* : 25 cycles intensifs de bascule sans fuite mémoire (croissance du heap JS strictement plafonnée).

---

## 6. Licence

Ce projet est sous licence MIT.
