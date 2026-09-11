# FinalFlow Project Overview

> FinalFlow is an explainable scenario-planning platform for World Cup mobility,
> not a real-time traffic-control or passenger-count system.

FinalFlow is a match-synchronized mobility-readiness platform for a World Cup
transportation and urban-sustainability project.

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

The repository contains a tested seven-page Streamlit application in
`paddydash/`: Executive Overview, Matchday Timeline, Mobility & Access,
Commercial & POI Intelligence, Weather & Heat, Scenario Lab, and Ask FinalFlow.
It combines compact derived exports, reproducible synthetic mobility inputs,
historical store-visit/weather/heat context, deterministic analytics, optional
server-side OpenAI wording, and conditional SerpAPI public-information search.
The app can run completely in prepared-data mode and does not load restricted
raw data at runtime.

The current deployment target is Streamlit Community Cloud from protected
`main`. A standalone HTTP API, TypeScript frontend, AWS infrastructure, and
operational simulator calibration are not implemented and must not be assumed by
a deployment owner.

## Contributor principles

- Reuse existing folders before creating new architecture.
- Keep raw datasets local unless explicitly approved.
- Keep notebooks reproducible from top to bottom.
- Use clear names and relative paths.
- Document assumptions, limitations, and whether data is `provided`, `derived`, `synthetic`, or `web`.
- Do not commit secrets, credentials, local environments, notebook checkpoints, or large generated files.
