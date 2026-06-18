"""Tests voor derivatiefuncties in transform.py."""

from pathlib import Path

import pandas as pd
import pytest

from duo_mbo_datafiles.ingest import parse_grondslag_ip, parse_ro, parse_tbgi
from duo_mbo_datafiles.transform import (
    derive_cohortjaar,
    derive_dropout,
    derive_leeftijd,
    derive_opleidingssector,
    derive_vooropleiding_categorie,
)

DEMO = Path(__file__).parent.parent / "data" / "01-raw" / "demo"
H15 = DEMO / "h15" / "RO_27DV_20240731_20260324.csv"
H16 = DEMO / "h16" / "TBGI_25LX_2027_20251124.XML"
H17 = DEMO / "h17" / "GRONDSLAG_IP_MBO_27DV_20251119_2025.csv"


@pytest.fixture
def df_h15():
    return parse_ro(H15)


@pytest.fixture
def df_h16():
    return parse_tbgi(H16)


@pytest.fixture
def df_h17():
    return parse_grondslag_ip(H17)


class TestDeriveCohortjaar:
    def test_geeft_integer_serie(self, df_h15):
        result = derive_cohortjaar(df_h15)
        assert pd.api.types.is_integer_dtype(result) or str(result.dtype) in ("Int64", "int64")

    def test_waarden_plausibel(self, df_h15):
        result = derive_cohortjaar(df_h15)
        assert result.dropna().between(2010, 2030).all()

    def test_werkt_op_h17(self, df_h17):
        result = derive_cohortjaar(df_h17)
        assert not result.isna().all()


class TestDeriveLeeftijd:
    def test_h15_berekent_uit_geboortedatum(self, df_h15):
        result = derive_leeftijd(df_h15)
        assert result.name == "leeftijd_afgeleid"
        assert result.notna().any()

    def test_h15_leeftijd_plausibel(self, df_h15):
        result = derive_leeftijd(df_h15)
        geldig = result.dropna()
        assert (geldig >= 15).all()
        assert (geldig <= 60).all()

    def test_h16_gebruikt_direct_veld(self, df_h16):
        result = derive_leeftijd(df_h16)
        assert result.notna().any()
        assert (result.dropna() >= 15).all()

    def test_h17_gebruikt_direct_veld(self, df_h17):
        result = derive_leeftijd(df_h17)
        assert result.notna().any()
        assert (result.dropna() >= 15).all()


class TestDeriveDropout:
    def test_geeft_bool_serie(self, df_h15):
        result = derive_dropout(df_h15)
        assert result.dtype == bool

    def test_met_diploma_geen_dropout(self, df_h15):
        heeft_diploma = df_h15["heeft_diploma"]
        dropout = derive_dropout(df_h15)
        assert not (heeft_diploma & dropout).any()

    def test_werkt_op_h17(self, df_h17):
        result = derive_dropout(df_h17)
        assert result.dtype == bool

    def test_h16_dropout_via_werkelijk(self, df_h16):
        """H16 heeft geen uitschrijving_reden; dropout-detectie via uitschrijving_werkelijk."""
        result = derive_dropout(df_h16)
        assert result.dtype == bool
        # Studenten met diploma mogen nooit dropout zijn
        assert not (df_h16["heeft_diploma"] & result).any()

    def test_h16_heeft_diploma_gedetecteerd(self, df_h16):
        """Diploma-elementen zijn top-level in H16 XML; moeten correct worden gekoppeld."""
        assert df_h16["heeft_diploma"].any(), (
            "H16 zou minimaal één student met diploma moeten bevatten"
        )


class TestDeriveVooropleidingCategorie:
    def test_geeft_string_serie(self, df_h15):
        result = derive_vooropleiding_categorie(df_h15)
        assert pd.api.types.is_string_dtype(result) or result.dtype == object

    def test_geen_lege_waarden(self, df_h15):
        result = derive_vooropleiding_categorie(df_h15)
        assert (result != "").all()
        assert result.notna().all()

    def test_vorig_onderwijs_niet_beschikbaar_in_mbo(self, df_h15, df_h17):
        """GEO-records zijn generieke examenonderdelen, geen vooropleidingsdata."""
        assert df_h15["vorig_onderwijs_niveau"].isna().all(), (
            "vorig_onderwijs_niveau moet None zijn — vooropleiding niet in H15"
        )
        assert df_h17["vorig_onderwijs_niveau"].isna().all(), (
            "vorig_onderwijs_niveau moet None zijn — vooropleiding niet in H17"
        )

    def test_geeft_onbekend_als_niveau_none(self, df_h15):
        result = derive_vooropleiding_categorie(df_h15)
        assert (result == "Onbekend").all()

    def test_onbekend_bij_lege_niveau(self):
        df = pd.DataFrame({"vorig_onderwijs_niveau": [None, "", pd.NA]})
        result = derive_vooropleiding_categorie(df)
        assert (result == "Onbekend").all()


class TestLeertraject:
    def test_h15_leertraject_niet_leeg(self, df_h15):
        """Leertraject (BOL/BBL) zit op ISP-positie 6; was eerder fout gelezen van positie 7."""
        leertraject = df_h15["leertraject"].dropna()
        assert len(leertraject) > 0, "H15 moet leertraject-waarden bevatten"
        assert leertraject.isin(["BOL", "BBL", "OVO", "EX", "ODT", "BOL_DT"]).all()

    def test_h17_leertraject_niet_leeg(self, df_h17):
        leertraject = df_h17["leertraject"].dropna()
        assert len(leertraject) > 0
        assert leertraject.isin(["BOL", "BBL", "OVO", "EX", "ODT", "BOL_DT"]).all()

    def test_h16_leertraject_niet_leeg(self, df_h16):
        leertraject = df_h16["leertraject"].dropna()
        assert len(leertraject) > 0
        assert leertraject.isin(["BOL", "BBL", "OVO", "EX", "ODT", "BOL_DT"]).all()


class TestMboNiveau:
    def test_h16_niveau_aanwezig(self, df_h16):
        niveau = df_h16["mbo_niveau"].dropna()
        assert len(niveau) > 0
        assert niveau.str.startswith("MBO-").all()

    def test_h15_niveau_optioneel(self, df_h15):
        assert "mbo_niveau" in df_h15.columns


class TestH17Herkomst:
    def test_postcode_aanwezig(self, df_h17):
        postcode = df_h17["postcode"].dropna()
        assert len(postcode) > 0

    def test_geboorteland_aanwezig(self, df_h17):
        assert "geboorteland" in df_h17.columns
        assert df_h17["geboorteland"].notna().any()

    def test_nationaliteit_aanwezig(self, df_h17):
        assert "nationaliteit_1" in df_h17.columns
        assert df_h17["nationaliteit_1"].notna().any()


class TestDeriveOpleidingssector:
    def test_zonder_mapping_alles_onbekend(self, df_h15):
        result = derive_opleidingssector(df_h15)
        assert (result == "Onbekend").all()

    def test_met_mapping_vertaalt_code(self, df_h15):
        codes = df_h15["opleidingscode"].dropna().unique()
        mapping = {str(c): "Testssector" for c in codes}
        result = derive_opleidingssector(df_h15, mapping=mapping)
        bekende = result[df_h15["opleidingscode"].notna()]
        assert (bekende == "Testssector").all()

    def test_onbekende_code_geeft_onbekend(self, df_h15):
        result = derive_opleidingssector(df_h15, mapping={"99999": "X"})
        assert (result == "Onbekend").all()
