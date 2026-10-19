# AGENTS.md

Ce fichier encadre la rédaction de code dans ce dépôt. Il est volontairement simple et court : n'importe qui peut le lire et le modifier.

> **Règle d'or** : toute modification se fait dans une **branche**, puis est **validée par un humain** avant d'atteindre `master`. Un robot (IA, agent, script) ne fusionne jamais tout seul.

---

## 1. Le projet en une phrase

Outil Python qui récupère, analyse et visualise des données hydrologiques et météo françaises (Hub'Eau, MétéoFrance, ONDE) et génère des cartes au format GeoJSON pour QGIS.

- **Langage** : Python 3.11+
- **Point d'entrée** : `main.py` (mode interactif sans argument, mode CLI avec `--type`)

## 2. Structure

```
recup-etiage/
├── main.py              # Point d'entrée (interactif + CLI)
├── src/
│   ├── cli/             # Interface CLI et mode interactif
│   ├── config/          # Configuration, logging, chemins, styles
│   ├── io/              # Téléchargement (Hub'Eau, MétéoFrance, Pynsee)
│   ├── model/           # Enums et utilitaires de modèle
│   ├── plotting/        # Cartes et graphiques
│   ├── processing/      # Calculs (hydraulicité, VCN3, nettoyage, météo, ONDE)
│   └── utils/           # Fonctions utilitaires
├── tests/
│   ├── unit/            # Tests unitaires
│   └── integration/     # Tests d'intégration
├── scripts/             # Scripts d'aide (mise à jour, tests)
├── output/              # Résultats générés (ignoré par git)
└── data/                # Données
```

## 3. Lancer le programme

```bash
# Installation (installe les dépendances dans le venv)
install.bat        # Windows
install.sh         # Linux

# Lancer le programme
python main.py                          # mode interactif
python main.py --type hydraulicite      # mode CLI
```

## 4. Conventions de code

- **Langage des commentaires et docstrings** : français.
- **Logger** : toujours via `setup_logger(name="...")` (depuis `src.config.logging_config`), jamais `print`.
- **Types** : indiquer les types des paramètres et retours quand c'est simple.
- **Docstrings** : décrire le rôle de la fonction, ses `:param:` et `:return:`.
- **Pas de données sensibles** : ne jamais committer `.env` (proxy, webhook). Utiliser `.env_example` comme modèle.

## 5. Tests

Deux niveaux de tests, du plus rapide au plus long :

### 1. Tests pytest (unitaires + intégration) — rapides, sans réseau

- **Où** : `tests/unit/` (une fonction à la fois) et `tests/integration/` (plusieurs modules ensemble).
- **Config** : `pytest.ini` (`testpaths`, `pythonpath = src`, marqueurs).
- **Fixtures partagées** : `tests/conftest.py` (DataFrames d'exemple, `temp_dir`, et un fixture `autouse` qui redirige `OUTPUT_DIR`/`DATA_DIR` vers un dossier temporaire).
- **Règle d'or : tout est mocké.** Les accès réseau (Hub'Eau, MétéoFrance, `requests`) et le système de fichiers sont mockés avec `unittest.mock.patch` / `MagicMock`. Un test unitaire ne doit **jamais** toucher à internet ni écrire dans `output/`.
- **Marqueurs** : `@pytest.mark.network` (nécessite internet), `@pytest.mark.slow` (long), `@pytest.mark.integration`.

```bash
pytest                                  # tous les tests
pytest -m "not network"                 # sans les tests qui nécessitent internet
pytest -m "not slow"                    # sans les tests lents
pytest tests/unit/test_processing.py    # un seul fichier
pytest -k hydraulicite                  # filtrer par nom
```

### 2. Tests de bout en bout (commandes réelles) — longs

`scripts/run_test_commands.py` exécute les vraies commandes CLI de `commande_test.txt`, vérifie que les fichiers générés dans `output/` ne sont pas vides, et notifie Discord en cas d'échec. C'est la validation « ça marche vraiment » (VCN3 peut prendre 2-3 h au premier run).

```bash
python scripts/run_test_commands.py --dry-run          # voir les commandes sans les lancer
python scripts/run_test_commands.py --filter "meteo"   # un sous-ensemble
```

### Ce qu'il faut faire
- **Toute nouvelle fonction** de `src/processing/` ou `src/io/` doit avoir un test dans `tests/unit/`.
- **Tout bug corrigé** doit être accompagné d'un test qui aurait échoué avant le fix (régression).
- Lancer `pytest -m "not network"` avant de pousser une branche.

## 6. Documentation

La documentation vit dans `docs/` et est publiée en **site statique Jekyll** (thème `minima`) sur GitHub Pages : https://agryos.github.io/recup-etiage/

### Structure (miroir du code)

```
docs/
├── index.md              # Accueil
├── getting-started.md    # Guide de démarrage
├── usage/                # Mode interactif et CLI
├── modules/              # Une page par module (miroir de src/)
│   ├── processing/       #   ex. calcul_hydraulicite.md
│   ├── io/
│   ├── plotting/
│   └── ...
├── concepts/             # Explications des concepts (hydraulicité, VCN3, SPI...)
├── data/                 # Sources de données et format de sortie
└── api/reference.md      # Référence API
```

### Règle : le code et la doc avancent ensemble
- **Toute modification de code doit être accompagnée de la mise à jour de la page de doc correspondante** dans `docs/modules/`.
- Ajouter une fonction publique dans `src/processing/calcul_hydraulicite.py` → mettre à jour `docs/modules/processing/calcul_hydraulicite.md`.
- Changer un comportement documenté (format de sortie, option CLI, concept) → mettre à jour la page concernée (`usage/`, `data/`, `concepts/`).
- `README.md` reste la porte d'entrée : ne le mettre à jour que pour les changements visibles par l'utilisateur final (commandes, installation, options).

### Format d'une page de module
Chaque page de module suit le même modèle :
- **Front matter** Jekyll : `layout`, `title`, `description`, `nav_order`, `parent` / `grand_parent` (pour la navigation).
- **Une section par fonction** : description, exemple d'import + d'appel, paramètres, processus, résultat.
- **Exemple complet** et **liens croisés** vers les pages liées.

> La doc est en français, comme le code.

## 7. Workflow Git (à respecter)

Toute modification suit ce cycle :

```
branche → commits → push → validation humaine → merge sur master
```

### Ce qu'il faut faire
1. **Créer une branche** depuis `master` pour chaque changement.
   - Nom : `<type>/<description-courte>` (ex. `fix/vcn3-telechargement`, `feat/carte-sswi`).
2. **Committer** avec des messages au format conventionnel : `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`.
3. **Pousser la branche** et demander la validation.

### Ce qu'il ne faut PAS faire
- **Ne jamais committer ou pousser directement sur `master`.**
- **Ne jamais fusionner (merge) une branche sur `master` tout seul.** C'est un humain qui valide et fusionne.
- **Ne jamais forcer un push** (`git push --force`) sur une branche partagée.

> En pratique : l'agent prépare la branche, la pousse, puis s'arrête. L'humain relit les changements et décide du merge.
