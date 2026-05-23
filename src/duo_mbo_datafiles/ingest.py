"""Inlezen van DUO MBO bestandsformaten naar genormaliseerde DataFrames."""

from pathlib import Path

import pandas as pd

_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def parse_ro(path: str | Path) -> pd.DataFrame:
    """Parse H15 Registratie Overzicht naar student DataFrame.

    Ondersteunt zowel pipe-delimited (Aventus) als semicolon-delimited (Curio) varianten.
    BRIN wordt uit de VLP-header gehaald; als die ontbreekt, uit de bestandsnaam.
    """
    path = Path(path)
    brin_fallback = path.stem.split("_")[1] if "_" in path.stem else None
    return _parse_ro_records(path, brin_fallback=brin_fallback)


def parse_grondslag_ip(path: str | Path) -> pd.DataFrame:
    """Parse H17 Afslag register-levering IP (semicolon-delimited) naar student DataFrame.

    BRIN staat in ISG-records (positie [2]), geslacht in PER-records op positie [6].
    Datumformaat: yyyyMMdd.
    """
    students: dict[str, dict] = {}

    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split(";")
            record_type = parts[0]

            if record_type == "PER":
                bsn = parts[1] or (parts[2] if len(parts) > 2 else "")
                if not bsn:
                    continue
                students[bsn] = _init_student_record(
                    bsn, brin=None, geslacht=parts[6] if len(parts) > 6 else None
                )
                raw_leeftijd = parts[2] if len(parts) > 2 else None
                students[bsn]["leeftijd"] = (
                    int(raw_leeftijd) if raw_leeftijd and raw_leeftijd.isdigit() else None
                )

            elif record_type == "ISG" and parts[1] in students:
                s = students[parts[1]]
                s["brin"] = parts[2] if len(parts) > 2 else None
                s["inschrijving_start"] = parts[4] if len(parts) > 4 else None
                s["inschrijving_eind"] = parts[5] if len(parts) > 5 else None
                s["uitschrijving_reden"] = parts[7] if len(parts) > 7 else None

            elif record_type == "ISP" and parts[1] in students:
                s = students[parts[1]]
                s["opleidingscode"] = parts[6] if len(parts) > 6 else None
                s["leertraject"] = parts[8] if len(parts) > 8 else None

            elif record_type == "DIP" and parts[1] in students:
                students[parts[1]]["heeft_diploma"] = True

            elif record_type == "GEO" and parts[1] in students:
                _update_geo(students[parts[1]], parts, niveau_pos=7, graad_pos=6)

    df = pd.DataFrame(students.values())
    return _cast_types(df, date_format="%Y%m%d")


def parse_tbgi(path: str | Path) -> pd.DataFrame:
    """Parse H16 TBG-i XML naar student DataFrame."""
    from lxml import etree

    root = etree.parse(str(path)).getroot()
    records = [_extract_tbgi_inschrijving(el) for el in root.findall("Inschrijving")]
    return _cast_types(pd.DataFrame(records), date_format="iso")


def _parse_ro_records(path: Path, brin_fallback: str | None) -> pd.DataFrame:
    """Parser voor H15 RO record-structuur; detecteert scheidingsteken uit eerste regel."""
    students: dict[str, dict] = {}
    brin = brin_fallback
    sep: str | None = None

    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if sep is None:
                sep = "|" if "|" in stripped else ";"
            parts = stripped.split(sep)
            record_type = parts[0]

            if record_type == "VLP":
                brin = parts[1] if len(parts) > 1 else brin_fallback

            elif record_type == "PER":
                bsn = parts[1] or (parts[2] if len(parts) > 2 else "")
                if not bsn:
                    continue
                students[bsn] = _init_student_record(
                    bsn, brin=brin, geslacht=parts[4] if len(parts) > 4 else None
                )
                students[bsn]["geboortedatum"] = parts[3] if len(parts) > 3 else None

            elif record_type == "ISG" and parts[1] in students:
                s = students[parts[1]]
                s["inschrijving_start"] = parts[4] if len(parts) > 4 else None
                s["inschrijving_eind"] = parts[5] if len(parts) > 5 else None
                s["uitschrijving_reden"] = parts[7] if len(parts) > 7 else None

            elif record_type == "ISP" and parts[1] in students:
                s = students[parts[1]]
                s["opleidingscode"] = parts[5] if len(parts) > 5 else None
                s["leertraject"] = parts[7] if len(parts) > 7 else None

            elif record_type == "DIP" and parts[1] in students:
                students[parts[1]]["heeft_diploma"] = True

            elif record_type == "GEO" and parts[1] in students:
                _update_geo(students[parts[1]], parts, niveau_pos=8, graad_pos=7)

    df = pd.DataFrame(students.values())
    return _cast_types(df, date_format="mixed")


def _init_student_record(bsn: str, brin: str | None, geslacht: str | None) -> dict:
    return {
        "bsn": bsn,
        "brin": brin,
        "geslacht": geslacht,
        "heeft_diploma": False,
        "inschrijving_start": None,
        "inschrijving_eind": None,
        "uitschrijving_reden": None,
        "leertraject": None,
        "opleidingscode": None,
        "vorig_onderwijs_niveau": None,
        "vorig_onderwijs_graad": None,
        "geboortedatum": None,
        "leeftijd": None,
    }


def _update_geo(student: dict, parts: list[str], niveau_pos: int, graad_pos: int) -> None:
    """Vul vooropleidingsvelden uit een GEO-record; overschrijft niet als al aanwezig."""
    if student["vorig_onderwijs_niveau"] is None:
        student["vorig_onderwijs_niveau"] = parts[niveau_pos] if len(parts) > niveau_pos else None
        student["vorig_onderwijs_graad"] = parts[graad_pos] if len(parts) > graad_pos else None


def _extract_tbgi_inschrijving(node) -> dict:
    """Extraheer genormaliseerde velden uit een TBG-i <Inschrijving> XML-element.

    nil-attributen (xsi:nil='true') worden als None behandeld.
    """

    def text(tag: str) -> str | None:
        el = node.find(tag)
        if el is None:
            return None
        return None if el.get(f"{{{_XSI_NS}}}nil") == "true" else el.text

    teldatum = node.find("Teldatum")

    raw_leeftijd = (
        teldatum.findtext("LeeftijdOpEenAugustusStudiejaar") if teldatum is not None else None
    )

    return {
        "bsn": text("Burgerservicenummer"),
        "brin": text("BRIN"),
        "geslacht": None,
        "inschrijving_start": text("DatumInschrijving"),
        "inschrijving_eind": text("DatumUitschrijvingGepland"),
        "uitschrijving_reden": text("DatumUitschrijvingWerkelijk"),
        "leertraject": teldatum.findtext("Leertraject") if teldatum is not None else None,
        "opleidingscode": teldatum.findtext("Opleidingcode") if teldatum is not None else None,
        "heeft_diploma": node.find("Diploma") is not None,
        "vorig_onderwijs_niveau": None,
        "vorig_onderwijs_graad": None,
        "geboortedatum": None,
        "leeftijd": int(raw_leeftijd) if raw_leeftijd and raw_leeftijd.isdigit() else None,
    }


def _cast_types(df: pd.DataFrame, date_format: str) -> pd.DataFrame:
    """Cast datumkolommen en booleans naar correcte dtypes.

    date_format: 'iso', 'mixed' (Europese of ISO gemixed), of strftime-patroon.
    """
    if df.empty:
        return df
    for col in ("inschrijving_start", "inschrijving_eind"):
        if col in df.columns:
            if date_format == "iso":
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif date_format == "mixed":
                df[col] = pd.to_datetime(df[col], format="mixed", dayfirst=True, errors="coerce")
            else:
                df[col] = pd.to_datetime(df[col], format=date_format, errors="coerce")
    if "geboortedatum" in df.columns:
        df["geboortedatum"] = pd.to_datetime(
            df["geboortedatum"], format="mixed", dayfirst=False, errors="coerce"
        )
    if "leeftijd" in df.columns:
        df["leeftijd"] = pd.to_numeric(df["leeftijd"], errors="coerce").astype("Int64")
    if "heeft_diploma" in df.columns:
        df["heeft_diploma"] = df["heeft_diploma"].astype(bool)
    if "vorig_onderwijs_graad" in df.columns:
        df["vorig_onderwijs_graad"] = pd.to_numeric(df["vorig_onderwijs_graad"], errors="coerce")
    return df
