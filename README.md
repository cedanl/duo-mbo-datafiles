# duo-mbo-datafiles

Parsers en analyse voor DUO MBO bestandsformaten: H15 Registratie Overzicht, H16 TBG-i en H17 Afslag register-levering IP.

## Installatie

```bash
uv sync
```

## Gebruik

```python
from duo_mbo_datafiles.ingest import parse_ro, parse_tbgi, parse_grondslag_ip

df_ro = parse_ro("pad/naar/RO_bestand.csv")
df_tbgi = parse_tbgi("pad/naar/TBGI_bestand.XML")
df_ip = parse_grondslag_ip("pad/naar/GRONDSLAG_IP_bestand.csv")
```

Alle drie functies retourneren een DataFrame met kolommen:
`bsn`, `brin`, `geslacht`, `inschrijving_start`, `inschrijving_eind`, `uitschrijving_reden`, `leertraject`, `opleidingscode`, `heeft_diploma`, `vorig_onderwijs_niveau`, `vorig_onderwijs_graad`.

## Rapport

```bash
quarto render rapport.qmd
```

Genereert `rapport.html` met veldanalyse per formaat en bevindingen voor terugkoppeling aan Datacoalitie.

## Development

```bash
uv run pytest          # tests draaien
uv run ruff check src  # linting
```

## License

MIT
