import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


METRIC_LABELS = {
    "percent_change": "Cambio porcentual",
    "absolute_change": "Cambio absoluto",
    "population_end": "Población final",
    "annualized_change": "Crecimiento anual medio",
}


def plot_change_ranking(
    change: pd.DataFrame,
    metric: str,
    ranking_mode: str,
    ascending: bool,
) -> go.Figure:
    if change.empty or metric not in change.columns:
        return _empty_figure("No hay datos para el ranking")

    label_col = "territory_name" if "territory_name" in change.columns else "territory_id"
    ranked = (
        change.dropna(subset=[metric])
        .sort_values(metric, ascending=ascending)
        .head(12)
        .sort_values(metric, ascending=not ascending)
    )

    colors = ["#b94b4b" if value < 0 else "#2c8c6c" for value in ranked[metric]]
    fig = go.Figure(
        go.Bar(
            x=ranked[metric],
            y=ranked[label_col],
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}<br>%{x:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=ranking_mode,
        xaxis_title=METRIC_LABELS.get(metric, metric),
        yaxis_title="Territorio",
        height=440,
        margin=dict(l=10, r=10, t=55, b=35),
    )
    return fig


def plot_population_trend(population: pd.DataFrame, selected_territory: str) -> go.Figure:
    if population.empty or "territory_name" not in population.columns:
        return _empty_figure("No hay datos para la serie temporal")

    territory = population.loc[population["territory_name"] == selected_territory].sort_values("year")
    if territory.empty:
        return _empty_figure("No hay datos para el territorio seleccionado")

    fig = px.line(
        territory,
        x="year",
        y="population",
        markers=True,
        title=f"Evolución de población: {selected_territory}",
        labels={"year": "Año", "population": "Población"},
    )
    fig.update_traces(line_color="#305f8f", hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>")
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=55, b=35))
    return fig


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(height=360)
    return fig
