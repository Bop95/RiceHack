import math

import streamlit as st

st.set_page_config(page_title="RiceHack Dashboard", layout="wide")

PALETTE = ["#00C2A8", "#7AA6FF", "#FF8A3D", "#9B6DFF", "#FFD166", "#FF5C8A"]


def build_mock_dashboard_data() -> dict:
    return {
        "dates": [f"Jul {day}" for day in range(1, 31)],
        "signups": [
            120, 126, 132, 128, 140, 145, 150, 148, 154, 160,
            158, 166, 172, 169, 178, 184, 190, 188, 196, 204,
            210, 208, 216, 224, 230, 236, 242, 248, 255, 262,
        ],
        "active_users": [
            80, 82, 85, 84, 88, 90, 94, 93, 96, 100,
            99, 103, 106, 108, 111, 114, 118, 117, 121, 125,
            129, 130, 133, 136, 140, 143, 147, 150, 154, 158,
        ],
        "revenue": [
            900, 940, 980, 970, 1020, 1060, 1090, 1110, 1150, 1190,
            1180, 1230, 1270, 1290, 1340, 1380, 1420, 1410, 1470, 1510,
            1560, 1590, 1630, 1680, 1710, 1760, 1810, 1850, 1900, 1950,
        ],
        "conversion_rate": [
            2.8, 2.9, 3.0, 2.7, 3.1, 3.2, 3.2, 3.1, 3.4, 3.5,
            3.3, 3.5, 3.6, 3.6, 3.8, 3.9, 4.0, 3.8, 4.1, 4.2,
            4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.0,
        ],
        "channels": [
            {"label": "Organic", "users": 420},
            {"label": "Referral", "users": 260},
            {"label": "Paid Ads", "users": 310},
            {"label": "Email", "users": 180},
            {"label": "Partners", "users": 140},
        ],
        "regions": {
            "Mon": {"North": 52, "South": 38, "East": 30, "West": 28},
            "Tue": {"North": 55, "South": 40, "East": 33, "West": 29},
            "Wed": {"North": 58, "South": 43, "East": 35, "West": 31},
            "Thu": {"North": 62, "South": 46, "East": 37, "West": 34},
            "Fri": {"North": 65, "South": 49, "East": 40, "West": 36},
            "Sat": {"North": 69, "South": 51, "East": 43, "West": 39},
            "Sun": {"North": 72, "South": 54, "East": 45, "West": 41},
        },
        "campaigns": [
            {"label": "Launch", "spend": 1200, "revenue": 2800},
            {"label": "Retention", "spend": 900, "revenue": 2150},
            {"label": "Student", "spend": 650, "revenue": 1480},
            {"label": "Referral", "spend": 500, "revenue": 1310},
            {"label": "Weekend", "spend": 780, "revenue": 1740},
        ],
    }


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .chart-card {
            background: linear-gradient(180deg, #121826 0%, #0d1118 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 18px;
            padding: 16px 18px 10px 18px;
            margin-bottom: 18px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.20);
        }
        .chart-title {
            color: #f6f7fb;
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .chart-subtitle {
            color: #96a0b5;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }
        .legend-row {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 10px;
            color: #cad1e1;
            font-size: 0.88rem;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .legend-swatch {
            width: 10px;
            height: 10px;
            border-radius: 999px;
            display: inline-block;
        }
        .table-wrap {
            background: #0d1118;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 18px;
            padding: 14px 16px;
            margin-top: 8px;
        }
        table.mock-table {
            width: 100%;
            border-collapse: collapse;
            color: #f6f7fb;
        }
        table.mock-table th,
        table.mock-table td {
            text-align: left;
            padding: 8px 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 0.92rem;
        }
        table.mock-table th {
            color: #96a0b5;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def scale_points(values: list[float], width: int, height: int, padding: int) -> list[tuple[float, float]]:
    min_val = min(values)
    max_val = max(values)
    spread = max(max_val - min_val, 1)
    step_x = (width - 2 * padding) / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x = padding + index * step_x
        y = height - padding - ((value - min_val) / spread) * (height - 2 * padding)
        points.append((x, y))
    return points


def render_line_chart(title: str, subtitle: str, series: list[dict]) -> None:
    width, height, padding = 640, 260, 28
    all_values = [value for item in series for value in item["values"]]
    min_val = min(all_values)
    max_val = max(all_values)
    spread = max(max_val - min_val, 1)

    grid_lines = []
    for i in range(5):
        y = padding + i * (height - 2 * padding) / 4
        label_value = max_val - i * spread / 4
        grid_lines.append(
            f"<line x1='{padding}' y1='{y:.1f}' x2='{width - padding}' y2='{y:.1f}' "
            "stroke='rgba(255,255,255,0.10)' stroke-width='1'/>"
            f"<text x='4' y='{y + 4:.1f}' fill='#96a0b5' font-size='11'>{label_value:.0f}</text>"
        )

    paths = []
    points_markup = []
    legend = []
    for index, item in enumerate(series):
        points = []
        scaled = scale_points(item["values"], width, height, padding)
        for x, y in scaled:
            points.append(f"{x:.1f},{y:.1f}")
            points_markup.append(
                f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='{PALETTE[index]}' "
                "stroke='#0d1118' stroke-width='2'/>"
            )
        paths.append(
            f"<polyline fill='none' stroke='{PALETTE[index]}' stroke-width='3' "
            f"points='{' '.join(points)}'/>"
        )
        legend.append(
            "<div class='legend-item'>"
            f"<span class='legend-swatch' style='background:{PALETTE[index]}'></span>"
            f"<span>{item['label']}</span></div>"
        )

    x_labels = []
    label_count = len(series[0]["x_labels"])
    for index, label in enumerate(series[0]["x_labels"]):
        if index % max(label_count // 6, 1) != 0 and index != label_count - 1:
            continue
        x = padding + index * (width - 2 * padding) / max(label_count - 1, 1)
        x_labels.append(
            f"<text x='{x:.1f}' y='{height - 6}' text-anchor='middle' fill='#96a0b5' font-size='11'>{label}</text>"
        )

    svg = (
        f"<div class='chart-card'><div class='chart-title'>{title}</div>"
        f"<div class='chart-subtitle'>{subtitle}</div>"
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='260'>"
        f"{''.join(grid_lines)}{''.join(paths)}{''.join(points_markup)}{''.join(x_labels)}</svg>"
        f"<div class='legend-row'>{''.join(legend)}</div></div>"
    )
    st.markdown(svg, unsafe_allow_html=True)


def render_bar_chart(title: str, subtitle: str, labels: list[str], values: list[float], color: str) -> None:
    width, height, padding = 640, 260, 30
    max_val = max(values)
    bar_width = (width - 2 * padding) / max(len(values) * 1.4, 1)
    bars = []
    x_labels = []
    for index, value in enumerate(values):
        x = padding + index * bar_width * 1.4
        bar_height = (value / max_val) * (height - 2 * padding)
        y = height - padding - bar_height
        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_width:.1f}' height='{bar_height:.1f}' "
            f"rx='8' fill='{color}' opacity='{0.65 + index * 0.06:.2f}'/>"
            f"<text x='{x + bar_width / 2:.1f}' y='{y - 8:.1f}' text-anchor='middle' fill='#cad1e1' font-size='11'>{value:.0f}</text>"
        )
        x_labels.append(
            f"<text x='{x + bar_width / 2:.1f}' y='{height - 8}' text-anchor='middle' fill='#96a0b5' font-size='11'>{labels[index]}</text>"
        )
    svg = (
        f"<div class='chart-card'><div class='chart-title'>{title}</div>"
        f"<div class='chart-subtitle'>{subtitle}</div>"
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='260'>"
        f"{''.join(bars)}{''.join(x_labels)}</svg></div>"
    )
    st.markdown(svg, unsafe_allow_html=True)


def render_donut_chart(title: str, subtitle: str, segments: list[dict]) -> None:
    radius = 76
    circumference = 2 * math.pi * radius
    total = sum(item["users"] for item in segments)
    offset = 0.0
    arcs = []
    legend = []
    for index, item in enumerate(segments):
        portion = item["users"] / total
        dash = portion * circumference
        arcs.append(
            f"<circle cx='110' cy='110' r='{radius}' fill='transparent' stroke='{PALETTE[index]}' "
            f"stroke-width='32' stroke-dasharray='{dash:.2f} {circumference - dash:.2f}' "
            f"stroke-dashoffset='{-offset:.2f}' transform='rotate(-90 110 110)'/>"
        )
        offset += dash
        legend.append(
            "<div class='legend-item'>"
            f"<span class='legend-swatch' style='background:{PALETTE[index]}'></span>"
            f"<span>{item['label']} ({item['users']})</span></div>"
        )
    svg = (
        f"<div class='chart-card'><div class='chart-title'>{title}</div>"
        f"<div class='chart-subtitle'>{subtitle}</div>"
        "<div style='display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;'>"
        "<svg viewBox='0 0 220 220' width='220' height='220'>"
        "<circle cx='110' cy='110' r='76' fill='transparent' stroke='rgba(255,255,255,0.08)' stroke-width='32'/>"
        f"{''.join(arcs)}"
        f"<text x='110' y='104' text-anchor='middle' fill='#f6f7fb' font-size='24' font-weight='700'>{total}</text>"
        "<text x='110' y='128' text-anchor='middle' fill='#96a0b5' font-size='12'>Total Users</text>"
        "</svg>"
        f"<div class='legend-row' style='max-width:240px'>{''.join(legend)}</div></div></div>"
    )
    st.markdown(svg, unsafe_allow_html=True)


def render_multi_region_chart(title: str, subtitle: str, region_map: dict[str, dict[str, int]]) -> None:
    width, height, padding = 640, 260, 28
    days = list(region_map.keys())
    region_names = list(next(iter(region_map.values())).keys())
    all_values = [region_map[day][region] for day in days for region in region_names]
    min_val = min(all_values)
    max_val = max(all_values)
    spread = max(max_val - min_val, 1)

    def to_points(values: list[int]) -> str:
        result = []
        step_x = (width - 2 * padding) / max(len(values) - 1, 1)
        for index, value in enumerate(values):
            x = padding + index * step_x
            y = height - padding - ((value - min_val) / spread) * (height - 2 * padding)
            result.append(f"{x:.1f},{y:.1f}")
        return " ".join(result)

    lines = []
    legend = []
    for index, region in enumerate(region_names):
        region_values = [region_map[day][region] for day in days]
        lines.append(
            f"<polyline fill='none' stroke='{PALETTE[index]}' stroke-width='3' points='{to_points(region_values)}'/>"
        )
        legend.append(
            "<div class='legend-item'>"
            f"<span class='legend-swatch' style='background:{PALETTE[index]}'></span>"
            f"<span>{region}</span></div>"
        )

    x_labels = []
    for index, day in enumerate(days):
        x = padding + index * (width - 2 * padding) / max(len(days) - 1, 1)
        x_labels.append(
            f"<text x='{x:.1f}' y='{height - 6}' text-anchor='middle' fill='#96a0b5' font-size='11'>{day}</text>"
        )

    svg = (
        f"<div class='chart-card'><div class='chart-title'>{title}</div>"
        f"<div class='chart-subtitle'>{subtitle}</div>"
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='260'>{''.join(lines)}{''.join(x_labels)}</svg>"
        f"<div class='legend-row'>{''.join(legend)}</div></div>"
    )
    st.markdown(svg, unsafe_allow_html=True)


def render_scatter_chart(title: str, subtitle: str, campaigns: list[dict]) -> None:
    width, height, padding = 640, 260, 34
    max_spend = max(item["spend"] for item in campaigns)
    max_revenue = max(item["revenue"] for item in campaigns)
    points = []
    for index, item in enumerate(campaigns):
        x = padding + (item["spend"] / max_spend) * (width - 2 * padding)
        y = height - padding - (item["revenue"] / max_revenue) * (height - 2 * padding)
        radius = 10 + (item["revenue"] / max_revenue) * 12
        points.append(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{radius:.1f}' fill='{PALETTE[index]}' opacity='0.75'/>"
            f"<text x='{x:.1f}' y='{y - radius - 6:.1f}' text-anchor='middle' fill='#cad1e1' font-size='11'>{item['label']}</text>"
        )
    svg = (
        f"<div class='chart-card'><div class='chart-title'>{title}</div>"
        f"<div class='chart-subtitle'>{subtitle}</div>"
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='260'>"
        f"<line x1='{padding}' y1='{height - padding}' x2='{width - padding}' y2='{height - padding}' stroke='rgba(255,255,255,0.16)'/>"
        f"<line x1='{padding}' y1='{padding}' x2='{padding}' y2='{height - padding}' stroke='rgba(255,255,255,0.16)'/>"
        f"{''.join(points)}"
        f"<text x='{width / 2:.1f}' y='{height - 6}' text-anchor='middle' fill='#96a0b5' font-size='11'>Spend</text>"
        f"<text x='14' y='{height / 2:.1f}' text-anchor='middle' fill='#96a0b5' font-size='11' transform='rotate(-90 14 {height / 2:.1f})'>Revenue</text>"
        "</svg></div>"
    )
    st.markdown(svg, unsafe_allow_html=True)


def render_mock_table(data: dict) -> None:
    recent_rows = []
    for index in range(-5, 0):
        recent_rows.append(
            "<tr>"
            f"<td>{data['dates'][index]}</td>"
            f"<td>{data['signups'][index]}</td>"
            f"<td>{data['active_users'][index]}</td>"
            f"<td>${data['revenue'][index]:,}</td>"
            f"<td>{data['conversion_rate'][index]:.1f}%</td>"
            "</tr>"
        )
    st.markdown(
        (
            "<div class='table-wrap'><div class='chart-title'>Recent Mock Data</div>"
            "<table class='mock-table'><thead><tr>"
            "<th>Date</th><th>Signups</th><th>Active Users</th><th>Revenue</th><th>Conversion</th>"
            "</tr></thead><tbody>"
            f"{''.join(recent_rows)}</tbody></table></div>"
        ),
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    data = build_mock_dashboard_data()
    inject_styles()

    st.title("Operations Dashboard")
    st.caption("Mock graphs only for now. Once you share real data, we can plug it into the same layout.")

    left, right = st.columns(2)
    with left:
        render_line_chart(
            "Growth Trend",
            "Signups and active users over the last 30 days.",
            [
                {"label": "Signups", "values": data["signups"], "x_labels": data["dates"]},
                {"label": "Active Users", "values": data["active_users"], "x_labels": data["dates"]},
            ],
        )
    with right:
        render_bar_chart(
            "Revenue Trend",
            "Daily mock revenue for the same period.",
            data["dates"][-10:],
            data["revenue"][-10:],
            PALETTE[1],
        )

    lower_left, lower_right = st.columns(2)
    with lower_left:
        render_donut_chart(
            "Channel Mix",
            "Where mock users are coming from.",
            data["channels"],
        )
    with lower_right:
        render_multi_region_chart(
            "Regional Activity",
            "Weekly activity across four regions.",
            data["regions"],
        )

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        render_line_chart(
            "Conversion Rate",
            "Mock conversion trend over time.",
            [
                {"label": "Conversion %", "values": data["conversion_rate"], "x_labels": data["dates"]},
            ],
        )
    with bottom_right:
        render_scatter_chart(
            "Campaign Efficiency",
            "Mock spend versus revenue by campaign.",
            data["campaigns"],
        )

    render_mock_table(data)


render_dashboard()
