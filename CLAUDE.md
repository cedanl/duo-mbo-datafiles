# duo-mbo-datafiles

## Overview
Parsers en analyse voor DUO MBO bestandsformaten: H15 Registratie Overzicht (RO), H16 TBG-i (XML) en H17 Afslag register-levering IP. Antwoordt op de vraag: welke velden zijn beschikbaar per formaat en wat ontbreekt voor gebruik in uitvalanalyse?

## Standards
Follow CEDA technical standards: https://github.com/cedanl/.github/tree/main/standards/README.md

## Tech Stack
Python 3.13, pandas, lxml, Quarto (rapport).

## Project Structure
```
├── src/duo_mbo_datafiles/
│   ├── __init__.py
│   └── ingest.py          # parse_ro, parse_tbgi, parse_grondslag_ip
├── data/01-raw/demo/
│   ├── h15/               # H15 RO voorbeeldbestanden (Aventus + Curio)
│   ├── h16/               # H16 TBGI XML voorbeeldbestand (Curio)
│   └── h17/               # H17 GRONDSLAG_IP voorbeeldbestand (Aventus)
├── tests/
│   └── test_parsers.py
├── rapport.qmd            # Quarto analyserapport
└── pyproject.toml
```

## How to Run
```bash
uv sync
uv run pytest
quarto render rapport.qmd
```

## Data
Voorbeeldbestanden (10 studenten per bestand, geanonimiseerde BSN) van Aventus (BRIN 27DV) en Curio (BRIN 21CY, 25LX). Afkomstig van Hutspot/Datacoalitie voor validatie iteratie 6.
