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
        # BSN3 heeft uitschrijving_reden en geen diploma → dropout
        bsn3 = df_h17[df_h17["bsn"] == "BSN3"]
        if not bsn3.empty:
            assert derive_dropout(bsn3).iloc[0] is True or derive_dropout(bsn3).iloc[0]


class TestDeriveVooropleidingCategorie:
    def test_geeft_string_serie(self, df_h15):
        result = derive_vooropleiding_categorie(df_h15)
        assert pd.api.types.is_string_dtype(result) or result.dtype == object

    def test_geen_lege_waarden(self, df_h15):
        result = derive_vooropleiding_categorie(df_h15)
        assert (result != "").all()
        assert result.notna().all()

    def test_mbo_niveau_herkend(self, df_h15):
        mbo_studenten = df_h15[df_h15["vorig_onderwijs_niveau"] == "MBO"]
        if not mbo_studenten.empty:
            result = derive_vooropleiding_categorie(mbo_studenten)
            assert result.str.startswith("MBO").all()

    def test_onbekend_bij_lege_niveau(self):
        df = pd.DataFrame({"vorig_onderwijs_niveau": [None, "", pd.NA]})
        result = derive_vooropleiding_categorie(df)
        assert (result == "Onbekend").all()


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
