# Team Workstreams

This document defines the expected ownership areas so contributors can work independently without creating conflicting folders or naming conventions.

## Phuong Anh

Role: Business Analyst and Power BI lead.

Focus areas:

- business opportunity;
- brand revenue;
- visitor spending;
- vendor placement;
- mobility and commercial trade-offs;
- recommended, controlled, and avoided commercial zones;
- Power BI dashboards and recommendation summaries.

Expected outputs:

- Power BI-ready summary tables;
- business interpretation notes;
- vendor-placement recommendations;
- commercial-zone recommendations tied to mobility constraints.

Collaboration points:

- Works closely with Duc Anh on clean tables and business features.
- Uses Que Anh outputs for POI, spend-pattern, and urban-heat context.
- May use Hai Nam and Tan Dat summary exports when store visits or weather affect business recommendations.

## Duc Anh

Role: Business-data and Python lead.

Focus areas:

- reusable Python data-audit scripts;
- cleaning pipelines;
- summary tables;
- feature engineering;
- modest synthetic scenarios where needed;
- Power BI export tables;
- FinalFlow integration datasets.

Expected outputs:

- audited and cleaned data tables;
- shared feature tables;
- validation notes;
- export tables for Phuong Anh.

Collaboration points:

- Coordinates table schemas with Phuong Anh.
- Helps Hai Nam and Tan Dat keep cleaning outputs consistent.
- Keeps synthetic scenarios clearly labeled as `synthetic`.

## Hai Nam

Role: Store-visit data analysis and AI interface development.

Primary dataset:

- `store-visits-rice`

Focus areas:

- focused store-visit cleaning;
- important statistics and visualizations;
- static and interactive plots;
- Streamlit prototype work;
- TypeScript frontend contributions;
- future OpenAI-backed assistant interface.

Expected outputs:

- cleaned store-visit tables;
- summary tables useful to Phuong Anh and Duc Anh;
- selected plots with interpretation;
- UI components for assistant and visualization display when frontend work begins.

Collaboration points:

- Works with Tan Dat on displaying search sources in the UI.
- Coordinates with Duc Anh on export formats and shared fields.
- Keeps assistant responses grounded in documented data contracts.

## Tan Dat

Role: Weather analysis and search-augmented AI backend.

Primary dataset:

- `daily-weather-rice`

Focus areas:

- cleaning weather data;
- detecting sentinel and invalid values;
- summarizing temperature, precipitation, humidity, wind, visibility, and pressure;
- weather visualizations;
- weather-risk indicators;
- compact FinalFlow weather integration table;
- future SerpAPI backend integration;
- future OpenAI plus search behavior;
- source display testing with Hai Nam.

Expected outputs:

- cleaned weather tables;
- weather-risk indicators;
- weather summary exports;
- structured search-source behavior notes for the UI.

Collaboration points:

- Helps Hai Nam test source cards and search-result display.
- Coordinates with Duc Anh on weather export schemas.
- Will later work on a separate branch named `tan-dat`; do not create or switch to that branch until that task begins.

## Que Anh

Role: Spatial business, POI, and urban-heat analysis.

Primary datasets:

- `spend-patterns-rice`
- `core-poi-geometry-rice`
- `urban-heat-index-rice`

Focus areas:

- concise Jupyter analysis;
- dataset loading and initial data view;
- focused cleaning;
- important summaries;
- static plots;
- at least one interactive chart or map;
- simple cross-dataset analysis;
- recommendation exports.

Expected outputs:

- one organized notebook, or a small notebook set if necessary;
- summary tables for Phuong Anh;
- spatial and urban-heat interpretation;
- limitations and final findings.

Collaboration points:

- Helps Phuong Anh after completing the core spatial analysis.
- Coordinates with Duc Anh on export formats.

## Minh Tue

Role: Deployment and infrastructure handoff.

Focus areas:

- AWS deployment later in the project;
- frontend/backend setup instructions;
- environment-variable documentation;
- build and run commands;
- API endpoint documentation;
- deployment readiness checks.

Expected outputs:

- deployment plan;
- AWS configuration notes;
- reproducible setup and run documentation.

Collaboration points:

- Receives finalized app and service instructions from Hai Nam and Tan Dat.
- Uses the handoff template in `docs/handoff/minh-tue-aws-handoff.md`.
- Does not create AWS resources until the project is ready for deployment.
