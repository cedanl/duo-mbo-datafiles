"""Tests voor DUO MBO bestandsformaat parsers."""

from pathlib import Path

import pandas as pd
import pytest

from duo_mbo_datafiles.ingest import parse_grondslag_ip, parse_ro, parse_tbgi

DEMO = Path(__file__).parent.parent / "data" / "01-raw" / "demo"

VERWACHTE_KOLOMMEN = {
    "bsn",
    "brin",
    "geslacht",
    "inschrijving_start",
    "inschrijving_eind",
    "uitschrijving_reden",
    "leertraject",
    "opleidingscode",
    "heeft_diploma",
    "vorig_onderwijs_niveau",
    "vorig_onderwijs_graad",
}

RO_BESTANDEN = list((DEMO / "h15").glob("*.csv"))


@pytest.mark.parametrize("pad", RO_BESTANDEN, ids=[p.name for p in RO_BESTANDEN])
def test_parse_ro_laadt(pad):
    df = parse_ro(pad)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


@pytest.mark.parametrize("pad", RO_BESTANDEN, ids=[p.name for p in RO_BESTANDEN])
def test_parse_ro_kolommen(pad):
    df = parse_ro(pad)
    assert VERWACHTE_KOLOMMEN.issubset(df.columns)


@pytest.mark.parametrize("pad", RO_BESTANDEN, ids=[p.name for p in RO_BESTANDEN])
def test_parse_ro_datatypes(pad):
    df = parse_ro(pad)
    assert pd.api.types.is_bool_dtype(df["heeft_diploma"])
    assert pd.api.types.is_datetime64_any_dtype(df["inschrijving_start"])


def test_parse_ro_aventus_studenten():
    pad = DEMO / "h15" / "RO_27DV_20240731_20260324.csv"
    df = parse_ro(pad)
    assert len(df) == 10


def test_parse_tbgi_laadt():
    pad = DEMO / "h16" / "TBGI_25LX_2027_20251124.XML"
    df = parse_tbgi(pad)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_parse_tbgi_kolommen():
    pad = DEMO / "h16" / "TBGI_25LX_2027_20251124.XML"
    df = parse_tbgi(pad)
    assert VERWACHTE_KOLOMMEN.issubset(df.columns)


def test_parse_tbgi_datatypes():
    pad = DEMO / "h16" / "TBGI_25LX_2027_20251124.XML"
    df = parse_tbgi(pad)
    assert pd.api.types.is_bool_dtype(df["heeft_diploma"])
    assert pd.api.types.is_datetime64_any_dtype(df["inschrijving_start"])


def test_parse_grondslag_ip_laadt():
    pad = DEMO / "h17" / "GRONDSLAG_IP_MBO_27DV_20251119_2025.csv"
    df = parse_grondslag_ip(pad)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_parse_grondslag_ip_kolommen():
    pad = DEMO / "h17" / "GRONDSLAG_IP_MBO_27DV_20251119_2025.csv"
    df = parse_grondslag_ip(pad)
    assert VERWACHTE_KOLOMMEN.issubset(df.columns)


def test_parse_grondslag_ip_studenten():
    pad = DEMO / "h17" / "GRONDSLAG_IP_MBO_27DV_20251119_2025.csv"
    df = parse_grondslag_ip(pad)
    assert len(df) == 10
