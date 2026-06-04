from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

UNDESA_URL = (
    "https://www.un.org/development/desa/pd/sites/"
    "www.un.org.development.desa.pd/files/"
    "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx"
)
UNDESA_FILENAME = "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx"
NATURAL_EARTH_URL = (
    "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
)
NATURAL_EARTH_FILENAME = "ne_110m_admin_0_countries.zip"

DESTINATION_NAME = "Region, development group, country or area of destination"
DESTINATION_CODE = "Location code of destination"
ORIGIN_NAME = "Region, development group, country or area of origin"
ORIGIN_CODE = "Location code of origin"

M49_OVERRIDES_BY_ADM0 = {
    "NOR": "578",
    "KOS": "383",
}


def build_migration_corridor_datasets() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    undesa_path = _download_if_missing(UNDESA_URL, RAW_DIR / UNDESA_FILENAME)
    natural_earth_path = _download_if_missing(NATURAL_EARTH_URL, RAW_DIR / NATURAL_EARTH_FILENAME)

    centroids = build_country_centroids(natural_earth_path)
    corridors = build_migration_corridors(undesa_path, centroids)

    centroids.to_csv(PROCESSED_DIR / "country_centroids.csv", index=False)
    corridors.to_csv(PROCESSED_DIR / "migration_corridors.csv", index=False)


def build_country_centroids(natural_earth_path: Path) -> pd.DataFrame:
    countries = gpd.read_file(f"zip://{natural_earth_path}")
    points = countries.geometry.representative_point()
    result = pd.DataFrame(
        {
            "country_code": countries.apply(_m49_code_from_natural_earth, axis=1),
            "iso_a3": countries["ADM0_A3"].replace("-99", pd.NA),
            "country_name": countries["ADMIN"],
            "region": countries["REGION_UN"].fillna("Sin región"),
            "subregion": countries["SUBREGION"].fillna("Sin subregión"),
            "lon": points.x,
            "lat": points.y,
        }
    )
    result = result.dropna(subset=["country_code", "lat", "lon"])
    return result.drop_duplicates("country_code").sort_values("country_name")


def build_migration_corridors(undesa_path: Path, centroids: pd.DataFrame) -> pd.DataFrame:
    data = pd.read_excel(undesa_path, sheet_name="Table 1", header=10)
    year_columns = [column for column in data.columns if isinstance(column, int)]
    data = data[
        [
            DESTINATION_NAME,
            DESTINATION_CODE,
            ORIGIN_NAME,
            ORIGIN_CODE,
            *year_columns,
        ]
    ].copy()
    data[DESTINATION_CODE] = data[DESTINATION_CODE].map(_format_m49_code)
    data[ORIGIN_CODE] = data[ORIGIN_CODE].map(_format_m49_code)
    data[DESTINATION_NAME] = data[DESTINATION_NAME].map(_clean_country_name)
    data[ORIGIN_NAME] = data[ORIGIN_NAME].map(_clean_country_name)

    corridors = data.melt(
        id_vars=[DESTINATION_NAME, DESTINATION_CODE, ORIGIN_NAME, ORIGIN_CODE],
        value_vars=year_columns,
        var_name="year",
        value_name="migrant_stock",
    )
    corridors = corridors.rename(
        columns={
            DESTINATION_NAME: "destination_name",
            DESTINATION_CODE: "destination_code",
            ORIGIN_NAME: "origin_name",
            ORIGIN_CODE: "origin_code",
        }
    )
    corridors["year"] = corridors["year"].astype(int)
    corridors["migrant_stock"] = pd.to_numeric(corridors["migrant_stock"], errors="coerce")
    corridors = corridors.dropna(subset=["origin_code", "destination_code", "migrant_stock"])
    corridors = corridors.loc[
        (corridors["migrant_stock"] > 0)
        & (corridors["origin_code"] != corridors["destination_code"])
    ].copy()

    origin_centroids = centroids.rename(
        columns={
            "country_code": "origin_code",
            "region": "origin_region",
            "subregion": "origin_subregion",
            "lat": "origin_lat",
            "lon": "origin_lon",
        }
    )[["origin_code", "origin_region", "origin_subregion", "origin_lat", "origin_lon"]]
    destination_centroids = centroids.rename(
        columns={
            "country_code": "destination_code",
            "region": "destination_region",
            "subregion": "destination_subregion",
            "lat": "destination_lat",
            "lon": "destination_lon",
        }
    )[
        [
            "destination_code",
            "destination_region",
            "destination_subregion",
            "destination_lat",
            "destination_lon",
        ]
    ]

    corridors = corridors.merge(origin_centroids, on="origin_code", how="inner")
    corridors = corridors.merge(destination_centroids, on="destination_code", how="inner")
    corridors["migrant_stock"] = corridors["migrant_stock"].round().astype("int64")
    return corridors[
        [
            "year",
            "origin_code",
            "origin_name",
            "origin_region",
            "origin_subregion",
            "destination_code",
            "destination_name",
            "destination_region",
            "destination_subregion",
            "migrant_stock",
            "origin_lat",
            "origin_lon",
            "destination_lat",
            "destination_lon",
        ]
    ].sort_values(["year", "migrant_stock"], ascending=[True, False])


def _download_if_missing(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    urlretrieve(url, path)
    return path


def _m49_code_from_natural_earth(row) -> str | None:
    override = M49_OVERRIDES_BY_ADM0.get(str(row.get("ADM0_A3", "")))
    if override:
        return override
    for column in ["UN_A3", "ISO_N3", "ISO_N3_EH"]:
        code = _format_m49_code(row.get(column))
        if code:
            return code
    return None


def _format_m49_code(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.startswith("-"):
        return None
    try:
        return str(int(float(text))).zfill(3)
    except ValueError:
        return None


def _clean_country_name(value) -> str:
    return "" if pd.isna(value) else str(value).replace("*", "").strip()


if __name__ == "__main__":
    build_migration_corridor_datasets()
