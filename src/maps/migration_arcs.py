from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go


REGION_COLORS = {
    "Africa": "#f28e2b",
    "Americas": "#4e79a7",
    "Asia": "#e15759",
    "Europe": "#76b7b2",
    "Oceania": "#59a14f",
    "Seven seas (open ocean)": "#9c755f",
    "Sin región": "#bab0ab",
}


def build_migration_arc_map(corridors: pd.DataFrame) -> go.Figure:
    if corridors.empty:
        return _empty_map("No hay corredores migratorios para los filtros seleccionados")

    fig = go.Figure()
    widths = _scaled_widths(corridors["migrant_stock"])
    legend_regions = set()

    for width, row in zip(widths, corridors.itertuples()):
        region = getattr(row, "origin_region", "Sin región") or "Sin región"
        color = REGION_COLORS.get(region, "#bab0ab")
        lon, lat = curved_arc_points(
            row.origin_lon,
            row.origin_lat,
            row.destination_lon,
            row.destination_lat,
        )
        fig.add_trace(
            go.Scattergeo(
                lon=lon,
                lat=lat,
                mode="lines",
                line=dict(color=color, width=width),
                opacity=0.78,
                name=region,
                legendgroup=region,
                showlegend=region not in legend_regions,
                text=_hover_text(row),
                hovertemplate="%{text}<extra></extra>",
            )
        )
        legend_regions.add(region)

    destination_sizes = _scaled_marker_sizes(corridors["migrant_stock"])
    destination_colors = [
        REGION_COLORS.get(region or "Sin región", "#bab0ab")
        for region in corridors["origin_region"]
    ]
    fig.add_trace(
        go.Scattergeo(
            lon=corridors["destination_lon"],
            lat=corridors["destination_lat"],
            mode="markers",
            marker=dict(
                size=destination_sizes,
                color=destination_colors,
                symbol="diamond",
                line=dict(width=1.4, color="#f8fafc"),
                opacity=0.94,
            ),
            name="Destino",
            showlegend=True,
            text=[_hover_text(row) for row in corridors.itertuples()],
            hovertemplate="%{text}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lon=corridors["origin_lon"],
            lat=corridors["origin_lat"],
            mode="markers",
            marker=dict(size=4, color="#d1d5db", opacity=0.62),
            name="Origen",
            showlegend=True,
            text=[_hover_text(row) for row in corridors.itertuples()],
            hovertemplate="%{text}<extra></extra>",
        )
    )

    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor="#202936",
        showcountries=True,
        countrycolor="#435162",
        countrywidth=0.45,
        showocean=True,
        oceancolor="#0f1720",
        showlakes=True,
        lakecolor="#0f1720",
        coastlinecolor="#435162",
        bgcolor="#0f1720",
    )
    fig.update_layout(
        height=690,
        margin=dict(l=0, r=0, t=32, b=0),
        paper_bgcolor="#0f1720",
        plot_bgcolor="#0f1720",
        font=dict(color="#e5e7eb"),
        legend=dict(
            title="Región de origen",
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(15, 23, 32, 0.68)",
        ),
    )
    return fig


def curved_arc_points(
    origin_lon: float,
    origin_lat: float,
    destination_lon: float,
    destination_lat: float,
    steps: int = 36,
) -> tuple[list[float], list[float]]:
    lon1 = float(origin_lon)
    lat1 = float(origin_lat)
    lon2 = float(destination_lon)
    lat2 = float(destination_lat)

    delta_lon = lon2 - lon1
    if delta_lon > 180:
        lon2 -= 360
    elif delta_lon < -180:
        lon2 += 360

    dx = lon2 - lon1
    dy = lat2 - lat1
    distance = max(math.hypot(dx, dy), 1.0)
    curve_height = min(max(distance * 0.18, 4.0), 24.0)
    perp_x = -dy / distance
    perp_y = dx / distance

    lons = []
    lats = []
    for step in range(steps):
        t = step / (steps - 1)
        base_lon = lon1 + dx * t
        base_lat = lat1 + dy * t
        offset = math.sin(math.pi * t) * curve_height
        lons.append(_wrap_longitude(base_lon + perp_x * offset))
        lats.append(max(min(base_lat + perp_y * offset, 84), -84))

    return lons, lats


def _scaled_widths(values: pd.Series) -> list[float]:
    stocks = pd.to_numeric(values, errors="coerce").fillna(0).clip(lower=1)
    logged = stocks.map(math.log10)
    min_value = logged.min()
    max_value = logged.max()
    if min_value == max_value:
        return [3.5] * len(stocks)
    return (1.0 + (logged - min_value) / (max_value - min_value) * 7.0).tolist()


def _scaled_marker_sizes(values: pd.Series) -> list[float]:
    stocks = pd.to_numeric(values, errors="coerce").fillna(0).clip(lower=1)
    logged = stocks.map(math.log10)
    min_value = logged.min()
    max_value = logged.max()
    if min_value == max_value:
        return [8.0] * len(stocks)
    return (6.0 + (logged - min_value) / (max_value - min_value) * 9.0).tolist()


def _hover_text(row) -> str:
    rank = getattr(row, "rank", "")
    return (
        f"{row.origin_name} → {row.destination_name}<br>"
        f"Stock migratorio: {row.migrant_stock:,.0f}<br>"
        f"Año: {int(row.year)}<br>"
        f"Ranking: {int(rank) if rank else ''}<br>"
        f"Origen regional: {row.origin_region}<br>"
        f"Destino regional: {row.destination_region}"
    )


def _wrap_longitude(value: float) -> float:
    return ((value + 180) % 360) - 180


def _empty_map(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(height=520, paper_bgcolor="#0f1720", font=dict(color="#e5e7eb"))
    return fig
