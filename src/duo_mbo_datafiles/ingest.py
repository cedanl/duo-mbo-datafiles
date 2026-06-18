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

    PER-record bevat naast leeftijd ook postcode en herkomstvariabelen (geboorteland,
    nationaliteit). BSN is gepseudonimiseerd (PGN). Geboortedatum wordt niet geleverd;
    leeftijden op vier peildata worden geleverd — hier wordt de eerste gebruikt.
    """
    students: dict[str, dict] = {}

    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split(";")
            record_type = parts[0]

            if record_type == "PER":
                bsn = parts[1] if len(parts) > 1 else ""
                if not bsn:
                    continue
                geslacht = parts[6] if len(parts) > 6 else None
                students[bsn] = _init_student_record(bsn, brin=None, geslacht=geslacht)
                students[bsn]["leeftijd"] = _parse_int(parts[2] if len(parts) > 2 else None)
                students[bsn]["postcode"] = parts[7] if len(parts) > 7 else None
                students[bsn]["geboorteland"] = parts[11] if len(parts) > 11 else None
                students[bsn]["geboorteland_ouder_1"] = parts[12] if len(parts) > 12 else None
                students[bsn]["geboorteland_ouder_2"] = parts[13] if len(parts) > 13 else None
                students[bsn]["nationaliteit_1"] = parts[16] if len(parts) > 16 else None
                students[bsn]["nationaliteit_2"] = parts[17] if len(parts) > 17 else None

            elif record_type == "ISG" and parts[1] in students:
                s = students[parts[1]]
                s["brin"] = parts[2] if len(parts) > 2 else None
                s["inschrijving_start"] = parts[4] if len(parts) > 4 else None
                s["inschrijving_eind"] = parts[5] if len(parts) > 5 else None
                s["uitschrijving_werkelijk"] = parts[6] if len(parts) > 6 else None
                s["uitschrijving_reden"] = parts[7] if len(parts) > 7 else None

            elif record_type == "ISP" and parts[1] in students:
                s = students[parts[1]]
                s["opleidingscode"] = parts[6] if len(parts) > 6 else None
                s["mbo_niveau"] = parts[7] if len(parts) > 7 else None
                s["leertraject"] = parts[8] if len(parts) > 8 else None

            elif record_type == "DIP" and parts[1] in students:
                students[parts[1]]["heeft_diploma"] = True
                students[parts[1]]["diploma_datum"] = parts[5] if len(parts) > 5 else None

    df = pd.DataFrame(students.values())
    return _cast_types(df, date_format="%Y%m%d")


def parse_tbgi(path: str | Path) -> pd.DataFrame:
    """Parse H16 TBG-i XML naar student DataFrame.

    Diploma-elementen zijn top-level (geen children van Inschrijving) en worden
    apart gematcht op BSN. heeft_diploma wordt op True gezet voor studenten die
    in een Diploma-element voorkomen.
    """
    from lxml import etree

    root = etree.parse(str(path)).getroot()
    students: dict[str, dict] = {}

    for el in root.findall("Inschrijving"):
        record = _extract_tbgi_inschrijving(el)
        bsn = record["bsn"]
        if bsn:
            students[bsn] = record

    for el in root.findall("Diploma"):
        bsn = _tbgi_text(el, "Burgerservicenummer") or _tbgi_text(el, "Onderwijsnummer")
        if not bsn:
            continue
        diploma_datum = _tbgi_text(el, "DatumBehaald")
        if bsn in students:
            students[bsn]["heeft_diploma"] = True
            students[bsn]["diploma_datum"] = diploma_datum
        else:
            rec = _init_student_record(bsn, brin=_tbgi_text(el, "BRIN"), geslacht=None)
            rec["heeft_diploma"] = True
            rec["diploma_datum"] = diploma_datum
            students[bsn] = rec

    df = pd.DataFrame(students.values())
    return _cast_types(df, date_format="iso")


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
                s["uitschrijving_werkelijk"] = parts[6] if len(parts) > 6 else None
                s["uitschrijving_reden"] = parts[7] if len(parts) > 7 else None

            elif record_type == "ISP" and parts[1] in students:
                s = students[parts[1]]
                s["opleidingscode"] = parts[5] if len(parts) > 5 else None
                s["leertraject"] = parts[6] if len(parts) > 6 else None
                s["mbo_niveau"] = parts[7] if len(parts) > 7 else None

            elif record_type == "DIP" and parts[1] in students:
                students[parts[1]]["heeft_diploma"] = True
                students[parts[1]]["diploma_datum"] = parts[5] if len(parts) > 5 else None

    df = pd.DataFrame(students.values())
    return _cast_types(df, date_format="mixed")


def _init_student_record(bsn: str, brin: str | None, geslacht: str | None) -> dict:
    return {
        "bsn": bsn,
        "brin": brin,
        "geslacht": geslacht,
        "heeft_diploma": False,
        "diploma_datum": None,
        "inschrijving_start": None,
        "inschrijving_eind": None,
        "uitschrijving_werkelijk": None,
        "uitschrijving_reden": None,
        "leertraject": None,
        "mbo_niveau": None,
        "opleidingscode": None,
        "vorig_onderwijs_niveau": None,   # niet beschikbaar in MBO-leveringen
        "vorig_onderwijs_graad": None,    # niet beschikbaar in MBO-leveringen
        "geboortedatum": None,
        "leeftijd": None,
        "postcode": None,
        "geboorteland": None,
        "geboorteland_ouder_1": None,
        "geboorteland_ouder_2": None,
        "nationaliteit_1": None,
        "nationaliteit_2": None,
    }


def _tbgi_text(node, tag: str) -> str | None:
    """Geeft tekstinhoud van een XML-element terug; None bij ontbrekend of xsi:nil."""
    el = node.find(tag)
    if el is None:
        return None
    return None if el.get(f"{{{_XSI_NS}}}nil") == "true" else el.text


def _extract_tbgi_inschrijving(node) -> dict:
    """Extraheer genormaliseerde velden uit een TBG-i <Inschrijving> XML-element."""
    teldatum = node.find("Teldatum")
    raw_leeftijd = (
        teldatum.findtext("LeeftijdOpEenAugustusStudiejaar") if teldatum is not None else None
    )

    rec = _init_student_record(
        bsn=_tbgi_text(node, "Burgerservicenummer") or _tbgi_text(node, "Onderwijsnummer"),
        brin=_tbgi_text(node, "BRIN"),
        geslacht=None,
    )
    rec.update({
        "inschrijving_start": _tbgi_text(node, "DatumInschrijving"),
        "inschrijving_eind": _tbgi_text(node, "DatumUitschrijvingGepland"),
        "uitschrijving_werkelijk": _tbgi_text(node, "DatumUitschrijvingWerkelijk"),
        "leertraject": teldatum.findtext("Leertraject") if teldatum is not None else None,
        "mbo_niveau": teldatum.findtext("Niveau") if teldatum is not None else None,
        "opleidingscode": teldatum.findtext("Opleidingcode") if teldatum is not None else None,
        "leeftijd": _parse_int(raw_leeftijd),
    })
    return rec


def _parse_int(value: str | None) -> int | None:
    if value and str(value).isdigit():
        return int(value)
    return None


def _cast_types(df: pd.DataFrame, date_format: str) -> pd.DataFrame:
    """Cast datumkolommen en booleans naar correcte dtypes."""
    if df.empty:
        return df
    date_cols = [
        "inschrijving_start", "inschrijving_eind",
        "uitschrijving_werkelijk", "diploma_datum",
    ]
    for col in date_cols:
        if col not in df.columns:
            continue
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
        df["vorig_onderwijs_graad"] = pd.to_numeric(
            df["vorig_onderwijs_graad"], errors="coerce"
        )
    return df
