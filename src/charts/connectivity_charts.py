import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_connectivity_scatter(data: pd.DataFrame) -> go.Figure:
    distance_col = _first_existing_column(
        data,
        ["distance_to_node_km", "distance_to_city_km", "distance_to_airport_km"],
    )
    if data.empty or distance_col is None or "percent_change" not in data.columns:
        return _empty_figure("Faltan datos de conectividad para el scatter")

    fig = px.scatter(
        data,
        x=distance_col,
        y="percent_change",
        size="population_end" if "population_end" in data.columns else None,
        color="quadrant" if "quadrant" in data.columns else None,
        hover_name="territory_name" if "territory_name" in data.columns else None,
        labels={
            distance_col: "Distancia a nodo (km)",
            "percent_change": "Cambio poblacional (%)",
        },
        title="Accesibilidad frente a cambio poblacional",
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#666666")
    fig.add_vline(x=data[distance_col].median(), line_dash="dash", line_color="#666666")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=35))
    return fig


def plot_quadrant_counts(data: pd.DataFrame) -> go.Figure:
    if data.empty or "quadrant" not in data.columns:
        return _empty_figure("Faltan categorías territoriales")

    counts = data["quadrant"].value_counts().reset_index()
    counts.columns = ["quadrant", "territories"]
    fig = px.bar(
        counts,
        x="territories",
        y="quadrant",
        orientation="h",
        title="Distribución por cuadrantes",
        labels={"territories": "Territorios", "quadrant": "Categoría"},
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=55, b=35))
    return fig


def _first_existing_column(data: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in data.columns), None)


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(height=320)
    return fig
