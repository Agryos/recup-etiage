"""
Mode CLI (Command Line Interface) pour générer des cartes et données hydrologiques/météorologiques.

Ce module contient les fonctions pour le mode CLI qui permet d'automatiser les tâches
via des arguments en ligne de commande.
"""

import argparse
from datetime import timedelta, datetime
import calendar

# Import des modules locaux
import src.plotting.plot_grandeur as plot_grandeur
import src.plotting.plot_meteoFrance as plot_meteoFrance
import src.plotting.plot_onde as plot_onde
from src.model.enums import OndeCampagneType, GeographicScaleClip, MeteoFranceDataType
from src.config.logging_config import setup_logger
from src.cli.utils import formater_date_vers_datetime

# Configuration du logger
logger = setup_logger(name="main_cli")


def setup_parser():
    """
    Configure et retourne le parseur d'arguments pour le mode CLI.
    
    Returns:
        argparse.ArgumentParser: Le parseur configuré
    """
    parser = argparse.ArgumentParser(
        description="Exporter des données hydrologiques/météorologiques sous forme de cartes GeoJSON.",
        epilog="Pour plus d'informations : https://github.com/Agryos/recup-etiage"
    )
    
    # Argument principal : type de carte
    parser.add_argument(
        "--type",
        choices=[
            "hydraulicite",
            "vcn3",
            "meteo_brut_MENS",
            "meteo_sim2_MENS",
            "meteo_brut_QUOT",
            "meteo_sim2_QUOT",
            "stations-sites",
            "onde_USUELLE",
            "onde_ALL"
        ],
        help="""
        Type de données à générer :
        - hydraulicite : Carte d'hydraulicité (niveaux d'eau) pour un mois
        - vcn3 : Carte de VCN3 et périodes de retour (étiage) pour un mois
        - meteo_brut_MENS : Données Météo France brutes mensuelles
        - meteo_sim2_MENS : Données Météo France SIM2 mensuelles
        - meteo_brut_QUOT : Données Météo France brutes quotidiennes
        - meteo_sim2_QUOT : Données Météo France SIM2 quotidiennes
        - stations-sites : Liste des stations et sites
        - onde_USUELLE : Données ONDE (campagnes usuelles)
        - onde_ALL : Données ONDE (toutes campagnes)
        """
    )
    
    # Arguments de dates
    parser.add_argument(
        "--start_date",
        help="Date de début au format AAAA-MM-JJ ou AAAA-MM (défaut : premier jour du mois précédent)"
    )
    parser.add_argument(
        "--end_date",
        help="Date de fin au format AAAA-MM-JJ ou AAAA-MM (défaut : dernier jour du mois précédent)"
    )
    
    # Arguments spécifiques
    parser.add_argument(
        "--reseau_sandre",
        help="Réseau SANDRE à utiliser (défaut : BSH001). Utilisez 'custom' pour la liste personnalisée"
    )
    parser.add_argument(
        "--vcn3_graphic",
        action='store_true',
        help="[VCN3] Générer des graphiques individuels pour chaque station"
    )
    parser.add_argument(
        "--geographic_scale",
        choices=[
            GeographicScaleClip.NATIONAL,
            GeographicScaleClip.BASSIN,
            GeographicScaleClip.REGION_ADMINISTRATIVE,
            GeographicScaleClip.DEPARTEMENT_ADMINISTRATIF,
            GeographicScaleClip.REGION_BASSIN,
            GeographicScaleClip.DEPARTEMENT_BASSIN,
            GeographicScaleClip.ECOREGION_HYDROLOGIQUE
        ],
        help="[météo/onde] Échelle géographique (défaut : BASSIN)",
        default=GeographicScaleClip.BASSIN
    )
    parser.add_argument(
        "--onde_zone_code",
        help="[onde] Code de la zone géographique (ex : '06' pour bassin Rhône-Méditerranée)"
    )
    parser.add_argument(
        "--meteo_aggregate",
        action='store_true',
        help="[météo] Aggréger les données sur la période sélectionnée"
    )
    parser.add_argument(
        "--meteo_no_index_update",
        action='store_false',
        help="[météo] Ne pas mettre à jour l'index de correspondance des datasets"
    )
    parser.add_argument(
        "--meteo_no_update",
        action='store_false',
        help="[météo] Ne pas mettre à jour les données (désactive aussi mise à jour index)"
    )
    
    return parser


def mode_cli(args):
    """
    Exécute le script en mode CLI avec les arguments fournis.
    
    Args:
        args: Les arguments parsés par argparse
    """
    aujourdhui = datetime.now()
    
    # Initialisation des variables
    start_date = None
    end_date = None
    
    # Date de début
    if args.start_date:
        start_date = formater_date_vers_datetime(args.start_date, est_debut=True)
    
    if start_date is None:
        start_date = (aujourdhui.replace(day=1) - timedelta(days=1)).replace(day=1)
        logger.info(f"Date de début par défaut : {start_date}")
    
    # Date de fin
    if args.end_date:
        end_date = formater_date_vers_datetime(args.end_date, est_debut=False)
    
    if end_date is None:
        end_date = start_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        logger.info(f"Date de fin par défaut : {end_date}")
    
    # Réseau Sandre par défaut
    reseau_sandre = args.reseau_sandre if args.reseau_sandre else "BSH001"
    
    # Appel de la fonction principale
    main(
        type_carte=args.type,
        start_date=start_date,
        end_date=end_date,
        reseau_sandre=reseau_sandre,
        has_vcn3_graphic=args.vcn3_graphic,
        has_meteo_aggregate=args.meteo_aggregate,
        has_meteo_index_update=not args.meteo_no_index_update,
        is_data_update_allowed=not args.meteo_no_update,
        geographic_scale=args.geographic_scale,
        code_zone=args.onde_zone_code if args.onde_zone_code else "01"
    )


def main(
    type_carte: str,
    start_date: datetime,
    end_date: datetime,
    reseau_sandre: str,
    has_vcn3_graphic: bool = False,
    has_meteo_aggregate: bool = False,
    has_meteo_index_update: bool = True,
    is_data_update_allowed: bool = True,
    geographic_scale: GeographicScaleClip = GeographicScaleClip.BASSIN,
    code_zone: str = "01",
):
    """
    Fonction principale qui génère les GeoJSON en fonction des paramètres.
    
    Args:
        type_carte: Type de carte à générer
        start_date: Date de début
        end_date: Date de fin
        reseau_sandre: Réseau SANDRE à utiliser
        has_vcn3_graphic: Si True, génère les graphiques individuels pour VCN3
        has_meteo_aggregate: Si True, aggrège les données météo
        has_meteo_index_update: Si True, met à jour l'index météo
        is_data_update_allowed: Si True, autorise la mise à jour des données
        geographic_scale: Échelle géographique pour les données météo/onde
        code_zone: Code de la zone géographique pour ONDE
    """
    if not is_data_update_allowed:
        has_meteo_index_update = False
    
    # Exécution en fonction du type de carte
    if type_carte == "hydraulicite":
        logger.info("Génération de la carte d'hydraulicité...")
        plot_grandeur.create_geojson_from_hydraulicite(
            start_date.strftime("%Y-%m"),
            reseau_sandre
        )
    
    elif type_carte == "vcn3":
        logger.info("Génération de la carte VCN3/périodes de retour...")
        plot_grandeur.create_geojson_from_periode_de_retour(
            start_date.strftime("%Y-%m"),
            reseau_sandre,
            has_vcn3_graphic
        )
    
    elif type_carte == "meteo_brut_MENS":
        logger.info("Génération des données Météo France brutes mensuelles...")
        plot_meteoFrance.export_all_format_geojson_range(
            geographic_scale,
            MeteoFranceDataType.MENS,
            start_date,
            end_date,
            is_data_aggregated=has_meteo_aggregate,
            has_index_update=has_meteo_index_update,
            is_data_update_allowed=is_data_update_allowed
        )
    
    elif type_carte == "meteo_sim2_MENS":
        logger.info("Génération des données Météo France SIM2 mensuelles...")
        plot_meteoFrance.export_all_format_geojson_range(
            geographic_scale,
            MeteoFranceDataType.SIM2_MENS,
            start_date,
            end_date,
            is_data_aggregated=has_meteo_aggregate,
            has_index_update=has_meteo_index_update,
            is_data_update_allowed=is_data_update_allowed
        )
    
    elif type_carte == "meteo_brut_QUOT":
        logger.info("Génération des données Météo France brutes quotidiennes...")
        plot_meteoFrance.export_all_format_geojson_range(
            geographic_scale,
            MeteoFranceDataType.QUOT,
            start_date,
            end_date,
            is_data_aggregated=has_meteo_aggregate,
            has_index_update=has_meteo_index_update,
            is_data_update_allowed=is_data_update_allowed
        )
    
    elif type_carte == "meteo_sim2_QUOT":
        logger.info("Génération des données Météo France SIM2 quotidiennes...")
        plot_meteoFrance.export_all_format_geojson_range(
            geographic_scale,
            MeteoFranceDataType.SIM2_QUOT,
            start_date,
            end_date,
            is_data_aggregated=has_meteo_aggregate,
            has_index_update=has_meteo_index_update,
            is_data_update_allowed=is_data_update_allowed
        )
    
    elif type_carte == "onde_USUELLE":
        logger.info("Génération des données ONDE (campagnes usuelles)...")
        plot_onde.plot_everything(
            OndeCampagneType.USUELLE,
            start_date,
            geographic_scale,
            code_zone
        )
    
    elif type_carte == "onde_ALL":
        logger.info("Génération des données ONDE (toutes campagnes)...")
        plot_onde.plot_everything(
            OndeCampagneType.ALL_CAMPAGNE,
            start_date,
            geographic_scale,
            code_zone
        )
    
    elif type_carte == "stations-sites":
        logger.info("Génération des stations et sites...")
        # Générer les fichiers de base
        plot_grandeur.create_geojson_from_stations(reseau_sandre, start_date.strftime("%Y-%m"))
        plot_grandeur.create_geojson_from_sites(reseau_sandre)
        plot_grandeur.create_geojson_from_stations(reseau_sandre, None)
        plot_grandeur.create_geojson_from_stations(None, None)
        plot_grandeur.create_geojson_from_sites(None)
    
    else:
        raise NotImplementedError(f"Type de carte non implémenté : {type_carte}")
