# Hai Nam Notebook Workspace

Role: Store-visit data analysis and AI interface support.

Assigned dataset:

- `store-visits-rice`

Expected outputs:

- cleaned store-visit tables;
- store-visit summary statistics;
- useful static and interactive plots;
- interpretation notes;
- exports for Phuong Anh and Duc Anh;
- notes that support the future Streamlit prototype and OpenAI-backed assistant interface.

Collaboration dependencies:

- Duc Anh for shared cleaning and export conventions.
- Phuong Anh for business questions and dashboard-ready summaries.
- Tan Dat for source display patterns and future AI interface testing.

Suggested filenames:

- `store_visits_initial_analysis.ipynb`
- `store_visits_cleaning_notes.ipynb`
- `store_visits_summary_exports.ipynb`

Completed visualization handoff:

- `store_visits_visualizations.ipynb` - one executed notebook containing the
  visualization code, six plot outputs, interpretations, and limitations. It
  uses the compact version-controlled summary CSVs and can be rerun from top to
  bottom from anywhere inside the repository.

Do not commit:

- raw `store-visits-rice` files;
- secrets or OpenAI API keys;
- large interactive exports unless approved;
- notebooks with huge embedded outputs.
