# FinalFlow Hosted Deployment Guide

This guide turns the existing FinalFlow code into a shareable hosted Streamlit
application. The app runs on Streamlit Community Cloud, while OpenAI calls run
from Streamlit's Python server process. Visitors never receive the API key.

## 1. What is already prepared

The repository includes:

- the four-page Streamlit application at `paddydash/app.py`;
- compact derived summary CSVs instead of the 5.2 GB cleaned dataset;
- a clearly labeled synthetic scenario CSV;
- server-side prepared-data retrieval and an OpenAI Responses API connection;
- evidence, data-type labels, limitations, and related plots;
- deterministic prepared-data answers when OpenAI is unavailable;
- a 500-character question limit and configurable per-session AI allowance;
- pinned application dependencies; and
- a deployment readiness checker.

## 2. Accounts and credentials you provide

You need:

1. A GitHub account with access to the repository and the `HaiNam` branch.
2. A Streamlit Community Cloud account connected to GitHub.
3. An OpenAI API project with billing/credits and a project API key.

Use a project key created for this application. Do not use someone else's key,
paste the key into Python, place it in GitHub, send it in chat, or expose it in a
browser-side request.

## 3. Verify the bundle before committing

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Before deployment, run the stricter tracking check:

```powershell
.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py --require-tracked
```

The checker never calls OpenAI and never prints a secret. Without a key it
reports a warning because prepared-data mode is still deployable.

## 4. Push the approved application

Only after reviewing the local changes, commit and push them to the existing
`HaiNam` branch. Streamlit cannot deploy local uncommitted files; every required
application file and compact CSV must exist on GitHub.

Do not push:

- `.env`;
- `.streamlit/secrets.toml`;
- raw, external, or processed source data;
- Parquet files; or
- generated interactive HTML files.

The repository `.gitignore` protects these paths, but always inspect the staged
file list before committing.

## 5. Create the hosted Streamlit app

1. Sign in to Streamlit Community Cloud with GitHub.
2. Select **Create app**.
3. Choose the GitHub repository.
4. Choose branch `HaiNam`.
5. Enter `paddydash/app.py` as the main file path.
6. In Advanced settings, use Python 3.12 if a version choice is shown.
7. Deploy once without an OpenAI key if you want to verify the visual pages
   first. Ask FinalFlow will clearly operate in prepared-data mode.

The result is a hosted URL that other people can open. It is not tied to your
local PowerShell window or computer.

## 6. Add the OpenAI server secret

Open the deployed app's settings, find Advanced settings or Secrets, and paste
TOML in this form:

```toml
OPENAI_API_KEY = "your-real-project-key"
OPENAI_MODEL = "gpt-5.6-luna"
FINALFLOW_MAX_AI_REQUESTS_PER_SESSION = "10"
```

The tracked `.env.example` file documents the same variable names for local
development. Never edit that example to contain a real value. For Community
Cloud, paste the equivalent TOML values only into the deployment's Secrets box.

Streamlit exposes root-level secret entries to the server process as environment
variables. The OpenAI Python SDK reads `OPENAI_API_KEY` there. The application
does not render or log the value.

After saving secrets, reboot or redeploy the app if Streamlit does not do so
automatically. Ask FinalFlow should display that secure OpenAI mode is configured
and show the model name, never the key.

## 7. Configure access and spending before sharing broadly

For the first review, restrict the app to your team if your Streamlit workspace
supports private apps. Before making the URL public:

- set an OpenAI project budget and appropriate rate limits;
- keep the per-session allowance small, such as 10;
- monitor OpenAI project usage;
- rotate the project key immediately if it is exposed; and
- remember that a Streamlit browser session limit is best-effort, not a global
  user identity or abuse-prevention system.

For a public hackathon demonstration, this is a suitable server-hosted design.
For sustained public traffic, place a dedicated authenticated backend and a
shared rate limiter in front of paid model calls.

## 8. Verify the live application

Open the hosted URL in a private/incognito browser window and check:

1. Overview loads metrics and charts.
2. Store-Visit Explorer filters and Plotly interactions work.
3. Scenario Explorer always identifies its records as synthetic.
4. Each suggested Ask FinalFlow question returns an answer, evidence, data label,
   limitation, and related chart.
5. An unrelated question is declined.
6. The page never displays the API key or a detailed backend exception.
7. After the configured AI allowance, prepared-data answers continue working.
8. A phone-sized browser view remains readable.

## 9. Updating the live app

Community Cloud watches the selected GitHub branch. After later approved changes
are committed and pushed to `HaiNam`, the hosted app rebuilds from that branch.
Run the tests and readiness checker before each push.

## 10. Troubleshooting

### The app says prepared-data mode

The key is missing or not visible to the server. Confirm the secret name is
exactly `OPENAI_API_KEY`, save it in the deployed app's settings, and reboot.

### The AI backend temporarily falls back

Check OpenAI project billing, usage limits, model access, and Streamlit logs. The
visitor still receives the verified prepared-data answer, while internal error
details remain hidden.

### Deployment cannot import a package

Confirm the root `requirements.txt` is committed. Streamlit Community Cloud
installs it from the repository during deployment.

### Deployment cannot find a CSV

Run the readiness checker with `--require-tracked`. A local file that was never
committed is invisible to Streamlit Community Cloud.
