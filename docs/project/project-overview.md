# FinalFlow Project Overview

FinalFlow is a match-synchronized mobility-readiness platform for a World Cup transportation and urban-sustainability project.

## Case study

- Event: 2026 World Cup Final
- Match: Spain versus Argentina
- Venue: New York New Jersey Stadium
- Primary corridor: Midtown Manhattan to New York Penn Station to Secaucus Junction to Meadowlands Station to Stadium

## Objective

The project helps the team study mobility conditions before, during, and after the match. The goal is to connect transportation movement, crowd behavior, weather, urban heat, commercial activity, and resilience planning into a clear analytical and software workflow.

## Match phases

- Pre-match arrival
- Kickoff
- 45 minutes
- Halftime
- 90 minutes
- Extra time
- 106 minutes
- 120 minutes
- Final whistle
- Post-match departure

## Analysis scope

FinalFlow is expected to support:

- spectator movement simulation;
- rail, road, shuttle, parking, and pedestrian flows;
- first- and last-mile accessibility;
- congestion and queue analysis;
- weather and urban-heat considerations;
- transportation disruptions and resilience scenarios;
- commercial activity and vendor-placement recommendations;
- emissions and traffic-relief analysis;
- static and interactive visualizations;
- an AI assistant grounded in prepared project data;
- frontend, backend, and Streamlit development;
- later AWS deployment.

## Current repository state

The repository contains a tested four-page Streamlit application in
`paddydash/`, compact derived summaries, reproducible synthetic scenarios,
deterministic analytics, and optional server-side OpenAI narration. The app can
run completely in prepared-data mode and does not load restricted raw data at
runtime.

The current deployment target is Streamlit Community Cloud from the protected
`main` branch. A standalone HTTP API, TypeScript frontend, SerpAPI integration,
and AWS infrastructure are not implemented and must not be assumed by a
deployment owner.

## Contributor principles

- Reuse existing folders before creating new architecture.
- Keep raw datasets local unless explicitly approved.
- Keep notebooks reproducible from top to bottom.
- Use clear names and relative paths.
- Document assumptions, limitations, and whether data is `provided`, `derived`, `synthetic`, or `web`.
- Do not commit secrets, credentials, local environments, notebook checkpoints, or large generated files.
