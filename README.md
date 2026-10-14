# Ekko (Beta v0.1.0)

> **Tampon cognitif (staging buffer) & sentinelle de veille intégrée sous la barre système.**  
> Zéro distraction, absorption réflexe in-place et établi éphémère à sortie universelle.

---

## 1. Repositionnement Produit

Ekko n'est **ni un chatbot**, **ni un assistant conversationnel**, **ni un simple gestionnaire de notes**.  
Ekko est un **tampon cognitif ambiant** (*staging buffer*) qui opère en amont pour capturer, distiller et structurer l'information brute en tâche de fond :

- **Règle d'or de l'interaction (< 3 secondes) :** Ekko ne vole jamais le focus. L'utilisateur consulte, extrait ou vide d'un geste instinctif sans rompre sa concentration.
- **Intégration Organique (Notch UI) :** Une encoche fusionnée avec la barre supérieure du bureau (hauteur compacte de **230 px**, extensible avec fluidité à **460 px** sans fuite de clic).
- **Mascotte Sentinelle :** Une goutte d'eau vectorielle animée exprimant l'état du système par **7 micro-émotions réactives** (*idle*, *welcome*, *hover_drop*, *ingesting*, *ready*, *alert*, *error*).
- **Distillation Locale Autonome :** Daemon en tâche de fond traitant l'information via Ollama (`qwen2.5:7b`, rétention VRAM de 5m) et embeddings FastEmbed (`bge-small-en-v1.5`, ONNX CPU 384d).
- **Mémoire Hybride Locale :** SQLite en mode WAL combinant recherche plein texte FTS5 (BM25), recherche dense `sqlite-vec`, fusion Reciprocal Rank Fusion (**RRF** $k=60$) et synchronisation Markdown Obsidian.

---

## 2. Le Triptyque Officiel

Ekko s'articule autour de 3 volets d'action clairs :

```text
               +------------------------------------------------+
               |        BARRE SYSTÈME (PANNEAU SUPÉRIEUR)       |
               +------------------------------------------------+
                                       |
                     +-----------------+-----------------+
                     |                                   |
             [ 💧 HOME ]                      [ 📡 RADAR ]                   [ ⚡ BUFFER ]
          Sas d'entrée réflexe             Veille distillée                Établi d'action
       - Mascotte interactive           - Agrégation silencieuse        - 5 à 7 fiches récentes
       - Drop physique universel        - 3 à 5 faits saillants / jour  - Copie Markdown / Drag .md
       - Auto-détection RSS/Atom        - Badges sources cliquables     - Inbox Zéro & Filtre FTS5
```

### 1. HOME — Sas d'entrée réflexe
- **Fusion avec la barre système :** Aucune démarcation supérieure, transition douce avec les congés concaves latéraux.
- **Drop Physique Universel :** Glissez n'importe quel document (`.pdf`, `.md`, `.txt`) ou URL directement sur l'encoche. L'absorption s'effectue in-place sans redirection.
- **Détection Automatique à l'Ingestion :** Si vous déposez un lien de flux RSS ou Atom, Ekko le configure automatiquement comme nouvelle source de veille sans ouvrir de formulaire.

### 2. RADAR — Veille distillée en tâche de fond
- **Agrégation Silencieuse :** Le daemon local interroge périodiquement les flux et sources configurées avec polite polling, cache conditionnel ETag et protection anti-SSRF.
- **Synthèse Quotidienne Condensée :** Chaque jour, un condensé de **3 à 5 faits saillants** est généré localement par `qwen2.5`, avec des pastilles et badges cliquables renvoyant directement aux articles sources.

### 3. BUFFER — Établi d'action éphémère
- **Sas de Transit Chaud :** Présente les **5 à 7 fiches récentes** produites par les captures et la distillation.
- **Sortie Universelle :** 
  - Copie du contenu en Markdown standard Obsidian d'un simple clic.
  - Glisser-déposer d'une fiche directement vers votre éditeur ou bureau pour créer un fichier `.md` natif.
- **Mécanique Inbox Zéro :** Bouton d'évacuation par fiche ou vidage complet du buffer en un clic pour maintenir l'esprit libre.
- **Filtre Éclair :** Barre de recherche instantanée combinant FTS5 et similarité vectorielle `sqlite-vec` pour repêcher n'importe quelle archive de la base locale.

> **Note de dépréciation :**  
> Les concepts antérieurs de « chat conversationnel », de « flux de discussion multi-tours » et de « boucle ReAct conversationnelle » sont **dépréciés** et programmés pour élagage lors du prochain sprint de refactorisation.

---

## 3. Architecture Technique

```text
+-----------------------------------------------------------------------------------+
|                        Couche Présentation (Desktop Notch)                        |
|   +---------------------------------------------------------------------------+   |
|   |         Client Desktop Electron (React 19 + TypeScript + Tailwind)        |   |
|   |                  Triptyque : [ Home | Radar | Buffer ]                    |   |
|   +-------------------------------------+-------------------------------------+   |
|                                         |                                         |
+-----------------------------------------|-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               Driving Adapter IPC (Socket UNIX Local / JSON-RPC 2.0)              |
|        Socket : /tmp/ekko.sock | Push événementiel : daemon:note_created          |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              Noyau Hexagonal (Daemon)                             |
|  - Ingestion : Polite Polling, Token Bucket, Anti-SSRF, Détection RSS             |
|  - Distillation : SignalDistiller (Ollama qwen2.5:7b, keep_alive: "5m", nice +10) |
|  - Mémoire Hybride : SQLite WAL, FTS5 BM25, sqlite-vec, Fusion RRF (k=60)        |
+-----------------------------------------------------------------------------------+
```

---

## 4. Guide de Démarrage Rapide

### Prérequis
- **OS :** Linux (Ubuntu/Debian, Arch, Fedora) avec serveur d'affichage X11 ou Wayland.
- **Python :** 3.14+ avec gestionnaire de paquets [`uv`](https://github.com/astral-sh/uv).
- **Node.js :** 20+ avec `npm`.
- **Modèle Local :** [Ollama](https://ollama.com/) avec `qwen2.5:7b` :
  ```bash
  ollama pull qwen2.5:7b
  ```

### Installation
```bash
git clone https://github.com/your-username/Ekko.git
cd Ekko
uv sync
cd clients/desktop-electron
npm install
```

### Lancement Unifié (Une Seule Commande)
```bash
cd clients/desktop-electron
npm run dev
```

> **Supervision Automatique :**  
> Electron vérifie le socket `/tmp/ekko.sock`. Si le daemon Python n'est pas actif, Electron le lance automatiquement en arrière-plan (`uv run ekko daemon`), attend activement son initialisation puis affiche l'encoche. À la fermeture (`Ctrl+Q`), le daemon supervisé est éteint proprement.

---

## 5. Raccourcis & Gestes Essentiels

| Action / Raccourci | Fonction |
|---|---|
| `Ctrl+Q` | Ferme l'application et arrête proprement le daemon managé |
| `Escape` | Replie / masque l'encoche sans quitter |
| `CommandOrControl+Shift+Space` | Raccourci global d'apparition / masquage |
| **Drop sur le Notch** | Ingestion réflexe in-place du fichier ou de l'URL |
| **Drop d'un flux RSS/Atom** | Détection automatique et inscription directe en source de veille |
| **Clic Icône Goutte (Home)** | Sas d'entrée réflexe avec mascotte et drop in-place |
| **Clic Icône Radar (Radar)** | Consultation des 3 à 5 faits saillants du jour |
| **Clic Icône Buffer (Buffer)** | Établi des 5 à 7 fiches récentes, export Markdown et Inbox Zéro |

---

## 6. Qualité & Validation

- **Suite Python (291 tests passants) :** Couverture totale de l'architecture hexagonale, de la résilience réseau, de l'indexation hybride SQLite et du cycle de vie daemon.
- **Banc E2E Playwright Electron (7 scénarios passants) :** Géométrie notch 230/460px, mur transparent click-through, cycle de vie sentinelle, neutralité de la mascotte, fluidité 60 FPS (zéro Long Task) et soak test sans fuite mémoire.

---

## 7. Licence

Ce projet est sous licence MIT.
