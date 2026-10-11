# CIVISCOPE initial audit — 2026-09-28

## Deep audit decision — 2026-09-29

Focused executable-source review confirms the following additional defects: the intelligence report hard-codes VALIDATED/READY; legacy station risk merges city pollutant trends; station summary averages different pollutant scales; collectors retry indefinitely and can expose API-key URLs through exception strings; several scripts execute network requests or overwrite outputs on import. The production station no-city-copy policy is correct and will be retained. The existing Streamlit loaders and presentation separation are useful, but page navigation, filters, maps, quality reporting and scientific eligibility need implementation.

Implementation will reuse the existing production module locations, consolidate duplicate entry points, and retain original source in `data/archive/pre_upgrade_source_20260929.zip`. Shared configuration/observation validation are missing and warrant a small `src/core` package. Historical/raw files remain immutable inputs; new validated observations and versioned run outputs will preserve prior generated products.

Authoritative CPCB source checked: https://cpcb.nic.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvQWJvdXRfQVFJLnBkZg%3D%3D . It specifies concentration units and averaging periods. The OGD catalog describes AQI values, while local records expose no unit or averaging metadata. The values' concentration/sub-index meaning therefore remains unverified. Do not automatically convert them to concentrations or run them through AQI interpolation. Display source-reported values and provenance; return unavailable derived AQI when metadata is insufficient. Above open-ended severe breakpoints, do not invent an upper concentration for interpolation.

Fix order: observation validation/provenance; centralized AQI eligibility; chronological station-specific forecasting and validation; risk/warnings; atomic pipeline/report generation; dashboard; offline and UI verification; final documentation. All existing raw/history data and read-only exploratory inspection tools should remain unchanged unless a specific defect requires a targeted edit.

Status: baseline inspection completed; deep audit and implementation remain in progress. This is not a claim that the full master specification has been validated. Existing application code and datasets were preserved.

## Architecture and current functionality

The project is a Python script pipeline exchanging CSV and JSON files. `src/pipeline/run_pipeline.py` invokes collection, cleaning, historical construction, analysis, production forecast, validation, AQI, risk and warning scripts. `src/dashboard/app.py` reads saved outputs using Streamlit. A second dashboard exists at `src/dashboard.py`. Station intelligence and the JSON intelligence report have separate scripts under `src/production/intelligence`; they are absent from the orchestrator's step list.

Existing functionality includes government API collection, snapshot storage, cleaning, historical aggregation, trends, city pollutant forecasting, model comparison, forecast validation, AQI calculations, station summaries, risk and warning outputs, and dashboard presentation. These should be inspected and repaired in place, rather than replaced wholesale.

## Data inventory

- 11 historical JSON snapshots and one raw JSON file are present.
- `delhi_historical.csv`: 3,020 rows, 45 stations, 11 collection timestamps from 2026-08-17 19:44:18 through 2026-08-19 17:01:18. These saved observations are stale relative to the audit date.
- Historical schema: country, state, city, station, last_update, latitude, longitude, pollutant_id, min_value, max_value, avg_value, collection_time.
- Zero duplicate station/pollutant/collection-time keys; 1,310 rows repeat a station/pollutant/last-update key. Repeated retrieval is not independent measurement history. Conflicting values within these keys still need investigation.
- Clean snapshot: 273 rows. City AQI, production forecast, validation, risk analysis and early-warning files each contain seven rows. Station intelligence contains 45 rows; several older station products contain 44.
- Historical and clean CSV schemas contain neither unit nor averaging-period metadata. Source metadata and transformation lineage remain to be verified; CO units cannot be established from these files alone.

## Findings and status

| Component | Status | Evidence and implication |
| --- | --- | --- |
| Dashboard baseline | PARTIALLY WORKING | Streamlit AppTest completed with zero exceptions and 16 metrics. Browser appearance, navigation, filters, mobile layout and failure states are not yet verified. |
| Python syntax | WORKING within this check | All 34 Python source/test files parsed successfully. This does not establish import or runtime correctness. |
| Reproducible environment | BROKEN | `requirements.txt` is empty. Existing environment has pandas, numpy, Streamlit, Plotly, dotenv and requests; pytest, sklearn and statsmodels were not found. Missing optional packages are not automatically application defects. |
| Automated testing | PARTIALLY WORKING | Only `tests/test_api.py` was found. It performs a network request at import time and has no assertion-based regression coverage. It was not executed. |
| Pipeline orchestration | PARTIALLY WORKING | The step called Pollution Trend Analysis runs `src/analyze_data.py`, which prints a summary rather than creating the required trend output. Output verification checks existence, so old files can conceal missing work. `main()` does not act on the verification return value. |
| AQI consistency | BROKEN | Direct calls with PM2.5 = 30.5 return 51.82 from production city AQI and 50.5 from production station AQI. Multiple breakpoint/calculation implementations exist. Authoritative boundary and rounding rules still need verification before selecting a replacement. |
| AQI scientific validity | NEEDS VALIDATION | Unit and averaging-period provenance are missing from processed observations. Several modules implement their own severe-range behavior. No official AQI claim is justified by this audit. |
| Forecasting | SCIENTIFICALLY QUESTIONABLE | Production forecasting aggregates by collection timestamp and pollutant and uses a hard-coded model map. Eleven irregular retrieval times, including repeated source observations, do not establish reliable hourly forecast skill. |
| Forecast validation | SCIENTIFICALLY QUESTIONABLE | `validate_forecast.py` accepts the first observation at or after forecast_time without an upper tolerance. Its fallback uses absolute time distance within two hours, permitting earlier observations. The seven saved validation rows contain zero actual_time values before forecast_time; that does not rule out target-time or training-overlap problems. |
| Station intelligence | PARTIALLY WORKING | Production module uses station observations and explicitly leaves station forecasts/risk/warnings unavailable rather than copying city outputs. Preserve this safeguard. Genuine station forecast validation remains missing in this path. |
| Risk and warnings | NEEDS VALIDATION | Existing analytical outputs and scripts are present. Formula calibration, evidence, missing-data behavior, stale-data handling and legacy/production consistency require further testing. |
| Documentation | PARTIALLY WORKING | README describes an early broad urban-platform vision; installation, current analytical methodology and validation evidence are not documented adequately. docs/config/notebooks contained no files at baseline. |

## Duplication and preservation

AQI logic exists in root and production modules and in station intelligence. Forecast, station, risk and dashboard variants also coexist, including station backup scripts. Similar names alone do not prove safe deletion. Trace callers and output consumers before consolidation. Preserve all raw/history data, existing user edits, backups until dependencies are understood, and the station no-city-copy safeguard.

## Tests actually performed

1. Parsed all 34 Python files using `ast.parse`: no syntax errors.
2. Checked module availability without installing packages.
3. Inspected CSV schemas and counted historical keys/timestamps.
4. Ran Streamlit AppTest against `src/dashboard/app.py`: zero exceptions, 16 metrics.
5. Called guarded production city and station AQI functions on the same input: reproduced inconsistency above.
6. Compared saved validation actual_time and forecast_time: zero earlier actual times among seven rows.

No collection, historical rewrite, full pipeline execution, dependency installation or application-code changes were performed. API availability, official CPCB methodology, secret handling throughout the repository, full import safety, browser rendering and end-to-end output compatibility remain unverified. `.env` contents were not read or printed.

## Implementation sequence after the remaining audit

1. Complete focused reads of ingestion, cleaning, model comparison, risk/warning and both dashboard paths; verify CPCB methodology and source units against primary sources. Produce a definitive component/dependency map.
2. Add offline regression tests for reproduced AQI discrepancies, missing/invalid data, forecast target matching, station separation and orchestration failure propagation. Populate dependencies from actual imports and tested versions.
3. Consolidate the existing AQI implementation with documented unit/period eligibility and consistent edge handling. Preserve unavailable results when provenance is insufficient.
4. Separate retrieval time from observation time, resolve duplicate source observations, and validate forecast horizons with chronological backtesting. Only enable station forecasts when sufficient independent history exists.
5. Repair pipeline stages and require fresh, schema-valid outputs. Include station intelligence/report generation and explicit failure propagation.
6. Validate risk/warning evidence and freshness; then improve existing dashboard pages, filters, quality reporting and methodology presentation. Check desktop/mobile visuals and empty/error states.

Expected modification candidates: `requirements.txt`, `README.md`, existing AQI modules, `src/validate_forecast.py`, `src/production/_forecast.py`, `src/pipeline/run_pipeline.py`, historical builder, station intelligence and dashboard. Exact scope awaits dependency review.

Expected additions: offline regression tests and architecture, methodology, source-provenance and model-validation documents. Do not introduce parallel implementations of already-existing features.

Existing dashboard launch command from the project root: `.\.venv\Scripts\python.exe -m streamlit run src/dashboard/app.py`. This displays saved data; it does not make that data current or validated.
