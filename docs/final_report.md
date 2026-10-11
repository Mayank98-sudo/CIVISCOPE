# CIVISCOPE validation and handoff report

Validated on October 9, 2026. The dashboard now includes fresh official CPCB concentrations and 47 eligible station AQI estimates. It is ready for a demonstration of these retrieved observations and calculated estimates. It is **not yet an automated operational AQI/forecast service**: the OGD API refuses connections, CPCB collection used the visible portal after a user-completed CAPTCHA, and independently available history remains insufficient for forecasts. Estimates are CIVISCOPE calculations, not official published AQI.

## What existed and was preserved

The project already contained government-source JSON retrieval, cleaning, historical CSV construction, trend and model experiments, production AQI/risk/warning scripts, station intelligence and a Streamlit dashboard. The existing station policy of withholding city-derived station forecasts was correct and retained. All original raw/historical snapshots and prior flat analytical products remain intact. Original source and README are recoverable from `data/archive/pre_upgrade_source_20260929.zip`. Existing unrelated workspace files were not changed.

## Defects corrected

- Conflicting city/station AQI implementations and unsupported severe-range extrapolation were consolidated into one engine with diagnostics.
- Missing source units, averaging periods and value-kind verification now prevent automatic AQI conversion, including CO.
- Repeated retrievals no longer count as independent measurements; conflicting values/metadata are quarantined.
- Retrieval time and source observation time are distinct; observations published after a forecast origin cannot enter its training history.
- Hard-coded pollutant model choices and unsafe before-target validation fallback were replaced with chronological selection/evaluation and exact future-target matching.
- Station risk now uses station observations and station trends. Missing/stale results no longer silently become low risk or stable conditions.
- Indefinite API retries, credential-bearing exception output and import-time network execution were removed from supported collection paths.
- The pipeline now publishes a complete versioned run with input/output checksums and atomic promotion. Stale files cannot masquerade as newly computed outputs.
- Dashboard readiness labels derive from actual availability instead of unconditional READY/VALIDATED constants.
- Expired predictions are withheld and correctly labelled. Manifest loading requires checksums for every required output.
- Dashboard navigation, maps, filters, quality reporting, explanatory methodology and mobile layout were implemented in the existing application.
- Visual QA corrected a clipped header, low-contrast sidebar button and mobile sidebar overlay. Marker-click detail selection was unreliable in this renderer; an explicit map station selector provides the verified detail interaction, and help text reflects it.

## New capabilities and architecture

Shared source configuration and observation validation live under `src/core`. Canonical analytics remain in the existing production module locations. The pipeline writes observations, trends, AQI diagnostics, station forecasts, validation, station summaries, risk, warnings, coverage, quality and report files under `data/processed/runs`. A complete `latest_run.json` manifest points the read-only dashboard at the successful run. Legacy analytic entry points delegate to the same pipeline; read-only exploration scripts are preserved.

The dashboard has Overview, Live AQI, Stations, Forecast, Trends, Risk & Warnings, Spatial Intelligence, Data Quality, Methodology and About pages. Station, pollutant, date and horizon controls are implemented. Maps show actual monitoring locations and source values, with missing values disclosed. No estimated spatial surface is presented as measurement.

## Verification evidence

- Offline unittest suite: **55 tests run; 54 passed, 1 optional live API test skipped**. Seven CPCB tests cover units, interval completeness, future exclusion, duplicates and AQI averaging coverage. Three monitoring tests verify blocked-source retention, complete-run publication and credential-free failure handling.
- All ten pages and station/pollutant/horizon/daily-aggregation filters passed Streamlit AppTest checks.
- Missing and corrupt runs display unavailable states without uncaught application errors.
- Integrity tests reject omitted checksums and escaped output paths.
- The complete pipeline successfully published `20261009T184421_bea15970`, including the new CPCB observations.
- Python syntax check: 44 source/test files parsed successfully; 35 non-application modules imported without network or output-publication side effects.
- Source credential-pattern scan found no hard-coded credentials. `.env` remains ignored and its contents were not printed.
- The local Streamlit server started successfully and its health endpoint returned `ok`.
- Isolated Chrome browser QA passed all ten pages, map rendering/zoom input, explicit map station detail selection and a 390px mobile viewport with no horizontal overflow and a collapsed initial sidebar. No browser JavaScript errors were reported. Actual results and screenshots are under `docs/qa`; use `browser_results.json` as the browser check record.

Tests use generated fixtures only in test code and temporary directories. They establish software behavior, not measurement accuracy or empirical Delhi forecast skill. The external API refresh failed after three attempts; no partial snapshot was saved. Follow-up diagnostics establish a refused HTTPS connection before authentication, while the government website remained reachable; the website resource route timed out. This does not distinguish provider outage from local routing or network policy.

Follow-up completion work added `src/readiness.py`, five diagnostic tests, a Data Quality readiness panel and `docs/live_setup.md`. The latest check saved `data/diagnostics/live_readiness.json`: fresh observations and current station AQI gates pass; the OGD API and forecast gates remain blocked. Exceptions are classified without printing credentials or request URLs. An HTTP 200 HTML response cannot pass the API gate, and availability does not establish forecast skill.

Signed-in Chrome inspection subsequently confirmed an existing Active portal key matching the configured key by SHA-256 fingerprint. The key was not printed, changed or regenerated. Source preview/API details remained unavailable; the alternative CSV download requires a purpose form and CAPTCHA, left for the user. This resolves uncertainty about which key is configured, not the provider connection or missing measurement evidence.

## Current data evidence

The combined run contains 16,209 input records and 14,899 distinct observations across 49 station names, after removing 1,310 repeated keys. The original 1,710 archive observations retain unknown units. The new import supplies 13,189 hourly concentration observations, including missing values explicitly retained. There are no conflicting records. Latest completed source interval ends October 9, 2026 at 18:00 IST. The readiness check found 931 fresh usable observations and 47 eligible current station AQI estimates. All 1,715 forecast status records withhold predictions.

The official CPCB portal listed 50 Delhi stations: 49 returned tables and Lodhi Road, Delhi - IITM returned no data. Raw visible table captures, source URL, units, collection times and collection summary are preserved under `data/raw/cpcb`. Alipur uses complete sets of four 15-minute observations per hour; other captured tables report hourly intervals. Incomplete/future intervals are excluded or retained as missing, never filled. NO is preserved in raw captures but is not treated as NO2. CO is mg/m³; other supported pollutants are µg/m³. Coordinates come only from exact station-name matches in the preserved archive; unmatched stations are omitted from maps. AQI uses trailing 24-hour windows with at least 16 valid hours, and 8-hour CO/O3 windows with all eight valid hours. Source history is unchanged by AQI averaging.

Historical observations retrieved today cannot be treated as known at yesterday's forecast origins. Forecast training therefore preserves collection-time restrictions even when a portal returns historical measurements. No automatic CPCB refresh has been installed.

## Files changed or added

Modified: README, requirements, supported collector, pipeline runner, production AQI/forecast/validator/risk/warning/station/report modules, station trend module, forecast matching, hourly collection runner, existing dashboard application and legacy analytical entry points. The legacy cleaner now delegates to the shared validation/pipeline path.

Created: `.env.example`; `src/core` configuration and data modules; dashboard components, verified data access and package initialization; offline core/UI tests and optional browser-check script; architecture, methodology, provenance, model-validation and this report; versioned analytical outputs and QA evidence. `requirements.txt` pins the six existing runtime dependencies; browser QA tooling was installed separately in a temporary directory and is not an application dependency.

## Run and inspect

From the project root:

```powershell
.\.venv\Scripts\python.exe -m src.pipeline.run_pipeline
.\.venv\Scripts\python.exe -m streamlit run src/dashboard/app.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For a configured official API refresh, use `-m src.pipeline.run_pipeline --collect`. See README for installation/configuration and the collector's 15-minute check cycle. The current running local dashboard is available at `http://127.0.0.1:8501` while its server process remains active.

## Remaining operational requirements

Automatic OGD collection is now running in a hidden process on this PC, with 15-minute source checks, a singleton lock, atomic status and retention of the last successful analytical run on failure. Dashboard screens reload every 60 seconds and display source failures explicitly. The initial background check failed before authentication, so this change does not establish a working live feed. Status is under `data/runtime/monitor_status.json`. The collector stops at Windows shutdown and is not installed as a startup service. Automatic CPCB collection remains unimplemented because no suitable unattended feed was verified.

Browser verification confirmed an actual timed screen refresh, a visible blocked-source state and no application exceptions; results and screenshot are in `docs/qa/monitor_results.json` and `docs/qa/monitor_desktop.png`. All ten pages and mobile checks also passed after enabling monitoring. A second collector invocation exited without starting a competing collector.

1. Establish a reliable ongoing official collection path; the OGD API remains inaccessible and CPCB retrieval currently requires portal access.
2. Preserve explicit source semantics and units for each new source. The archived OGD values remain unverified; CPCB table units do not retroactively validate them.
3. Evaluate station models on sufficiently long, independent real histories and additional pollution episodes before claiming forecast skill.
4. Treat calibrated prediction intervals, seasonal inference, meteorology, causal attribution, drift monitoring and policy simulation as future research requiring data and validation.

The software preserves these limits explicitly. There is no claim that every requested research feature is operational or that all environmental outputs are scientifically certified.
