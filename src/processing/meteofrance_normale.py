from src.model.enums import GeographicScaleClip,MeteoFranceDataType
from pathlib import Path
from datetime import datetime
import pandas as pd
from src.config.paths import OUTPUT_DIR
from src.model.utils import meteofrance_data_type_to_str
from src.utils.utils import get_path_meteofrance_historic_mean, get_chemin_sauvegarde_geographie
from src.utils.utils_file import is_path_valid_age
import src.processing.meteoFrance_aggregation_donnee as MeteoAgg
import src.io.download_meteoFrance as DMeteo
from src.processing.meteoFrance_aggregation_donnee import GroupByMethod
from src.config.logging_config import setup_logger

# Initialiser le logger
logger = setup_logger(name="meteofrance_normale")

def df_range_processed(data_freq:MeteoFranceDataType, start_date:datetime, end_date:datetime, is_data_aggregated:bool,
                                    has_index_update:bool=True, is_data_update_allowed:bool=True) -> pd.DataFrame:
    """
    Renvoie un Dataframe avec toutes les données allant de start_date à end_date, en aggrégeant les données si demandé.
    :param data_freq:Le type de données souhaité
    :param start_date:La date de début des données
    :param end_date:La date de fin des données
    :param is_data_aggregated:Si a vrai, on aggrège les données sur la période.
    :param has_index_update:On autorise l'index de correspondance données -> id_datagouv à se mettre à jour
    :param is_data_update_allowed: On autorise les fichiers à se re-télécharger pour être à jour.
    :return: Le Dataframe contenant toute les données de start_date à end_date.
    """
    df_intervalle = DMeteo.get_data_in_range(data_freq, start_date, end_date, has_index_update, is_data_update_allowed)
    if df_intervalle.empty:
        logger.warning(f"L'intervalle de données ({start_date} - {end_date}) est vide. Abandon.")
        return df_intervalle

    if is_data_aggregated:
        df_intervalle = MeteoAgg.aggregate_range(data_freq, df_intervalle, GroupByMethod.BY_POSITION)

    return df_intervalle

def get_unit_to_mean(data_freq: MeteoFranceDataType) -> list[str]:
    """
    Renvoie la liste des colonnes dont il faut faire la moyenne lors d'un calcul historique.
    """
    match data_freq:
        case MeteoFranceDataType.SIM2_QUOT:
            return ["PRENEI","PRELIQ","T","FF","Q","DLI","SSI","HU","EVAP","ETP","PE","SWI","DRAINC","RUNC","RESR_NEIGE","RESR_NEIGE6","HTEURNEIGE","HTEURNEIGE6","HTEURNEIGEX","SNOW_FRAC","ECOULEMENT","WG_RACINE","WGI_RACINE","TINF_H","TSUP_H"]
        case MeteoFranceDataType.SIM2_MENS:
            return ["PRENEI","PRELIQ","PRETOTM","T","EVAP","ETP","PE","SWI","DRAINC","RUNC","ECOULEMENT"]
        case MeteoFranceDataType.QUOT:
            return ["RR","TN","HTN","TX","HTX","TM","TNTXM","TNSOL","TN50","DG","FFM","FF2M","FXY","DXY","HXY","FXI","DXI","HXI","FXI2","DXI2","HXI2","FXI3S","DXI3S","HXI3S","DRR","STATUS_FXI3S","STATUS_DXI3S"]
        case MeteoFranceDataType.MENS:
            return ["RR","RR_ME","RRAB","TX","TX_ME"]

def get_position_columns(data_freq: MeteoFranceDataType) -> list[str]:
    """
    Renvoie les colonnes identifiant une position géographique selon le type de donnée.
    Les données SIM2 utilisent les coordonnées Lambert (LAMBX/LAMBY),
    les données brutes (QUOT/MENS) utilisent la latitude/longitude (LAT/LON).
    """
    match data_freq:
        case MeteoFranceDataType.SIM2_QUOT | MeteoFranceDataType.SIM2_MENS:
            return ["LAMBX", "LAMBY"]
        case MeteoFranceDataType.QUOT | MeteoFranceDataType.MENS:
            return ["LAT", "LON"]
        case _:
            raise NotImplementedError

def get_date_column_name(data_freq: MeteoFranceDataType) -> str:
    """
    Renvoie le nom de la colonne contenant la date (au format int) selon le type de donnée.
    Après une agrégation par position, cette colonne devient '{colonne}_min'/'{colonne}_max'.
    """
    match data_freq:
        case MeteoFranceDataType.SIM2_QUOT | MeteoFranceDataType.SIM2_MENS:
            return "DATE"
        case MeteoFranceDataType.QUOT:
            return "AAAAMMJJ"
        case MeteoFranceDataType.MENS:
            return "AAAAMM"
        case _:
            raise NotImplementedError

def get_historic_mean(data_freq:MeteoFranceDataType, date_debut:datetime, date_fin:datetime):
    """
    Récupère les données historiques d'une unité particulière.

    Les dates de début et dates de fin doivent appartenir à la même année.
    """
    if date_debut.year != date_fin.year:
        raise ValueError("La date de début et date de fin ne sont pas de la même année.")

    if date_debut.year > date_fin.year:
        raise ValueError("La date de fin est plus tôt que la date de début.")

    chemin_historic_aggregation = get_path_meteofrance_historic_mean(data_freq, date_debut, date_fin)
    # Si le calcul des données historiques a déjà été fait, on charge juste le fichier.
    if chemin_historic_aggregation.exists() and is_path_valid_age(chemin_historic_aggregation):
        return pd.read_csv(chemin_historic_aggregation)

    # On récupère tous les dataframes de chaque années sur la période date_début-date_fin
    all_df = []
    position_columns = get_position_columns(data_freq)
    date_column = get_date_column_name(data_freq)
    for annee in range(1990,2021):
        date_debut_extrait_historique = date_debut.replace(year=annee)
        date_fin_extrait_historique = date_fin.replace(year=annee)

        df_panda = df_range_processed(data_freq, date_debut_extrait_historique, date_fin_extrait_historique, True)
        df_panda["DATE"] = df_panda[f"{date_column}_min"]
        df_panda["DATE_DATETIME"] = df_panda["DATE_DATETIME_min"]
        all_df.append(df_panda)

    df_concatenated = pd.concat(all_df, ignore_index=True)

    df_groupped_by = df_concatenated.groupby(by=position_columns)

    # On récupère toutes les colonnes dont on doit faire la moyenne
    list_unit_to_mean = get_unit_to_mean(data_freq)

    # On crée le dictionnaire qui sert à agréger le DataFrame.
    dico_aggregation = {
        "DATE":"first",
        "DATE_DATETIME":"first",
        "DATE_DATETIME_min":"min",
        "DATE_DATETIME_max":"max",
    }

    # On fait des moyennes avec les unités
    for unit in list_unit_to_mean:
        dico_aggregation[unit] = "mean"

    df_aggregated = df_groupped_by.agg(dico_aggregation)

    df_aggregated.reset_index(inplace=True)

    return df_aggregated

def get_rapport_normale(data_freq:MeteoFranceDataType, df_donnee_actuelle:pd.DataFrame, date_debut:datetime, date_fin:datetime):
    """
    Prend le dataFrame en entrée, créer les normales pour ce DataFrame.

    Le ratio est calculé en fusionnant les données actuelles avec la moyenne historique
    sur les colonnes de position. La moyenne historique contient une entrée unique par
    position, tandis que les données actuelles peuvent en contenir plusieurs (une par
    date, par exemple sur une plage de plusieurs mois). La fusion propage la valeur
    historique à chaque ligne des données actuelles, ce qui évite l'erreur
    "cannot handle a non-unique multi-index" qui survenait avec une division directe
    sur un index de position non-unique.
    """
    logger.info("Récupération des données historiques et calcul du ratios")
    df_donnee_moyenne_historique = get_historic_mean(data_freq, date_debut, date_fin)

    position_columns = get_position_columns(data_freq)
    list_unit_to_mean = get_unit_to_mean(data_freq)

    # On fusionne les données actuelles avec la moyenne historique sur les colonnes de position.
    # Les colonnes de la moyenne historique reçoivent le suffixe "_ref" pour éviter les conflits.
    df_ref = df_donnee_moyenne_historique[position_columns + list_unit_to_mean].copy()
    df_actuel = df_donnee_actuelle.merge(df_ref, on=position_columns, how="left", suffixes=("", "_ref"))

    # On fait le ratio pour chaque unité : valeur actuelle / valeur historique (bornée à 0.01).
    for unit in list_unit_to_mean:
        df_actuel[f"{unit}_rapport_normale"] = df_actuel[unit] / df_actuel[f"{unit}_ref"].abs().clip(lower=0.01)

    # On supprime les colonnes de référence temporaires.
    df_actuel = df_actuel.drop(columns=[f"{unit}_ref" for unit in list_unit_to_mean])

    logger.info("Récupération des données historiques et calcul ratio terminé.")
    return df_actuel

if __name__ == "__main__":
    date_debut = datetime(2026, 6, 1)
    date_fin = datetime(2026, 6, 30)

    get_rapport_normale(GeographicScaleClip.BASSIN, MeteoFranceDataType.SIM2_MENS, date_debut, date_fin)