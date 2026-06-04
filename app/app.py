from pathlib import Path
import subprocess
import sys

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx


def relaunch_with_streamlit_if_needed() -> None:
    """Permite arrancar la app con el botón Run del IDE."""
    if get_script_run_ctx(suppress_warning=True) is not None:
        return

    app_path = Path(__file__).resolve()
    command = [sys.executable, "-m", "streamlit", "run", str(app_path), *sys.argv[1:]]
    raise SystemExit(subprocess.call(command))


relaunch_with_streamlit_if_needed()


st.set_page_config(
    page_title="Estudio demográfico y migratorio",
    layout="wide",
)

st.title("Estudio demográfico sobre población y corredores migratorios")

st.write(
    "Este trabajo analiza el ascenso y descenso de la población a escala global "
    "y lo relaciona con los principales corredores migratorios internacionales. "
    "El objetivo es observar qué países crecen, cuáles pierden población o se "
    "estancan, y cómo los movimientos acumulados de población conectan unas "
    "regiones del mundo con otras."
)

st.info(
    "La aplicación se centra en dos mapas: una coropleta de cambio poblacional "
    "por país y un mapa de corredores migratorios origen-destino."
)

st.markdown("### Preguntas del trabajo")
st.write(
    "- ¿Qué países han ganado o perdido población entre dos años seleccionados?\n"
    "- ¿Dónde se concentran los mayores cambios absolutos y porcentuales?\n"
    "- ¿Qué corredores migratorios internacionales tienen más peso y qué regiones conectan?"
)

st.markdown("### Recorrido")
st.page_link(
    "pages/1_cambio_demografico.py",
    label="Cambio demográfico",
    help="Mapa de coropletas, ranking y serie temporal de población.",
)
st.page_link(
    "pages/2_migracion.py",
    label="Corredores migratorios",
    help="Mapa de arcos, ranking y agregación regional del stock migratorio.",
)

st.markdown("### Datasets utilizados")
st.write(
    "- **Banco Mundial**: población total anual por país. El dataset se transforma "
    "a formato largo con país, región, año y población para calcular cambios "
    "absolutos y porcentuales.\n"
    "- **UN DESA International Migrant Stock 2024**: stock migratorio bilateral "
    "por país de origen, país de destino y año.\n"
    "- **Natural Earth**: cartografía global usada para obtener centroides "
    "representativos de los países y poder dibujar los arcos migratorios."
)

st.markdown("### Fuentes y metodología")
st.write(
    "El primer mapa es una coropleta por país: compara la población entre un "
    "año inicial y un año final, y permite alternar entre población final, "
    "cambio absoluto y cambio porcentual. El segundo mapa representa "
    "corredores origen-destino mediante arcos entre centroides; el grosor del "
    "arco es proporcional al stock migratorio y el color identifica la región "
    "de origen."
)
st.caption(
    "Nota metodológica: los datos de migración son stocks acumulados en años "
    "concretos, no flujos migratorios anuales. Por tanto, el análisis es "
    "descriptivo y no establece causalidad."
)
