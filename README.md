# Ekko - Assistant Personnel Local d'Ingénierie

Ekko est un assistant personnel autonome opérant localement sur Ubuntu Linux. Conçu selon les principes de simplicité radicale et d'architecture modulaire (Rasoir d'Ockham, SOLID), il combine un moteur de raisonnement ReAct interactif en ligne de commande et des outils primitifs universels (recherche web, lecteur de pages, inspection système).

---

## Architecture & Fonctionnement

```
   ┌─────────────────────────────────────────────────────────┐
   │                       Ekko CLI                          │
   │           Interface Terminal Interactive (Rich)         │
   └────────────────────────────┬────────────────────────────┘
                                │ AgentRequest / Streaming
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │                      EkkoEngine                         │
   │               Boucle ReAct & Streaming Events           │
   │        (Thought -> Action -> Observation -> Answer)     │
   └──────┬─────────────────────┬─────────────────────┬──────┘
          │                     │                     │
          ▼                     ▼                     ▼
   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
   │ LLM Providers │     │ SQLiteMemory  │     │ ToolRegistry  │
   │  - Gemini     │     │  - Messages   │     │  (LEGO Tools) │
   │  - Ollama/Loc │     │  - Task Runs  │     └───────┬───────┘
   └───────────────┘     │  - TTL Purge  │             │
                         └───────────────┘             ▼
                                         ┌───────────────────────────┐
                                         │Outils Primitifs Génériques│
                                         │ - web_search (DuckDuckGo) │
                                         │ - fetch_page (Lecteur Web)│
                                         │ - get_system_info (Matos) │
                                         └───────────────────────────┘
```

### 1. Moteur ReAct & Streaming
- **Cycle complet :** Le moteur (`agent/engine.py`) orchestre la réflexion et l'exécution d'outils via un flux d'événements typés (`ThoughtEvent`, `ToolCallEvent`, `ToolResultEvent`, `DoneEvent`).
- **Présentateurs :** Affichage interactif avec Rich (`ConsolePresenter`) en mode normal ou avec diagnostics détaillés (`-d / --debug`), ou sortie machine (`JsonPresenter`).
- **Garde-fous :** Interception automatique des actions redondantes et limitation stricte du nombre d'itérations.

### 2. Outils découplés (Tool Registry - Primitives LEGO)
- **`web_search` :** Recherche universelle sur le web sans clé d'API via DuckDuckGo (`ddgs`). Permet d'extraire les actualités récentes, documentations ou solutions techniques.
- **`fetch_page` :** Lecteur de page web asynchrone via `httpx`. Extrait le contenu textuel pur d'une URL en supprimant le bruit (scripts, styles, balises HTML).
- **`get_system_info` :** Inspection matérielle locale de la machine hôte (OS, CPU, mémoire vive disponible, détection GPU Nvidia).

### 3. Mémoire SQLite & Gestion de sessions
- **Mémoire court-terme :** Fenêtre glissante conversationnelle isolée par identifiant de session.
- **Commande `/reset` :** Réinitialise instantanément l'affichage du terminal et instancie une nouvelle session vierge.
- **Rétention automatique (TTL) :** Purge automatique des anciens messages et exécutions d'outils au démarrage selon la configuration (`history_retention_days`).

### 4. Fournisseurs LLM (Strategy Pattern)
- **Local (par défaut) :** Compatible Ollama / vLLM / LM Studio via API standard OpenAI (`http://localhost:11434/v1`).
- **Google GenAI :** Compatible avec les modèles Gemini via le SDK officiel `google-genai`.

---

## Installation & Démarrage

### Prérequis
- Ubuntu Linux avec Python 3.11+
- [uv](https://docs.astral.sh/uv/) installé sur la machine

### 1. Configuration de l'environnement
Copiez le gabarit `.env.example` vers `.env` et ajustez vos paramètres :
```bash
cp .env.example .env
```

Exemple pour modèle local (Ollama) :
```dotenv
LLM_PROVIDER=local
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5:7b
```

Exemple pour Google Gemini :
```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=votre_cle_api_ici
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Lancement du CLI interactif
```bash
uv run python cli.py
```

Options disponibles :
- `uv run python cli.py -d` : Active le mode débogage (affiche les pensées détaillées et arguments d'outils).
- `/reset` : Dans l'invite de commande, réinitialise la session et efface l'écran.
- `exit` ou `quit` : Quitte la session.

---

## Tests & Validation

La suite de tests unitaires et d'intégration couvre l'intégralité des modules :

```bash
uv run pytest
```
