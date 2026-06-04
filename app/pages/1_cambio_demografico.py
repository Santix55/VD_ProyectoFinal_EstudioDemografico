import streamlit as st
import app.bootstrap

from src.charts.demographic_charts import (
    METRIC_LABELS,
    plot_change_ranking,
    plot_population_trend,
)
from src.data.load_data import load_population_data
from src.data.preprocess_population import prepare_population_change
from src.maps.choropleth import build_population_choropleth


st.title("Cambio demográfico global")
st.caption("Pregunta guía: dónde crece y dónde disminuye la población.")

population = load_population_data()

if population.empty:
    st.warning("No se ha podido cargar población. Revisa `data/processed/population.csv`.")
    st.stop()

required_columns = {"territory_id", "territory_name", "year", "population"}
missing_columns = sorted(required_columns - set(population.columns))
if missing_columns:
    st.error(f"Faltan columnas necesarias en population.csv: {', '.join(missing_columns)}")
    st.stop()

years = sorted(population["year"].dropna().unique())
if len(years) < 2:
    st.warning("El dataset de población necesita al menos dos años.")
    st.stop()

with st.sidebar:
    st.header("Filtros")
    start_year = st.selectbox("Año inicial", years, index=0)
    later_years = [year for year in years if year > start_year]
    end_year = st.selectbox("Año final", later_years, index=len(later_years) - 1)
    metric = st.selectbox(
        "Métrica del mapa",
        ["percent_change", "absolute_change", "population_end"],
        format_func=lambda value: METRIC_LABELS.get(value, value),
    )
    if "region" in population.columns:
        region_options = ["Todas"] + sorted(population["region"].dropna().unique().tolist())
    else:
        region_options = ["Todas"]
    selected_region = st.selectbox("Región", region_options)

filtered_population = population.copy()
if selected_region != "Todas" and "region" in filtered_population.columns:
    filtered_population = filtered_population.loc[filtered_population["region"] == selected_region]

change = prepare_population_change(
    filtered_population,
    start_year=start_year,
    end_year=end_year,
)

names = filtered_population[["territory_id", "territory_name"]].drop_duplicates()
change = change.merge(names, on="territory_id", how="left")

st.markdown(
    "Esta vista compara dos años y muestra qué territorios ganan población, "
    "cuáles se estancan y cuáles pierden peso demográfico. Si no hay datos "
    "procesados propios, se intenta cargar el indicador oficial de población "
    "total del Banco Mundial."
)

total_start = change["population_start"].sum()
total_end = change["population_end"].sum()
total_change = total_end - total_start
mean_percent_change = change["percent_change"].mean()

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
kpi_1.metric("Territorios", f"{len(change):,}")
kpi_2.metric("Población inicial", f"{total_start:,.0f}")
kpi_3.metric("Población final", f"{total_end:,.0f}", f"{total_change:,.0f}")
kpi_4.metric("Cambio medio", f"{mean_percent_change:.2f}%")

left, right = st.columns([1.35, 1])

with left:
    st.subheader("Mapa de cambio poblacional")
    fig_map = build_population_choropleth(
        change,
        metric,
        title=f"{METRIC_LABELS.get(metric, metric)} ({start_year}-{end_year})",
    )
    st.plotly_chart(fig_map, width="stretch")
    st.caption(
        "Colores verdes indican crecimiento y rojos indican pérdida cuando la métrica es de cambio."
    )

with right:
    st.subheader("Ranking de territorios")
    ranking_mode = st.radio(
        "Tipo de ranking",
        ["Mayores pérdidas", "Mayores crecimientos"],
        horizontal=True,
    )
    st.plotly_chart(
        plot_change_ranking(
            change,
            "percent_change",
            ranking_mode,
            ascending=ranking_mode == "Mayores pérdidas",
        ),
        width="stretch",
    )
    st.caption("Ranking calculado con el cambio porcentual entre los años seleccionados.")

st.subheader("Evolución temporal")
territories = sorted(filtered_population["territory_name"].dropna().unique())
default_index = territories.index("Spain") if "Spain" in territories else 0
selected_territory = st.selectbox(
    "Territorio para la serie temporal",
    territories,
    index=default_index,
)
st.plotly_chart(
    plot_population_trend(filtered_population, selected_territory),
    width="stretch",
)
