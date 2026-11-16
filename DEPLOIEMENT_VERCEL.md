# Volt Explorer — correction du déploiement Vercel

## Pourquoi le déploiement échouait

Le dépôt GitHub `ytahaxx/volt2.0` contenait une configuration `package.json` et
`vercel.json` qui exécutaient `node scripts/build.mjs`, mais aucun fichier
`scripts/build.mjs` n'existait. De plus, les fichiers qui doivent se trouver
à l'intérieur de `routes/`, `database/`, `services/`, `templates/` et `static/`
avaient été mis **directement à la racine**. L'application ne peut pas importer
ses modules ni trouver ses modèles HTML sous cette structure.

## Correctif inclus

- Application Flask dans `app.py` et dépendances dans `pyproject.toml` / `requirements.txt`.
- Pas de `package.json` et **aucune commande Node.js de build**.
- Configuration `vercel.json` sans `buildCommand` ni `outputDirectory`.
- `.python-version` : Python 3.12.
- Répertoire `public/static/` : CSS, JS, icônes, manifeste pour le CDN Vercel.
- `public/sw.js` : service worker à la racine, compatible PWA.
- SQLite sur `/tmp` sur Vercel (création automatique à partir du JSON).

## IMPORTANT : remplacer le contenu du dépôt, sans l'aplatir

Ne déposez pas le ZIP directement dans GitHub : GitHub ne l'extrait pas.
Ne téléversez pas non plus les fichiers un par un depuis les sous-dossiers.
Il faut conserver les répertoires de l'archive.

Avec Git installé sur PC :

```bash
git clone https://github.com/ytahaxx/volt2.0.git
cd volt2.0
git rm -r -- .
# Extraire MAINTENANT tous les fichiers de ce ZIP directement dans volt2.0/
# Les dossiers routes/, templates/, data/, static/, services/, etc. doivent être présents.
git add -A
git commit -m "Fix Flask project structure and Vercel deployment"
git push origin main
```

**Attention :** `git rm -r -- .` supprime les fichiers actuellement suivis dans
ce dépôt : assurez-vous d'avoir une copie de travail avant de remplacer
l'ancienne version aplatie. Ne supprimez pas le dossier caché `.git`.

Dans Vercel > Project > Settings > Build and Deployment :

1. Framework Preset : **Flask** (ou détection automatique Flask).
2. Root Directory : la **racine du dépôt** (là où se trouve `app.py`).
3. Build Command : **aucune surcharge** (Override désactivé).
4. Output Directory : **aucune surcharge** (Override désactivé).
5. Install Command : **aucune surcharge** (Override désactivé).
6. Redéployer le dernier commit (Deployments > Redeploy).

Aucune variable `LLM_PROVIDER` n'est nécessaire pour le mode de démonstration.
Pour une intégration LLM, renseigner la clé en variables Vercel, jamais dans Git.

## Vérifications après déploiement

- `/` doit afficher la page d'accueil.
- `/thematiques`, `/explorer` et `/quiz` doivent charger.
- `/static/css/style.css` doit répondre avec une feuille CSS.
- `/sw.js` et `/static/manifest.webmanifest` doivent être accessibles.

**Limitation :** les fichiers de `/tmp` sur Vercel sont éphémères.
C'est suffisant pour cette base de démonstration en lecture seule, qui est
reconstruite depuis les propositions JSON. Ne pas y stocker de données
utilisateur persistantes.

Ce paquet a été validé statiquement ; le déploiement sur Vercel n'a pas été
exécuté ici.
