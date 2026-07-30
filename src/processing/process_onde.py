import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime
import calendar
from functools import cache
from src.model.enums import GeographicScaleClip
from src.model.enums import OndeCampagneType
import src.io.download_Hubeau as download_Hubeau
from src.config.logging_config import setup_logger
from src.config.paths import OUTPUT_DIR

# Initialiser le logger
logger = setup_logger(name="process_onde")

def save_df_onde(df_to_save:pd.DataFrame, csv_path:Path, geojson_path:Path, filter_annee_mois:datetime|None):
    """
    Sauvegarde le dataframe sous forme de GeoJSON et de csv dans les chemins indiqués
    :param df_to_save: Le DataFrame à sauvegarder
    :param csv_path: Le chemin pour le csv
    :param geojson_path: Le chemin pour le geojson
    :param filter_annee_mois: L'année et le mois à extraire du DataFrame à sauvegarder. Si à None, sauvegarde le DataFrame dans son entièreté.
    :return: Rien
    """
    if filter_annee_mois is not None:
        df_to_save = df_to_save[df_to_save["date_observation"].between(
            filter_annee_mois.replace(day=1),
            filter_annee_mois.replace(day=calendar.monthrange(filter_annee_mois.year,
                                                               filter_annee_mois.month)[1])
        )]

    df_to_save.to_csv(csv_path, index=False)
    gpd.GeoDataFrame(df_to_save, geometry=df_to_save["geometry"]).to_file(geojson_path, driver="GeoJSON", index=False)

@cache
def get_df_observations_data(geographic_scale:GeographicScaleClip, zone_code:str) -> pd.DataFrame:
    """
    Récupère toutes les données d'observations de 2012 à aujourd'hui.
    :param geographic_scale: la zone géographique à récupérer
    :param zone_code: Le code de la zone géographique à récupérer
    :return: Un DataFrame contenant toutes les données d'observations de 2012 à aujourd'hui.
    """
    df_observations = download_Hubeau.download_hubeau_onde_observations_geographic_zone(
        datetime(2012, 1, 1),
        datetime.today(),
        geographic_scale,
        zone_code,
    )
    df_observations["code_campagne"] = df_observations["code_campagne"].astype("int64")
    return df_observations

@cache
def get_df_campagnes_data(zone_geographic:GeographicScaleClip, code_zone:str) -> pd.DataFrame:
    """
    Récupère les modalités des campagnes de toute la France depuis 2012 jusqu'à aujourd'hui.
    :return: Un DataFrame contenant toutes les campagnes Onde.
    """
    df_campagnes = download_Hubeau.download_hubeau_onde_campagnes(zone_geographic, code_zone)
    # On ne garde quie les colonnes utiles et on enlève les doublons. Les campgnes osnt enregistré pour chaque départements.
    # On a besoin uniquement des modalités, donc on ne garde qu'un seul code.
    df_campagne_reduit = df_campagnes[["code_campagne", "date_campagne", "nombre_modalite_ecoulement",
                                       "code_type_campagne", "libelle_type_campagne", "code_reseau",
                                       "libelle_reseau", "uri_reseau"]].drop_duplicates(subset="code_campagne",
                                                                                        ignore_index=True)
    return df_campagne_reduit

def save_observations_campagnes_export(df_to_save:pd.DataFrame, df_campagne_derniere_donnee_chaque_station:pd.DataFrame, onde_campagne_type:OndeCampagneType, annee_mois:datetime, geographic_scale:GeographicScaleClip, zone_code:str) -> None:
    """
    Sauvegarde les données d'observations dans les formats csv et GeoJSON
    :param df_to_save: Le DataFrame a sauvegarder contenant toutes les données de toutes les campagnes
    :param df_campagne_derniere_donnee_chaque_station: Le DataFrame complètement nettoyé, contenant les dernières données mensuelles pour chaque stations
    :param onde_campagne_type: Le type de campagne Onde
    :param annee_mois: L'année et le mois ciblé
    :param geographic_scale: L'échelle géographique souhaité
    :param zone_code: Le code de la zone géographique
    :return: Rien.
    """
    annee_mois_str = annee_mois.strftime('%Y-%m')
    dossier_csv = OUTPUT_DIR / "onde" / f"BSH_{annee_mois_str}" / f"{geographic_scale[0]}{zone_code}" / "csv"
    dossier_csv.mkdir(parents=True, exist_ok=True)
    output_path_campagne_all_csv: Path = dossier_csv / Path(
        f"observations_et_campagnes_all_{annee_mois_str}.csv")
    output_path_campagne_usuelles_csv: Path = dossier_csv / Path(
        f"observations_et_campagnes_usuelles_{annee_mois_str}.csv")
    output_path_campagne_complementaire_csv: Path = dossier_csv / Path(
        f"observations_et_campagnes_complementaires_{annee_mois_str}.csv")

    output_path_campagne_no_duplicated_csv: Path = dossier_csv / Path(
        f"observations_et_campagnes_latest_{geographic_scale[0]}{zone_code}_{onde_campagne_type}_{annee_mois_str}.csv")

    dossier_geojson = OUTPUT_DIR / "onde" / f"BSH_{annee_mois_str}" / f"{geographic_scale[0]}{zone_code}" / "geojson"
    dossier_geojson.mkdir(parents=True, exist_ok=True)
    output_path_campagne_all_geojson: Path = dossier_geojson / Path(
        f"observations_et_campagnes_all_{annee_mois_str}.geojson")
    output_path_campagne_usuelles_geojson: Path = dossier_geojson / Path(
        f"observations_et_campagnes_usuelles_{annee_mois_str}.geojson")
    output_path_campagne_complementaire_geojson: Path = dossier_geojson / Path(
        f"observations_et_campagnes_complementaires_{annee_mois_str}.geojson")

    output_path_campagne_no_duplicated_geojson: Path = dossier_geojson / Path(
        f"observations_et_campagnes_latest_{annee_mois_str}_{onde_campagne_type}_{geographic_scale[0]}{zone_code}.geojson")

    save_df_onde(df_to_save, output_path_campagne_all_csv, output_path_campagne_all_geojson, annee_mois)

    # On filtre avec que les campagnes usuelles
    df_to_save_campagne_usuelle = df_to_save[df_to_save["code_type_campagne"] == 1]
    save_df_onde(df_to_save_campagne_usuelle, output_path_campagne_usuelles_csv, output_path_campagne_usuelles_geojson,
                 annee_mois)

    # On sauvegarde aussi les campagnes complémentaires
    df_to_save_campagne_complementaire = df_to_save[df_to_save["code_type_campagne"] == 2]
    save_df_onde(df_to_save_campagne_complementaire, output_path_campagne_complementaire_csv,
                 output_path_campagne_complementaire_geojson, annee_mois)

    # On sauvegarde les données les plus récentes pour chaque coordonnée.
    save_df_onde(df_campagne_derniere_donnee_chaque_station, output_path_campagne_no_duplicated_csv, output_path_campagne_no_duplicated_geojson, annee_mois)

def filter_campagne_type(df_to_filter:pd.DataFrame, campagne_type:OndeCampagneType):
    """
    Filtre le dataframe pour avoir les données correspondant au type de campagne souhaité.
    :param df_to_filter: Le DataFrame a filtrer, doit posséder la colonne 'code_type_campagne'
    :param campagne_type: Le type de campagne souhaité
    :return: Le dataframe filtré.
    """
    match campagne_type:
        case OndeCampagneType.COMPLEMENTAIRE:
            return df_to_filter[df_to_filter["code_type_campagne"] == 2]
        case OndeCampagneType.USUELLE:
            return df_to_filter[df_to_filter["code_type_campagne"] == 1]
        case OndeCampagneType.ALL_CAMPAGNE:
            return df_to_filter
        case _:
            raise NotImplementedError(f"Type de Campagne non implémenté : {campagne_type}")

def keep_last_station_data(df:pd.DataFrame) -> pd.DataFrame:
    """
    Trie le dataframe en entier et ne garde que les dernière données de chaque mois pour chaque point géographique.
    :param df: Le DataFrame où il ne faut garder que les dernières données de chaque mois, doit contenir les colonnes data_observation, geometry, annee, mois
    :return: Un DataFrame contenant uniquement les données de chaque mois.
    """
    df_trie = df.sort_values(by="date_observation", ascending=False)
    df_derniere_donne_chaque_station = df_trie.drop_duplicates(subset=["geometry", "annee", "mois"],
                                                                                 keep="first")
    return df_derniere_donne_chaque_station

def load_and_prepare_onde_data(onde_campagne_type:OndeCampagneType, annee_mois:datetime, geographic_scale:GeographicScaleClip, zone_code:str) -> pd.DataFrame:
    """
    Récupère les données des campagnes et des observations depuis 2012 jusqu'à today(), nettoie et sauvegardes ces données
    :return: Un DataFrame contenant toutes les données de 2012 à today(), qui pour chaque station n'a gardé que les données les plus récente du mois.
    """
    # Récupérations des observations
    df_observations = get_df_observations_data(geographic_scale, zone_code).copy()

    df_campagnes = get_df_campagnes_data(geographic_scale, zone_code).copy()

    # Les observations jointes aux campagnes.
    df_observation_join_campagne = df_observations.merge(df_campagnes, on="code_campagne", how="left")

    # On filtre les données pour ne retenir que les types de campagnes souhaité.
    df_campagne = filter_campagne_type(df_observation_join_campagne, onde_campagne_type).copy()

    # Mise en formes des dates.
    df_campagne["date_observation"] = pd.to_datetime(df_campagne["date_observation"])
    df_campagne["annee"] = df_campagne["date_observation"].dt.year
    df_campagne["mois"] = df_campagne["date_observation"].dt.month

    # On supprime les duplicatas et on garde le plus récent :
    df_campagne_derniere_donne_chaque_station = keep_last_station_data(df_campagne)

    # On sauvegarde toute les données.
    save_observations_campagnes_export(df_observation_join_campagne, df_campagne_derniere_donne_chaque_station,
                                       onde_campagne_type, annee_mois, geographic_scale, zone_code)

    return df_campagne_derniere_donne_chaque_station
