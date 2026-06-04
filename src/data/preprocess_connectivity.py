import pandas as pd


def classify_connectivity_quadrants(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data

    result = data.copy()
    distance_col = _first_existing_column(
        result,
        ["distance_to_node_km", "distance_to_city_km", "distance_to_airport_km"],
    )
    if distance_col is None or "percent_change" not in result.columns:
        result["quadrant"] = "Sin datos suficientes"
        return result

    threshold = result[distance_col].median()
    connected = result[distance_col] <= threshold
    grows = result["percent_change"] >= 0

    result["quadrant"] = "Aislado y pierde población"
    result.loc[connected & grows, "quadrant"] = "Conectado y crece"
    result.loc[connected & ~grows, "quadrant"] = "Conectado pero pierde población"
    result.loc[~connected & grows, "quadrant"] = "Aislado pero crece"
    return result


def _first_existing_column(data: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in data.columns), None)
