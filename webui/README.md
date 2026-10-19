# WebUI de Recup-Etiage

Interface web pour lancer les scripts de génération de cartes hydrologiques et
météorologiques. Elle reprend **les mêmes fonctionnalités que le mode interactif
et le mode CLI** :

- Les 6 entrées du menu interactif (hydraulicité, VCN3, les deux, Météo France,
  ONDE, stations et sites).
- L'ensemble des options du mode CLI (dates, réseau SANDRE, échelle
  géographique, code de zone, agrégation, graphiques, mise à jour des données…).

Chaque génération est exécutée en **sous-processus** (`python main.py ...`), ce
qui garantit un comportement strictement identique au mode CLI, une isolation
complète (un plantage ne fait pas tomber le serveur) et une annulation simple.

## Architecture

```
webui/
├── __init__.py
├── app.py              # Application FastAPI (routes API + service des fichiers)
├── job_manager.py      # Gestion des jobs (sous-processus + capture des logs)
├── schema.py           # Types de génération + construction des commandes CLI
├── static/
│   ├── index.html      # Page unique
│   ├── style.css       # Styles
│   └── app.js          # Logique frontend (vanilla JS, sans build)
└── README.md
```

- **Backend** : FastAPI. Sert l'interface, expose l'API REST, diffuse les logs
  en temps réel via **SSE** (Server-Sent Events) et sert les fichiers de
  `output/`.
- **Frontend** : HTML/CSS/JS vanilla, aucune étape de build.
- **Exécution** : chaque job lance `python main.py --type ...` en
  sous-processus, dans le même environnement (venv) que le serveur.

## Installation

La WebUI s'appuie sur les dépendances du projet. Ajoutez les dépendances web :

```bash
# Linux / macOS
pip install -r requirements-webui.txt

# Windows (venv)
.\venv\Scripts\pip.exe install -r requirements-webui.txt
```

## Lancement

Depuis la racine du projet, dans le venv :

```bash
python -m webui.app
```

Ou via les scripts fournis :

- **Linux / macOS** : `./run_webui.sh`
- **Windows** : double-cliquer sur `run_webui.bat`

Puis ouvrez **http://127.0.0.1:8000** dans votre navigateur.

### Options de lancement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `WEBUI_HOST` | `127.0.0.1` | Interface d'écoute |
| `WEBUI_PORT` | `8000` | Port d'écoute |

Exemple : `WEBUI_PORT=9000 python -m webui.app`

> Le serveur écoute par défaut sur `127.0.0.1` (machine locale uniquement).
> Pour l'exposer au réseau, passez `WEBUI_HOST=0.0.0.0` — à faire uniquement
> sur un réseau de confiance, l'API ne comporte pas d'authentification.

## Utilisation

1. **Choisissez le type de génération** (menu déroulant).
2. **Renseignez les paramètres** : les champs s'adaptent au type choisi, avec
   les mêmes valeurs par défaut que le mode CLI/interactif.
3. **Lancez la génération**. Les logs s'affichent en direct dans l'onglet
   *Logs*.
4. **Suivez l'état** dans l'onglet *Jobs* (en cours, terminé, échec, annulé).
5. **Parcourez les résultats** dans l'onglet *Résultats* : navigation dans
   `output/`, clic sur un fichier pour l'ouvrir/télécharger.

Vous pouvez **annuler** un job en cours via le bouton *Annuler*.

## Correspondance avec le mode CLI

| Type WebUI | Commande CLI équivalente |
|------------|--------------------------|
| Hydraulicité | `--type hydraulicite --start_date AAAA-MM --reseau_sandre X` |
| VCN3 | `--type vcn3 --start_date AAAA-MM --reseau_sandre X [--vcn3_graphic]` |
| Hydraulicité + VCN3 | les deux commandes ci-dessus, exécutées l'une après l'autre |
| Météo France | `--type meteo_{brut\|sim2}_{MENS\|QUOT} --start_date … --end_date … --geographic_scale … [--meteo_aggregate] [--meteo_no_update] [--meteo_no_index_update]` |
| ONDE | `--type onde_{USUELLE\|ALL} --start_date AAAA-MM --geographic_scale … [--onde_zone_code …]` |
| Stations et sites | `--type stations-sites --reseau_sandre X [--start_date AAAA-MM]` |

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/health` | État du service |
| `GET` | `/api/types` | Schéma du formulaire (types + champs) |
| `POST` | `/api/jobs` | Crée un job — corps : `{"type": …, "params": {…}}` |
| `GET` | `/api/jobs` | Liste des jobs |
| `GET` | `/api/jobs/{id}` | Statut d'un job |
| `POST` | `/api/jobs/{id}/cancel` | Annule un job |
| `GET` | `/api/jobs/{id}/events` | Flux SSE des logs d'un job |
| `GET` | `/api/output?path=…` | Liste le contenu d'un sous-dossier de `output/` |
| `GET` | `/api/output/file?path=…` | Sert un fichier de `output/` |

## Sécurité

- L'API ne comporte **pas d'authentification** : elle est conçue pour un usage
  local (poste de travail / réseau interne de confiance).
- L'accès aux fichiers est restreint au dossier `output/` (protection contre la
  traversée de chemin).
