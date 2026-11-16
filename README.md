# Volt Explorer

> *Comprendre le programme, explorer les idées.*

Application web pédagogique et indépendante pour explorer un programme politique de Volt : navigation par thématique, recherche, filtres, favoris, quiz et assistant IA (RAG) qui cite ses sources.

**Ce n'est pas un site officiel de Volt.** L'application informe ; elle ne recommande aucun vote et ne fait pas de persuasion.

## ⚠️ Source utilisée (à lire avant la démonstration)

Le document officiel intégré est le **programme électoral des élections européennes** (« L'avenir : Made in Europe », Volt Europa), version française publiée sur voltfrance.org :
<https://voltfrance.org/storage/pdf/volt-ecp_fr.pdf>

- C'est un programme **européen**, pas un programme national français complet. Des thèmes comme la justice, la sécurité intérieure ou la santé (hors santé mentale des jeunes) n'y figurent pas : l'application ne les invente pas.
- Les **48 propositions** correspondent chacune à une mesure du document, **reformulée** (pas de citation longue). La référence indique la partie et la section du document.
- Les **numéros de page ne sont pas renseignés** : ils n'ont pas pu être vérifiés. Le champ `page` vaut `null`.
- Les « explications complémentaires » des fiches sont rédigées par l'application et clairement étiquetées **non officielles**.
- Les catégories (12) sont un **classement éditorial** de l'application.

D'autres documents existent sur voltfrance.org (programme des législatives 2024, programme Moonshot, document sur le handicap…). Ils n'ont pas été intégrés : voir « Évolutions ».

## Installation (Windows + Visual Studio Code)

Prérequis : Python 3.10 ou plus (<https://www.python.org/downloads/>, cocher « Add Python to PATH »).

Dans le terminal VS Code (PowerShell) à la racine du dossier `volt-explorer-main` :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Ouvrir <http://127.0.0.1:5000>.

> Si PowerShell refuse d'activer l'environnement : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, ou utiliser `cmd` avec `.venv\Scripts\activate.bat`.
> Dans VS Code : *Ctrl+Maj+P → Python: Select Interpreter → .venv*.

La base SQLite (`database/volt_explorer.sqlite3`) est créée automatiquement au premier lancement à partir de `data/propositions.json`. Après modification du JSON : `python scripts/init_db.py`.

## Installer l'application (PWA)

L'application est une PWA : manifeste, service worker et icônes sont fournis (`static/manifest.webmanifest`, `static/sw.js`, `scripts/make_icons.py`). Ce n'est **pas un APK**.

- **PC (Chrome/Edge)** : ouvrir <http://127.0.0.1:5000> puis cliquer sur l'icône « Installer » de la barre d'adresse (ou menu ⋮ → *Installer Volt Explorer*). L'application s'ouvre dans sa propre fenêtre.
- **Android** : l'installation exige **HTTPS** (ou localhost). Une adresse `http://192.168.x.x:5000` sur le réseau local permet d'utiliser le site dans Chrome mais pas de l'installer. Pour installer : déployer l'application en HTTPS (Render, Railway, etc.), ouvrir l'URL dans Chrome, menu ⋮ → *Installer l'application*.
- Hors ligne : les pages déjà visitées restent lisibles ; la recherche, le quiz et l'assistant nécessitent le serveur.

> Non vérifié : l'installation réelle sur Android et PC (aucun navigateur disponible ici). Les fichiers PWA et leur service (manifeste, icônes, service worker) sont testés par pytest.

## Mettre l'application en ligne (pour la partager)

Fichiers fournis : `Procfile`, `render.yaml`, `gunicorn` dans `requirements.txt`. Commande de démarrage : `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4` (un seul processus, car la base SQLite est créée au premier démarrage).

Résumé (hébergeur type Render) : 1) mettre le projet sur GitHub (sans `.env`), 2) créer un *Web Service* relié au dépôt, 3) build `pip install -r requirements.txt`, 4) start = commande ci-dessus, 5) variables : `LLM_PROVIDER=demo`, `SECRET_KEY=<valeur aléatoire>`, 6) ouvrir l'URL HTTPS fournie. En HTTPS, l'application devient aussi installable sur Android.

Limites : les offres gratuites s'endorment après inactivité (premier chargement lent) et le disque est éphémère, ce qui est sans conséquence ici (base recréée au démarrage, favoris stockés dans le navigateur). Si vous activez une clé API en ligne, saisissez-la dans les variables d'environnement de l'hébergeur, jamais dans le code. **Non testé** : le déploiement réel et gunicorn n'ont pas été exécutés ici.


### Vercel et résolution des erreurs de démarrage

L'entrée Python est `app.py` (variable WSGI `app`). Sur Vercel, la variable
d'environnement `VERCEL` fait utiliser `/tmp/volt_explorer.sqlite3` pour SQLite,
car les fichiers du projet sont en lecture seule. Le programme et le quiz sont
chargés depuis `data/*.json` dans l'archive. Sur une installation locale ou sur
Render, la base se trouve dans `database/` par défaut (ou dans `DATABASE_PATH`).

Si le projet ne démarre pas après une ancienne installation, vérifiez que votre
`config.py` est la version corrigée et relancez `pip install -r requirements.txt`.
Pour repartir de données locales à jour, exécutez `python scripts/init_db.py`
(ceci recrée la base, sans toucher à vos favoris enregistrés dans le navigateur).

## Tests

```powershell
python -m pytest -q
```

Les tests couvrent les pages, les liens internes, les API (recherche, filtres, tri, quiz, assistant), l'intégrité des données, le fonctionnement hors ligne de l'assistant et l'absence de fuite de clé API.

## Assistant IA : modes et configuration

| `LLM_PROVIDER` | Comportement |
|---|---|
| `demo` (défaut) | Aucun service externe : l'assistant retrouve les passages pertinents et les reformule. Idéal pour la démonstration. |
| `anthropic` | Génération via l'API Anthropic. Renseigner `ANTHROPIC_API_KEY` dans `.env`. |
| `openai` | Génération via l'API OpenAI (ou compatible, avec `OPENAI_BASE_URL`). Renseigner `OPENAI_API_KEY`. |

Sans clé, un fournisseur choisi retombe automatiquement en mode démonstration (avec un message). Si l'appel au modèle échoue, la réponse est générée en mode démonstration. **Les clés ne sont lues que côté serveur** (`.env`, ignoré par Git) et ne sont jamais envoyées au navigateur.

> ⚠️ Les fournisseurs `anthropic` et `openai` n'ont **pas été testés contre les vrais services** (aucune clé disponible pendant le développement). Seuls la sélection du fournisseur, la forme de la requête (avec HTTP simulé) et le repli en cas d'erreur sont testés. Testez avec votre clé avant la démo si vous voulez montrer ce mode.

**PDF officiel (optionnel)** : placer le PDF dans `data/programme.pdf`. Ses passages (avec numéro de page réel) sont alors ajoutés à l'index de l'assistant au prochain démarrage.

## Fonctionnalités

- **Accueil**, **Programme** (structure du document), **Thématiques** (12 cartes), fiche détaillée de chaque proposition.
- **Explorer** : recherche instantanée (insensible aux accents/casse, mots-clés combinés), surlignage, filtres thématique / sous-thématique / type, tri alphabétique, sans rechargement de page.
- **Favoris** : `localStorage`, sans compte.
- **Quiz** : 14 questions, 3 niveaux, une question à la fois, correction et explication avec lien vers la proposition, barre de progression, score calculé côté serveur, recommencer.
- **Assistant IA** : RAG, réponses en français avec sources, refus des demandes de conseil de vote, message clair quand rien n'est trouvé.
- Interface responsive (menu mobile), accessible au clavier.

## Structure

```
volt_explorer/
├── app.py                  # fabrique Flask, services, gestion d'erreurs
├── config.py               # configuration (variables d'environnement)
├── data/                   # propositions.json, quiz.json (+ programme.pdf optionnel)
├── database/               # db.py (SQLite), models.py (requêtes)
├── routes/                 # main (pages), programme, search, quiz, assistant (API REST)
├── services/               # search, quiz, document_parser, rag, llm_providers, text_utils
├── templates/ static/      # interface
├── scripts/                # build_propositions.py, init_db.py
├── tests/                  # pytest
└── docs/ARCHITECTURE.md
```

Documentation technique détaillée : [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Écarts par rapport au cahier des charges

- **SQLAlchemy** : non utilisé. Il n'était pas installé dans l'environnement de développement et l'installation de paquets y était bloquée. La base utilise `sqlite3` (bibliothèque standard), isolée dans `database/` pour faciliter la migration vers SQLAlchemy/PostgreSQL.
- **ChromaDB / FAISS / embeddings** : non utilisés, pour la même raison. L'index RAG est un TF-IDF (scikit-learn) ; `RagIndex.retrieve()` est isolé pour être remplacé par une recherche vectorielle.
- **Bootstrap** : CSS personnalisé, sans dépendance (fonctionne hors ligne).
- **Interface non testée visuellement** dans un navigateur (pas de navigateur disponible) : tout le backend, les pages servies et la logique JavaScript (surlignage, favoris) sont testés, mais pas le rendu graphique ni le responsive. Parcourez les pages une fois avant la démo.

## Évolutions possibles

- Intégrer les autres documents officiels (législatives 2024, Moonshot, handicap) avec leurs propres références.
- Recherche sémantique (embeddings + ChromaDB), meilleure classification des mesures.
- SQLAlchemy + PostgreSQL, déploiement (Docker, Render, etc.).
- Mode comparaison de thématiques, export des favoris.
