# Data sources and provenance

## Primary source

[Open Government Data real-time AQI catalog](https://www.data.gov.in/catalog/real-time-air-quality-index), supplied by CPCB. API resource: `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`.

Official methodology: [CPCB About National AQI](https://cpcb.nic.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvQWJvdXRfQVFJLnBkZg%3D%3D).

Other potential official measurement sources include [DPCC](https://www.dpccairdata.com/) and [Delhi Open Data](https://delhi.data.gov.in/). Their ingestion is not implemented by this upgrade, and they are not claimed as current dataset suppliers.

## Official CPCB concentration tables added October 9

[CPCB CAAQM advance search](https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/advance-search) supplied visible Delhi station tables after a user-completed CAPTCHA. Fifty listed stations were checked; 49 returned data for October 8–9 and Lodhi Road, Delhi - IITM returned no data. Captures under `data/raw/cpcb` retain every visible row, explicit unit headers, source URL, collection time and row counts; the collection summary records the unsuccessful station too.

`src/import_cpcb.py` validates the captures before writing exclusive historical snapshots with raw-file SHA-256 provenance. CO headers report mg/m³; PM2.5, PM10, NO2, NH3, SO2 and Ozone report µg/m³. NO is excluded from supported analytics, not renamed NO2. Completed hourly values use either a reported hourly interval or four complete quarter-hour records. Future/incomplete intervals cannot become usable observations. No interpolation is performed. Only exact archived station-name coordinate matches were supplied; unmatched locations remain unavailable. Collection times are preserved for forecast availability checks. This manual retrieval does not establish a continuously refreshing feed.

## Original archive

Historical files remain under `data/historical/`; the original raw JSON and flat processed products remain intact. The initial audit found 11 retrieval snapshots over August 17-19, 2026 and 3,020 flat historical rows. Repeated station/pollutant/source-timestamp records are removed from analytical sample counts. Conflicts are quarantined. Exact resulting counts are recorded per run in `quality.json`.

Observed fields include country, state, city, station, last_update, latitude, longitude, pollutant label and minimum/maximum/average source values. The archived fields do not establish concentration units or averaging periods. The normalizer accepts documented API aliases but refuses conflicting duplicate aliases.

## Provenance chain

Each validated observation records source URL, source file, observation time, first collection time, unit/value-kind status and quality status. Each promoted run contains SHA-256 checksums of snapshot inputs and all consumed output files. Source snapshots are checked for changes during analysis before the run is promoted. Forecast records identify station, pollutant, horizon, issuance, target, historical sample count, model and validation metrics.

## Collection and security

`OGD_API_KEY` is loaded from `.env` at collection time. `.env.example` contains no secret. Credentials are not stored in manifests or logs. HTTP requests use separate connect/read timeouts and at most three attempts per page. Repeated pages, incomplete page sequences, malformed records and maximum-page overruns abort retrieval. Snapshots are written only after collection succeeds and use exclusive creation to preserve history.

A live retrieval attempt on October 9, 2026 failed after the bounded retry limit. A subsequent diagnostic resolved the API hostname but found a refused HTTPS connection (Windows socket error 10061), before an HTTP response or authentication. The government website and CPCB website were reachable. The current website frontend advertises a resource route under `https://www.data.gov.in/backend/dataapi/v1`; a bounded sample probe there timed out, so it was not adopted as a working fallback. No partial snapshot was saved. Local dataset availability is not treated as proof of API connectivity. These observations do not distinguish a provider outage from a network policy or routing problem.

The official catalog was reviewed again on October 9. It describes National AQI values; it does not establish the concentration meaning, units and averaging period of the archived `pollutant_avg` fields. The current rendered catalog did not expose usable resource rows. No archived measurement metadata was changed based on that page.
