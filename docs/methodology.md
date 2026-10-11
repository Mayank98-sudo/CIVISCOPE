# Scientific methodology

## Observations

Source observation time and collection time are separate fields. Legacy timestamps are interpreted in Asia/Kolkata. Pollutant aliases are normalized without equating different chemical species. Negative/nonfinite values and inconsistent minimum/average/maximum ranges are invalid. Invalid identities and future observations are excluded; unusable measurements remain missing. Repeated source keys do not increase historical sample count. Conflicting measurements or metadata are quarantined rather than selecting a later revision for historical training.

Hourly coverage is the number of hours containing a usable observation divided by elapsed hourly bins between the first and last record, per station/pollutant. It is neither forecast confidence nor evidence of adequate AQI averaging.

## AQI

Reference: [CPCB About National AQI](https://cpcb.nic.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvQWJvdXRfQVFJLnBkZg%3D%3D), checked during the audit. PM2.5, PM10, NO2, SO2, NH3 and Pb use micrograms per cubic metre and 24-hour averages. CO uses milligrams per cubic metre and an 8-hour average; O3 uses micrograms per cubic metre and an 8-hour average for supported lower categories.

Within a finite published concentration band:

`I = I_low + (C - C_low) * (I_high - I_low) / (C_high - C_low)`

CIVISCOPE requires explicit concentration meaning and the expected unit before automatic conversion. Verified finite concentrations with incomplete averaging metadata are labelled analytical estimates. The 24-hour path checks at least 16 valid hours; the 8-hour path conservatively requires eight valid hours. These results are CIVISCOPE calculations and are never presented as official published CPCB AQI.

For the October CPCB import, hourly concentrations are aggregated over the trailing pollutant-specific window ending at that station/pollutant's latest completed interval. Each counted hour must have the expected unit, explicit concentration meaning and complete source interval coverage. A quarter-hour table requires four usable quarters per hour; hourly tables require one completed reported hour. Partial current hours and future interval ends cannot contribute. Averaging modifies only the AQI calculation inputs, preserving the original hourly observation history.

Published decimal gaps are bridged linearly and disclosed as an analytical convention, not an official rounding rule. Results above finite severe thresholds carry a category diagnostic without invented numerical extrapolation. Higher O3 categories are withheld pending separately verified one-hour methodology. Category labels are Good, Satisfactory, Moderately Polluted, Poor, Very Poor and Severe.

Overall station estimates need at least three fresh, aligned eligible pollutants including PM2.5 or PM10. Unsupported numeric ranges prevent an overall numeric result. A displayed city median is explicitly a statistic of eligible station estimates; it is not official city AQI.

## Source meaning and CO

The bundled OGD snapshots expose `avg_value` without concentration units, averaging coverage or an explicit value-kind declaration. The official catalog describes AQI values. These facts do not establish whether a local reported value is a concentration or sub-index. CIVISCOPE preserves the source value and withholds derived AQI. CO receives no assumed ppm/mg/m3 conversion. This eligibility gate also applies to other pollutants.

## Trends, risk and warnings

Trend comparisons are scoped to one station/pollutant, unchanged metadata and a positive interval no greater than three hours. Changes above 5% are Increasing; below -5% are Decreasing; otherwise Stable. Zero baselines and missing measurements do not receive fabricated percentage changes.

CIVISCOPE risk preserves the prior tier-based base scores: 10, 25, 50, 70, 85 and 100. An increasing trend adds 15; a decreasing trend subtracts 10; results are clipped to 0-100. Missing trends contribute no adjustment and are disclosed. Missing or stale AQI produces unavailable risk. Forecast adjustment is withheld until concentration averaging-window eligibility can be established. Risk labels are project policy, not official health classifications.

Warnings include source timestamp, station, pollutant, condition, severity, evidence, status and source file. Conditions include stale or invalid observations, rapid PM source-value increases of at least 25% in an allowed comparison interval, and eligible analytical sub-indices at or above 201. Old analytical events are historical; stale-data warnings remain active.

Potential anomalies compare a value with at least 12 preceding measurements using median absolute deviation: `abs(value - median) / (1.4826 * MAD) > 4`. Zero-MAD baselines are not assigned an arbitrary deviation. Flags are possible anomalies, not diagnoses of sensor failure. Sparse coverage, gaps and source uncertainty limit interpretation. No causal attribution or medical advice is generated.
