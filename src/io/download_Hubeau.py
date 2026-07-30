import pandas as pd
import geopandas as gpd
from cl_hubeau import hydrometry
from datetime import datetime
from cl_hubeau import watercourses_flow
import calendar
import logging
import src.utils.utils as utils
import src.utils.utils_proxy as utils_proxy
from src.model.enums import GeographicScaleClip
from functools import cache
import src.config.init_project
from src.config.logging_config import setup_logger
from src.io.pynsee_departement import get_departements_from_regions

# Initialiser le logger
logger = setup_logger(name="download_Hubeau")
import src.utils.utils_file as utils_file

# TELECHARGEMENT DONNEES MENSUELLES

def ensure_grandeur_mensuel_downloaded(annee_mois:str, grandeur:str):
    """
    S'assure que le fichier contenant la grandeur mensuel est téléchargé et à jour
    :param annee_mois: AAAA-MM
    :param grandeur: Une grandeur à télécharger
    :return: Rien
    """
    complete_path = utils.get_path_mensuel_raw_csv(annee_mois,grandeur)
    if utils_file.is_file_need_download(complete_path):
        logging.info(f"Téléchargement du fichier en cours : {complete_path}")
        download_hubeau_AURA_mois(annee_mois,grandeur)
        logging.info(f"Téléchargement du fichier terminé : {complete_path}")


def download_hubeau_AURA_mois(annee_mois : str, grandeur : str):
    """
    Télécharge les observations élaboré via l'api Hubeau dans le dossier OUTPUT_DIR/hubeau/downloaded_data/observations_elaboree.
    :param annee_mois: L'année et le mois à télécharger au format AAAA-MM
    :param grandeur: La grandeur à télécharger parmis -> HIXM, HIXnJ, QINM, QINnJ, QixM, QIXnJ, QmM ou QmnJ
    """
    # initialisation du proxy
    utils_proxy.set_up_working_proxy()

    # Bounding box grossière du bassin versant Auvergne-Rhône-Alpes
    bounding_box_grossiere = [1.142578, 42.039587, 8.481445, 49.612271]

    dernier_jour = calendar.monthrange(int(annee_mois[0:4]), int(annee_mois[5:7]))[1]

    date_debut_observation = f"{annee_mois}-01"
    date_fin_observation = f"{annee_mois}-{dernier_jour}"

    logger.info(f"Téléchargement de la période  : {date_debut_observation}->{date_fin_observation}")
    logger.info(f"Téléchargement de la grandeur : {grandeur}")

    grandeur_hydro = [grandeur]

    # Format des données souhaité, pour n'avoir que les bons champs parmi
    # code_site,code_station,date_obs_elab,resultat_obs_elab,date_prod,code_statut,libelle_statut,code_methode,libelle_methode,code_qualification,libelle_qualification,longitude,latitude,grandeur_hydro_elab
    format_attendu = [
        "code_site",
        "code_station",
        "date_obs_elab",
        "resultat_obs_elab",
        "date_prod",
        "libelle_statut",
        "libelle_methode",
        "libelle_qualification",
    ]

    dataframe_observation = hydrometry.get_observations(
        date_debut_obs_elab=date_debut_observation,
        date_fin_obs_elab=date_fin_observation,
        grandeur_hydro_elab=grandeur_hydro,
        bbox=bounding_box_grossiere,
        fields=format_attendu,
    )

    chemin_fichier = utils.get_path_mensuel_raw_csv(annee_mois,grandeur)
    dataframe_observation.to_csv(chemin_fichier)
    logger.info(f"Fichier téléchargé : {chemin_fichier}")


def ensure_grandeur_historique_downloaded(grandeur:str):
    """
    Garantie que les données historiques pour la grandeur sont téléchargées.
    :param grandeur: La grandeur téléchargée souhaitée
    :return: Rien
    """
    path_grandeur = utils.get_path_historique_raw_csv(grandeur)
    if grandeur != "QmnJ" and utils_file.is_file_need_download(path_grandeur):
        download_hubeau_1991_2020(grandeur)
    if grandeur == "QmnJ":
        for date in pd.date_range("1990-12-01", "2020-12-01", freq="MS"):
            annee_mois = date.strftime("%Y-%m")
            ensure_grandeur_mensuel_downloaded(annee_mois, "QmnJ")


# TELECHARGEMENT DONNEES HISTORIQUE

def download_hubeau_1991_2020(grandeur_souhaite):
    """
    Télécharge les observations de 1991 à 2020 de la grandeur souhaite et de toute la france
    :param grandeur_souhaite: La grandeur souhaité à télécharger parmis : HIXM, HIXnJ, QINM, QINnJ, QixM, QIXnJ, QmM ou QmnJ.
    """
    logger.info(f"Téléchargement des données historiques : 1991 à 2020 de la grandeur {grandeur_souhaite}")
    # Permet d'accéder à internet via le réseau interne de la DREAL
    # initialisation du proxy
    utils_proxy.set_up_working_proxy()

    # Bounding box grossière du bassin versant Auvergne-Rhône-Alpes
    bounding_box_grossiere = [1.142578, 42.039587, 8.481445, 49.612271]

    # Format de date AAAA-MM-JJ
    date_debut_observation = "1991-01-01"
    date_fin_observation = "2020-12-31"

    # Format des données souhaité, pour n'avoir que les bons champs parmi
    # code_site,code_station,date_obs_elab,resultat_obs_elab,date_prod,code_statut,libelle_statut,code_methode,libelle_methode,code_qualification,libelle_qualification,longitude,latitude,grandeur_hydro_elab
    format_attendu = [
        "code_site",
        "code_station",
        "date_obs_elab",
        "resultat_obs_elab",
        "date_prod",
        "libelle_statut",
        "libelle_methode",
        "libelle_qualification",
    ]

    if grandeur_souhaite == "QmM":
        dataframe_observation = hydrometry.get_observations(
            date_debut_obs_elab=date_debut_observation,
            date_fin_obs_elab=date_fin_observation,
            grandeur_hydro_elab=[grandeur_souhaite],
            bbox=bounding_box_grossiere,
            fields=format_attendu,
        )

        dataframe_observation.to_csv(utils.get_path_historique_raw_csv(grandeur_souhaite), index=False)
    else:
        ensure_grandeur_historique_downloaded("QmnJ")

@cache
def download_hubeau_onde_campagnes(zone_geographic:GeographicScaleClip, code_zone:str) -> pd.DataFrame:
    """
    Télécharge les observations de 1991 à 2020 de la grandeur souhaite et de toute la france
    :param grandeur_souhaite: La grandeur souhaité à télécharger parmis : HIXM, HIXnJ, QINM, QINnJ, QixM, QIXnJ, QmM ou QmnJ.
    """
    logger.info("Téléchargement des données des campagnes ONDE")
    utils_proxy.set_up_working_proxy()
    match zone_geographic:
        case GeographicScaleClip.DEPARTEMENT_BASSIN | GeographicScaleClip.DEPARTEMENT_ADMINISTRATIF:
            gdf = watercourses_flow.get_all_campaigns(code_departement=[code_zone])
        case GeographicScaleClip.REGION_BASSIN | GeographicScaleClip.REGION_ADMINISTRATIVE:
            gdf = watercourses_flow.get_all_campaigns(code_departement=get_departements_from_regions(code_zone))
        case _:
            gdf = watercourses_flow.get_all_campaigns()
    chemin_campagne_onde = utils.get_path_campagne_onde()
    gdf["date_campagne"] = pd.to_datetime(gdf["date_campagne"])
    gdf.to_csv(chemin_campagne_onde, index=False)
    logger.info(f"Données campagne ONDE téléchargés à : {chemin_campagne_onde}")
    return gdf

@cache
def download_hubeau_onde_observations_geographic_zone(date_debut_obs:datetime, date_fin_obs:datetime, zone_geographic:GeographicScaleClip, code_zone:str):
    """
    Télécharge les observations de 1991 à 2020 de la grandeur souhaite et de toute la france
    :param date_debut_obs: Les observations depuis ce jour-là inclus.
    :param date_fin_obs: Les observations allant jusqu'à ce jour-là inclus.
    :param zone_geographic: La zone géographic à extraire.
    :param code_zone: Le code correspondant à la zone géographique (INSEE)
    """
    logger.info("Téléchargement des données des observations ONDE")
    utils_proxy.set_up_working_proxy()

    kwargs = {
        "date_observation_min": date_debut_obs.strftime("%Y-%m-%d"),
        "date_observation_max": date_fin_obs.strftime("%Y-%m-%d"),
    }

    match zone_geographic:
        case GeographicScaleClip.BASSIN:
            kwargs["code_bassin"] = code_zone
        case GeographicScaleClip.REGION_BASSIN | GeographicScaleClip.REGION_ADMINISTRATIVE:
            kwargs["code_region"] = code_zone
        case GeographicScaleClip.DEPARTEMENT_BASSIN | GeographicScaleClip.DEPARTEMENT_ADMINISTRATIF:
            kwargs["code_departement"] = code_zone

    df = watercourses_flow.get_all_observations(**kwargs)
    if df.empty:
        logger.warning("DataFrame vide ! Pas de données sur cette période.")
        return

    chemin_observations_onde = utils.get_path_observation_onde(date_debut_obs, date_fin_obs, zone_geographic, code_zone)
    df["date_observation"] = pd.to_datetime(df["date_observation"])
    df.to_csv(chemin_observations_onde, index=False)
    logger.info(f"Données observations ONDE téléchargés à : {chemin_observations_onde}")
    return df

@cache
def download_hubeau_onde_stations_geographic_zone(zone_geographic:GeographicScaleClip, code_zone:str):
    logger.info("Téléchargement des stations ONDE")
    utils_proxy.set_up_working_proxy()

    kwargs = {
    }

    match zone_geographic:
        case GeographicScaleClip.BASSIN:
            kwargs["code_bassin"] = code_zone
        case GeographicScaleClip.REGION_BASSIN | GeographicScaleClip.REGION_ADMINISTRATIVE:
            kwargs["code_region"] = code_zone
        case GeographicScaleClip.DEPARTEMENT_BASSIN | GeographicScaleClip.DEPARTEMENT_ADMINISTRATIF:
            kwargs["code_departement"] = code_zone

    df = watercourses_flow.get_all_stations(**kwargs)
    if df.empty:
        logger.warning("DataFrame vide ! Pas de données sur cette période.")
        return

    chemin_observations_onde = utils.get_path_stations_onde(zone_geographic, code_zone)
    df.to_csv(chemin_observations_onde, index=False)
    logger.info(f"Données stations ONDE téléchargés à : {chemin_observations_onde}")
    return df

# TELECHARGEMENT DONNEES STATIONS ET SITES

def download_stations():
    """
    Télécharge toute les stations de France qui ont existé.
    :return: Rien
    """
    logger.info("Téléchargement des stations.")
    utils_proxy.set_up_working_proxy()

    df_all_stations = hydrometry.get_all_stations()
    df_all_stations.to_csv(utils.get_path_stations())
    logger.info(f"Stations téléchargées -> {utils.get_path_stations()}")

def download_sites():
    """
    Télécharges tous les sites de France.
    :return: Rien
    """
    logger.info("Téléchargement des sites.")
    utils_proxy.set_up_working_proxy()

    df_all_sites = hydrometry.get_all_sites()
    df_all_sites.to_csv(utils.get_path_sites())
    logger.info(f"Sites téléchargées -> {utils.get_path_sites()}")

def ensure_station_downloaded():
    """
    Assure que toutes les stations sont téléchargés.
    :return: Rien
    """
    chemin = utils.get_path_stations()
    if utils_file.is_file_need_download(chemin):
        download_stations()

def ensure_sites_downloaded():
    """
    Assure que tous les sites sont téléchargés.
    :return: Rien
    """
    chemin = utils.get_path_sites()
    if utils_file.is_file_need_download(chemin):
        download_sites()

# Code executé uniquement si on lance ce fichier individuellement, pas si on l'importe à l'aide d'un autre fichier.
if __name__ == "__main__":
    # Données Mensuels
    # ensure_grandeur_mensuel_downloaded("2025-06","QmnJ")
    # ensure_grandeur_mensuel_downloaded("2025-07","QmnJ")
    # ensure_grandeur_mensuel_downloaded("2025-08","QmnJ")
    # # Données Historiques
    # ensure_grandeur_historique_downloaded("QmM")
    # ensure_grandeur_historique_downloaded("QmnJ")
    # # Stations et sites
    # ensure_station_downloaded()
    # ensure_sites_downloaded()
    pass
    # download_hubeau_onde_campagnes()
    # download_hubeau_onde_observations_geographic_zone(
    #     datetime(2026,6,1),
    #     datetime(2026,6,30),
    #     GeographicScaleClip.REGION_ADMINISTRATIVE,
    #     "84",
    # )
    download_hubeau_onde_stations_geographic_zone(GeographicScaleClip.REGION_ADMINISTRATIVE,"84")
    # df_test = get_df_observations_geographic_zone(datetime(2025,5,1), datetime(2025,9,2),GeographicScaleClip.DEPARTEMENT_ADMINISTRATIF,"33")
    # df_test.to_csv(Path("output/test/testetst-onde.csv"),index=False)
    # gdf_test = gpd.GeoDataFrame(data=df_test,geometry=df_test.geometry)
    # gdf_test.to_file(Path("output/test/testetst-onde.geojson"),driver="GeoJSON")