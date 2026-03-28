---
name: ingest
description: Run data ingestion pipelines for GC Housing RAG (INE, Turismo, ISTAC, Airbnb)
disable-model-invocation: true
---

# Ingest Skill

Ejecuta los scripts de ingesta de datos del proyecto GC Housing RAG.

## Usage

```
/ingest [source]

Arguments:
  source    - Optional: ine, turismo, istac, airbnb, or all (default: all)
```

## Available Sources

| Source | Command | Description |
|--------|---------|-------------|
| `ine` | `python -m src.ingest.ine` | INE population data |
| `turismo` | `python -m src.ingest.turismo` | Tourism housing registry |
| `istac` | `python -m src.ingest.istac_data` | ISTAC statistics |
| `airbnb` | `python -m src.ingest.airbnb_data` | Airbnb data |
| `all` | Runs all above | Full data ingestion |

## Examples

```
/ingest ine          # Run only INE data ingestion
/ingest turismo     # Run only Turismo data
/ingest all         # Run all ingestion pipelines
```

## Workflow

1. Validates Python environment is activated
2. Runs the selected ingestion script
3. Reports success/failure with output summary

## Notes

- Scripts expect `.env` file to be configured with API keys
- Check `data/raw/` for downloaded data after execution
- Processed data goes to `data/processed/`
