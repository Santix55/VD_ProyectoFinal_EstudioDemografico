import streamlit as st

from src.charts.migration_charts import (
    plot_corridor_ranking,
    plot_region_heatmap,
    plot_region_sankey,
)
from src.data.load_data import load_migration_corridors
from src.maps.migration_arcs import build_migration_arc_map


st.title("Mapa 2: corredores migratorios internacionales")
st.caption(
    "Pregunta guía: cuáles son los principales corredores migratorios globales "
    "medidos como stock migratorio origen-destino."
)

corridors = load_migration_corridors()

if corridors.empty:
    st.warning(
        "Faltan datos procesados para el mapa de corredores migratorios. "
        "Ejecuta `python -m src.data.preprocess_migration_corridors` para generar "
        "`migration_corridors.csv` y `country_centroids.csv`."
    )
    st.stop()

required_columns = {
    "year",
    "origin_name",
    "origin_region",
    "destination_name",
    "destination_region",
    "migrant_stock",
    "origin_lat",
    "origin_lon",
    "destination_lat",
    "destination_lon",
}
missing_columns = sorted(required_columns - set(corridors.columns))
if missing_columns:
    st.error(
        "Faltan columnas necesarias en `migration_corridors.csv`: "
        + ", ".join(missing_columns)
    )
    st.stop()

years = sorted(corridors["year"].dropna().astype(int).unique())
origin_regions = sorted(corridors["origin_region"].dropna().unique())
destination_regions = sorted(corridors["destination_region"].dropna().unique())

with st.sidebar:
    st.header("Filtros")
    selected_year = st.selectbox("Año", years, index=len(years) - 1)
    top_n = st.slider("Top-N corredores", 10, 100, 50, 5)
    selected_origin_region = st.selectbox("Región de origen", ["Todas"] + origin_regions)
    selected_destination_region = st.selectbox(
        "Región de destino",
        ["Todas"] + destination_regions,
    )

filtered = corridors.loc[corridors["year"].astype(int) == selected_year].copy()
if selected_origin_region != "Todas":
    filtered = filtered.loc[filtered["origin_region"] == selected_origin_region]
if selected_destination_region != "Todas":
    filtered = filtered.loc[filtered["destination_region"] == selected_destination_region]

filtered = filtered.sort_values("migrant_stock", ascending=False).head(top_n).copy()
filtered["rank"] = range(1, len(filtered) + 1)

st.markdown(
    "Esta vista representa una red migratoria internacional mediante arcos entre "
    "países de origen y destino. El grosor indica el volumen del corredor y el "
    "color identifica la región de origen. Los marcadores destacados señalan el "
    "destino del corredor, de modo que la lectura sea origen → destino."
)

if filtered.empty:
    st.info("No hay corredores migratorios que cumplan los filtros seleccionados.")
    st.stop()

total_stock = filtered["migrant_stock"].sum()
top_corridor = filtered.iloc[0]
region_count = filtered["origin_region"].nunique()

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
kpi_1.metric("Corredores visibles", f"{len(filtered):,}")
kpi_2.metric("Stock representado", f"{total_stock:,.0f}")
kpi_3.metric("Regiones de origen", f"{region_count}")
kpi_4.metric(
    "Principal corredor",
    f"{top_corridor['origin_name']} → {top_corridor['destination_name']}",
    f"{top_corridor['migrant_stock']:,.0f}",
)

left, right = st.columns([1.65, 0.9])

with left:
    st.subheader("Red migratoria internacional")
    st.plotly_chart(build_migration_arc_map(filtered), width="stretch")
    st.caption(
        "Los países se muestran como contexto cartográfico neutro. No se usa una "
        "coropleta continua porque el foco visual está en los corredores."
    )

with right:
    st.subheader("Top N corredores")
    st.plotly_chart(plot_corridor_ranking(filtered), width="stretch")

st.subheader("Agregación regional")
chart_left, chart_right = st.columns(2)
with chart_left:
    st.plotly_chart(plot_region_sankey(filtered), width="stretch")
with chart_right:
    st.plotly_chart(plot_region_heatmap(filtered), width="stretch")

st.subheader("Detalle de corredores")
detail = filtered[
    [
        "rank",
        "origin_name",
        "destination_name",
        "origin_region",
        "destination_region",
        "migrant_stock",
        "year",
    ]
].copy()
st.dataframe(
    detail,
    width="stretch",
    hide_index=True,
    column_config={
        "rank": st.column_config.NumberColumn("Ranking", format="%d"),
        "origin_name": "Origen",
        "destination_name": "Destino",
        "origin_region": "Región de origen",
        "destination_region": "Región de destino",
        "migrant_stock": st.column_config.NumberColumn(
            "Stock migratorio origen-destino",
            format="%d",
        ),
        "year": st.column_config.NumberColumn("Año", format="%d"),
    },
)

st.info(
    "Nota metodológica: los datos representan stock migratorio bilateral en un año "
    "determinado. No deben interpretarse como flujos migratorios anuales."
)
