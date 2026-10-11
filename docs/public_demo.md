# Public interactive demo

The public entrypoint is `streamlit_app.py`. It uses the existing dashboard and a checksum-verified archive of the October 9 analytical run. No credentials, private PC documents, runtime collector status or personal files are included. The archive contains only the manifest and its named analytical outputs derived from the public government observations.

The demonstration evaluates freshness and AQI eligibility at the recorded analytical time, October 9, 2026, 18:44 IST. A prominent banner discloses this on every page. Navigation uses **Snapshot AQI**, not Live AQI; the original application entrypoint retains real-time freshness rules. Historical replay does not change measurements, invent forecasts or establish today's pollution conditions. The saved forecast outputs contain no available predictions.

## Local start

Install `requirements.txt` with Python 3.11, then run `python -m streamlit run streamlit_app.py`. The demo archive is less than 1 MB and restores locally once per server process; no API call or model training occurs at startup. Checksum and archive-member validation reject unexpected contents before writing them. The ordinary collector and offline pipeline remain available via their existing entrypoints.

## Streamlit Community Cloud

Use the public repository `Mayank98-sudo/CIVISCOPE`, branch `main`, entrypoint `streamlit_app.py`, and Python 3.11. No secrets are required. The root requirements file declares dependencies. The official deployment flow requires signing in to Streamlit and accepting its terms; hosting is not complete until a public app URL has been verified.

## Verification on October 11

The demo restored a complete checksum-verified run with 14,899 distinct observations, 49 station names and 47 eligible station AQI estimates at the snapshot time. All ten pages and station detail selection passed Streamlit AppTest checks. Two new tests verify clean startup/idempotence and refusal of unexpected archive members. Forecasts remain unavailable.
