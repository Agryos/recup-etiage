from tqdm import tqdm
from src.model.enums import GeographicScaleClip,MeteoFranceDataType
from datetime import datetime
from pathlib import Path
import pandas as pd
import geopandas as gpd
import src.processing.meteoFrance_aggregation_donnee as MeteoAgg
from src.processing.meteoFrance_aggregation_donnee import GroupByMethod
import matplotlib.pyplot as plt
from src.config.logging_config import setup_logger
from src.config.paths import OUTPUT_DIR
from src.plotting.rasterize import rasterize_geodataframe_geographiv_zone
from src.plotting.utils import get_bassin_versant, get_geographic_element
from src.io.download_meteoFrance import get_geographic_list
from src.utils.utils import get_chemin_sauvegarde_meteofrance, get_chemin_sauvegarde_geographie
import src.processing.meteofrance_normale as MeteoNormale

# Initialiser le logger
logger = setup_logger(name="plot_meteoFrance")

def to_lambert2_geodataframe(data_freq:MeteoFranceDataType, df_to_convert:pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Convertis le DataFrame en GeoDataFrame, doit avoir les colonne LAMBX et LAMBY et être en coordonnées EPSG:27572
    :param df_to_convert: Le DataFrame a convertir ne GeoDataFrame.
    :return: Le GeoDataFrame convertis.
    """
    match data_freq:
        case MeteoFranceDataType.SIM2_QUOT | MeteoFranceDataType.SIM2_MENS:
            return gpd.GeoDataFrame(df_to_convert,
                                    geometry=gpd.points_from_xy(df_to_convert.LAMBX * 100, df_to_convert.LAMBY * 100),
                                    crs="EPSG:27572")
        case MeteoFranceDataType.QUOT | MeteoFranceDataType.MENS:
            return gpd.GeoDataFrame(df_to_convert,
                                    geometry=gpd.points_from_xy(df_to_convert.LON, df_to_convert.LAT),
                                    crs="EPSG:4326").to_crs("EPSG:27572")

def clip_with_distance(gdf_to_clip : gpd.GeoDataFrame, clip_mask:gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Clip le geoDataFrame avec le clip_mask en utilisant une distance pour prendre les contours.
    :param gdf_to_clip: Le GeoDataFrame a découper.
    :param clip_mask: Le Masque de découpage
    :return: Un GeoDataFrame Découpé.
    """
    if len(clip_mask) > 1:
        logger.warning("Auscour ascour clip_mask a plusieurs géométrie.........")
    return gdf_to_clip[gdf_to_clip.geometry.distance(clip_mask.geometry.iloc[0]) < 7000]

def plot_geojson_from_lambert2(output_path:Path, gdf_ready: gpd.GeoDataFrame):
    """
    Enregistre le Dataframe sous forme de Geojson et de csv dans l'output_path.
    Si le gdf_ready est vide, ne fais rien.
    :param output_path: Endroit où le fichier va être sauvegardé.
    :param gdf_ready: Le DataFrame à plot.
    :return: Rien
    """
    logger.info("Saving...")
    if not gdf_ready.empty:
        gdf_ready.to_file(output_path.with_suffix(".geojson"), driver="GeoJSON", mode="w")
        gdf_ready.to_csv(output_path.with_suffix(".csv"), mode="w", index=False)
    else:
        logger.warning("gdf empty ! " + str(output_path))


def export_to_every_geographic_element(data_freq: MeteoFranceDataType, geographic_scale:GeographicScaleClip, df:pd.DataFrame, chemin_save_original:Path, is_data_aggregated:bool, is_single_data:bool):
    """
    Export en géojson le df à toute les échelles.

    Génère des plots si associés à chaque zone géographique, si les données ne sont pas aggrégé.
    :param is_data_aggregated: Si les données sont aggrégé, ne génère pas les plots.
    :param data_freq:
    :param geographic_scale:
    :param df:
    :param chemin_save_original:
    :param is_single_data:
    :return:
    """
    logger.info(f"Export de tous les region géographique en cours : {geographic_scale}...")
    # Conversion des coordonnées du dataframe
    logger.info("Conversion des coordonnées")
    gdf = to_lambert2_geodataframe(data_freq, df)
    chemin_save_plot = chemin_save_original.parent / "plots"
    # De manière générale, sauf nationale et bassin le masque doit être redécoupé.
    is_bassin_clip_required = False
    match geographic_scale:
        case GeographicScaleClip.NATIONAL:
            plot_geojson_from_lambert2(chemin_save_original, gdf)
            return
        case GeographicScaleClip.BASSIN | GeographicScaleClip.DEPARTEMENT_ADMINISTRATIF | GeographicScaleClip.REGION_ADMINISTRATIVE:
            is_bassin_clip_required = False
        case GeographicScaleClip.DEPARTEMENT_BASSIN | GeographicScaleClip.REGION_BASSIN:
            is_bassin_clip_required = True
        case GeographicScaleClip.ECOREGION_HYDROLOGIQUE:
            is_bassin_clip_required = False
        case _:
            raise NotImplementedError("L'échelle geographique n'est pas implémenté")

    element_list = get_geographic_list(geographic_scale)
    if "DATE_DATETIME" in gdf.columns:
        start_date = gdf["DATE_DATETIME"].min()
        end_date = gdf["DATE_DATETIME"].max()
    elif "DATE_DATETIME_min" in gdf.columns and "DATE_DATETIME_max":
        start_date = gdf["DATE_DATETIME_min"].min()
        end_date = gdf["DATE_DATETIME_max"].max()
    else:
        raise ValueError("Date de début et de fin non trouvée")

    chemin_zone_geographique = chemin_save_plot / geographic_scale
    logger.info("Récupération Mask bassin versant")
    # Récupération du bassin versant (on prend le premier bassin versant de la liste des bassin versant.
    code_bassin_decoupe = get_geographic_list(GeographicScaleClip.BASSIN)[0]
    gdf_bassin_mask = get_bassin_versant(code_bassin_decoupe)
    for code in tqdm(element_list):
        logger.debug(f"code : {code}")
        logger.info("Récupération Mask")
        gdf_geographie_mask = get_geographic_element(geographic_scale, code)

        # On procède au clipping du gdf d'origine.
        logger.info("Clipping GeoDataFrame with geographic mask.")
        gdf_first_clip = clip_with_distance(gdf, gdf_geographie_mask)

        # Si on doit prendre l'échelle bassin, on découpe les données restantes avec le masque du bassin.
        logger.info("Clipping GeoDataFrame with Bassin mask.")
        if is_bassin_clip_required:
            gdf_second_clip = clip_with_distance(gdf_first_clip, gdf_bassin_mask)
        else:
            gdf_second_clip = gdf_first_clip

        if len(gdf_second_clip) == 0:
            logger.warning("Les données se sont fait supprimé par la découpe sur bassin et la géographie !")
            logger.info("Passage à l'élément suivant !")
            continue

        # On récupère le chemin de sauvegarde.
        chemin_save = get_chemin_sauvegarde_geographie(geographic_scale, chemin_save_original,code)
        chemin_save.parent.mkdir(exist_ok=True)

        # On plot le résultat
        logger.info("Sauvegarde gdf")
        plot_geojson_from_lambert2(chemin_save, gdf_second_clip)

        # On crée les plots matplotlib associé à cette zone gégraphique.
        if (not is_single_data) and (not is_data_aggregated):
            logger.info("Créations des plots pour la zone géographique.")
            gdf_aggrege_by_datetime = MeteoAgg.aggregate_range(data_freq ,gdf_second_clip, GroupByMethod.BY_DATE)
            #Créer le dossier de cahque zone geographiique et faire a l'interieur un dossier par code.
            chemin_code = chemin_zone_geographique / code
            chemin_code.mkdir(parents=True, exist_ok=True)
            nom_echelle = f"{geographic_scale}-{code}"
            create_all_plot_for_unique_scale(gdf_aggrege_by_datetime, nom_echelle, start_date,end_date, chemin_code)
        else:
            # On créer les raster si les données sont aggrégés.
            rasterize_meteofrance(gdf_second_clip.to_crs(2154), data_freq, geographic_scale, code, chemin_save)

    logger.info(f"Export de tous les {geographic_scale} terminés.")

def rasterize_meteofrance(gdf: gpd.GeoDataFrame, data_freq:MeteoFranceDataType, geographic_scale: GeographicScaleClip, code_zone: str, chemin_save:Path, no_interpolation: bool = False):
    def rasterize_colonne(nom_colonne:str, unite:str=""):
        rasterize_geodataframe_geographiv_zone(
            gdf,
            nom_colonne,
            geographic_scale,
            code_zone,
            chemin_save.with_stem(f"{chemin_save.stem}-{nom_colonne}").with_suffix(".png"),
            f"{chemin_save.stem}-{nom_colonne}{unite}",
            no_interpolation
        )

    match data_freq:
        case MeteoFranceDataType.SIM2_QUOT:
            rasterize_colonne("SSWI_10J")
            rasterize_colonne("EVAP", "(mm)")
            rasterize_colonne("ETP", "(mm)")
            rasterize_colonne("PE", "(mm)")
            rasterize_colonne("PRELIQ", "(mm)")
        case MeteoFranceDataType.SIM2_MENS:
            rasterize_colonne("SSWI1")
            rasterize_colonne("EVAP", "(mm)")
            rasterize_colonne("ETP", "(mm)")
            rasterize_colonne("PE", "(mm)")
            rasterize_colonne("PRELIQ", "(mm)")
            rasterize_colonne("SPI1")
        case MeteoFranceDataType.QUOT:
            pass
        case MeteoFranceDataType.MENS:
            pass


def create_all_plot_for_unique_scale(df_aggregated:pd.DataFrame, nom_echelle:str, start_date:datetime, end_date:datetime, chemin_de_base:Path):
    """
    Créer tous les plots avec ce Dataframe en entrée, les sauvegarde dans le dossier pointé par le chemin_de_base.

    Le titre des plots est au format '[Description de l'unité] : [nom_echelle] [start_date] [end_date]'.
    :param df_aggregated:
    :param nom_echelle: Chaine de caractère indiquant le nom de cette échelle.
    :param start_date:
    :param end_date:
    :param chemin_de_base:
    :return:
    """
    # On crée le dossier où tout est sauvegardé.
    chemin_de_base.mkdir(exist_ok=True)

    dataframe_trie_par_date = df_aggregated.sort_values(by=["DATE_DATETIME"])
    dataframe_date = dataframe_trie_par_date["DATE_DATETIME"]
    # SSWI_10J
    if "SSWI_10J" in dataframe_trie_par_date.columns:
        max_value = max(2, dataframe_trie_par_date["SSWI_10J"].max()) + 0.2
        min_value = min(-2, dataframe_trie_par_date["SSWI_10J"].min()) - 0.2
        plot_bar_dataframe(dataframe_trie_par_date["SSWI_10J"],
                           dataframe_date,
                           normale_value=0,
                           plot_title=f"Standardized Soil Wetness Index : {nom_echelle} {start_date:%Y%m%d} {end_date:%Y%m%d}",
                           output_path=chemin_de_base / "SSWI_10J.png",
                           reference_lines={
                               "Extrêmement humide": (1.75, max_value, "midnightblue"),
                               "Très humide": (1.28, 1.75, "royalblue"),
                               "Modérément humide": (0.84, 1.28, "turquoise"),
                               "Autour de la Normale": (-0.84, 0.84, "lime"),
                               "Modérément sec": (-1.28, -0.84, "yellow"),
                               "Très sec": (-1.75, -1.28, "darkorange"),
                               "Extrêmement sec": (min_value, -1.75, "darkred"),
                           })

    if "PE" in dataframe_trie_par_date.columns:
        plot_bar_dataframe(dataframe_trie_par_date["PE"],
                           dataframe_date,
                           plot_title=f"Pluie Efficace : {nom_echelle} {start_date:%Y%m%d} {end_date:%Y%m%d}",
                           output_path=chemin_de_base / "PE.png")

    if "PRELIQ" in dataframe_trie_par_date.columns:
        plot_bar_dataframe(dataframe_trie_par_date["PRELIQ"],
                           dataframe_date,
                           plot_title=f"Cumul des précipitation liquide quotidiennes (mm) : {nom_echelle} {start_date:%Y%m%d} {end_date:%Y%m%d}",
                           output_path=chemin_de_base / "PRELIQ.png")

    if "EVAP" in dataframe_trie_par_date.columns:
        plot_bar_dataframe(dataframe_trie_par_date["EVAP"],
                           dataframe_date,
                           plot_title=f"Cumul de l'évapotranspiration quotidienne (mm) : {nom_echelle} {start_date:%Y%m%d} {end_date:%Y%m%d}",
                           output_path=chemin_de_base / "EVAP.png")

    if "ETP" in dataframe_trie_par_date.columns:
        plot_bar_dataframe(dataframe_trie_par_date["ETP"],
                           dataframe_date,
                           plot_title=f"Cumul de l'évapotranspiration potentielle quotidienne (mm) : {nom_echelle} {start_date:%Y%m%d} {end_date:%Y%m%d}",
                           output_path=chemin_de_base / "ETP.png")

    if "RR" in dataframe_trie_par_date.columns:
        plot_bar_dataframe(dataframe_trie_par_date["RR"],
                           dataframe_date,
                           plot_title=f"Cumul de pluie : {nom_echelle} {start_date:%Y%m%d} {end_date:%Y%m%d}",
                           output_path=chemin_de_base / "RR.png")

    if "SPI1" in dataframe_trie_par_date.columns:
        max_value = max(2, dataframe_trie_par_date["SPI1"].max()) + 0.2
        min_value = min(-2, dataframe_trie_par_date["SPI1"].min()) - 0.2
        plot_bar_dataframe(dataframe_trie_par_date["SPI1"],
                           dataframe_date,
                           normale_value=0,
                           plot_title=f"Cumul de pluie : {nom_echelle} {start_date:%Y%m%d} {end_date:%Y%m%d}",
                           output_path=chemin_de_base / "SPI1.png",
                           reference_lines={
                               "Extrêmement humide": (2.0, max_value, "midnightblue"),
                               "Modérément humide": (1.0, 2.0, "turquoise"),
                               "Autour de la Normale": (-1.0, 1.0, "lime"),
                               "Modérément sec": (-2.0, -1.0, "yellow"),
                               "Extrêmement sec": (min_value, -2, "darkred"),
                           }
                           )



def export_all_format_geojson_range(geo_scale:GeographicScaleClip, data_freq:MeteoFranceDataType, start_date:datetime, end_date:datetime, is_data_aggregated:bool,
                                    has_index_update:bool=True, is_data_update_allowed:bool=True) -> None:
    """
    Enregistre des geojson contenant toutes les données entre start_date et end_date.
    Créer des découpages à l'échelle départementale, régionale et bassin.

    De plus, si les données ne sont pas aggrégé, produit des plots pour chaque métrique surveillé.
    :param geo_scale: L'échelle à laquelle le geojson sera produit
    :param is_data_aggregated: Si a True, les données sont aggrégés, si a False, on retrouve les données individuelles.
    :param data_freq: Type de donnée à récupérer
    :param start_date: Date de début (inclus dans l'intervalle)
    :param end_date: Date de fin (inclus dans l'intervalle)
    :param has_index_update: Défini si l'index fichiers -> id_datagouv est mis à jour. Peut-être long pour les fichiers données non-analysé.
    :param is_data_update_allowed: Si à faux, aucune mis à jour n'est fait, ni sur les fichiers à télécharger, ni sur les index.
    :return: Rien
    """
    if not is_data_update_allowed:
        has_index_update = False

    df_intervalle = MeteoNormale.df_range_processed(data_freq, start_date, end_date, is_data_aggregated, has_index_update, is_data_update_allowed)
    # Il y a trop de données dans les données quotidiennes pour qu'on puisse se permettre de les agréger en mémoire...
    match data_freq:
        case MeteoFranceDataType.MENS | MeteoFranceDataType.SIM2_MENS:
            df_rapport_normale = MeteoNormale.get_rapport_normale(data_freq, df_intervalle, start_date, end_date)
        case MeteoFranceDataType.QUOT | MeteoFranceDataType.SIM2_QUOT:
            df_rapport_normale = df_intervalle
    chemin_sauvegarde = get_chemin_sauvegarde_meteofrance(data_freq, start_date, end_date, is_data_aggregated)
    chemin_sauvegarde.parent.mkdir(exist_ok=True)

    is_single_data = False
    if start_date.strftime("%Y%m%d") == end_date.strftime("%Y%m%d") and (data_freq == MeteoFranceDataType.SIM2_QUOT or data_freq == MeteoFranceDataType.QUOT):
        is_single_data = True

    if start_date.strftime("%Y%m") == end_date.strftime("%Y%m") and (data_freq == MeteoFranceDataType.SIM2_MENS or data_freq == MeteoFranceDataType.MENS):
        is_single_data = True

    export_to_every_geographic_element(data_freq, geo_scale, df_rapport_normale, chemin_sauvegarde, is_data_aggregated, is_single_data)

def plot_bar_dataframe(
    series_to_plot: pd.Series,
    series_date: pd.Series,
    normale_value: float = None,
    plot_title: str = "",
    reference_lines: dict[str, tuple[float,float,str]] = None,
    output_path: Path = None
):
    """
    Affiche une serie de données sous forme de barres,
    avec en abscisse la date et en ordonnée les valeurs de la série.
    Compare les valeurs à la normale_value.

    Enregistre le plot dans output_path.
    :param series_to_plot:La série de valeurs à afficher
    :param series_date:La série de datetime correspondant aux valeurs
    :param normale_value: La valeur normale pour cette série.
    :param plot_title:Le titre du plot
    :param reference_lines: Un ensemble de ligne horizontale traversant le graphique
    :param output_path: Chemin vers lequel le plot est enregistré.
    :return: Rien
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Zone horizontale de référence.
    if reference_lines is not None:
        for key_label in reference_lines.keys():
            start_range, end_range, color = reference_lines[key_label]
            ax.axhspan(
                ymin=start_range,
                ymax=end_range,
                alpha=0.3,
                color=color,
                linestyle="--",
                linewidth=1,
                label=f"{key_label} [{start_range:.2f}:{end_range:.2f}]"
            )

    # Barres de la série
    ax.bar(
        series_date.values,
        series_to_plot.values,
        label=series_to_plot.name or "Valeurs"
    )

    # Ligne de normale
    if normale_value is not None:
        ax.axhline(
            y=normale_value,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Normale 1991-2020 : {normale_value:.2f}"
        )

    ax.set_title(plot_title)
    ax.set_xlabel(series_date.name or "")
    ax.set_ylabel(series_to_plot.name or "Valeur")
    ax.legend()

    plt.tight_layout()

    if output_path is not None:
        fig.savefig(output_path, dpi=300)
    plt.close(fig)



if __name__ == "__main__":
    logger.info("Plotting !")

    # Donnée MENS aggrégé de 2025 à 2026.
    # export_geojson_range(MeteoFranceDataType.SIM2_MENS, datetime(2025, 1, 1), datetime(2025, 12, 31), False)
    # Cumul depuis le dernier bulletin 10 juin et nombre de jour où la temptérature est au-dessus de la normale.
    #today = datetime.today()
    #export_geojson_range(MeteoFranceDataType.SIM2_QUOT, datetime(2026, 6, 10), today, True)

    # SWI du 14 juin
    # export_geojson_day(datetime(2026,6,14))

    # # Données pour 1 seul jour
    # plot_day(datetime(2026,5,18))
    #
    # # Données non-aggrégé sur 1 mois.
    #export_geojson_month(MeteoFranceDataType.SIM2_QUOT, datetime(2026, 5, 1))
    #export_geojson_day(MeteoFranceDataType.QUOT, datetime(2026, 6, 1))
    # export_geojson_month(MeteoFranceDataType.MENS, datetime(2026, 5, 1))

    # # Données aggrégé de base sur 1 mois.
    # plot_month(MeteoFranceDataType.SIM2_MENS, datetime(2026,5,1))
    #
    # # Données aggrégés allant d'un jour à un autre.
    # export_geojson_range(MeteoFranceDataType.SIM2_QUOT, datetime(2026,5,7), datetime(2026, 5,14), True)
    #
    # # Donnée MENS non-aggrégé de 2020 à 2026.
    # export_geojson_range(MeteoFranceDataType.SIM2_MENS, datetime(2020, 1, 1), datetime(2026, 5, 1), False)

    # CUMUL des quantités d'eau depuis le début de l'année hydrologique.
    today = datetime.today()
    # export_all_format_geojson_range(MeteoFranceDataType.SIM2_MENS, datetime(2025, 9, 1), today, False)
    # export_all_format_geojson_range(MeteoFranceDataType.MENS, datetime(2025, 9, 1), today, False)

    # Evlution du 10 au 24 juin.
    #export_all_format_geojson_range(MeteoFranceDataType.SIM2_QUOT, datetime(2026, 6, 10), today, False)

    # export_all_format_geojson_range(MeteoFranceDataType.SIM2_QUOT, datetime(2026, 6, 10), today, True)

    #export_all_format_geojson_range(MeteoFranceDataType.QUOT, datetime(2026, 6, 10), today, True)
    #export_all_format_geojson_range(MeteoFranceDataType.QUOT, datetime(2026, 6, 10), today, False)
    annee = 2026
    export_all_format_geojson_range(GeographicScaleClip.REGION_BASSIN, MeteoFranceDataType.SIM2_MENS, datetime(annee, 6, 1), datetime(annee, 6, 30), True)
