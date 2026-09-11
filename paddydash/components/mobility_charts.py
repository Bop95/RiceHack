"""Queue comparison chart using only deterministic simulation snapshots."""

import plotly.graph_objects as go

from paddydash.services.mobility_simulator import MobilityRun


def queue_comparison_figure(baseline: MobilityRun, selected: MobilityRun,
                            label: str, minute: int, whistle: int) -> go.Figure:
    figure = go.Figure()
    for name, run, color, dash in (
        ('Baseline', baseline, '#68737d', 'dash'),
        (label, selected, '#008579', 'solid'),
    ):
        figure.add_trace(go.Scatter(
            x=[s.time_minutes for s in run.snapshots],
            y=[sum(n.queue for n in s.node_states) for s in run.snapshots],
            name=name, mode='lines', line=dict(color=color, width=3, dash=dash),
            hovertemplate='%{y:,} people waiting<br>Kickoff %{x} min<extra>%{fullData.name}</extra>',
        ))
    figure.add_vline(x=minute, line_color='#bb4639', line_width=2)
    figure.add_vline(x=whistle, line_color='#9a792a', line_dash='dot')
    figure.update_layout(
        height=310, margin=dict(l=10, r=10, t=25, b=30),
        legend=dict(orientation='h', y=1.15, x=0),
        xaxis_title='Minutes from kickoff', yaxis_title='People waiting for service',
        hovermode='x unified', font=dict(size=12),
    )
    figure.update_xaxes(zeroline=True, zerolinecolor='#aaaaaa')
    return figure
