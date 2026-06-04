# Fuentes de datos

Este archivo documenta las fuentes usadas por la aplicación. Cada dataset debe descargarse desde una fuente fiable y quedar transformado en `data/processed/` antes de usarse como fuente principal de la app.

## Resumen de ficheros esperados

| Fichero procesado | Contenido | Fuente |
| --- | --- | --- |
| `data/processed/population.csv` | Población por territorio y año | Banco Mundial |
| `data/processed/territories.geojson` | Geometrías de países o regiones | Natural Earth |
| `data/processed/migration_corridors.csv` | Stock migratorio bilateral por origen, destino y año | UN DESA International Migrant Stock 2024 |
| `data/processed/country_centroids.csv` | Centroides/representative points de países para arcos migratorios | Natural Earth |

## Fuentes

### Banco Mundial - Population, total

- Uso en la app: población total anual por país para `data/processed/population.csv`.
- Página oficial del indicador: https://data.worldbank.org/indicator/SP.POP.TOTL
- API/descarga: https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?downloadformat=csv
- Descarga usada para el CSV procesado: https://api.worldbank.org/v2/en/indicator/SP.POP.TOTL?downloadformat=csv
- Fecha de descarga: 2026-05-30.
- Última actualización indicada por el CSV del Banco Mundial: 2026-04-08.
- Cobertura usada: países y economías con región asignada por el Banco Mundial; se excluyen agregados regionales sin región.
- Años disponibles en `population.csv`: 1960-2024.
- Variables usadas: país, código ISO alfa-3, región, año y población total.
- Preprocesamiento aplicado: conversión de la tabla ancha original a formato largo con columnas `territory_id`, `territory_name`, `region`, `year`, `population` y `source_indicator`.
- Fiabilidad: el Banco Mundial publica indicadores internacionales ampliamente usados en trabajos académicos y técnicos.
- Limitaciones: escala principalmente nacional; no resuelve análisis regional o municipal.

### Natural Earth - Admin 0 Countries

- Uso en la app: geometrías globales ligeras para calcular `country_centroids.csv` y, opcionalmente, `territories.geojson`.
- Página oficial: https://www.naturalearthdata.com/downloads/
- Página de descarga recomendada: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/
- Variables previstas: geometría, nombre de país, códigos ISO y atributos cartográficos.
- Fiabilidad: Natural Earth es una fuente cartográfica pública muy usada para mapas globales de pequeña escala.
- Limitaciones: no es adecuada para análisis administrativos detallados o límites de alta precisión.

### UN DESA - International Migrant Stock 2024

- Uso en la app: corredores migratorios internacionales para `data/processed/migration_corridors.csv`.
- Página oficial: https://www.un.org/development/desa/pd/content/international-migrant-stock
- Descarga usada: https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx
- Cobertura usada: stock migratorio bilateral por país o área de destino y origen para 1990, 1995, 2000, 2005, 2010, 2015, 2020 y 2024.
- Variables usadas: país de origen, país de destino, códigos M49, año y stock migratorio total de ambos sexos.
- Preprocesamiento aplicado: selección de la tabla `Table 1`, transformación de años a formato largo, cruce con centroides de Natural Earth y exclusión de agregados sin geometría de país.
- Licencia indicada por Naciones Unidas: Creative Commons CC BY 3.0 IGO.
- Limitaciones: representa stocks migratorios origen-destino en años concretos; no debe interpretarse como flujos migratorios anuales.

## Reglas de uso

- No usar datos sin enlace de descarga o página oficial identificable.
- Registrar fecha de descarga, licencia, variables usadas y transformaciones aplicadas cuando se incorpore cada dataset real.
- Guardar en `data/processed/` solo datos ya limpios y listos para la app.
