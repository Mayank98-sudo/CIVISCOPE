# Live prerequisites and recovery

The software is runnable; live AQI/forecast operation remains blocked by external source access and missing scientific evidence. A successful installation or a reachable dashboard does not remove these requirements.

## Current check: October 9, 2026

- `api.data.gov.in` resolves, but HTTPS is refused before authentication (socket error 10061). This is not evidence of an invalid key.
- A repeat check after switching to USB tethering also failed with socket error 10061. Windows reported the physical Ethernet adapter disconnected and a Remote NDIS Internet Sharing adapter present. Government-data and CPCB websites remained reachable. Failure on both connections makes the original Ethernet connection a less likely sole cause, but does not prove a provider outage or exclude a shared local restriction.
- Signed-in Chrome inspection confirmed that the existing portal API key is labelled Active and its SHA-256 fingerprint matches the configured project key. No key was regenerated or changed. Portal status does not establish successful API authentication while the connection is refused.
- `www.data.gov.in` and `cpcb.nic.in` returned HTTP 200. The website's advertised resource endpoint timed out. The subsequent CPCB portal recovery supplied a manual snapshot, described below; an unattended alternative feed remains unverified.
- Latest saved source timestamp after the CPCB import: October 9, 2026, 18:00 IST. The explicit check found 931 fresh usable observations, 47 eligible current station AQI estimates and zero unexpired forecasts.
- The original 1,710 archive observations retain unverified meaning and unknown units. New CPCB concentrations carry units shown in the official table; these do not validate old OGD values.
- The signed-in OGD resource preview remained a loading placeholder; its API panel supplied only a Generate API Key link. Its CSV download required a purpose form and CAPTCHA. Current observations were subsequently obtained from the separate CPCB portal.

## CPCB recovery completed

After the user completed the CPCB portal CAPTCHA, the official advance-search tables supplied data for 49 of 50 listed Delhi stations for October 8–9. Lodhi Road, Delhi - IITM returned no data. Raw tables and their provenance are preserved under `data/raw/cpcb`; `src/import_cpcb.py` validates their units, interval alignment, row counts and completed-hour coverage. The pipeline now calculates eligible station AQI estimates from verified trailing concentration windows. This is a manually retrieved snapshot, not an unattended feed or official published AQI.

To import a newly preserved table capture and rebuild:

```powershell
.\.venv\Scripts\python.exe -m src.import_cpcb path/to/table.json
.\.venv\Scripts\python.exe -m src.pipeline.run_pipeline
.\.venv\Scripts\python.exe -m src.readiness
```

Forecasts remain withheld. A historical table downloaded today does not supply observations that were available to yesterday's forecast origins; ongoing collection and independent evaluation are still required.

## Recovery sequence

1. Establish working HTTPS access to the official API from the machine or deployment environment. A network diagnostic is `Test-NetConnection api.data.gov.in -Port 443`. It does not test authentication or dataset correctness. Do not disable TLS verification, publish credentials or assume repeated retries resolve a refused connection.
2. Run `.\.venv\Scripts\python.exe -m src.readiness`. This checks the configured key without printing it. A nonempty authenticated records response establishes only sample connectivity.
3. Run `.\.venv\Scripts\python.exe -m src.pipeline.run_pipeline --collect`. Only a complete validated collection can promote new analytics. Inspect source observation timestamps; a new retrieval time alone does not make old measurements fresh.
4. Obtain authoritative field definitions establishing whether reported values are concentrations or indices, pollutant-specific units, averaging periods and valid-hour coverage. Preserve the evidence with source metadata. Never convert an already computed index as if it were a concentration or relabel unknown units by assumption. The current engine accepts explicit verified concentration metadata; this upgrade has not supplied invented metadata for OGD rows.
5. Collect independent ongoing station histories with `-m src.run_collection` when API access works. Forecast evaluation requires contiguous hourly training history and independent chronological selection/evaluation origins for each horizon. One fresh snapshot cannot satisfy those requirements. Collecting repeated copies of an unchanged timestamp does not increase sample count.
6. Recheck readiness and inspect held-out evaluation results. These minimum availability gates do not certify forecast skill, sensor accuracy or full network coverage. Independent empirical validation remains necessary before an operational forecasting claim.

The collector now checks the official API every 15 minutes, saves atomic status under `data/runtime/monitor_status.json`, and publishes a complete run only after successful retrieval and validation. A singleton OS lock prevents competing collectors. Failures retain the previous run and last successful update time, with credential-free reasons. The dashboard reloads saved outputs and freshness every 60 seconds; it does not fetch data itself.

A hidden background collector was started on this PC on October 9. Its first check remains blocked by connection refusal; there has been no automatic successful update. It survives closing the initiating terminal but is not installed as a Windows startup service. PC shutdown or process termination stops it. Start again with `-m src.run_collection --interval 900`. An expired heartbeat is shown as inactive instead of implying a healthy live connection.

## Diagnostic artifacts

`data/diagnostics/live_readiness.json` is a point-in-time report independent of the immutable analytical run. Data Quality displays its timestamp and gate evidence. Recheck explicitly after network or data changes; the UI does not poll the provider. No API key, response body or exception URL is stored in the diagnostic.
