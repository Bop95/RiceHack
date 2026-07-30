# FinalFlow

FinalFlow is a match-synchronized mobility-readiness platform for a World Cup transportation and urban-sustainability project.

The case study replays the 2026 World Cup Final between Spain and Argentina at New York New Jersey Stadium, with a primary travel corridor from Midtown Manhattan to New York Penn Station, Secaucus Junction, Meadowlands Station, and the stadium.

The project studies pre-match, match, and post-match mobility across rail, road, shuttle, parking, pedestrian movement, first- and last-mile access, congestion, weather, urban heat, commercial activity, transportation disruptions, resilience strategies, visualizations, and a future AI assistant grounded in project data.

## Current state

This repository currently contains a preserved Streamlit dashboard prototype in `paddydash/`. The app uses mock analytics data and should not be treated as the completed FinalFlow analysis.

No production backend, TypeScript frontend, AI chatbot, Rice dataset pipeline, or AWS deployment has been implemented yet.

## Project structure

```
docs/
├── data/
│   └── dataset-layout.md
├── handoff/
│   └── minh-tue-aws-handoff.md
└── project/
    ├── data-contracts.md
    ├── project-overview.md
    └── team-workstreams.md
paddydash/
├── app.py             # Streamlit dashboard app
└── requirements.txt   # Python dependencies
scripts/
├── README.md
└── data/
    └── audit_data.py  # First reusable CSV audit utility
```

## Documentation

- [Project overview](docs/project/project-overview.md)
- [Team workstreams](docs/project/team-workstreams.md)
- [Data contracts](docs/project/data-contracts.md)
- [Dataset layout](docs/data/dataset-layout.md)
- [AWS handoff template](docs/handoff/minh-tue-aws-handoff.md)
- [Scripts guide](scripts/README.md)

## Local setup

### Streamlit prototype

```bash
cd paddydash
python3 -m pip install -r requirements.txt
streamlit run app.py
```

Use a virtual environment for local Python work. Do not commit local environments, cache files, secrets, raw restricted datasets, or generated large files.

## Data policy

Raw Rice datasets should stay local unless the team explicitly approves committing a small public sample. Future dataset folders should follow the layout in [dataset-layout.md](docs/data/dataset-layout.md).

Use the standard data labels documented in [data-contracts.md](docs/project/data-contracts.md):

- `provided`
- `derived`
- `synthetic`
- `web`

## Branch policy

Active shared development for this setup work is on `stephen-develop`. Do not create feature branches unless the team lead asks for one. Tan Dat is expected to work later on a separate branch named `tan-dat`, but that branch is not used for this documentation task.

## Environment variables

Do not commit `.env`, `.env.local`, `.streamlit/secrets.toml`, OpenAI keys, SerpAPI keys, AWS credentials, or other secrets.

Future environment-variable names are documented in the handoff template. A safe `.env.example` can be added later once the backend or assistant integration exists.
