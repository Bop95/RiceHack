# FinalFlow integration rehearsal

Date: 2026-09-10. Working branch: `stephen-develop`.

## Validation environment

- Isolated virtual environment at `/tmp/finalflow-validation-venv`; Python 3.13.
  Python 3.12 is not installed locally; the existing CI target remains 3.12.
- Declared Streamlit 1.60.0, Plotly 6.9.0, OpenAI 2.52.0 and Pydantic 2.13.4.
- All 137 unittest tests passed, including mocked provider/security checks and
  the two judge-journey tests. No live OpenAI or SerpAPI calls were made.
- Compilation, Ruff, `pip check`, and staged whitespace checks passed.
- Strict deployment check passed: 7.67 MB bundle, no missing tracked files.
  Offline OpenAI mode produces the expected configuration warning.
- Retained-page smoke tests also passed on the original Python 3.11 / Streamlit
  1.42 environment (5 tests). Legacy sizing arguments remain deprecated on 1.60
  but work on both tested versions; removing legacy-version support is future work.

## Judge journey

The automated matrix covers baseline, rain and rail disruption at pre-match,
kickoff, final whistle and post-match. Displayed queues, waits, utilization,
clearance and baseline comparison values are checked against the engine.

Illustrative post-match preview, kickoff +165 minutes:

| Scenario | Largest node queue | Bottleneck | Wait, min | Whole-run peak total queue | Clearance after whistle, min |
| --- | ---: | --- | ---: | ---: | ---: |
| Baseline | 0 | None | 0 | 0 | 110 |
| Rain | 140 | Stadium | 5 | 240 | 135 |
| Rail disruption | 1000 | Meadowlands Station | 20 | 2400 | 150 |

All values above are synthetic, not event observations. Alternative capacity
boost runs are not combined disruption interventions. Baseline, capacity boost
and staggered departure tie at zero peak queue under current assumptions.

Navigation to contextual evidence and the assistant preserves selected replay
scope. History keeps its original scope after a control change. Questions about
recommendation changes and lowest queues use deterministic project answers.
Mocked transit/weather/access searches produce separate web source cards; missing
keys retain project answers with a safe no-search message. Project questions make
no search request. Fabricated model facts cannot replace prepared values.

## Browser observations

Headless Chrome through installed Playwright exercised the actual Streamlit app,
including selecting post-match rail disruption, opening commercial/weather
evidence and asking the offline assistant why the recommendation changed.
The phase selector virtualizes its long list; filtering by label works.

Desktop (1440x1000) and fresh mobile (390x844) screenshots were inspected.
Controls and metrics render; the mobile sidebar starts collapsed and metrics
stack vertically. No document-level horizontal overflow was detected. Wide
tables retain internal horizontal scrolling rather than squeezing columns.
Large contextual evidence and assistant sections require vertical scrolling.
Temporary screenshots remain outside Git under `/tmp/finalflow-*.png`.
Startup health returned HTTP 200 (`ok`); the rehearsal server was stopped.

## Publication boundary and follow-up

No new raw datasets, real credentials or large generated artifacts were staged.
Both existing 50-row business CSVs retain their original numeric and identity
fields; only provenance and recommendation wording changed.

Site-specific historical evidence review, simulator calibration, live provider
verification and deployment are not complete. A future `main` release remains a
separate decision. Before an event-facing demonstration, review source scope and
operational assumptions with the team, then run the Python 3.12 CI gate.

Reproduce from a compatible activated environment:

```bash
python3 -m pip check
python3 -m ruff check paddydash scripts tests
python3 -m compileall -q paddydash notebooks scripts tests
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true python3 -m unittest discover -s tests -v
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true python3 scripts/validation/check_streamlit_deployment.py --require-tracked
```
