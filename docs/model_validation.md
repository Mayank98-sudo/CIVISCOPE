# Model validation and forecast limits

## Scope

The prediction target is a source-reported station/pollutant value on the hourly clock. A prediction is not a concentration or AQI forecast unless that meaning, unit and averaging-window relationship are independently verified.

## Training and evaluation

Each station/pollutant is processed independently. The latest actual record in each hourly bin is retained; absent hours remain missing. Training truncates at the most recent gap and excludes records retrieved after the origin. The recent 30-day window bounds computation. No random split, interpolation or forward-fill is used.

At least 24 consecutive available training hours are required. Candidate models are Naive, a three-value rolling mean and linear extrapolation fitted to the recent 24 values. Origins and targets advance chronologically. Early origins select the lowest-MAE candidate, with stable ties favouring Naive. Later origins evaluate the selected method. The last selection target must precede the first held-out origin, providing a horizon embargo. At least 12 selection origins and 12 held-out origins are required.

Forecast horizons are 1, 3, 6, 12 and 24 hours ahead of the hourly clock origin. The current partially observed hour is excluded from training. Consequently a linear model extrapolates horizon + 1 steps from the final training hour. Exact target timestamps are retained; a separate outcome-matching function accepts only the requested future target and matching station/pollutant/metadata, never a before-target nearest observation.

## Metrics

MAE and RMSE are reported separately per station/pollutant/horizon. MAPE excludes zero actual values. Metrics are held-out historical diagnostics, not guarantees about future episodes. Model-selection results are identified separately from held-out results. Adjacent origins may share training data and forecast targets over time; sample counts are not counts of independent pollution episodes.

## Readiness and confidence

Stale observations, inadequate contiguous history, changing units/meaning, unavailable recent hourly observations and missing validation produce explicit unavailable statuses. Predictions are nonnegative; arbitrary confidence percentages and synthetic forecast values are never generated.

For available experimental forecasts, the confidence policy is High with at least 168 held-out samples and MAE / mean absolute training value <= 0.10; Medium with at least 48 and <= 0.20; otherwise Low. These cutoffs are project policy, not calibrated probabilities or prediction-interval coverage.

## Evidence limits

The bundled sparse August archive cannot establish hourly forecast skill, seasonal effects, model superiority or reliable 24-hour prediction. Software tests use generated fixtures strictly within test code and temporary directories. They verify chronology, publication-time exclusion, station separation and failure handling; they do not demonstrate empirical performance on Delhi measurements.

Before operational forecasting, collect longer independent station histories, verify source meaning/units and assess skill against Naive on additional time periods and pollution episodes. Calibrated intervals and drift monitoring remain research work.
