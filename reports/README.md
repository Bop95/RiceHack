# FinalFlow Reports

Generated report artifacts should use clear, descriptive names and should be small enough to review when committed.

## Folder purposes

```text
reports/
├── figures/      # Static figures such as PNG or SVG charts.
├── interactive/  # Interactive HTML outputs, usually local unless approved.
└── summaries/    # Written summaries and compact final report tables.
```

## Guidance

- Use snake_case filenames.
- Include dates in ISO format when needed.
- Keep large generated outputs local unless the team approves versioning them.
- Important final summaries may be versioned when they are safe to share.
- Avoid committing files that contain raw restricted data, secrets, or local-only paths.

## Store-visit visualizations

Generate the Step-3 store-visit outputs from the repository root:

```bash
python scripts/visualization/create_store_visit_charts.py
```

This creates:

- four static PNG plots covering brands, categories, weekdays, and the visit
  distribution;
- two self-contained interactive HTML plots covering monthly dates and markets;
- `reports/summaries/store_visits_visualization_notes.md` with concise,
  automatically synchronized interpretations.

The interactive HTML files remain ignored by Git unless the team explicitly approves
sharing them. Use `--overwrite` to regenerate outputs after the Step-2 summaries change.
