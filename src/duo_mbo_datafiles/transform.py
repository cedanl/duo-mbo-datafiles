"""Derivatiefuncties voor afleidbare variabelen uit DUO MBO bestandsformaten.

Elke functie accepteert een genormaliseerde student-DataFrame (output van parse_*)
en geeft een Series terug die als kolom aan de DataFrame toegevoegd kan worden.
"""

from __future__ import annotations

import pandas as pd


def derive_cohortjaar(df: pd.DataFrame) -> pd.Series:
    """Leid cohortjaar af als jaar van de eerste inschrijving."""
    return df["inschrijving_start"].dt.year.astype("Int64").rename("cohortjaar")


def derive_leeftijd(df: pd.DataFrame) -> pd.Series:
    """Leid leeftijd af op peildatum 1 oktober van het cohortjaar.

    H15: berekend vanuit geboortedatum (PER-record).
    H16/H17: direct beschikbaar als integer (LeeftijdOpEenAugustusStudiejaar / PER[2]).
    Als beide aanwezig zijn, heeft geboortedatum voorrang (hogere precisie).
    """
    if "geboortedatum" in df.columns and df["geboortedatum"].notna().any():
        peildatum = pd.to_datetime({
            "year": df["inschrijving_start"].dt.year,
            "month": 10,
            "day": 1,
        })
        geboortedatum = pd.to_datetime(df["geboortedatum"], errors="coerce")
        dagen = (peildatum - geboortedatum).dt.days / 365.25
        return dagen.round().astype("Int64").rename("leeftijd_afgeleid")
    if "leeftijd" in df.columns:
        return df["leeftijd"].rename("leeftijd_afgeleid")
    return pd.Series(pd.NA, index=df.index, name="leeftijd_afgeleid", dtype="Int64")


def derive_dropout(df: pd.DataFrame) -> pd.Series:
    """Leid dropout af: uitgeschreven zonder diploma.

    Definitie: `uitschrijving_reden` is ingevuld én `heeft_diploma` is False.
    Beperking: in een snapshot-levering is niet te controleren of de student
    later elders heringeschreven is. Gebruik meerdere opeenvolgende leveringen
    voor een volledige dropout-validatie conform 1-cijferHO-definitie.
    """
    uitgeschreven = df["uitschrijving_reden"].notna() & (df["uitschrijving_reden"] != "")
    return (uitgeschreven & ~df["heeft_diploma"]).rename("dropout")


_NIVEAU_MAP: dict[str, str] = {
    "VWO": "VWO",
    "HAVO": "HAVO",
    "VMBO": "VMBO/MAVO",
    "MAVO": "VMBO/MAVO",
    "VBO": "VMBO/MAVO",
}


def derive_vooropleiding_categorie(df: pd.DataFrame) -> pd.Series:
    """Vertaal vorig_onderwijs_niveau naar 1-cijferHO-achtige categorieën.

    MBO-subcategorieën (1-2 vs 3-4) zijn niet afleidbaar uit DUO GEO-records
    zonder aanvullende kwalificatiedossier-mapping; beide worden als 'MBO' geclassificeerd.
    Gebruik de graad-kolom voor verdere uitsplitsing als de DUO GEO-specificatie bekend is.
    """

    def _map(niveau: object) -> str:
        if pd.isna(niveau) or str(niveau).strip() == "":
            return "Onbekend"
        n = str(niveau).strip().upper()
        for key, label in _NIVEAU_MAP.items():
            if n.startswith(key):
                return label
        if "MBO" in n or "KZDL" in n:
            return "MBO"
        if "HBO" in n:
            return "HBO"
        return "Anders"

    return df["vorig_onderwijs_niveau"].map(_map).rename("vooropleiding_categorie")


def derive_opleidingssector(df: pd.DataFrame, mapping: dict[str, str] | None = None) -> pd.Series:
    """Leid MBO-sector af uit CREBO-opleidingscode.

    Vereist een externe CREBO-sectorMapping (dict van opleidingscode → sector).
    Zonder mapping worden alle waarden als 'Onbekend' geclassificeerd.
    Een volledige mapping is beschikbaar via het DUO CREBO-register (open data).
    """
    if mapping is None:
        return pd.Series("Onbekend", index=df.index, name="opleidingssector")
    sector = df["opleidingscode"].map(lambda c: mapping.get(str(c), "Onbekend"))
    return sector.rename("opleidingssector")
