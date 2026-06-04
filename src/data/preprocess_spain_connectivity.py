from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INE_POPULATION_URL = "https://www.ine.es/jaxi/files/_px/csv_bd/t20/e245/p08/l0/02003.csv"
AUTONOMOUS_REGIONS_TOPOJSON_URL = "https://unpkg.com/es-atlas/es/autonomous_regions.json"
RAILWAY_DATASET_URL = (
    "https://dataverse.csuc.cat/api/access/dataset/:persistentId?"
    "persistentId=doi:10.34810/DATA917"
)

RAILWAY_FILES = [
    ("HSR/HighSpeed_lines.zip", "Alta velocidad", True),
    ("IberianGauge/IberianGauge_Lines.zip", "Ancho ibérico", False),
    ("NarrowGauge/NarrowGauge_Lines.zip", "Vía estrecha", False),
]


def build_spain_processed_datasets() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    population = download_and_prepare_population()
    regions = download_and_prepare_regions()
    railways = download_and_prepare_railways()
    railway_summary = calculate_railway_summary_by_region(regions, railways)

    population.to_csv(PROCESSED_DIR / "spain_autonomous_population.csv", index=False)
    regions.to_file(PROCESSED_DIR / "spain_autonomous_communities.geojson", driver="GeoJSON")
    railways.to_file(PROCESSED_DIR / "spain_railway_history.geojson", driver="GeoJSON")
    railway_summary.to_csv(PROCESSED_DIR / "spain_railway_summary.csv", index=False)


def download_and_prepare_population() -> pd.DataFrame:
    raw = _read_remote_bytes(INE_POPULATION_URL)
    data = pd.read_csv(BytesIO(raw), sep="\t", low_memory=False)
    data = data.loc[
        (data["Comunidades y Ciudades Autónomas"].notna())
        & (data["Edad (año a año)"] == "TOTAL EDADES")
        & (data["Españoles/Extranjeros"] == "TOTAL")
        & (data["Sexo"] == "Ambos sexos")
    ].copy()

    data[["territory_id", "territory_name"]] = data[
        "Comunidades y Ciudades Autónomas"
    ].str.extract(r"^(\d{2})\s+(.+)$")
    data["territory_name"] = data["territory_name"].replace(
        {
            "Asturias, Principado de": "Principado de Asturias",
            "Balears, Illes": "Illes Balears",
            "Castilla - La Mancha": "Castilla-La Mancha",
            "Madrid, Comunidad de": "Comunidad de Madrid",
            "Murcia, Región de": "Región de Murcia",
            "Navarra, Comunidad Foral de": "Comunidad Foral de Navarra",
            "Rioja, La": "La Rioja",
        }
    )
    data["population"] = data["Total"].map(_parse_spanish_integer)
    data = data.dropna(subset=["territory_id", "population"])
    data["year"] = data["Periodo"].astype(int)
    data["population"] = data["population"].astype(int)
    data["source_indicator"] = "INE 02003"

    return data[
        ["territory_id", "territory_name", "year", "population", "source_indicator"]
    ].sort_values(["territory_id", "year"])


def download_and_prepare_regions() -> gpd.GeoDataFrame:
    topojson = json.loads(_read_remote_bytes(AUTONOMOUS_REGIONS_TOPOJSON_URL).decode("utf-8"))
    features = _topojson_to_features(topojson, "autonomous_regions")
    regions = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    regions = regions.loc[regions["territory_id"] != "20"].copy()
    regions["territory_name"] = regions["territory_name"].replace(
        {
            "Cataluña/Catalunya": "Cataluña",
            "País Vasco/Euskadi": "País Vasco",
            "Ciudad Autónoma de Ceuta": "Ceuta",
            "Ciudad Autónoma de Melilla": "Melilla",
        }
    )
    regions["geometry"] = regions.geometry.simplify(0.01, preserve_topology=True)
    return regions[["territory_id", "territory_name", "geometry"]].sort_values("territory_id")


def download_and_prepare_railways() -> gpd.GeoDataFrame:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with ZipFile(BytesIO(_read_remote_bytes(RAILWAY_DATASET_URL))) as archive:
            archive.extractall(tmp_path)

        layers = []
        for relative_path, rail_type, is_high_speed in RAILWAY_FILES:
            with ZipFile(tmp_path / relative_path) as archive:
                extract_dir = tmp_path / relative_path.replace("/", "_").replace(".zip", "")
                archive.extractall(extract_dir)
            shp_path = next(extract_dir.rglob("*.shp"))
            layer = gpd.read_file(shp_path, encoding="latin1")
            layer = layer.to_crs("EPSG:3034")
            layer["rail_type"] = rail_type
            layer["is_high_speed"] = is_high_speed
            layer["length_km"] = _first_existing_numeric(layer, ["LENGTH_KM", "LENGTH"])
            layer["line_name"] = layer.get("LINE", "").fillna("").map(_fix_text_encoding)
            layer["section_name"] = layer.get("SECTION", "").fillna("").map(_fix_text_encoding)
            layer["open_year"] = pd.to_numeric(layer.get("OPENING"), errors="coerce")
            layer["close_year"] = pd.to_numeric(layer.get("CLOSURE"), errors="coerce").replace(0, pd.NA)
            layer["reopen_year"] = (
                pd.to_numeric(layer.get("REOPENING"), errors="coerce").replace(0, pd.NA)
            )
            layers.append(layer)

    railways = pd.concat(layers, ignore_index=True)
    railways = gpd.GeoDataFrame(railways, geometry="geometry", crs="EPSG:3034")
    railways["rail_id"] = [f"rail_{idx:05d}" for idx in range(len(railways))]
    railways = railways.to_crs("EPSG:4326")
    railways["geometry"] = railways.geometry.simplify(0.005, preserve_topology=True)
    return railways[
        [
            "rail_id",
            "line_name",
            "section_name",
            "rail_type",
            "is_high_speed",
            "open_year",
            "close_year",
            "reopen_year",
            "length_km",
            "geometry",
        ]
    ]


def calculate_railway_summary_by_region(
    regions: gpd.GeoDataFrame,
    railways: gpd.GeoDataFrame,
) -> pd.DataFrame:
    regions_3034 = regions.to_crs("EPSG:3034")[["territory_id", "territory_name", "geometry"]]
    railways_3034 = railways.to_crs("EPSG:3034")
    min_year = int(railways_3034["open_year"].dropna().min())
    max_year = max(2023, int(railways_3034["open_year"].dropna().max()))
    railway_years = range(min_year, max_year + 1)

    rows = []
    for year in railway_years:
        active = filter_active_railways(railways_3034, year)
        if active.empty:
            for region in regions_3034.itertuples():
                rows.append(_summary_row(region.territory_id, region.territory_name, year, 0, 0, 0))
            continue

        clipped = gpd.overlay(
            active[["is_high_speed", "geometry"]],
            regions_3034,
            how="intersection",
            keep_geom_type=True,
        )
        clipped["km"] = clipped.geometry.length / 1000
        grouped = (
            clipped.groupby(["territory_id", "territory_name", "is_high_speed"], as_index=False)["km"]
            .sum()
            .pivot_table(
                index=["territory_id", "territory_name"],
                columns="is_high_speed",
                values="km",
                fill_value=0,
            )
            .reset_index()
            .rename(columns={False: "rail_km_other", True: "rail_km_high_speed"})
        )

        for column in ["rail_km_other", "rail_km_high_speed"]:
            if column not in grouped.columns:
                grouped[column] = 0.0
        grouped["rail_km_total"] = grouped["rail_km_other"] + grouped["rail_km_high_speed"]
        grouped["rail_year"] = year

        merged = regions_3034[["territory_id", "territory_name"]].merge(
            grouped,
            on=["territory_id", "territory_name"],
            how="left",
        )
        for row in merged.itertuples():
            rows.append(
                _summary_row(
                    row.territory_id,
                    row.territory_name,
                    year,
                    getattr(row, "rail_km_total", 0),
                    getattr(row, "rail_km_high_speed", 0),
                    getattr(row, "rail_km_other", 0),
                )
            )

    return pd.DataFrame(rows)


def filter_active_railways(railways: gpd.GeoDataFrame, rail_year: int) -> gpd.GeoDataFrame:
    open_year = pd.to_numeric(railways["open_year"], errors="coerce")
    close_year = pd.to_numeric(railways["close_year"], errors="coerce")
    reopen_year = pd.to_numeric(railways["reopen_year"], errors="coerce")

    opened = open_year.fillna(9999) <= rail_year
    never_closed = close_year.isna()
    closes_after_year = close_year.fillna(9999) > rail_year
    reopened = reopen_year.fillna(9999) <= rail_year
    return railways.loc[opened & (never_closed | closes_after_year | reopened)].copy()


def _summary_row(
    territory_id: str,
    territory_name: str,
    year: int,
    rail_km_total,
    rail_km_high_speed,
    rail_km_other,
) -> dict:
    return {
        "territory_id": territory_id,
        "territory_name": territory_name,
        "rail_year": int(year),
        "rail_km_total": float(pd.Series([rail_km_total]).fillna(0).iloc[0]),
        "rail_km_high_speed": float(pd.Series([rail_km_high_speed]).fillna(0).iloc[0]),
        "rail_km_other": float(pd.Series([rail_km_other]).fillna(0).iloc[0]),
    }


def _read_remote_bytes(url: str) -> bytes:
    with urlopen(url, timeout=120) as response:
        return response.read()


def _parse_spanish_integer(value) -> int | None:
    if pd.isna(value):
        return None
    text = str(value).strip().replace(".", "")
    if not text:
        return None
    return int(text)


def _first_existing_numeric(data: pd.DataFrame, columns: list[str]) -> pd.Series:
    for column in columns:
        if column in data.columns:
            return pd.to_numeric(data[column], errors="coerce")
    return pd.Series([pd.NA] * len(data), index=data.index)


def _fix_text_encoding(value) -> str:
    text = "" if pd.isna(value) else str(value)
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text


def _topojson_to_features(topojson: dict, object_name: str) -> list[dict]:
    transform = topojson["transform"]
    scale_x, scale_y = transform["scale"]
    translate_x, translate_y = transform["translate"]
    arcs = [_decode_arc(arc, scale_x, scale_y, translate_x, translate_y) for arc in topojson["arcs"]]

    features = []
    for geometry in topojson["objects"][object_name]["geometries"]:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "territory_id": geometry["id"],
                    "territory_name": geometry["properties"]["name"],
                },
                "geometry": _convert_topo_geometry(geometry, arcs),
            }
        )
    return features


def _decode_arc(arc: list[list[int]], scale_x: float, scale_y: float, tx: float, ty: float) -> list:
    x = 0
    y = 0
    coordinates = []
    for dx, dy in arc:
        x += dx
        y += dy
        coordinates.append([x * scale_x + tx, y * scale_y + ty])
    return coordinates


def _convert_topo_geometry(geometry: dict, arcs: list[list]) -> dict:
    if geometry["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": _convert_rings(geometry["arcs"], arcs)}
    if geometry["type"] == "MultiPolygon":
        polygons = [_convert_rings(polygon, arcs) for polygon in geometry["arcs"]]
        polygons = [polygon for polygon in polygons if polygon]
        return {
            "type": "MultiPolygon",
            "coordinates": polygons,
        }
    raise ValueError(f"Tipo TopoJSON no soportado: {geometry['type']}")


def _convert_rings(rings: list[list[int]], arcs: list[list]) -> list:
    return [coordinates for ring in rings if len(coordinates := _stitch_arcs(ring, arcs)) >= 4]


def _stitch_arcs(indices: list[int], arcs: list[list]) -> list:
    coordinates = []
    for index in indices:
        arc = arcs[index] if index >= 0 else list(reversed(arcs[~index]))
        if coordinates:
            coordinates.extend(arc[1:])
        else:
            coordinates.extend(arc)
    return coordinates


if __name__ == "__main__":
    build_spain_processed_datasets()
