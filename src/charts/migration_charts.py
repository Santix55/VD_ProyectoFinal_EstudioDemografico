import pandas as pd
import plotly.graph_objects as go

from src.maps.migration_arcs import REGION_COLORS


def plot_corridor_ranking(corridors: pd.DataFrame) -> go.Figure:
    if corridors.empty:
        return _empty_figure("No hay corredores para el ranking")

    ranked = corridors.sort_values("migrant_stock", ascending=True)
    labels = ranked["origin_name"] + " → " + ranked["destination_name"]
    colors = [
        REGION_COLORS.get(region or "Sin región", "#bab0ab")
        for region in ranked["origin_region"]
    ]

    fig = go.Figure(
        go.Bar(
            x=ranked["migrant_stock"],
            y=labels,
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}<br>%{x:,.0f} personas<extra></extra>",
        )
    )
    fig.update_layout(
        title="Top N corredores",
        xaxis_title="Stock migratorio origen-destino",
        yaxis_title="",
        height=max(420, min(900, 28 * len(ranked) + 120)),
        margin=dict(l=8, r=8, t=52, b=34),
    )
    return fig


def plot_region_sankey(corridors: pd.DataFrame) -> go.Figure:
    if corridors.empty:
        return _empty_figure("No hay datos para el Sankey regional")

    grouped = (
        corridors.groupby(["origin_region", "destination_region"], as_index=False)["migrant_stock"]
        .sum()
        .sort_values("migrant_stock", ascending=False)
    )
    origin_labels = [f"Origen: {value}" for value in sorted(grouped["origin_region"].unique())]
    destination_labels = [
        f"Destino: {value}" for value in sorted(grouped["destination_region"].unique())
    ]
    labels = origin_labels + destination_labels
    label_index = {label: index for index, label in enumerate(labels)}

    sources = [label_index[f"Origen: {value}"] for value in grouped["origin_region"]]
    targets = [label_index[f"Destino: {value}"] for value in grouped["destination_region"]]
    values = grouped["migrant_stock"].tolist()
    link_colors = [
        _rgba(REGION_COLORS.get(region or "Sin región", "#bab0ab"), 0.45)
        for region in grouped["origin_region"]
    ]

    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=18,
                thickness=16,
                line=dict(color="#ffffff", width=0.25),
                label=labels,
                color="#4b5563",
            ),
            link=dict(source=sources, target=targets, value=values, color=link_colors),
        )
    )
    fig.update_layout(
        title="Stock migratorio agregado por regiones",
        height=470,
        margin=dict(l=8, r=8, t=52, b=16),
    )
    return fig


def plot_region_heatmap(corridors: pd.DataFrame) -> go.Figure:
    if corridors.empty:
        return _empty_figure("No hay datos para la matriz regional")

    matrix = corridors.pivot_table(
        index="origin_region",
        columns="destination_region",
        values="migrant_stock",
        aggfunc="sum",
        fill_value=0,
    ).sort_index()
    matrix = matrix.reindex(sorted(matrix.columns), axis=1)

    fig = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            colorscale="YlOrRd",
            colorbar=dict(title="Stock"),
            hovertemplate="Origen: %{y}<br>Destino: %{x}<br>Stock: %{z:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Matriz origen-destino por regiones",
        xaxis_title="Región de destino",
        yaxis_title="Región de origen",
        height=470,
        margin=dict(l=8, r=8, t=52, b=80),
    )
    return fig


def _rgba(hex_color: str, opacity: float) -> str:
    value = hex_color.lstrip("#")
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {opacity})"


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(height=360)
    return fig
