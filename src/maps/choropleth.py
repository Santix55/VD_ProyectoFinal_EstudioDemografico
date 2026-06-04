import pandas as pd
import plotly.express as px


COLOR_SCALES = {
    "population_end": "Viridis",
    "vulnerability_index": "YlOrRd",
}
CHANGE_METRICS = {"percent_change", "absolute_change", "annualized_change"}
CHANGE_COLOR_SCALE = "RdYlGn"


def build_population_choropleth(
    change: pd.DataFrame,
    metric: str,
    title: str,
):
    if change.empty or metric not in change.columns:
        return px.choropleth(title="No hay datos para el mapa")

    hover_data = {
        "territory_id": False,
        "territory_name": True if "territory_name" in change.columns else False,
        "population_start": ":,.0f",
        "population_end": ":,.0f",
        "absolute_change": ":,.0f",
        "percent_change": ":.2f",
    }
    hover_data = {key: value for key, value in hover_data.items() if key in change.columns}

    color_args = _color_args(change, metric)

    fig = px.choropleth(
        change,
        locations="territory_id",
        color=metric,
        hover_name="territory_name" if "territory_name" in change.columns else "territory_id",
        hover_data=hover_data,
        projection="natural earth",
        title=title,
        **color_args,
    )
    fig.update_geos(showframe=False, showcoastlines=True, coastlinecolor="#a6a6a6")
    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=55, b=0),
        coloraxis_colorbar=dict(title=title),
    )
    return fig


def _color_args(data: pd.DataFrame, metric: str) -> dict:
    if metric not in CHANGE_METRICS:
        return {"color_continuous_scale": COLOR_SCALES.get(metric, "Viridis")}

    max_abs = data[metric].abs().quantile(0.95)
    if pd.isna(max_abs) or max_abs == 0:
        max_abs = data[metric].abs().max()
    if pd.isna(max_abs) or max_abs == 0:
        max_abs = 1

    return {
        "color_continuous_scale": CHANGE_COLOR_SCALE,
        "color_continuous_midpoint": 0,
        "range_color": [-max_abs, max_abs],
    }


def build_choropleth_map(geodata, data: pd.DataFrame, metric: str, title: str):
    if geodata is None or len(geodata) == 0 or data.empty or metric not in data.columns:
        return None

    try:
        import folium
    except ImportError:
        return None

    id_col = _first_existing_column(geodata, ["territory_id", "iso_a3", "ISO_A3", "ADM0_A3"])
    if id_col is None or "territory_id" not in data.columns:
        return None

    merged = geodata.merge(data, left_on=id_col, right_on="territory_id", how="left")
    geojson = merged.to_json()
    map_object = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
    folium.Choropleth(
        geo_data=geojson,
        data=merged,
        columns=[id_col, metric],
        key_on=f"feature.properties.{id_col}",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.25,
        legend_name=title,
        nan_fill_color="#dddddd",
    ).add_to(map_object)
    return map_object


def _first_existing_column(data, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in data.columns), None)
