import pandas as pd
import src.io.download_Hubeau as download_Hubeau
from pathlib import Path
import src.utils.utils as utils
import src.processing.station as station
from tqdm import tqdm
import logging
from functools import cache
import src.utils.utils_file as utils_file
from src.config.paths import OUTPUT_DIR
from src.config.logging_config import setup_logger

# Initialiser le logger
logger = setup_logger(name="clean")

colonne_date_hubeau = "date_obs_elab"
colonne_code_station_hubeau = "code_station"

_cache = {}
def get_grandeur_historique_df(grandeur:str):
    """
    Renvoie le dataframe correspondant à la grandeur sur la période 1991-2020.
    S'assure que la données est téléchargé, si ce n'est pas le cas, la télécharge.
    :param grandeur: Une grandeur à télécharger
    :return: Une DataFrame des données de 1991 à 2020 sur la grandeur correspondante.
    """
    if grandeur not in _cache:
        logging.info("Reading files...")
        download_Hubeau.ensure_grandeur_historique_downloaded(grandeur)
        if utils.get_path_historique_raw_csv(grandeur).exists():
            _cache[grandeur] = pd.read_csv(utils.get_path_historique_raw_csv(grandeur))
        else:
            # Le fichier des données n'est pas contenu dans un gros document, mais dans plein de petit, on dois tous les lire et les concaténer.
            all_opened_df= []
            download_Hubeau.ensure_grandeur_mensuel_downloaded("1990-12", grandeur)
            all_opened_df.append(pd.read_csv(utils.get_path_mensuel_raw_csv("1990-12", grandeur)))
            for annee in range(1991, 2021):
                for mois in range(1, 13):
                    annee_mois = f"{annee}-{mois}"
                    if mois <= 9:
                        annee_mois = f"{annee}-0{mois}"
                    download_Hubeau.ensure_grandeur_mensuel_downloaded(annee_mois, grandeur)
                    all_opened_df.append(pd.read_csv(utils.get_path_mensuel_raw_csv(annee_mois,grandeur)))
            all_df = pd.concat(all_opened_df, ignore_index=True)
            _cache[grandeur] = all_df
        logging.info("Files Reading Complete")
    return _cache[grandeur]

def clean_hubeau_data(date_a_filtrer: str, code_sandre: str, path_file_to_clean=Path(""), grandeur_a_filtrer="", fichier_station_hubeau=str(OUTPUT_DIR / "hubeau" / "downloaded_data" / "stations" / "stations.csv")) -> pd.DataFrame:
    """
    Va chercher le fichier des observations qmm dans les fichiers téléchargé.
    Charge les données et prendre uniquement les données correspondantes à la date en paramètre.
    On nettoie les rangs dupliqué et ceux qui n'ont pas de données.
    :param grandeur_a_filtrer: Une grandeur à filtrer, utile uniquement lorsque l'on souhaite nettoyer des données historiques
    :param path_file_to_clean: Fichier vers le csv à nettoyer
    :param code_sandre: Le code sandre correspondant à la liste de station à extraire
    :param fichier_station_hubeau: Le nom du fichier à ouvrir et nettoyer.
    :param date_a_filtrer: La date qui servira de filtre au format YYYY-MM
    :return: Renvoie un pd.DataFrame représentant la grandeur souhaité sur de la date YYYY-MM-DD via l'API Hubeau
    """

    if path_file_to_clean != Path(""):
        # Delimiteur temportiare
        df_hubeau = pd.read_csv(path_file_to_clean)
    elif grandeur_a_filtrer in utils.GRANDEUR:
        if grandeur_a_filtrer == "QmnJ":
            download_Hubeau.ensure_grandeur_mensuel_downloaded(date_a_filtrer, grandeur_a_filtrer)
            df_hubeau = pd.read_csv(utils.get_path_mensuel_raw_csv(date_a_filtrer, grandeur_a_filtrer), low_memory=False)
        else:
            df_hubeau = get_grandeur_historique_df(grandeur_a_filtrer)
    else:
        logging.error("Path à nettoyer vide et grandeur inexistante.")
        raise NameError

    if df_hubeau.empty:
        logging.error("Le datafame lu est vide.")

    # Filtrage pour avoir uniquement les enregistrements aux bonnes dates tous le bon mois.
    df_hubeau_filtre_date = df_hubeau[df_hubeau[colonne_date_hubeau].astype(str).str.contains(date_a_filtrer)]

    # Ouverture et lecture du fichier des stations hubeau.
    # fichier_station_hubeau = output_folder / "stations.csv"
    df_stations_hubeau = station.get_stations(code_sandre, date_a_filtrer)

    # Garder uniquement les données qui correspondent au code Sandre.
    df_stations_hubeau_code_sandre = df_hubeau_filtre_date[
        # On garde les colonnes où les données apparaissent dans les station-filtré
        df_hubeau_filtre_date[colonne_code_station_hubeau].isin(
            df_stations_hubeau[colonne_code_station_hubeau]
        )
    ]

    # On supprime les doublons du DataFrame
    df_code_sandre_with_data_no_duplicate = df_stations_hubeau_code_sandre.drop_duplicates(subset=["code_station","date_obs_elab"])

    return df_code_sandre_with_data_no_duplicate

# DONNEE MENSUEL
def clean_single_month(annee_mois:str, code_sandre:str, grandeur:str):
    """
    Clean a file containing a single month of data.
    Download it if the file does not exist.
    :param grandeur: La grandeur a récupérer
    :param annee_mois: Année et mois au format AAAA-MM
    :param code_sandre: Code sandre à extraire
    """
    download_Hubeau.ensure_grandeur_mensuel_downloaded(annee_mois, grandeur)
    complete_path = utils.get_path_mensuel_raw_csv(annee_mois, grandeur)

    df_clean = clean_hubeau_data(
        annee_mois,
        code_sandre,
        path_file_to_clean=complete_path,
    )

    # Dossier de sortie
    output_file = utils.get_path_clean_csv(code_sandre, annee_mois, grandeur)

    df_clean.to_csv(output_file, index=False)

    logging.info(f"Fichier créé : {output_file}")

# DONNEE HISTORIQUE
def clean_historic_data(code_sandre:str, grandeur:str):
    """
    Nettoie les données historiques de 1991 à 2020
    :param grandeur: Filtre la grandeur souhaitée
    :param code_sandre: Filtre les données avec les stations associées à code_sandre.
    """
    total_iterations = (2021 - 1991) * 12
    with (tqdm(total=total_iterations, desc=f"Nettoyage des données historiques : {grandeur} - {code_sandre}") as pbar):
        start_date = "1991-01-01"
        if grandeur == "QmnJ":
            start_date = "1990-12-01"
        for date in pd.date_range(start_date, "2020-12-01", freq="MS"):
                annee_mois_filtre = date.strftime("%Y-%m")

                # Clean Hubeau data
                df_hubeau_clean = clean_hubeau_data(annee_mois_filtre,code_sandre, grandeur_a_filtrer=grandeur)
                chemin_fichier_clean_hubeau = utils.get_path_clean_csv(code_sandre, annee_mois_filtre, grandeur)
                df_hubeau_clean.to_csv(chemin_fichier_clean_hubeau, index=False)

                pbar.update(1)

# ENSURING DATA HAS BEEN CLEANED AND IS UP TO DATE.
def ensure_single_month_cleaned(annee_mois:str, code_reseau_sandre:str, grandeur:str):
    """
    S'assure que les données du mois sont à jour et qu'elles ont été calculés et synchronisées avec les données brutes.
    :param annee_mois: AAAA-MM
    :param code_reseau_sandre: Code du réseau sandre qui est nettoyé.
    :param grandeur: La grandeur à nettoyer.
    :return: Rien
    """
    chemin_fichier_clean_mensuel = utils.get_path_clean_csv(code_reseau_sandre, annee_mois, grandeur)
    chemin_source = utils.get_path_sources(code_reseau_sandre, grandeur, annee_mois)
    if not utils_file.is_res_updated_with_source(chemin_source, chemin_fichier_clean_mensuel):
        clean_single_month(annee_mois, code_reseau_sandre, grandeur)

@cache
def ensure_historic_cleaned(code_reseau_sandre:str, grandeur:str):
    """
    S'assure que les données historiques sont à jour et qu'elles ont été calculés et synchronisés avec les données brutes.
    :param code_reseau_sandre: Code du réseau sandre qui est nettoyé.
    :param grandeur: La grandeur à nettoyer.
    :return: Rien
    """
    start_date = "1991-01-01"
    if grandeur == "QmnJ":
        start_date = "1990-12-01"
    chemin_source = utils.get_paths_source_historique(grandeur)
    for date in pd.date_range(start_date, "2020-12-01", freq="MS"):
        annee_mois = date.strftime("%Y-%m")
        chemin_fichier_clean_mensuel = utils.get_path_clean_csv(code_reseau_sandre, annee_mois, grandeur)
        if not utils_file.is_res_updated_with_source(chemin_source, chemin_fichier_clean_mensuel):
            clean_historic_data(code_reseau_sandre, grandeur)


if __name__ == "__main__":
    ensure_single_month_cleaned("2025-06", "BSH001","QmnJ")
    ensure_single_month_cleaned("2025-07", "BSH001","QmnJ")
    ensure_single_month_cleaned("2025-08", "BSH001","QmnJ")
    ensure_single_month_cleaned("2024-06", "custom", "QmM")
    ensure_historic_cleaned("BSH001", "QmM")
    ensure_historic_cleaned("BSH001", "QmnJ")
    ensure_historic_cleaned("custom", "QmM")
    ensure_historic_cleaned("custom", "QmnJ")

