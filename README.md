Aplicación de visualización de datos en Streamlit para explorar el cambio poblacional y la migración

## Ejecución local

```bash
streamlit run app/app.py
```

## Estructura

```text
app/                 Aplicación Streamlit y páginas
src/                 Lógica reutilizable de datos, mapas, gráficas e índice
data/raw/            Datos originales
data/processed/      Datos limpios listos para la app
data/external/       Cartografía y fuentes externas
fuentes.md           Fuentes de datos y enlaces de descarga
docs/                Metodología y limitaciones
outputs/             Figuras, mapas y tablas exportadas
notebooks/           Exploración y preprocesamiento
```

## Datos esperados

El fichero `data/processed/population.csv` ya contiene población total por país
del Banco Mundial hasta 2024. La página 2 usa stock migratorio bilateral de
UN DESA y centroides derivados de Natural Earth.

Para generar los corredores migratorios globales:

```bash
python -m src.data.preprocess_migration_corridors
```

Para regenerar los datos españoles:

```bash
python -m src.data.preprocess_spain_connectivity
```

Ten en cuenta que para ejecutar el programa de pre-procesamiento es necesario tener
instaladas las librerías presentes en el fichero `pre-process_requirements.txt`
