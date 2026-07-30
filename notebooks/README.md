# FinalFlow Notebooks

This folder is for exploratory and reproducible FinalFlow analysis notebooks.

## Contributor folders

```text
notebooks/
├── shared/
├── phuong-anh/
├── duc-anh/
├── hai-nam/
├── tan-dat/
└── que-anh/
```

Use contributor folders for individual work. Use `shared/` only for notebooks or helper notes that multiple contributors actively maintain.

## Notebook standards

- Use clear Markdown headings for purpose, data sources, cleaning, analysis, interpretation, limitations, and exports.
- Use relative paths or configurable path variables.
- Keep notebooks runnable from top to bottom.
- Interpret important outputs instead of leaving charts or tables unexplained.
- Do not store secrets, API keys, `.env` values, or credentials in notebooks.
- Avoid huge embedded outputs. Clear large outputs when appropriate before sharing.
- Preserve raw data. Write cleaned or generated outputs to the appropriate `data/` folder.
- Restart the kernel and run all cells before submission.

## Naming

Use lowercase snake_case filenames:

```text
store_visits_initial_analysis.ipynb
weather_risk_indicators.ipynb
que_anh_spatial_business_analysis.ipynb
```

Do not create completed notebooks with fake analysis or fake data.
