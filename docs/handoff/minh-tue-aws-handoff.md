# Minh Tue AWS Handoff Template

This is a deployment handoff checklist for later work. AWS deployment is not complete, and no AWS resources should be created from this document yet.

## Repository setup

- Repository path: `/Users/macbook/Hack/RiceHack`
- Main development branch for current setup work: `stephen-develop`
- Confirm latest code is pulled before deployment planning.
- Confirm no secrets or raw restricted datasets are committed.

## Python version

- Placeholder: document the supported Python version once the backend and data pipeline dependencies are finalized.
- Current Streamlit prototype has only `streamlit` listed in `paddydash/requirements.txt`.

## Python dependencies

- Streamlit prototype: `paddydash/requirements.txt`
- Future backend: placeholder for `backend/requirements.txt` or `pyproject.toml`
- Future data scripts: placeholder for pandas, NumPy, Matplotlib, Seaborn, Plotly, GeoPandas, Shapely, Folium, PyArrow, and validation dependencies as needed.

## Frontend dependencies

- Placeholder: document Node version and package manager after a frontend is added.
- Placeholder: document install command, such as `npm install`, `pnpm install`, or `yarn install`.

## Environment variables

Do not commit real values.

Expected future variables:

```text
OPENAI_API_KEY=
SERPAPI_API_KEY=
```

AWS variable names should be added only after the deployment approach is selected.

## Streamlit run command

```bash
cd paddydash
python3 -m pip install -r requirements.txt
streamlit run app.py
```

## Future backend run command

Placeholder:

```bash
cd backend
# install dependencies
# run FastAPI or the selected backend framework
```

Document the exact command once the backend exists.

## Future frontend run command

Placeholder:

```bash
cd frontend
# install dependencies
# run the selected frontend framework
```

Document the exact command once the frontend exists.

## API routes

Placeholder for future backend routes:

- `GET /health`
- `POST /chat`
- `GET /sources`
- `GET /plots`
- `GET /datasets`

Route names should be updated to match the implemented backend.

## Health checks

Expected future checks:

- backend `/health` returns a successful response;
- frontend loads without build errors;
- Streamlit prototype starts locally;
- required environment variables are present;
- AI and search features fail gracefully when optional keys are absent;
- data files needed by the app are available in documented locations.

## Data locations

Reference layout: `docs/data/dataset-layout.md`

Expected local data areas:

- `data/raw/rice/` for local provided Rice data;
- `data/processed/` for cleaned derived tables;
- `data/synthetic/` for generated scenarios;
- `data/summaries/` for small summary tables;
- `data/exports/` for app-ready or Power BI-ready exports.

## Build notes

Placeholder:

- document frontend build command after frontend creation;
- document backend packaging approach after backend creation;
- document Streamlit hosting decision if Streamlit remains part of the deployed product;
- document required data build steps before deployment.

## Deployment assumptions

Placeholder assumptions to verify later:

- final frontend and backend frameworks are selected;
- environment variables are documented in `.env.example`;
- secrets are stored in AWS-managed secret storage or deployment platform settings;
- raw restricted datasets are not bundled into public artifacts;
- generated exports are small enough and approved for deployment;
- CORS and API URLs are configured for the deployed frontend.

## Known limitations

- The current repository contains only a Streamlit prototype with mock analytics.
- No production backend exists yet.
- No TypeScript frontend exists yet.
- No AI assistant is implemented yet.
- No SerpAPI integration is implemented yet.
- No AWS resources are provisioned.
- Data pipeline folders and script scaffolds exist, with only the first lightweight CSV audit utility implemented.
