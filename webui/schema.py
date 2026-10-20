"""
Définition des types de génération et construction des commandes CLI.

Ce module est la source de vérité pour la WebUI : il décrit, pour chaque type de
génération, les champs du formulaire (avec leurs valeurs par défaut) et traduit
les valeurs saisies en arguments de la ligne de commande ``python main.py ...``.

Les valeurs par défaut reproduisent fidèlement celles du mode CLI et du mode
interactif (voir ``src/cli/main_cli.py`` et ``src/cli/main_interactive.py``).
"""

import calendar
import sys
from datetime import datetime, timedelta
from typing import List, Optional

# Échelles géographiques disponibles (miroir de GeographicScaleClip).
GEOGRAPHIC_SCALES = [
    "NATIONAL",
    "BASSIN",
    "REGION_ADMINISTRATIVE",
    "DEPARTEMENT_ADMINISTRATIF",
    "REGION_BASSIN",
    "DEPARTEMENT_BASSIN",
    "ECOREGION_HYDROLOGIQUE",
]

# Code de zone ONDE par défaut selon l'échelle géographique (miroir du mode interactif).
ONDE_ZONE_DEFAULTS = {
    "NATIONAL": "",
    "BASSIN": "06",
    "REGION_ADMINISTRATIVE": "84",
    "REGION_BASSIN": "84",
    "DEPARTEMENT_ADMINISTRATIF": "69",
    "DEPARTEMENT_BASSIN": "69",
    "ECOREGION_HYDROLOGIQUE": "1",
}


def _default_dates() -> dict:
    """Dates par défaut : premier et dernier jour du mois précédent."""
    aujourdhui = datetime.now()
    debut = (aujourdhui.replace(day=1) - timedelta(days=1)).replace(day=1)
    dernier_jour = calendar.monthrange(debut.year, debut.month)[1]
    fin = debut.replace(day=dernier_jour)
    return {
        "month": debut.strftime("%Y-%m"),
        "start": debut.strftime("%Y-%m-%d"),
        "end": fin.strftime("%Y-%m-%d"),
    }


def _reseau_field() -> dict:
    return {
        "name": "reseau_sandre",
        "label": "Réseau SANDRE",
        "type": "select",
        "options": ["BSH001", "custom"],
        "default": "BSH001",
        "help": "BSH001 (par défaut) ou custom (liste personnalisée).",
    }


def build_types_schema() -> dict:
    """Retourne le schéma des types de génération, prêt à être servi au frontend."""
    d = _default_dates()
    return {
        "hydraulicite": {
            "label": "Hydraulicité",
            "description": "Niveaux d'eau par rapport à la normale (1 mois).",
            "fields": [
                {"name": "start_date", "label": "Mois (AAAA-MM)", "type": "month",
                 "default": d["month"]},
                _reseau_field(),
            ],
        },
        "vcn3": {
            "label": "VCN3 / Périodes de retour",
            "description": "Étiage : VCN3, période de retour, fréquence de non-dépassement (1 mois).",
            "fields": [
                {"name": "start_date", "label": "Mois (AAAA-MM)", "type": "month",
                 "default": d["month"]},
                _reseau_field(),
                {"name": "vcn3_graphic", "label": "Graphiques individuels par station",
                 "type": "checkbox", "default": False},
            ],
        },
        "both": {
            "label": "Hydraulicité + VCN3",
            "description": "Les deux cartes Hubeau (plus long au premier lancement).",
            "fields": [
                {"name": "start_date", "label": "Mois (AAAA-MM)", "type": "month",
                 "default": d["month"]},
                _reseau_field(),
                {"name": "vcn3_graphic", "label": "Graphiques individuels VCN3",
                 "type": "checkbox", "default": False},
            ],
        },
        "meteo": {
            "label": "Météo France",
            "description": "Données Météo France (brutes ou SIM2, mensuelles ou quotidiennes).",
            "fields": [
                {"name": "meteo_freq", "label": "Fréquence", "type": "select",
                 "options": ["QUOT", "MENS"], "default": "QUOT",
                 "help": "QUOT = quotidienne, MENS = mensuelle."},
                {"name": "meteo_source", "label": "Source", "type": "select",
                 "options": ["sim2", "brut"], "default": "sim2",
                 "help": "sim2 = grille 8x8 km, brut = données brutes."},
                {"name": "geographic_scale", "label": "Échelle géographique",
                 "type": "select", "options": GEOGRAPHIC_SCALES, "default": "BASSIN"},
                {"name": "start_date", "label": "Date de début", "type": "date",
                 "default": d["start"]},
                {"name": "end_date", "label": "Date de fin (inclusive)", "type": "date",
                 "default": d["end"]},
                {"name": "meteo_aggregate", "label": "Agrégation sur la période",
                 "type": "checkbox", "default": True,
                 "help": "Si non coché, des graphiques jour par jour sont générés."},
                {"name": "meteo_no_update", "label": "Ne pas mettre à jour les données",
                 "type": "checkbox", "default": False},
                {"name": "meteo_no_index_update", "label": "Ne pas mettre à jour l'index",
                 "type": "checkbox", "default": False},
            ],
        },
        "onde": {
            "label": "ONDE",
            "description": "Écoulements des cours d'eau (campagnes usuelles ou toutes).",
            "fields": [
                {"name": "onde_campagne", "label": "Type de campagne", "type": "select",
                 "options": ["ALL", "USUELLE"], "default": "ALL",
                 "help": "ALL = usuelle + complémentaire, USUELLE = usuelle uniquement."},
                {"name": "geographic_scale", "label": "Échelle géographique",
                 "type": "select", "options": GEOGRAPHIC_SCALES, "default": "BASSIN"},
                {"name": "onde_zone_code", "label": "Code de zone", "type": "text",
                 "default": "06", "placeholder": "ex : 06 (Rhône-Méditerranée)"},
                {"name": "start_date", "label": "Mois (AAAA-MM)", "type": "month",
                 "default": d["month"]},
            ],
        },
        "stations-sites": {
            "label": "Stations et sites",
            "description": "Liste de référence des stations et sites.",
            "fields": [
                _reseau_field(),
                {"name": "start_date", "label": "Mois (AAAA-MM, optionnel)", "type": "month",
                 "default": d["month"],
                 "help": "Laisser vide pour toutes les stations."},
            ],
        },
    }


def build_commands(
    type_key: str,
    params: dict,
    python_executable: Optional[str] = None,
    main_script: str = "main.py",
) -> List[List[str]]:
    """
    Construit la liste des commandes CLI à exécuter pour un type de génération.

    Args:
        type_key: Clé du type (hydraulicite, vcn3, both, meteo, onde, stations-sites).
        params: Valeurs saisies dans le formulaire.
        python_executable: Interpréteur Python (défaut : celui du serveur).
        main_script: Chemin du script principal (défaut : main.py).

    Returns:
        Liste de commandes (chaque commande est une liste d'arguments).
    """
    py = python_executable or sys.executable
    base = [py, main_script]

    if type_key == "hydraulicite":
        return [base + [
            "--type", "hydraulicite",
            "--start_date", params["start_date"],
            "--reseau_sandre", params["reseau_sandre"],
        ]]

    if type_key == "vcn3":
        cmd = base + [
            "--type", "vcn3",
            "--start_date", params["start_date"],
            "--reseau_sandre", params["reseau_sandre"],
        ]
        if params.get("vcn3_graphic"):
            cmd.append("--vcn3_graphic")
        return [cmd]

    if type_key == "both":
        cmd1 = base + [
            "--type", "hydraulicite",
            "--start_date", params["start_date"],
            "--reseau_sandre", params["reseau_sandre"],
        ]
        cmd2 = base + [
            "--type", "vcn3",
            "--start_date", params["start_date"],
            "--reseau_sandre", params["reseau_sandre"],
        ]
        if params.get("vcn3_graphic"):
            cmd2.append("--vcn3_graphic")
        return [cmd1, cmd2]

    if type_key == "meteo":
        freq = params["meteo_freq"]  # QUOT | MENS
        source = params["meteo_source"]  # sim2 | brut
        type_carte = f"meteo_{source}_{freq}"
        cmd = base + [
            "--type", type_carte,
            "--start_date", params["start_date"],
            "--end_date", params["end_date"],
            "--geographic_scale", params["geographic_scale"],
        ]
        if params.get("meteo_aggregate"):
            cmd.append("--meteo_aggregate")
        if params.get("meteo_no_update"):
            cmd.append("--meteo_no_update")
        if params.get("meteo_no_index_update"):
            cmd.append("--meteo_no_index_update")
        return [cmd]

    if type_key == "onde":
        campagne = params["onde_campagne"]  # ALL | USUELLE
        type_carte = f"onde_{campagne}"
        cmd = base + [
            "--type", type_carte,
            "--start_date", params["start_date"],
            "--geographic_scale", params["geographic_scale"],
        ]
        zone = (params.get("onde_zone_code") or "").strip()
        if zone:
            cmd += ["--onde_zone_code", zone]
        return [cmd]

    if type_key == "stations-sites":
        cmd = base + [
            "--type", "stations-sites",
            "--reseau_sandre", params["reseau_sandre"],
        ]
        if (params.get("start_date") or "").strip():
            cmd += ["--start_date", params["start_date"]]
        return [cmd]

    raise ValueError(f"Type de génération inconnu : {type_key}")
