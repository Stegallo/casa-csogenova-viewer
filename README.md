# Casa Genova Listing Explorer

A focused Streamlit application that connects to the MotherDuck view `test_cso_g.casa.vw_a_cgenova` and surfaces real-estate listings with interactive summaries, filters, and downloadable results. The dashboard highlights:

- Aggregate metrics: number of listings, average price, and average price per square meter.
- Filter controls: room count, price range, and size range.
- A listings table with clickable URLs to open the original source.

## Requirements

- Python 3.14 or newer
- A MotherDuck account plus an API token (generate one in the MotherDuck UI under **Settings → Tokens**)

## Setup

1. Install the dependencies with your preferred tool. Using [uv](https://github.com/astral-sh/uv):
   ```bash
   uv sync
   ```
   or, if you prefer pip:
   ```bash
   pip install -e .
   ```
2. Export your MotherDuck token so DuckDB can authenticate:
   ```bash
   export MOTHERDUCK_TOKEN="duckdb_secret_token"
   ```
3. (Optional) Set a default database name so the sidebar pre-fills automatically:
   ```bash
   export MOTHERDUCK_DATABASE="analytics"
   ```

## Running the app

Start Streamlit and point it at `main.py`:

```bash
uv run streamlit run main.py
# or
streamlit run main.py
```

Provide the MotherDuck database name (plain name or `md:` URI) in the sidebar and paste a MotherDuck token, then the app will automatically fetch the Casa Genova listings. Use the filters to slice the dataset and click the download button to export the filtered view as CSV.
