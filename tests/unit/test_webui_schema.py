"""
Unit tests for webui/schema.py — construction des commandes CLI.

Ce module est la source de vérité de la parité CLI de la WebUI : ces tests
vérifient que ``build_commands`` produit exactement les arguments attendus pour
chaque type de génération, et que ``build_types_schema`` expose la forme attendue
au frontend.
"""
import sys
from pathlib import Path

import pytest

# Ajoute la racine du projet au path (pour le paquet webui).
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.schema import build_commands, build_types_schema


class TestBuildTypesSchema:
    """Forme du schéma servi au frontend."""

    def test_six_types(self):
        schema = build_types_schema()
        assert set(schema.keys()) == {
            "hydraulicite", "vcn3", "both", "meteo", "onde", "stations-sites",
        }

    def test_chaque_type_a_label_et_fields(self):
        schema = build_types_schema()
        for key, t in schema.items():
            assert t["label"], key
            assert isinstance(t["fields"], list) and t["fields"], key
            for f in t["fields"]:
                assert "name" in f and "label" in f and "type" in f, (key, f)

    def test_selects_ont_options_et_default_valide(self):
        schema = build_types_schema()
        for key, t in schema.items():
            for f in t["fields"]:
                if f["type"] == "select":
                    assert "options" in f, (key, f["name"])
                    assert f["default"] in f["options"], (key, f["name"])


class TestBuildCommands:
    """Construction des commandes CLI par type."""

    def test_hydraulicite(self):
        cmds = build_commands(
            "hydraulicite",
            {"start_date": "2026-09", "reseau_sandre": "BSH001"},
            python_executable="python",
        )
        assert cmds == [["python", "main.py", "--type", "hydraulicite",
                         "--start_date", "2026-09", "--reseau_sandre", "BSH001"]]

    def test_vcn3_sans_graphic(self):
        cmds = build_commands(
            "vcn3",
            {"start_date": "2026-09", "reseau_sandre": "BSH001", "vcn3_graphic": False},
            python_executable="python",
        )
        assert cmds == [["python", "main.py", "--type", "vcn3",
                         "--start_date", "2026-09", "--reseau_sandre", "BSH001"]]

    def test_vcn3_avec_graphic(self):
        cmds = build_commands(
            "vcn3",
            {"start_date": "2026-09", "reseau_sandre": "BSH001", "vcn3_graphic": True},
            python_executable="python",
        )
        assert cmds[0][-1] == "--vcn3_graphic"

    def test_both_produit_deux_commandes(self):
        cmds = build_commands(
            "both",
            {"start_date": "2026-09", "reseau_sandre": "BSH001", "vcn3_graphic": False},
            python_executable="python",
        )
        assert len(cmds) == 2
        assert cmds[0][3] == "hydraulicite"
        assert cmds[1][3] == "vcn3"

    def test_meteo_type_compose_et_flags(self):
        cmds = build_commands(
            "meteo",
            {
                "meteo_freq": "QUOT",
                "meteo_source": "sim2",
                "geographic_scale": "BASSIN",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
                "meteo_aggregate": True,
                "meteo_no_update": False,
                "meteo_no_index_update": False,
            },
            python_executable="python",
        )
        cmd = cmds[0]
        assert "meteo_sim2_QUOT" in cmd
        assert "BASSIN" in cmd
        assert "--meteo_aggregate" in cmd
        assert "--meteo_no_update" not in cmd
        assert "--meteo_no_index_update" not in cmd

    def test_meteo_flags_optionnels(self):
        cmds = build_commands(
            "meteo",
            {
                "meteo_freq": "MENS",
                "meteo_source": "brut",
                "geographic_scale": "NATIONAL",
                "start_date": "2026-09",
                "end_date": "2026-09",
                "meteo_aggregate": False,
                "meteo_no_update": True,
                "meteo_no_index_update": True,
            },
            python_executable="python",
        )
        cmd = cmds[0]
        assert "meteo_brut_MENS" in cmd
        assert "--meteo_aggregate" not in cmd
        assert "--meteo_no_update" in cmd
        assert "--meteo_no_index_update" in cmd

    def test_onde_avec_zone(self):
        cmds = build_commands(
            "onde",
            {
                "onde_campagne": "ALL",
                "geographic_scale": "BASSIN",
                "onde_zone_code": "06",
                "start_date": "2026-09",
            },
            python_executable="python",
        )
        cmd = cmds[0]
        assert "onde_ALL" in cmd
        assert "--onde_zone_code" in cmd and "06" in cmd

    def test_onde_sans_zone(self):
        cmds = build_commands(
            "onde",
            {
                "onde_campagne": "USUELLE",
                "geographic_scale": "BASSIN",
                "onde_zone_code": "",
                "start_date": "2026-09",
            },
            python_executable="python",
        )
        cmd = cmds[0]
        assert "onde_USUELLE" in cmd
        assert "--onde_zone_code" not in cmd

    def test_stations_sites_date_optionnelle(self):
        # Date vide => pas de --start_date.
        cmds = build_commands(
            "stations-sites",
            {"reseau_sandre": "BSH001", "start_date": ""},
            python_executable="python",
        )
        assert "--start_date" not in cmds[0]
        # Date remplie => --start_date présent.
        cmds = build_commands(
            "stations-sites",
            {"reseau_sandre": "BSH001", "start_date": "2026-09"},
            python_executable="python",
        )
        assert "--start_date" in cmds[0] and "2026-09" in cmds[0]

    def test_type_inconnu_leve_value_error(self):
        with pytest.raises(ValueError):
            build_commands("inexistant", {}, python_executable="python")

    def test_python_executable_par_defaut(self):
        cmds = build_commands(
            "hydraulicite",
            {"start_date": "2026-09", "reseau_sandre": "BSH001"},
        )
        assert cmds[0][0] == sys.executable
