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

## Ce que l'application permet

La WebUI permet de lancer, depuis un navigateur, les 6 types de génération du
programme. Chaque type produit des fichiers **GeoJSON** (compatibles QGIS),
souvent accompagnés d'une **carte PNG** et d'un **CSV**, écrits dans `output/`.

| Type | Ce que ça calcule / récupère | Période | Principales sorties |
|------|------------------------------|---------|---------------------|
| **Hydraulicité** | Niveau d'eau par rapport à la normale (1991-2020) | 1 mois | `QGIS/hydraulicite/*.geojson` + `.png` + `hydraulicite/*.csv` |
| **VCN3 / Périodes de retour** | Étiage : VCN3, période de retour, fréquence de non-dépassement | 1 mois | `VCN3/` (analyse, moyenne historique, graphiques par station) |
| **Hydraulicité + VCN3** | Les deux cartes ci-dessus, exécutées l'une après l'autre | 1 mois | les deux ensembles |
| **Météo France** | Données météo brutes ou SIM2 (SPI, SSWI, précipitations, évapotranspiration…) | intervalle | `QGIS/meteoFrance/` (GeoJSON + PNG + CSV par période) |
| **ONDE** | Écoulements des cours d'eau (campagnes usuelles ou toutes) | 1 mois | `onde/BSH_YYYY-MM/` (GeoJSON + PNG + CSV par zone) |
| **Stations et sites** | Liste de référence des stations et sites | — | `QGIS/stations/` + `QGIS/sites/` (GeoJSON + CSV) |

### Paramètres disponibles

| Paramètre | S'applique à | Valeurs / format | Défaut |
|-----------|-------------|------------------|--------|
| Mois / dates | tous | `AAAA-MM` (cartes mensuelles) ou `AAAA-MM-JJ` (météo quotidienne) | mois précédent |
| Réseau SANDRE | hydraulicité, VCN3, stations-sites | `BSH001`, `custom` | `BSH001` |
| Fréquence météo | météo | `MENS` (mensuelle), `QUOT` (quotidienne) | `QUOT` |
| Source météo | météo | `brut` (brutes), `sim2` (grille 8×8 km) | `sim2` |
| Échelle géographique | météo, ONDE | `NATIONAL`, `BASSIN`, `REGION_ADMINISTRATIVE`, `DEPARTEMENT_ADMINISTRATIF`, `REGION_BASSIN`, `DEPARTEMENT_BASSIN`, `ECOREGION_HYDROLOGIQUE` | `BASSIN` |
| Code de zone | ONDE | ex. `06` (Rhône-Méditerranée), `84` (Auvergne-Rhône-Alpes), `69` (Rhône) | selon l'échelle |
| Campagne ONDE | ONDE | `ALL` (usuelle + complémentaire), `USUELLE` | `ALL` |
| Graphiques VCN3 | VCN3 | coché / non coché | non |
| Agrégation météo | météo | coché (somme sur la période) / non (jour par jour) | coché |
| Mise à jour des données | météo | coché / non coché | non |

> Les valeurs par défaut sont identiques à celles du mode CLI et du mode
> interactif. Le formulaire s'adapte automatiquement au type choisi : seuls les
> champs pertinents s'affichent.

## Architecture

```
webui/
├── __init__.py
├── app.py              # Application FastAPI (routes API + flux SSE)
├── job_manager.py      # Gestion des jobs (sous-processus + capture des logs)
├── schema.py           # Types de génération + construction des commandes CLI
├── static/
│   ├── index.html      # Page unique (structure)
│   ├── style.css       # Styles
│   └── app.js          # Logique frontend (vanilla JS, sans build)
└── README.md
```

- **Backend** : FastAPI. Sert l'interface, expose l'API REST et diffuse les
  logs en temps réel via **SSE** (Server-Sent Events).
- **Frontend** : HTML/CSS/JS vanilla, aucune étape de build.
- **Exécution** : chaque job lance `python main.py --type ...` en
  sous-processus, dans le même environnement (venv) que le serveur.

## Comprendre le code

### Rôle de chaque fichier

| Fichier | Rôle |
|---------|------|
| `app.py` | Point d'entrée FastAPI. Sert la page, expose les routes API (`/api/types`, `/api/jobs`, …) et le flux SSE des logs. Ne contient **aucune** logique métier de génération. |
| `job_manager.py` | Classe `Job` (état + logs d'une tâche) et `JobManager` (création, suivi, annulation). Lance les commandes en sous-processus et capture leur sortie ligne à ligne. |
| `schema.py` | **Source de vérité** : décrit les 6 types (champs + valeurs par défaut) et traduit les valeurs du formulaire en arguments CLI (`build_commands`). |
| `static/index.html` | Structure de la page : formulaire + onglets Logs/Jobs. |
| `static/app.js` | Logique frontend : charge le schéma, rend le formulaire dynamique, lance les jobs, lit le flux SSE, gère les onglets. |
| `static/style.css` | Apparence (thème sombre). |

### Cycle de vie d'un job

```
pending ──▶ running ──▶ completed
                  ├──▶ failed      (code de retour non nul)
                  └──▶ cancelled   (annulé par l'utilisateur)
```

- **pending** : job créé, sous-processus pas encore démarré.
- **running** : sous-processus `main.py` en cours d'exécution.
- **completed** : toutes les commandes se sont terminées avec le code 0.
- **failed** : une commande a renvoyé un code non nul (le job s'arrête).
- **cancelled** : l'utilisateur a annulé (le processus est tué).

### Flux de données (depuis le clic sur « Lancer »)

```
[Formulaire] ──POST /api/jobs {type, params}──▶ [app.py]
                                                    │
                              build_commands(type, params)   ← schema.py
                                                    │
                              job_manager.create_job(cmds)   ← job_manager.py
                                                    │
                              subprocess : python main.py --type …
                                                    │
                              (sortie capturée ligne à ligne → job.logs)
                                                    │
[app.js] ──EventSource /api/jobs/{id}/events──▶ [app.py] ──SSE──▶ [console de logs]
```

1. Le frontend collecte les valeurs du formulaire et envoie `POST /api/jobs`.
2. `app.py` valide le type, appelle `build_commands()` pour obtenir la liste des
   commandes CLI.
3. `job_manager.create_job()` démarre un thread qui exécute les commandes en
   sous-processus et capture leur sortie.
4. Le frontend ouvre un flux SSE sur `/api/jobs/{id}/events` et affiche les
   logs au fur et à mesure.
5. À la fin, un événement de statut est émis ; le frontend met à jour l'onglet
   *Jobs*.

### Choix de conception

- **Sous-processus plutôt qu'appel direct de `main()`** : comportement
  strictement identique au mode CLI, isolation (un plantage ne fait pas tomber
  le serveur), annulation triviale (on tue le processus).
- **SSE plutôt que WebSocket** : le flux de logs est unidirectionnel
  (serveur → client) ; SSE est plus simple et suffit.
- **Vanilla JS sans build** : pas d'outillage, lisible, facile à maintenir.
- **`schema.py` comme source de vérité** : le formulaire et la construction des
  commandes CLI partagent la même définition des types — ajouter un type ne
  demande de toucher qu'à ce fichier.

### Ajouter un nouveau type de génération

1. Dans `schema.py`, ajoutez une entrée dans `build_types_schema()` (label,
   description, champs).
2. Dans `build_commands()`, ajoutez une branche qui traduit les paramètres en
   arguments CLI.
3. C'est tout : le formulaire s'adapte automatiquement (il est rendu depuis le
   schéma) et le job est lancé comme les autres.

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

Les fichiers générés sont écrits dans le dossier `output/` (format GeoJSON,
compatible QGIS). Vous pouvez **annuler** un job en cours via le bouton
*Annuler*.

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

## Sécurité

- L'API ne comporte **pas d'authentification** : elle est conçue pour un usage
  local (poste de travail / réseau interne de confiance).
