# Public dashboard and historical archive

**Public URL:** https://civiscope-mayank-raj.streamlit.app/

The default **Live Monitoring** page now shows selected Delhi PM2.5 readings from OpenAQ / AirGradient, collected hourly in the cloud. These four low-cost sensors are separate from the government archive. See [live monitoring](live_monitoring.md) for scope, freshness, attribution and collection details.

Deployed and verified on October 12, 2026, from the public GitHub repository using Python 3.11 and `streamlit_app.py`. All ten hosted pages loaded with zero application exceptions; station detail selection and map zoom worked. A separate unsigned-in browser opened the dashboard successfully. At a 390-pixel mobile viewport, document width matched the viewport, the sidebar was collapsed and no application exception appeared. The GitHub offline workflow passed for commit `92268b85aefe1d5f8813f5e81dda153fae69defa`.

The public entrypoint is `streamlit_app.py`. It uses the existing dashboard and a checksum-verified archive of the October 9 analytical run. No credentials, private PC documents or personal files are included. The separate live sensor feed publishes only measurement data and a sanitized collector status. The archive contains only the manifest and its named analytical outputs derived from the public government observations.

The demonstration evaluates freshness and AQI eligibility at the recorded analytical time, October 9, 2026, 18:44 IST. A prominent banner discloses this on every historical archive page. Navigation uses **Snapshot AQI**, not Live AQI; the original application entrypoint retains real-time freshness rules. Historical replay does not change measurements, invent forecasts or establish today's pollution conditions. The saved forecast outputs contain no available predictions.

## Local start

Install `requirements.txt` with Python 3.11, then run `python -m streamlit run streamlit_app.py`. The demo archive is less than 1 MB and restores locally once per server process; no API call or model training occurs at startup. Checksum and archive-member validation reject unexpected contents before writing them. The ordinary collector and offline pipeline remain available via their existing entrypoints.

## Streamlit Community Cloud

The deployed configuration uses repository `Mayank98-sudo/CIVISCOPE`, branch `main`, entrypoint `streamlit_app.py`, and Python 3.11. No secrets are required on the Streamlit server. The separate GitHub Actions collector uses the encrypted repository secret described in the live monitoring documentation. The root requirements file declares dependencies. Streamlit sign-in, terms acceptance and the displayed GitHub deployment permissions were completed with user approval. Hosting and unsigned-in public access have been verified.

## Verification on October 11

The demo restored a complete checksum-verified run with 14,899 distinct observations, 49 station names and 47 eligible station AQI estimates at the snapshot time. All ten pages and station detail selection passed Streamlit AppTest checks. Two new tests verify clean startup/idempotence and refusal of unexpected archive members. Forecasts remain unavailable.
