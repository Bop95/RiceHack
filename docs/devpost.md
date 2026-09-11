# FinalFlow

FinalFlow is a match-synchronized mobility-readiness platform that helps planners explore how an illustrative World Cup final could pressure the NY/NJ travel corridor before, during, and after a match.

## Inspiration

Mega-events do not create a single transportation problem. They create a moving sequence of decisions: when to add rail capacity, where queues may form after the final whistle, how weather changes access conditions, and when commercial activity may conflict with a safe, clear exit path.

We used a hypothetical 2026 World Cup Final between Spain and Argentina at New York New Jersey Stadium as a focused case study. Rather than show one static dashboard, we wanted FinalFlow to let a planner move from pre-match arrivals to post-match departure and see how the modeled corridor changes: Midtown Manhattan → Penn Station → Secaucus Junction → Meadowlands Station → Stadium.

## What it does

FinalFlow is a seven-page Streamlit decision-support prototype. A user selects a match phase, scenario, and replay minute once; the shared state carries through the experience.

- **Executive Overview** surfaces the current modeled bottleneck, largest queue, utilization, estimated wait, whole-run clearance, and supported actions.
- **Matchday Timeline** shows canonical markers from pre-match through final whistle and post-match, with queue and edge-throughput trends.
- **Mobility & Access** visualizes the five-node corridor, node queues, edge capacity/throughput, first- and last-mile indicators, and a baseline comparison.
- **Scenario Lab** compares baseline, rail disruption, rail capacity boost, rain, and staggered departure using peak queue, delay proxy, clearance, overloaded intervals, and utilization.
- **Commercial & POI Intelligence** brings in historical store-visit context, exploratory POI/heat information, and clearly labeled synthetic placement examples.
- **Weather & Heat** connects historical multi-station weather context and urban-heat locations to the selected mobility scenario. For example, the rain comparison uses simulator-derived effects rather than an AI-generated claim.
- **Ask FinalFlow** explains the selected project state using deterministic evidence. It can optionally use OpenAI for grounded wording, and it can request SerpAPI only for explicit current-public-information questions such as transit alerts, weather alerts, or venue access notices. Project evidence and web sources remain separate in the interface.

## How we built it

We built FinalFlow as a Python and Streamlit application. The core is an explainable, discrete five-minute corridor replay rather than a black-box prediction system. The model uses one validated configuration for its five nodes, directed edges, canonical match phases, and scenario definitions.

The data path is intentionally visible:

```text
Historical / prepared context
        +
Synthetic matchday demand and capacity assumptions
        ↓
Deterministic mobility simulation
        ↓
Derived queues, waits, throughput, utilization, and comparisons
        ↓
Interactive decision support and grounded explanations
```

We use pandas and NumPy for preparation and deterministic calculations, Pydantic for validated mobility contracts, Plotly for interactive charts and maps, and Streamlit for the interface. The optional assistant uses the official OpenAI Python SDK and the Responses API. The search layer uses SerpAPI through `requests`, with a small rule-based router that prevents search for questions already answerable from FinalFlow data.

## Data

FinalFlow combines several evidence types instead of blending everything into one misleading score:

- **Historical/contextual evidence:** prepared Rice-derived store-visit, spending, POI, weather, and urban-heat outputs.
- **Synthetic inputs:** transparent matchday passenger-demand profiles, transit service capacities, first/last-mile demand, road/parking/pedestrian inputs, interventions, emissions factors, and approximate corridor references.
- **Derived outputs:** node and edge time series, scenario summaries, intervention comparisons, weather/heat context, commercial context, and executive KPIs.
- **Web evidence:** optional current public search snippets, displayed independently from project evidence.

Event-specific passenger demand, capacities, coordinates, and intervention effects are scenario assumptions, not observed World Cup operations or validated train schedules. The current replay follows an illustrative 6,000-person corridor cohort; it does not claim to represent official attendance. Historical weather is multi-station context, not a stadium forecast. Synthetic vendor and placement examples are not verified recommendations.

## Challenges we ran into

The hardest challenge was building an honest event-day experience without official World Cup operations data. We had to separate what the repository can support from what it cannot: historical context is useful, but it cannot become a real-time passenger count or a validated train-capacity claim.

We also had to make different data layers work together. Store visits, POIs, urban heat, weather, and mobility do not share the same units, time scales, or geographic certainty. FinalFlow therefore keeps their provenance visible rather than silently converting commercial activity into ridership or historical rain into a future forecast.

Finally, we designed the assistant so it cannot invent project statistics. Deterministic retrieval selects the facts, evidence, labels, and limitations first. OpenAI can help present that context, but a factual guard prevents the model from replacing approved metrics. Provider or search failures preserve a usable prepared-data answer without exposing secrets or raw provider errors.

## Accomplishments that we're proud of

- Creating a match-synchronized corridor replay that makes pressure visibly change from arrivals to departure.
- Comparing five concrete resilience scenarios without treating synthetic outputs as observed reality.
- Building a single interface where mobility, weather/heat, commercial/POI context, and recommendation rules remain scoped and labeled.
- Making provenance a first-class product feature through `provided`, `derived`, `synthetic`, and `web` labels.
- Delivering a usable Streamlit prototype with automated contract, simulation, assistant, search-security, and page-rendering tests.

## What we learned

We learned that transportation planning is systems thinking: a rail disruption can shift pressure into transfer, pedestrian, commercial, and communication decisions. We also learned that a useful scenario model must make uncertainty easy to see. Clear labels, explicit assumptions, and deterministic comparisons are often more valuable to a decision-maker than a more complicated model with unclear inputs.

Most importantly, we learned that an AI assistant is most helpful when it explains evidence rather than becoming the source of evidence.

## What's next for FinalFlow

Next, we would replace scenario assumptions with approved agency, GTFS, venue, and event operations data; validate the replay against observed event data; and improve pedestrian, road, parking, accessibility, and emissions modeling. We would also add site-specific review for the commercial and heat layers.

On the software side, the next steps are live-provider monitoring, a defined backend/API boundary, and deployment work. The same approach could later be adapted for concerts, conventions, the Olympics, and other high-demand events, but each use case would need new local data and validation.

## Built With

- Python
- Streamlit
- pandas
- NumPy
- Plotly
- Pydantic
- OpenAI Python SDK and Responses API
- SerpAPI
- requests
- GitHub and GitHub Actions
