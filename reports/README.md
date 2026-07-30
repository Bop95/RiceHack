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
