# FinalFlow application services

This folder contains the implemented, in-process service layer used by the
Streamlit application:

- `data_service.py` validates and loads the compact derived and synthetic CSVs;
- `analytics.py` provides deterministic retrieval, evidence, plot metadata, and
  response contracts; and
- `ai_service.py` optionally uses the server-side OpenAI Responses API to
  narrate a deterministic answer without changing its facts.

There is currently no HTTP or REST server. Streamlit imports these Python
functions directly. See `docs/api/application-api.md` for callable signatures,
response shapes, failure behavior, and the boundary for a future backend.

Never place credentials in this folder. Local values belong in the ignored
`.env` file; hosted values belong in the deployment platform's secret store.
