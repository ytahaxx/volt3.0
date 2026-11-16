# Architecture technique

## Vue d'ensemble

```
Navigateur ──HTTP──▶ Flask (app.py)
   │                   ├─ routes/main.py        pages HTML (Jinja)
   │                   ├─ routes/programme.py   API catégories / fiche
   │                   ├─ routes/search.py      API recherche + filtres + tri
   │                   ├─ routes/quiz.py        API quiz
   │                   └─ routes/assistant.py   API assistant RAG
   │                            │
   │                   services/ (logique métier)        database/ (SQLite)
   │                   search · quiz · rag · llm · parser   db.py · models.py
   │                            │                              │
   └─ localStorage (favoris)    └────── data/*.json ◀──────────┘ (source de vérité)
```

Principe : **les routes sont minces** (validation + JSON), la logique est dans `services/`, l'accès aux données dans `database/`. Les services sont créés une fois dans `create_app()` (`app.extensions`).

## Données

- `data/propositions.json` : source de vérité (48 propositions, 12 catégories). Généré par `scripts/build_propositions.py` à partir d'une saisie structurée, puis chargé dans SQLite par `database/db.py::init_db`.
- Une proposition = **une mesure** (puce) du document officiel. Champs : `summary` (reformulation fidèle), `measures`, `objectives` (objectif annoncé de la section), `details` (explication complémentaire **non officielle**), `section_ref` (partie › section › n° de mesure), `source_url`, `page` (`null` : non vérifié).
- Séparation officiel / non officiel : le gabarit `proposition.html` distingue visuellement les blocs « Programme officiel » et « Non officielle ». `details` est exclu de l'index de l'assistant.
- `data/quiz.json` : questions liées à une proposition (`proposition_id`) ; un test vérifie que chaque référence existe.

## Base de données

SQLite via `sqlite3` (bibliothèque standard), deux tables (`categories`, `propositions`), listes stockées en JSON texte. `database/models.py` ne contient que des requêtes de lecture. Pour migrer vers SQLAlchemy/PostgreSQL, seuls `db.py` et `models.py` sont à réécrire : les routes et services consomment des dictionnaires Python.

## Recherche (`services/search_service.py`)

Déterministe, sans IA : normalisation (casse, accents), tous les mots doivent être présents (ET), mots courts (≤ 3 lettres, ex. « ia ») appariés comme mots entiers, score pondéré (titre 5, mots-clés 3, résumé 2, reste 1). Filtres catégorie / sous-thématique / type, tris `relevance`, `alpha`, `alpha_desc`, `document`. Le surlignage est fait côté navigateur (`VE.highlight`) sur du texte échappé.

## Pipeline RAG (`services/rag_service.py`)

| Étape | Implémentation |
|---|---|
| 1-2. PDF → texte | `document_parser.extract_pages` (pypdf), optionnel si `data/programme.pdf` existe |
| 3. Nettoyage / découpage | `clean_text`, `chunk_text` (~700 caractères, par phrases, 1 phrase de chevauchement) |
| 4. Index | `TfidfVectorizer` (unigrammes + bigrammes, racinisation légère, mots vides français), scikit-learn |
| 5. Recherche | similarité cosinus ; passage retenu si score ≥ `RAG_MIN_SCORE` **et** (couverture ≥ 50 % des mots de la question **ou** score ≥ 0,3) |
| 6-7. Génération | fournisseur LLM (`services/llm_providers.py`) avec consigne système restrictive et passages numérotés `[S1]…` |
| 8. Références | chaque réponse renvoie `sources` (titre, référence, URL, extrait, score) |

Garde-fous : refus des demandes de conseil de vote (motif sur la question normalisée), message « rien trouvé » plutôt qu'une réponse inventée, `details` non officiels hors index, clés API uniquement côté serveur, texte rendu via `textContent` côté navigateur.

Le critère de couverture existe car un seul mot générique (« recette », « monde ») suffisait à ramener un passage sans rapport.

### Changer de fournisseur

Ajouter une classe avec `generate(question, passages) -> str` dans `llm_providers.py`, l'enregistrer dans `get_provider()`, définir `LLM_PROVIDER` et la clé dans `.env`. `DemoProvider` est le repli automatique (clé absente, erreur réseau).

### Passer à une recherche vectorielle

Remplacer `RagIndex` (même méthode `retrieve(question, k, min_score)` renvoyant des dicts de passages avec `score`) par un index embeddings + ChromaDB/FAISS. Le reste (service, routes, interface) est inchangé.

## Frontend

HTML rendu côté serveur (Jinja) + JavaScript sans framework (`fetch`). `app.js` : menu mobile, utilitaires (`VE`), favoris (`localStorage`, clé `voltExplorer.favorites`, lecture tolérante aux données corrompues), page Favoris. `search.js`, `quiz.js`, `assistant.js` : une page chacun. Aucune dépendance externe ni CDN.

## Quiz

Les questions sont servies **sans** réponse ; `POST /api/quiz/answer` renvoie la correction et l'explication ; `POST /api/quiz/score` recalcule le score côté serveur (doublons ignorés).

## Erreurs

404/405/500 : page HTML pour les URL de pages, JSON `{error}` pour `/api/*`. Paramètres invalides → 400. Côté interface : messages dédiés (aucun résultat, service indisponible).

## Tests (`tests/`, pytest)

Pages et liens internes, API recherche/filtres/tri, quiz (score, doublons, validation), assistant (exemples du cahier des charges, hors-sujet, refus de vote, repli LLM, absence de fuite de clé, requête Anthropic simulée), intégrité des données. La logique JavaScript pure (surlignage, favoris) a été vérifiée dans Node avec un faux DOM ; ce script n'est pas conservé dans le dépôt.

## Limites connues

- Rendu graphique et responsive non vérifiés visuellement.
- Fournisseurs Anthropic/OpenAI non testés contre les vrais services.
- Index lexical : il ne comprend pas les synonymes (ex. « impôts » / « fiscalité » dépend des mots-clés saisis) et le classement des résultats n'est pas toujours optimal (la question sur les « transports » ramène aussi le transport d'animaux).
- Numéros de page absents tant que le PDF n'est pas fourni et indexé.
