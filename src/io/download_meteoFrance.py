from zipfile import ZipFile
from datagouv import Dataset, Resource
from pathlib import Path
import gzip
import shutil
import calendar
from functools import cache
import re
import pandas as pd
from datetime import datetime, timezone
from enum import Enum, StrEnum
import src.utils.utils_proxy as utils_proxy
import src.utils.utils_file as utils_file
from src.config.paths import DATA_DIR, OUTPUT_DIR
import src.config.init_project
from src.model.enums import GeographicScaleClip,MeteoFranceDataType
from src.config.logging_config import setup_logger

# Initialiser le logger
logger = setup_logger(name="download_meteoFrance")

def get_geographic_list(geographic_scale: GeographicScaleClip):
    match geographic_scale:
        case GeographicScaleClip.NATIONAL:
            return []
        case GeographicScaleClip.BASSIN:
            file_to_read = DATA_DIR / Path("liste_bassin.csv")
        case GeographicScaleClip.REGION_BASSIN | GeographicScaleClip.REGION_ADMINISTRATIVE:
            file_to_read = DATA_DIR / Path("liste_region.csv")
        case GeographicScaleClip.DEPARTEMENT_BASSIN | GeographicScaleClip.DEPARTEMENT_ADMINISTRATIF:
            file_to_read = DATA_DIR / Path("liste_departement.csv")
        case GeographicScaleClip.ECOREGION_HYDROLOGIQUE:
            file_to_read = DATA_DIR / Path("liste_eco_hydro.csv")
        case _:
            raise NotImplementedError

    if file_to_read.exists():
        df_liste = pd.read_csv(file_to_read, dtype={"code":str})
        liste = df_liste[df_liste.columns[0]].to_list()
    else:
        raise FileNotFoundError(f"Le fichier {file_to_read} n'existe pas !")

    return liste

def convert_chaine_to_date(chaine:str, is_start:bool) -> datetime:
    """
    Convertis un chaine de caractere en une datetime
    :param chaine: La chaine de caractere a convertir
    :param is_start: Si on veut le début du mois/année, mettre à True, si on veut la fin du mois, mettre à False
    :return:
    """
    if is_start:
        default_month = 1
        default_day = 1
    else:
        default_month = 12
        default_day = 31

    if len(chaine) == 4:
        return datetime(year=int(chaine), month=default_month, day=default_day)
    elif len(chaine) == 6:
        annee = int(chaine[0:4])
        mois = int(chaine[4:6])
        if not is_start:
            default_day = calendar.monthrange(annee, mois)[1]
        return datetime(year=int(chaine[0:4]), month=int(chaine[4:6]), day=default_day)
    else:
        return datetime.strptime(chaine, "%Y%m%d")


def fetch_and_update_decennie_ressource_id(data_freq:MeteoFranceDataType):
    """
    Va récupérer à partir de l'id du dataset donnees-changement-climatique-sim-quotidienne
    Tous les id des décénies de chaque ressources associé.
    :return: Rien.
    """
    logger.info("MISE A JOUR DE L'INDEX (date-debut,dete-fin -> id-datagouv)")
    if data_freq in [MeteoFranceDataType.MENS, MeteoFranceDataType.QUOT]:
        logger.info("La mise à jour de l'index de données peut prendre beaucoup de temps, le faire une fois par jour est utile, mais pas plus."
                    "Utilisez --meteo_no_index_update pour interdire la mise à jour de l'index de données.")
    # On met en place les expression régulière pour reconnaitre uniquement les données du bon format.
    match data_freq:
        case MeteoFranceDataType.SIM2_QUOT:
            id_dataset = "6569b27598256cc583c917a7"
            pattern = re.compile("(QUOT_SIM2_....-....)|(QUOT_SIM2_........-........)")
        case MeteoFranceDataType.SIM2_MENS:
            id_dataset = "65e040c50a5c6872ebebc711"
            pattern = re.compile("MENS_SIM2_....-....")
        case MeteoFranceDataType.QUOT:
            id_dataset = "6569b51ae64326786e4e8e1a"
            pattern = re.compile('|'.join(f"(QUOT_departement_{str_dep}_periode_....-...._.*)" for str_dep in get_geographic_list(GeographicScaleClip.DEPARTEMENT_BASSIN)))
        case MeteoFranceDataType.MENS:
            id_dataset = "6569b3d7d193b4daf2b43edc"
            pattern = re.compile('|'.join(f"(MENS_departement_{str_dep}_periode_....-....)" for str_dep in get_geographic_list(GeographicScaleClip.DEPARTEMENT_BASSIN)))
        case _:
            raise NotImplementedError
    chemin_decennie_id = get_path_decennie_to_id_datagouv(data_freq)
    utils_proxy.set_up_working_proxy()
    # Dataset contenant toutes les données météoFrance correspondant sur data.gouv.fr
    success = False
    utils_proxy.set_up_working_proxy()
    while not success:
        try:
            dataset_complet = Dataset(id_dataset)
            success = True
        except:
            pass

    tous_les_couples = []
    for res in dataset_complet.resources:
        titre_ressource = res.title
        if pattern.match(titre_ressource):
            debut_fin_decenie = titre_ressource.split("_")[-1]
            if "autres" in debut_fin_decenie  or "RR-T" in debut_fin_decenie:
                debut_fin_decenie = titre_ressource.split("_")[-2]
            date_debut = debut_fin_decenie.split("-")[0]
            date_fin = debut_fin_decenie.split("-")[1]
            tous_les_couples.append(
                {
                    "debut_decennie": convert_chaine_to_date(date_debut, True),
                    "fin_decennie": convert_chaine_to_date(date_fin, False),
                    "id_ressource_datagouv": res.id,
                }
            )
    df_decennie_id = pd.DataFrame(data=tous_les_couples)
    logger.info(f"Index decennie -> id_datagouv updated : {chemin_decennie_id}")
    df_decennie_id.to_csv(chemin_decennie_id, index=False)

def get_path_decennie_to_id_datagouv(data_freq:MeteoFranceDataType):
    match data_freq:
        case MeteoFranceDataType.SIM2_MENS:
            return OUTPUT_DIR / "meteoFrance" / "MENS_SIM2_decennie_to_id_datagouv.csv"
        case MeteoFranceDataType.SIM2_QUOT:
            return OUTPUT_DIR / "meteoFrance" / "QUOT_SIM2_decennie_to_id_datagouv.csv"
        case MeteoFranceDataType.QUOT:
            return OUTPUT_DIR / "meteoFrance" / "QUOT_decennie_to_id_datagouv.csv"
        case MeteoFranceDataType.MENS:
            return OUTPUT_DIR / "meteoFrance" / "MENS_decennie_to_id_datagouv.csv"
        case _:
            raise NotImplementedError

def get_df_decennie_to_id_datagouv(data_freq:MeteoFranceDataType):
    chemin_decennie_id = get_path_decennie_to_id_datagouv(data_freq)
    if not chemin_decennie_id.exists():
        return pd.DataFrame()
    df_decennie_to_id = pd.read_csv(chemin_decennie_id)
    return df_decennie_to_id

def delete_old_file(freq_data:MeteoFranceDataType, df_origine:pd.DataFrame, df_nouveau:pd.DataFrame):
    """
    Supprime les fichiers qui n'apparaissent plus dans le df_nouveau.
    :param freq_data: Le type de données visé,
    :param df_origine: Le df avant la mise à jour de l'index.
    :param df_nouveau: Le df après la mise à jour de l'index.
    :return: Rien
    """
    df_origine_reindex = df_origine.set_index(["debut_decennie","fin_decennie","id_ressource_datagouv"])
    df_origine_reindex["col_with_random_data_so_delete_isin_can_work"] = 1
    df_nouveau_reindex = df_nouveau.set_index(["debut_decennie","fin_decennie","id_ressource_datagouv"])
    df_nouveau_reindex["col_with_random_data_so_delete_isin_can_work"] = 1
    df_comparison = df_origine_reindex[~df_origine_reindex.isin(df_nouveau_reindex)].dropna()
    df_comparison_reseted = df_comparison.reset_index()
    if df_comparison_reseted.empty:
        return
    else:
        logger.info("Des choses on changé !")
        logger.debug(df_comparison)
    for i in df_comparison_reseted.index:
        row_a_supprimer = df_origine.loc[i]
        date_debut = datetime.strptime(row_a_supprimer["debut_decennie"], "%Y-%m-%d")
        date_fin = datetime.strptime(row_a_supprimer["fin_decennie"], "%Y-%m-%d")
        id_datagouv = row_a_supprimer["id_ressource_datagouv"]
        chemin_a_supprimer_csv = get_chemin_data_downloaded(freq_data, date_debut, date_fin, id_datagouv, False)
        chemin_a_supprimer_gz = get_chemin_data_downloaded(freq_data, date_debut, date_fin, id_datagouv, True)
        chemin_a_supprimer_csv.unlink(missing_ok=True)
        chemin_a_supprimer_gz.unlink(missing_ok=True)
        logger.info("Les vieux fichiers : ")
        logger.debug(chemin_a_supprimer_csv)
        logger.debug(chemin_a_supprimer_gz)
        logger.info("On été supprimé.")

@cache
def update_decennie_to_id_datagouv(freq_data:MeteoFranceDataType):
    """
    Met a jour l'index décenie -> id datagouv.
    Supprime les fichiers qui n'apparaissent plus dedans.

    Cette fonction est mise en cache de tel sorte qu'une mise à jour ne puisse s'effectuer qu'une fois par exécution.
    :param freq_data: Le type de donnée qui est affecté.
    :return: Rien
    """
    logger.info("Mise à jour de l'index.")
    old_df_decennie_to_id_datagouv = get_df_decennie_to_id_datagouv(freq_data)
    # Télécharger le nouveau
    fetch_and_update_decennie_ressource_id(freq_data)
    new_df_decennie_to_id_datagouv = get_df_decennie_to_id_datagouv(freq_data)
    # On cherche les différences entre les deux df.
    if not old_df_decennie_to_id_datagouv.empty:
        delete_old_file(freq_data, old_df_decennie_to_id_datagouv, new_df_decennie_to_id_datagouv)

def filter_range_in_df(df_to_filter:pd.DataFrame, data_freq: MeteoFranceDataType,
                       date_debut: datetime, date_end: datetime) -> pd.DataFrame:
    """
    Filtre le DataFrame d'entrée pour ne récupérer que les données entre le date_debut et date_end.
    :param df_to_filter: Le DataFrame a filter
    :param data_freq: Le type de fréquence de donnée
    :param date_debut: La date de début à filtrer
    :param date_end: La date de fin à filtrer
    :return: Le Dataframe filtré entre la date de début et la date de fin
    """
    match data_freq:
        case MeteoFranceDataType.SIM2_QUOT:
            format_to_catch = "%Y%m%d"
            nom_colonne_date = "DATE"
        case MeteoFranceDataType.SIM2_MENS:
            format_to_catch = "%Y%m"
            nom_colonne_date = "DATE"
        case MeteoFranceDataType.QUOT:
            format_to_catch = "%Y%m%d"
            nom_colonne_date = "AAAAMMJJ"
        case MeteoFranceDataType.MENS:
            format_to_catch = "%Y%m"
            nom_colonne_date = "AAAAMM"
        case _:
            raise NotImplementedError

    int_date_debut = int(date_debut.strftime(format_to_catch))
    int_date_end = int(date_end.strftime(format_to_catch))

    # Filtre les df pour qu'ils soient entre la date début et la date fin.
    df_reduit_bonne_date = df_to_filter[
        (int_date_debut <= df_to_filter[nom_colonne_date]) & (df_to_filter[nom_colonne_date] <= int_date_end)].copy()

    df_reduit_bonne_date["DATE_DATETIME"] = df_reduit_bonne_date[nom_colonne_date].apply(
        lambda x: datetime.strptime(str(x), format_to_catch))

    return df_reduit_bonne_date

def get_data_in_range(data_freq: MeteoFranceDataType, date_debut: datetime, date_end: datetime, has_index_update:bool, is_data_update_allowed:bool) -> pd.DataFrame:
    """
    Renvoie toutes les données mensuelles de SIM2 entre la date de début et la date de fin.

    :param data_freq: Le type de données souhaitées !
    :param date_debut: La date de début de la fenêtre à récupérer
    :param date_end:  La date de fin de la fenêtre à récupérer
    :param has_index_update: Si à True, l'index de correspondance est mis à jour.
    :param is_data_update_allowed: Si à False, les mises à jour des fihciers existant ne sont pas téléchargés.
    :return: Un dataframe contenant toutes les données mensuelles de SIM2 entre date_debut et date_fin inclus.
    """
    logger.info("Loading files...")
    if date_end < date_debut:
        raise ValueError("La date de fin est plut tot que la date de début !")

    # On met à jour les correspondance decennie -> id_datagouv.
    if has_index_update:
        update_decennie_to_id_datagouv(data_freq)

    # On récupère les correspondance.
    df_decenie_to_id = get_df_decennie_to_id_datagouv(data_freq)
    file_to_gather = []
    # On parcours les décénnies connues et on les sauvegardes.
    for i in df_decenie_to_id.index:
        row = df_decenie_to_id.loc[i]
        # On récupère les données du dictionnaire.
        date_debut_row = datetime.strptime(row["debut_decennie"],"%Y-%m-%d")
        date_fin_row = datetime.strptime(row["fin_decennie"],"%Y-%m-%d")
        id = row["id_ressource_datagouv"]
        # Si la date correspond à notre intervalle d'extraction, on la récupère.
        if is_date_overlapping(date_debut_row, date_fin_row, date_debut, date_end):
            file_to_gather.append((date_debut_row, date_fin_row, id))

    if not file_to_gather:
        logger.warning("Range vide. Données absente.")
        return pd.DataFrame()

    logger.debug(file_to_gather)
    all_df = []
    for date_debut_fichier, date_fin_fichier, id_datagouv in file_to_gather:
        all_df.append(get_df_decennie(data_freq, date_debut_fichier, date_fin_fichier, id_datagouv, is_data_update_allowed))
    df_complet = pd.concat(all_df, ignore_index=True)
    if len(all_df) > 1:
        match data_freq:
            case MeteoFranceDataType.SIM2_QUOT | MeteoFranceDataType.SIM2_MENS:
                df_complet.drop_duplicates(subset=["LAMBX","LAMBY","DATE"],inplace=True)
            case MeteoFranceDataType.QUOT:
                df_complet.drop_duplicates(subset=["LAT","LON","AAAAMMJJ"],inplace=True)
            case MeteoFranceDataType.MENS:
                df_complet.drop_duplicates(subset=["LAT", "LON", "AAAAMM"], inplace=True)
            case _:
                raise NotImplementedError
    logger.info("Files loaded successfully...")
    logger.debug(df_complet)

    df_date_filtre = filter_range_in_df(df_complet, data_freq, date_debut, date_end)

    return df_date_filtre

@cache
def get_gouv_ressource(id_gouv_data:str) -> Resource:
    """
    Permet de récupérer les ressources sur data.gouv en gardant en mémoir les requetes déjà faite !
    :param id_gouv_data: L'id à récupérer.
    :return: La ressource correspondante.
    """
    utils_proxy.set_up_working_proxy()
    return Resource(id_gouv_data)

def is_path_updated_with_datagouv(chemin_fichier:Path, id_gouv_data:str) -> bool:
    """
    Compare la date de dernière modification du fichier avec la date de dernière modification sur data.gouv
    Si la date de modification du fichier est plus récente que celle de data.gouv on renvoie True, sinon False
    :param chemin_fichier: Le chemin vers le fichier dont il faut comparer la date avec sa source sur data.gouv
    :param id_gouv_data: L'id de data.gouv pour aller chercher la date de dernière modification de la ressource.
    :return: Un booléen, True si le fichier est plus récent que data.gouv, false sinon.
    """
    nb_seconde_depuis_1991_modification = chemin_fichier.stat().st_mtime
    derniere_modification_fichier = datetime.fromtimestamp(nb_seconde_depuis_1991_modification, tz=timezone.utc)
    res = get_gouv_ressource(id_gouv_data)
    derniere_modification_gouv = datetime.fromisoformat(res.last_modified)
    return derniere_modification_gouv <= derniere_modification_fichier

@cache
def get_df_decennie(freq_data:MeteoFranceDataType, start_date: datetime,end_date: datetime,id_gouv_data: str, is_data_update_allowed:bool) -> pd.DataFrame:
    """
    Renvoie le dataframe contenant toutes les infosd du fichier de cette décénie.
    :param is_data_update_allowed: Si à False, les données ne sont pas mise à jour.
    :param freq_data:
    :param start_date:
    :param end_date:
    :param id_gouv_data:
    :return:
    """
    chemin = get_chemin_data_downloaded(freq_data, start_date, end_date, id_gouv_data, False)
    chemin_archive = get_chemin_data_downloaded(freq_data, start_date, end_date, id_gouv_data, True)

    logger.debug(f"Loading : {chemin}")
    if not chemin.exists():
        download_and_extract(id_gouv_data, chemin_archive, chemin)
    elif not is_path_updated_with_datagouv(chemin, id_gouv_data) and is_data_update_allowed:
        # On met a jour nos indices et on supprimes les fichiers qui n'existent plus.
        # On vérifie que le fichier est à jour par rapport au métadonnées du site.
        download_and_extract(id_gouv_data, chemin_archive, chemin)

    df = pd.read_csv(chemin, delimiter=";")
    return df

def download_and_extract(id_datagouv:str, chemin_archive:Path,chemin_final:Path):
    logger.info(f"Downloading {chemin_final.name}...")
    utils_proxy.set_up_working_proxy()
    r = get_gouv_ressource(id_datagouv)
    success = False
    while not success:
        try:
            r.download(chemin_archive)
            success = True
        except:
            pass

    try:
        with gzip.open(chemin_archive, "rb") as archive:
            with open(chemin_final, "wb") as final:
                shutil.copyfileobj(archive, final)
    except gzip.BadGzipFile:
        with ZipFile(chemin_archive, "r") as archive:
            archive.extractall(path=chemin_final.parent)


def is_date_overlapping(debut_1: datetime, fin_1: datetime, debut_2: datetime, fin_2: datetime):
    return debut_2 <=  debut_1 <= fin_2 or debut_2 <= fin_1 <= fin_2 or (debut_1 <= debut_2 and fin_2 <= fin_1)

def get_chemin_data_downloaded(freq_data:MeteoFranceDataType, debut_decenie:datetime,fin_decenie:datetime, id_gouv_data:str, is_archive: bool)->Path:
    """
    Renvoie le chemin vers le fichier contenant les données téléchargé pour le type de données souhaitée..
    :param freq_data: Le type de donnée
    :param debut_decenie: La datetime de début des données du fichier
    :param fin_decenie: La datetime de fin des données du fichier
    :param id_gouv_data: L'identifiant unique par fichier indiquant le id datagouv.
    :param is_archive: Si True, renvoie un .csv.gz, si faut, renvoie un .csv
    :return: Chemin vers le fichier sim2
    """
    match freq_data:
        case MeteoFranceDataType.SIM2_QUOT:
            if is_archive:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "quot_sim2_archive" / f"QUOT_SIM2_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv.gz"
            else:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "quot_sim2" / f"QUOT_SIM2_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv"
        case MeteoFranceDataType.SIM2_MENS:
            if is_archive:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "mens_sim2_archive" / f"MENS_SIM2_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv.gz"
            else:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "mens_sim2" / f"MENS_SIM2_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv"
        case MeteoFranceDataType.QUOT:
            if is_archive:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "quot_archive" / f"QUOT_{id_gouv_data}_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv.gz"
            else:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "quot" / f"QUOT_{id_gouv_data}_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv"
        case MeteoFranceDataType.MENS:
            if is_archive:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "mens_archive" / f"MENS_{id_gouv_data}_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv.gz"
            else:
                return OUTPUT_DIR / "meteoFrance" / "downloaded_data" / "mens" / f"MENS_{id_gouv_data}_{debut_decenie.strftime('%Y%m%d')}-{fin_decenie.strftime('%Y%m%d')}.csv"
        case _:
            raise NotImplementedError

if __name__ == "__main__":
    #liste = get_geographic_list(GeographicScaleClip.BASSIN)
    #logger.debug(liste)

    #liste = get_geographic_list(GeographicScaleClip.REGION_BASSIN)
    #logger.debug(liste)

    #liste = get_geographic_list(GeographicScaleClip.DEPARTEMENT_BASSIN)
    #logger.debug(liste)

    df = get_data_in_range(MeteoFranceDataType.SIM2_QUOT,datetime(2026,6,1),datetime(2026,6,30),True,True)
