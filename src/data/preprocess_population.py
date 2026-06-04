import pandas as pd


def prepare_population_change(
    population: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    start = (
        population.loc[population["year"] == start_year, ["territory_id", "population"]]
        .rename(columns={"population": "population_start"})
        .drop_duplicates("territory_id")
    )
    end = (
        population.loc[population["year"] == end_year, ["territory_id", "population"]]
        .rename(columns={"population": "population_end"})
        .drop_duplicates("territory_id")
    )

    change = start.merge(end, on="territory_id", how="inner")
    change["absolute_change"] = change["population_end"] - change["population_start"]
    change["percent_change"] = (
        change["absolute_change"] / change["population_start"].replace({0: pd.NA}) * 100
    )
    years = max(end_year - start_year, 1)
    change["annualized_change"] = (
        ((change["population_end"] / change["population_start"].replace({0: pd.NA})) ** (1 / years))
        - 1
    ) * 100
    return change
