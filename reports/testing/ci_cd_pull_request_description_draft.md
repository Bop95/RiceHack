# Suggested CI/CD pull request

## Suggested title

`Add FinalFlow CI quality gate and Streamlit delivery guide`

## Description

### Summary

This PR adds FinalFlow's first repository CI/CD foundation. Pull requests now
have a Python 3.12 quality gate for dependency compatibility, linting, syntax,
deployment-bundle readiness, and the full test suite. The accompanying guide
documents how maintainers make that check required and connect the protected
branch to Streamlit Community Cloud for automatic delivery.

### Pipeline

```text
Pull request
  -> Python 3.12 setup and cached dependencies
  -> pip compatibility check
  -> Ruff lint
  -> compile preflight
  -> Streamlit deployment readiness
  -> complete unittest suite
  -> review and merge
  -> Streamlit Community Cloud detects protected-branch update
```

### Updates

- Added `.github/workflows/ci.yml` for pull requests from every team branch,
  pushes to `main`, and manual runs.
- Added concurrency cancellation for superseded PR commits.
- Set `GITHUB_TOKEN` access to `contents: read` and disabled checkout credential
  persistence.
- Kept live OpenAI calls and secrets out of normal CI.
- Added pinned CI-only Ruff dependency and stable lint configuration.
- Added repository tests that protect the workflow's events, permissions,
  commands, Python version, and secret boundary.
- Added a repo-specific CI/CD guide covering branch rules, Streamlit setup,
  smoke testing, troubleshooting, and rollback.
- Linked the guide from the root README and deployment guide.

### Verification

```powershell
.\.venv\Scripts\python.exe -m pip check
# No broken requirements found

.\.venv\Scripts\python.exe -m ruff check paddydash scripts tests
# All checks passed

.\.venv\Scripts\python.exe -m compileall -q paddydash scripts tests
# passed

$env:FINALFLOW_DISABLE_OPENAI = "true"
.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py `
  --require-tracked
# no deployment errors; expected no-key prepared-data warning only

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# 59 tests passed
```

### Safety notes

- No OpenAI key or deployment secret is supplied to pull-request jobs.
- The workflow uses only official GitHub checkout/Python setup actions.
- Workflow permissions are read-only.
- Raw Rice files, Parquet files, `.env`, and Streamlit secret files remain
  excluded.
- This PR does not create AWS resources or publish release artifacts.

### Maintainer steps after merge

- Run the workflow once so its status-check name becomes selectable.
- Protect the Streamlit deployment branch and require
  **Python 3.12 quality gate**.
- Connect Streamlit Community Cloud to `paddydash/app.py` on that protected
  branch.
- Store `OPENAI_API_KEY` only in Streamlit's Secrets settings.
- Attach screenshots of the green Actions run, required branch check, and hosted
  Streamlit smoke check to the PR or deployment record.

### Documentation

See `docs/engineering/ci-cd-guide.md` for the complete team guide.
