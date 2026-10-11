"""Station/pollutant forecasts with hourly chronology and held-out evaluation."""
from __future__ import annotations

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from src.core.config import HORIZONS, STALE_HOURS
from src.core.data import now_local, timestamp

METHODS = ('Naive', 'Rolling Mean', 'Linear Trend')
MIN_TRAIN = 24
MIN_FOLDS = 12
COLUMNS = ['station','pollutant_id','horizon_hours','forecast_time','forecast_target_time','last_observation_time','forecast_value','last_observed_value','forecast_method','historical_observations','forecast_status','confidence','MAE','RMSE','MAPE_percent','validation_samples','selection_samples','unit','value_kind']
VALIDATION_COLUMNS = ['station','pollutant_id','horizon_hours','origin','target_time','method','forecast_value','actual_value','absolute_error','squared_error','percentage_error','split']


def predict(values, method: str, horizon: int) -> float:
    values = np.asarray(values,dtype=float)
    if method == 'Naive':
        result = values[-1]
    elif method == 'Rolling Mean':
        result = values[-3:].mean()
    elif method == 'Linear Trend':
        y = values[-24:]
        slope, intercept = np.polyfit(np.arange(len(y)),y,1)
        result = intercept + slope*(len(y)-1+horizon)
    else:
        raise ValueError('Unsupported model')
    return max(0.,float(result))


def hourly_series(group: pd.DataFrame) -> pd.DataFrame:
    """Last actual record per hour; no interpolation, forward fill or imputation."""
    g = group.sort_values('observation_time').copy()
    if g.empty:
        return pd.DataFrame(columns=['avg_value','collection_time','unit','value_kind'])
    g = g[g.observation_time >= g.observation_time.max()-pd.Timedelta(days=30)]
    g['hour'] = g.observation_time.dt.floor('h')
    g = g.drop_duplicates('hour',keep='last').set_index('hour')
    return g.reindex(pd.date_range(g.index.min(),g.index.max(),freq='h'))


def trailing_history(series: pd.DataFrame, origin: pd.Timestamp) -> np.ndarray:
    """Only measurements actually available at origin; truncate at gaps."""
    train = series.loc[:origin.floor('h')-pd.Timedelta(hours=1)].copy()
    available = train.collection_time.notna() & (train.collection_time <= origin)
    train.loc[~available,'avg_value'] = np.nan
    values = train.avg_value.to_numpy(dtype=float)
    if not len(values):
        return values
    missing = np.flatnonzero(~np.isfinite(values))
    return values[(missing[-1]+1 if len(missing) else 0):]


def backtest(series: pd.DataFrame, horizon: int) -> tuple[str | None,pd.DataFrame]:
    """Select on early origins; report later origins separated by a horizon embargo."""
    if series.avg_value.notna().sum() < MIN_TRAIN + 2*MIN_FOLDS + horizon:
        return None,pd.DataFrame()
    rows = []
    for origin in series.index[MIN_TRAIN:-horizon]:
        values = trailing_history(series,origin)
        target = origin + pd.Timedelta(hours=horizon)
        actual = series.at[target,'avg_value']
        if len(values) < MIN_TRAIN or not np.isfinite(actual):
            continue
        for method in METHODS:
            value = predict(values,method,horizon+1)
            error = value-actual
            rows.append(dict(origin=origin,target_time=target,method=method,forecast_value=value,actual_value=actual,absolute_error=abs(error),squared_error=error**2,percentage_error=abs(error/actual)*100 if actual else np.nan))
    df = pd.DataFrame(rows)
    if df.empty:
        return None,df
    origins = sorted(df.origin.unique())
    if len(origins) < 2*MIN_FOLDS+horizon:
        return None,pd.DataFrame()
    cut = origins[len(origins)//2]
    select = df[df.target_time < cut].copy()
    holdout = df[df.origin >= cut].copy()
    if select.origin.nunique() < MIN_FOLDS or holdout.origin.nunique() < MIN_FOLDS:
        return None,pd.DataFrame()
    # Stable tie preference keeps Naive when complexity adds no evidence.
    scores = select.groupby('method').absolute_error.mean()
    method = min(METHODS,key=lambda m:(scores[m],METHODS.index(m)))
    select['split'] = 'Model selection'
    holdout['split'] = 'Held-out evaluation'
    return method,pd.concat([select,holdout],ignore_index=True)


def forecast_group(group: pd.DataFrame, horizon: int, now=None) -> tuple[dict,pd.DataFrame]:
    if horizon not in HORIZONS:
        raise ValueError('Unsupported forecast horizon')
    now = timestamp(now) if now is not None else now_local()
    station = group.station.iloc[0] if len(group) else ''
    pollutant = group.pollutant_id.iloc[0] if len(group) else ''
    group = group[(group.observation_time <= now) & (group.collection_time <= now)
                  & (group.observation_time >= now-pd.Timedelta(days=30))].copy()
    series = hourly_series(group)
    last = group.sort_values('observation_time').iloc[-1] if len(group) else None
    row = dict.fromkeys(COLUMNS,np.nan)
    row.update(station=station,pollutant_id=pollutant,horizon_hours=horizon,forecast_time=now,forecast_target_time=now.floor('h')+pd.Timedelta(hours=horizon),forecast_status='Insufficient historical data',confidence='Unavailable',forecast_method='Unavailable',historical_observations=int(group.avg_value.notna().sum()),validation_samples=0,selection_samples=0,unit='unknown',value_kind='unverified')
    if last is None:
        return row,pd.DataFrame()
    row.update(last_observation_time=last.observation_time,last_observed_value=last.avg_value,unit=last.unit,value_kind=last.value_kind)
    # No aggregation across changing units/semantics.
    if group.unit.nunique()!=1 or group.value_kind.nunique()!=1:
        row['forecast_status']='Inconsistent source metadata'
        return row,pd.DataFrame()
    method,validation = backtest(series,horizon)
    if method is not None:
        evaluation = validation[(validation.split=='Held-out evaluation') & (validation.method==method)]
        row.update(forecast_method=method,MAE=evaluation.absolute_error.mean(),RMSE=np.sqrt(evaluation.squared_error.mean()),MAPE_percent=evaluation.percentage_error.mean(),validation_samples=len(evaluation),selection_samples=int(validation[validation.split=='Model selection'].origin.nunique()))
        for key,val in [('station',station),('pollutant_id',pollutant),('horizon_hours',horizon)]:
            validation[key]=val
    if (now-last.observation_time).total_seconds()/3600 > STALE_HOURS:
        row['forecast_status']='Stale observations; live forecast withheld'
        return row,validation
    if method is None:
        return row,validation
    # Live origin must have a complete current hourly observation. Do not shift a
    # stale last value forward and pretend it is a current measurement.
    origin=now.floor('h')
    if series.index.max()<origin-pd.Timedelta(hours=1):
        row['forecast_status']='Latest hourly observation unavailable'
        return row,validation
    values=trailing_history(series,now)
    if len(values)<MIN_TRAIN:
        row['forecast_status']='Insufficient contiguous available history'
        return row,validation
    row['forecast_value']=predict(values,method,horizon+1)
    row['forecast_status']='Experimental source-value forecast'
    scale=max(float(np.mean(np.abs(values))),1e-9)
    normalized_error=row['MAE']/scale
    row['confidence']='Medium' if row['validation_samples']>=48 and normalized_error<=.2 else 'Low'
    if row['validation_samples']>=168 and normalized_error<=.1:
        row['confidence']='High'
    return row,validation


def build_forecasts(observations: pd.DataFrame, now=None):
    rows,validations=[],[]
    for _,group in observations.groupby(['station','pollutant_id']):
        for horizon in HORIZONS:
            row,validation=forecast_group(group,horizon,now)
            rows.append(row)
            if not validation.empty:
                validations.append(validation)
    return (pd.DataFrame(rows,columns=COLUMNS), pd.concat(validations,ignore_index=True)[VALIDATION_COLUMNS] if validations else pd.DataFrame(columns=VALIDATION_COLUMNS))


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
