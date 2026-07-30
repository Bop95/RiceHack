# Data Contracts

This document defines early shared labels and fields for FinalFlow data products and future AI responses. It is documentation only and does not implement schemas.

## Data type labels

Use these labels consistently:

- `provided`: original source data supplied to the project, including approved raw or reference data.
- `derived`: cleaned, transformed, summarized, joined, or feature-engineered data created from provided data.
- `synthetic`: generated data created for scenario testing, demos, stress tests, or gap filling.
- `web`: information retrieved from web search or external online sources.

Do not mix these labels with alternative names such as `raw`, `generated`, `external`, or `internet` in shared outputs. If more detail is needed, add a separate notes column.

## Suggested shared fields

Use these fields where they fit the table:

| Field | Purpose |
| --- | --- |
| `data_type` | One of `provided`, `derived`, `synthetic`, or `web`. |
| `source_file` | Original file path or source name used to create the record. |
| `generated_at` | Timestamp for generated outputs, preferably ISO 8601. |
| `scenario_id` | Identifier for synthetic or scenario-specific records. |
| `zone_id` | Stable zone, station, venue, POI, or analysis-area identifier. |
| `location_name` | Human-readable location name. |
| `latitude` | Decimal latitude when point geometry is available. |
| `longitude` | Decimal longitude when point geometry is available. |

## Naming guidance

- Use lowercase folder names.
- Use hyphens for contributor folders.
- Use snake_case for Python files and generated table names.
- Use ISO date format where dates appear in filenames or data fields.
- Keep `provided`, `derived`, `synthetic`, and `web` labels exact.

## Future AI response contract

Future assistant responses should return structured data similar to this shape:

```json
{
  "answer": "...",
  "evidence": [],
  "relatedPlotId": null,
  "dataType": "provided",
  "webSources": [],
  "limitations": []
}
```

Field meanings:

- `answer`: concise user-facing answer.
- `evidence`: project data rows, snippets, metrics, or references used to support the answer.
- `relatedPlotId`: optional plot identifier for a related visualization.
- `dataType`: highest-risk or primary source type used in the answer.
- `webSources`: structured search sources when `web` data is used.
- `limitations`: known caveats, missing data, assumptions, or uncertainty.

## Source discipline

AI responses should distinguish project data from web results. Web results should not overwrite project data. Synthetic scenarios should always be labeled as `synthetic` and should not be presented as observed behavior.
