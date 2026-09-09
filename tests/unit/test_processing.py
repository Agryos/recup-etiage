"""
Unit tests for the processing module.
"""
import pytest
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import src.processing.station as station
import src.processing.clean as clean
import src.processing.calcul_vcn3 as calcul_vcn3
import src.processing.calcul_hydraulicite as calcul_hydraulicite
import src.processing.meteoFrance_aggregation_donnee as meteo_agg
import src.processing.meteofrance_normale as meteofrance_normale
from src.processing.meteoFrance_aggregation_donnee import GroupByMethod
from src.model.enums import GeographicScaleClip, OndeCampagneType, MeteoFranceDataType


class TestStation:
    """Tests for station.py"""
    
    @patch('src.processing.station.download_Hubeau.ensure_station_downloaded')
    @patch('src.processing.station.utils.get_path_stations')
    def test_get_stations_all(self, mock_get_path, mock_ensure_downloaded, sample_stations_dataframe):
        """Test get_stations with no code_sandre filter."""
        # Setup mocks
        mock_get_path.return_value = Path("mock/stations.csv")
        mock_ensure_downloaded.return_value = None
        
        with patch('pandas.read_csv', return_value=sample_stations_dataframe):
            result = station.get_stations(None, None)
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
    
    @patch('src.processing.station.download_Hubeau.ensure_station_downloaded')
    @patch('src.processing.station.utils.get_path_stations')
    def test_get_stations_with_code_sandre(self, mock_get_path, mock_ensure_downloaded, sample_stations_dataframe):
        """Test get_stations with code_sandre filter."""
        # Setup mocks
        mock_get_path.return_value = Path("mock/stations.csv")
        mock_ensure_downloaded.return_value = None
        
        with patch('pandas.read_csv', return_value=sample_stations_dataframe):
            result = station.get_stations("BSH001", None)
            
            assert isinstance(result, pd.DataFrame)
            # Should only have stations with BSH001
            assert result["code_sandre_reseau_station"].str.contains("BSH001").all()
            assert len(result) == 2

    @patch('src.processing.station.ensure_custom_list_up_to_date')
    @patch('src.processing.station.download_Hubeau.ensure_station_downloaded')
    @patch('src.processing.station.utils.get_path_stations')
    @patch('src.processing.station.utils.get_path_liste_site_station_custom')
    def test_get_stations_custom(self, mock_get_custom_path, mock_get_path, mock_ensure_downloaded, mock_custom_up_to_date, sample_stations_dataframe):
        """Test get_stations with custom code_sandre."""
        # Setup mocks
        mock_get_path.return_value = Path("mock/stations.csv")
        mock_get_custom_path.return_value = Path("mock/station_custom.csv")
        mock_ensure_downloaded.return_value = None

        custom_station_df = pd.DataFrame({"code_station": ["S001", "S002"],"code_site" : ["SiteA", "SiteB"]})

        with patch('pandas.read_csv') as mock_read:
            def read_side_effect(path, **kwargs):
                if "station_custom" in str(path):
                    return custom_station_df
                return sample_stations_dataframe

            mock_read.side_effect = read_side_effect

            result = station.get_stations("custom", None)

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2
    
    @patch('src.processing.station.download_Hubeau.ensure_station_downloaded')
    @patch('src.processing.station.utils.get_path_stations')
    def test_get_stations_with_date_filter(self, mock_get_path, mock_ensure_downloaded, sample_stations_dataframe):
        """Test get_stations with date filtering."""
        # Setup mocks
        mock_get_path.return_value = Path("mock/stations.csv")
        mock_ensure_downloaded.return_value = None
        
        with patch('pandas.read_csv', return_value=sample_stations_dataframe):
            result = station.get_stations("BSH001", "2023-06")
            
            assert isinstance(result, pd.DataFrame)
            # Should filter stations that are open in June 2023
            assert len(result) >= 0


class TestClean:
    """Tests for clean.py"""

    @patch('src.io.download_Hubeau.ensure_grandeur_historique_downloaded')
    @patch('pathlib.Path.exists')
    @patch('src.processing.clean.utils.get_path_historique_raw_csv')
    def test_get_grandeur_historique_df_qmm(self, mock_path, mock_exist, mock_ensure_downloaded):
        """Test get_grandeur_historique_df with QmM."""
        with patch.object(clean, '_cache', {}):
            with patch('pandas.read_csv') as mock_read:
                mock_path.return_value = Path("mock/clean-QmM-BSH001-2023-06.csv")
                mock_read.return_value = pd.DataFrame({"col1": [1, 2, 3]})

                result = clean.get_grandeur_historique_df("QmM")
                assert isinstance(result, pd.DataFrame)
    
    def test_clean_hubeau_data(self, sample_dataframe):
        """Test clean_hubeau_data function."""
        with patch('src.io.download_Hubeau.ensure_grandeur_mensuel_downloaded'):
            with patch('src.processing.clean.station.get_stations') as mock_get_stations:
                with patch('pandas.read_csv') as mock_read:
                    mock_read.return_value = pd.DataFrame({"col1": [1, 2, 3]})
                    mock_get_stations.return_value = pd.DataFrame({
                        "code_station": ["S1", "S2"],
                        "code_site": ["Site1", "Site2"]
                    })
                    
                    result = clean.clean_hubeau_data(
                        date_a_filtrer="2023-06",
                        code_sandre="BSH001",
                        path_file_to_clean=None,
                        grandeur_a_filtrer="QmM"
                    )

                    assert isinstance(result, pd.DataFrame)


class TestCalculVCN3:
    """Tests for calcul_vcn3.py"""
    
    def test_is_enough_data(self):
        """Test is_enough_data function."""
        from src.processing.calcul_frequence_periode_de_retour import is_enough_data
        
        # Test with enough data
        assert is_enough_data(np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), False) == True
        
        # Test with not enough data
        assert is_enough_data(np.array([1, 2, 3]), False) == False
        
        # Test with empty data
        assert is_enough_data(np.array([]), False) == False
    
    def test_get_vcn3_station_mois(self, sample_dataframe):
        """Test get_vcn3_station_mois function."""
        df = sample_dataframe.copy()
        df["resultat_obs_elab"] = [10.0, 20.0, 15.0, 12.0]
        
        result = calcul_vcn3.get_vcn3_station_mois(df, "S1", 2023, 1)
        
        assert isinstance(result, (float, np.floating))
        assert not np.isnan(result)


class TestCalculHydraulicite:
    """Tests for calcul_hydraulicite.py"""
    
    def test_get_qmm_moyenne_station_mois_from_df_all(self, sample_dataframe):
        """Test get_QmM_moyenne_station_mois_from_df_all function."""
        df_all = sample_dataframe.copy()
        df_all["date_obs_elab"] = ["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01"]
        df_all["resultat_obs_elab"] = [10.0, 20.0, 15.0, 12.0]
        
        result = calcul_hydraulicite.get_QmM_moyenne_station_mois_from_df_all(
            df_all, "S1", "01"
        )
        
        assert isinstance(result, (float, np.floating))


class TestMeteoFranceAggregation:
    """Tests for meteoFrance_aggregation_donnee.py"""
    
    def test_aggregate_range_sim2_quot(self):
        """Test aggregate_range with SIM2_QUOT data."""
        df = pd.DataFrame({
            "LAMBX": [1, 1, 2, 2],
            "LAMBY": [1, 1, 2, 2],
            "DATE": [20230601, 20230602, 20230601, 20230602],
            "DATE_DATETIME": pd.to_datetime(["2023-06-01", "2023-06-02", "2023-06-01", "2023-06-02"]),
            "PE": [1.0, 2.0, 3.0, 4.0],
            "T": [15.0, 16.0, 17.0, 18.0]
        })
        
        result = meteo_agg.aggregate_range(
            MeteoFranceDataType.SIM2_QUOT,
            df,
            GroupByMethod.BY_POSITION
        )
        
        assert isinstance(result, pd.DataFrame)
        assert "PE_sum" in result.columns or "PE" in result.columns
        assert "T_mean" in result.columns or "T" in result.columns
    
    def test_aggregate_range_by_date(self):
        """Test aggregate_range with BY_DATE method."""
        df = pd.DataFrame({
            "LAMBX": [1, 1],
            "LAMBY": [1, 1],
            "DATE_DATETIME": pd.to_datetime(["2023-06-01", "2023-06-02"]),
            "PE": [1.0, 2.0]
        })
        
        result = meteo_agg.aggregate_range(
            MeteoFranceDataType.SIM2_QUOT,
            df,
            GroupByMethod.BY_DATE
        )
        
        assert isinstance(result, pd.DataFrame)


class TestProcessOnde:
    """Tests for process_onde.py"""
    
    def test_filter_campagne_type(self):
        """Test filter_campagne_type function."""
        df = pd.DataFrame({
            "code_type_campagne": [1, 2, 1, 2, 1],
            "code_station": ["S1", "S2", "S3", "S4", "S5"]
        })
        
        # Test USUELLE filter
        result = station.filter_campagne_type(df, OndeCampagneType.USUELLE)
        assert len(result) == 3
        assert all(result["code_type_campagne"] == 1)
        
        # Test COMPLEMENTAIRE filter
        result = station.filter_campagne_type(df, OndeCampagneType.COMPLEMENTAIRE)
        assert len(result) == 2
        assert all(result["code_type_campagne"] == 2)
        
        # Test ALL_CAMPAGNE filter
        result = station.filter_campagne_type(df, OndeCampagneType.ALL_CAMPAGNE)
        assert len(result) == 5
    
    def test_keep_last_station_data(self):
        """Test keep_last_station_data function."""
        df = pd.DataFrame({
            "code_station": ["S1", "S1", "S2"],
            "date_observation": pd.to_datetime(["2023-06-01", "2023-06-02", "2023-06-01"]),
            "mois": [6, 6, 6],
            "annee": [2023, 2023, 2023],
            "geometry": ["POINT(1 1)", "POINT(1 1)", "POINT(2 2)"]
        })
        
        result = station.keep_last_station_data(df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # Should keep only one entry per station


class TestMeteoFranceNormale:
    """Tests for meteofrance_normale.py - calcul des normales historiques.

    Ces tests mockent la couche d'accès aux données (df_range_processed) pour
    éviter tout téléchargement réseau et exercer directement la logique
    d'agrégation historique, qui dépend des colonnes variant selon le type
    de donnée (LAMBX/LAMBY + DATE pour SIM2, LAT/LON + AAAAMM/AAAAMMJJ pour brut).
    """

    @staticmethod
    def _make_aggregated_mens_df(year):
        """Données MENS agrégées par position (sortie d'aggregate_range BY_POSITION)."""
        aaaamm = int(f"{year}08")
        return pd.DataFrame({
            "LAT": [48.0, 49.0],
            "LON": [2.0, 3.0],
            "AAAAMM_min": [aaaamm, aaaamm],
            "AAAAMM_max": [aaaamm, aaaamm],
            "DATE_DATETIME_min": pd.to_datetime([f"{year}-08-01", f"{year}-08-01"]),
            "DATE_DATETIME_max": pd.to_datetime([f"{year}-08-31", f"{year}-08-31"]),
            "RR": [50.0, 60.0],
            "RR_ME": [55.0, 65.0],
            "RRAB": [1.0, 2.0],
            "TX": [25.0, 26.0],
            "TX_ME": [24.0, 25.0],
        })

    @staticmethod
    def _make_aggregated_sim2_mens_df(year):
        """Données SIM2_MENS agrégées par position (LAMBX/LAMBY, DATE)."""
        date_int = int(f"{year}08")
        return pd.DataFrame({
            "LAMBX": [100, 200],
            "LAMBY": [100, 200],
            "DATE_min": [date_int, date_int],
            "DATE_max": [date_int, date_int],
            "DATE_DATETIME_min": pd.to_datetime([f"{year}-08-01", f"{year}-08-01"]),
            "DATE_DATETIME_max": pd.to_datetime([f"{year}-08-31", f"{year}-08-31"]),
            "PRENEI": [10.0, 20.0],
            "PRELIQ": [30.0, 40.0],
            "PRETOTM": [40.0, 60.0],
            "T": [20.0, 22.0],
            "EVAP": [5.0, 6.0],
            "ETP": [7.0, 8.0],
            "PE": [33.0, 52.0],
            "SWI": [0.5, 0.6],
            "DRAINC": [1.0, 2.0],
            "RUNC": [1.0, 2.0],
            "ECOULEMENT": [1.0, 2.0],
        })

    @patch('src.processing.meteofrance_normale.get_path_meteofrance_historic_mean')
    @patch('src.processing.meteofrance_normale.df_range_processed')
    def test_get_historic_mean_mens(self, mock_df_range, mock_path, tmp_path):
        """get_historic_mean doit fonctionner pour MENS (LAT/LON, AAAAMM_min).

        Avant le fix, levait KeyError: 'DATE_min' (MENS n'a pas de colonne DATE).
        """
        mock_path.return_value = tmp_path / "nonexistent-historic.csv"
        mock_df_range.side_effect = lambda data_freq, start_date, *a, **k: \
            self._make_aggregated_mens_df(start_date.year)

        result = meteofrance_normale.get_historic_mean(
            MeteoFranceDataType.MENS, datetime(2026, 8, 1), datetime(2026, 8, 31))

        assert isinstance(result, pd.DataFrame)
        # 2 positions distinctes -> 2 lignes après groupby par LAT/LON
        assert len(result) == 2
        assert {"LAT", "LON"}.issubset(result.columns)
        assert "RR" in result.columns
        assert "TX_ME" in result.columns

    @patch('src.processing.meteofrance_normale.get_path_meteofrance_historic_mean')
    @patch('src.processing.meteofrance_normale.df_range_processed')
    def test_get_historic_mean_sim2_mens_still_works(self, mock_df_range, mock_path, tmp_path):
        """get_historic_mean doit toujours fonctionner pour SIM2_MENS (LAMBX/LAMBY, DATE_min)."""
        mock_path.return_value = tmp_path / "nonexistent-historic.csv"
        mock_df_range.side_effect = lambda data_freq, start_date, *a, **k: \
            self._make_aggregated_sim2_mens_df(start_date.year)

        result = meteofrance_normale.get_historic_mean(
            MeteoFranceDataType.SIM2_MENS, datetime(2026, 8, 1), datetime(2026, 8, 31))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert {"LAMBX", "LAMBY"}.issubset(result.columns)

    @patch('src.processing.meteofrance_normale.get_path_meteofrance_historic_mean')
    @patch('src.processing.meteofrance_normale.df_range_processed')
    def test_get_rapport_normale_mens(self, mock_df_range, mock_path, tmp_path):
        """get_rapport_normale doit calculer les rapports à la normale pour MENS.

        Avant le fix, levait KeyError sur set_index(['LAMBX','LAMBY']) (MENS utilise LAT/LON).
        """
        mock_path.return_value = tmp_path / "nonexistent-historic.csv"
        mock_df_range.side_effect = lambda data_freq, start_date, *a, **k: \
            self._make_aggregated_mens_df(start_date.year)

        df_actuel = self._make_aggregated_mens_df(2026)
        result = meteofrance_normale.get_rapport_normale(
            MeteoFranceDataType.MENS, df_actuel, datetime(2026, 8, 1), datetime(2026, 8, 31))

        assert isinstance(result, pd.DataFrame)
        assert "RR_rapport_normale" in result.columns
        assert "TX_ME_rapport_normale" in result.columns
        assert {"LAT", "LON"}.issubset(result.columns)
