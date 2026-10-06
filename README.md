# Ekko - Assistant de Veille Automatisée (MVP)

Ekko est un système autonome de veille scientifique et technologique basé sur une architecture à deux agents spécialisés et une modélisation stricte Pydantic v2. Il extrait les sujets "trending" (Hacker News, Hugging Face Daily Papers), filtre les doublons via une mémoire persistante, classe les articles majeurs et génère un briefing quotidien synthétique en Markdown avec notification de bureau Ubuntu.

---

## 🏛️ Architecture & Fonctionnement

```
[ Hacker News API ]      [ HF Daily Papers ]
        │                        │
        └───────────┬────────────┘
                    ▼
     [ Filtre Anti-Doublon & Historique ]
             (~/.history.json)
                    │
                    ▼
      [ Agent 1 : Le Trieur ]
       - Pare-feu anti-bruit (Tech, Backend, Bio)
       - Sortie structurée (Pydantic)
                    │
                    ▼
     [ Agent 2 : Le Rédacteur ]
       - Synthèse percutante sans bavardage
       - Format Markdown strict
                    │
                    ├──────────────────────────┐
                    ▼                          ▼
      [ data/briefings/YYYY-MM-DD.md ]  [ notify-send OS ]
```

### 1. Collecte asynchrone
- **Hacker News :** Top stories avec filtrage sur score minimum (> 50 points).
- **Hugging Face Daily Papers :** Articles de recherche les plus populaires du jour.

### 2. Mémoire et Idempotence
- **Historique local (`data/history.json`) :** Indexation des URLs normalisées (nettoyage UTM, ancres) avec date et purge glissante à 60 jours.
- **Idempotence journalière (`data/briefings/YYYY-MM-DD.md`) :** Ne recalcule pas si le briefing a déjà été généré, sauf en cas d'utilisation du flag `--force`.

### 3. Architecture 2 Agents Découplés
- **Agent 1 (Trieur) :** Pare-feu anti-bruit ciblant l'informatique et la bioinformatique. Retient 3 à 5 articles majeurs et garantit la structure via `SelectionResult`. Validation anti-hallucination d'URL intégrée.
- **Agent 2 (Rédacteur) :** Rédige les sections directes (`C'est quoi`, `Pourquoi on en parle`, lien source) sans salutations superflues.

### 4. Support Multi-Providers (Strategy Pattern)
- **Google GenAI :** Utilise le SDK officiel `google-genai` (modèle `gemini-flash-lite-latest` par défaut).
- **Modèle Local :** Compatible Ollama / vLLM / LM Studio via API compatible OpenAI (`http://localhost:11434/v1`).

---

## 🚀 Installation & Démarrage

### Prérequis
- Ubuntu Linux avec Python 3.11+
- `notify-send` (inclus par défaut sur Ubuntu Desktop)

### 1. Cloner ou naviguer dans le dossier
```bash
cd Ekko
```

### 2. Configuration des variables d'environnement
Copiez le gabarit `.env.example` vers `.env` :
```bash
cp .env.example .env
```
Éditez le fichier `.env` avec votre clé API :
```bash
GEMINI_API_KEY=votre_cle_gemini_ici
```

*(Si vous souhaitez utiliser un modèle local comme Ollama : réglez `LLM_PROVIDER=local`)*

### 3. Exécution (avec uv ou python)

Avec **uv** (recommandé, rapide et sans configuration) :
```bash
# Exécution normale du matin
uv run main.py

# Forcer la regénération même si le fichier du jour existe déjà
uv run main.py --force
```

Ou avec le virtualenv standard :
```bash
./.venv/bin/python main.py
```

Le briefing sera disponible dans `~/watch/YYYY-MM-DD.md` et une notification de bureau s'affichera.

---

## 🧪 Tests Unitaires

Le projet inclut une suite de tests unitaires couvrant l'ensemble des modules :

```bash
uv run pytest -v
```

---

## 🔮 Évolution vers Ekko (Agent Orchestrateur / JARVIS)

Conçu selon le principe de simplicité radicale (**KISS** et **Rasoir d'Ockham**), ce module de veille est conçu pour être directement importable en tant que fonction/outil (`Tool`) par l'agent orchestrateur global Ekko :

```python
from main import execute_daily_watch
from config import get_settings

# Appelable directement comme tool d'orchestration
result = await execute_daily_watch(get_settings())
```
