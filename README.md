# Ekko - Assistant Personnel Local d'Ingénierie & Recherche

Ekko est un assistant personnel autonome opérant localement sur Ubuntu Linux. Conçu selon les principes de simplicité radicale et d'architecture modulaire (Rasoir d'Ockham, SOLID), il combine un workflow de recherche scientifique en deux temps (Enquêteur ReAct + Validateur Critique) et des primitives d'outils universelles (`search`, `reader`, `get_system_info`).

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
   │                1. L'Enquêteur (ReAct Loop)              │
   │         (Thought -> Tool Call -> Observation)           │
   └──────┬─────────────────────┬─────────────────────┬──────┘
          │                     │                     │
          ▼                     ▼                     ▼
   ┌───────────────┐     ┌────────────────┐     ┌───────────────┐
   │ LLM Providers │     │ SessionStorage │     │ ToolRegistry  │
   │  - Local 7B   │     │  - Messages    │     │ (Lego Primitives)
   │  - Gemini     │     │  - TTL Purge   │     └───────┬───────┘
   └───────────────┘     └────────────────┘             │
                                         ┌───────────────────────────┐
                                         │ Outils Universels         │
                                         │ - search (academic/code/  │
                                         │           web)            │
                                         │ - reader (lecteur texte)  │
                                         │ - system (GPU RTX / VRAM) │
                                         └─────────────┬─────────────┘
                                                       │
                                                       ▼ (Projet de réponse)
   ┌─────────────────────────────────────────────────────────┐
   │             2. Le Validateur / Critique                 │
   │   (Élagage du bruit, certification des sources/faits)   │
   └────────────────────────────┬────────────────────────────┘
                                │
                                ▼
                         Réponse Finale
```

### 1. Workflow en deux temps (Enquêteur + Validateur)
- **L'Enquêteur (ReAct) :** Orchestre la réflexion et l'exécution d'outils via un flux d'événements typés (`ThoughtEvent`, `ToolCallEvent`, `ToolResultEvent`).
- **Le Validateur (Checker) :** Évalue le projet de réponse, élimine le marketing creux et les spéculations non sourcées, certifie la présence de sources vérifiables (papiers, dépôts GitHub) et émet un `ValidationEvent`.

### 2. Outils Universels (Tool Registry)
- **`search` :** Moteur universel paramétrable via son sélecteur `focus` :
  - `focus="academic"` : Interroge arXiv pour extraire des abstracts scientifiques complets, auteurs, dates et liens PDF.
  - `focus="code"` : Interroge GitHub pour trouver les dépôts officiels, étoiles, langages et licences.
  - `focus="web"` : Recherche web ouverte via DuckDuckGo pour les documentations et annonces tech.
- **`reader` :** Lecteur de document asynchrone via `httpx`. Télécharge et extrait le texte pur d'une URL (page web, doc, README GitHub).
- **`get_system_info` :** Inspection matérielle locale (OS, CPU, VRAM du GPU NVIDIA RTX 5050).

### 3. Mémoire SQLite & Gestion de sessions
- **Mémoire court-terme :** Fenêtre glissante conversationnelle isolée par identifiant de session.
- **Commande `/reset` :** Réinitialise instantanément l'affichage du terminal et instancie une nouvelle session vierge.
- **Rétention automatique (TTL) :** Purge automatique des anciens messages et exécutions d'outils au démarrage selon la configuration (`history_retention_days`).

### 4. Fournisseurs LLM (Strategy Pattern)
- **Local (par défaut) :** Compatible Ollama / vLLM via API standard OpenAI (`http://localhost:11434/v1`).
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
- `uv run python cli.py -d` : Active le mode débogage (affiche les pensées détaillées, les arguments d'outils et le statut de validation).
- `/reset` : Dans l'invite de commande, réinitialise la session et efface l'écran.
- `exit` ou `quit` : Quitte la session.

---

## Tests & Validation

La suite de tests unitaires et d'intégration couvre l'intégralité des modules :

```bash
uv run pytest
```
