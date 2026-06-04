from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZipFile
from io import BytesIO, TextIOWrapper
import csv

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
WORLD_BANK_POPULATION_URL = (
    "https://api.worldbank.org/v2/en/indicator/SP.POP.TOTL?downloadformat=csv"
)


def _read_csv_if_exists(filename: str) -> pd.DataFrame:
    path = PROCESSED_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_population_data() -> pd.DataFrame:
    """Carga población procesada o usa el Banco Mundial como respaldo trazable."""
    population = _read_csv_if_exists("population.csv")
    if not population.empty:
        return population

    return _load_world_bank_population()


def _load_world_bank_population() -> pd.DataFrame:
    try:
        with urlopen(WORLD_BANK_POPULATION_URL, timeout=20) as response:
            payload = response.read()
    except (OSError, URLError):
        return pd.DataFrame()

    with ZipFile(BytesIO(payload)) as archive:
        data_name = next(
            name
            for name in archive.namelist()
            if name.startswith("API_SP.POP.TOTL") and name.endswith(".csv")
        )
        metadata_name = next(
            name
            for name in archive.namelist()
            if name.startswith("Metadata_Country") and name.endswith(".csv")
        )

        with archive.open(metadata_name) as handle:
            metadata_rows = list(csv.DictReader(TextIOWrapper(handle, encoding="utf-8-sig")))
        regions = {
            row["Country Code"]: row.get("Region", "")
            for row in metadata_rows
            if row.get("Country Code") and row.get("Region")
        }

        with archive.open(data_name) as handle:
            text = TextIOWrapper(handle, encoding="utf-8-sig")
            for _ in range(4):
                next(text)
            rows = list(csv.DictReader(text))

    year_columns = [column for column in rows[0] if column.isdigit()]
    output_rows = []
    for row in rows:
        code = row["Country Code"]
        region = regions.get(code, "")
        if not region:
            continue
        for year in year_columns:
            value = row.get(year, "")
            if not value:
                continue
            output_rows.append(
                {
                    "territory_id": code,
                    "territory_name": row["Country Name"],
                    "region": region,
                    "year": int(year),
                    "population": int(float(value)),
                    "source_indicator": "World Bank SP.POP.TOTL",
                }
            )

    return pd.DataFrame(output_rows)


@st.cache_data(show_spinner=False)
def load_connectivity_data() -> pd.DataFrame:
    return _read_csv_if_exists("connectivity.csv")


@st.cache_data(show_spinner=False)
def load_ageing_data() -> pd.DataFrame:
    return _read_csv_if_exists("ageing.csv")


@st.cache_data(show_spinner=False)
def load_country_geometries() -> pd.DataFrame:
    path = PROCESSED_DIR / "territories.geojson"
    if not path.exists():
        return pd.DataFrame()

    try:
        import geopandas as gpd
    except ImportError:
        return pd.DataFrame()

    return gpd.read_file(path)


@st.cache_data(show_spinner=False)
def load_migration_corridors() -> pd.DataFrame:
    corridors = _read_csv_if_exists("migration_corridors.csv")
    if corridors.empty:
        return corridors

    result = corridors.copy()
    result["year"] = pd.to_numeric(result["year"], errors="coerce").astype("Int64")
    result["migrant_stock"] = pd.to_numeric(result["migrant_stock"], errors="coerce")
    return result.dropna(subset=["year", "migrant_stock"])


@st.cache_data(show_spinner=False)
def load_country_centroids() -> pd.DataFrame:
    return _read_csv_if_exists("country_centroids.csv")


@st.cache_data(show_spinner=False)
def load_spain_autonomous_population() -> pd.DataFrame:
    population = _read_csv_if_exists("spain_autonomous_population.csv")
    return _format_spain_territory_id(population)


@st.cache_data(show_spinner=False)
def load_spain_autonomous_geometries() -> pd.DataFrame:
    return _read_geojson_if_exists("spain_autonomous_communities.geojson")


@st.cache_data(show_spinner=False)
def load_spain_railway_history() -> pd.DataFrame:
    return _read_geojson_if_exists("spain_railway_history.geojson")


@st.cache_data(show_spinner=False)
def load_spain_railway_summary() -> pd.DataFrame:
    summary = _read_csv_if_exists("spain_railway_summary.csv")
    return _format_spain_territory_id(summary)


def _read_geojson_if_exists(filename: str) -> pd.DataFrame:
    path = PROCESSED_DIR / filename
    if not path.exists():
        return pd.DataFrame()

    try:
        import geopandas as gpd
    except ImportError:
        return pd.DataFrame()

    return gpd.read_file(path)


def _format_spain_territory_id(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty or "territory_id" not in data.columns:
        return data

    result = data.copy()
    result["territory_id"] = result["territory_id"].astype(str).str.zfill(2)
    return result
