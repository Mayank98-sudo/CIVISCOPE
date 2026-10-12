"""CIVISCOPE presentation layer: source observations, evidence and availability."""
from pathlib import Path
import json
import os
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.core.config import DATA,HORIZONS,SOURCE_URL,CPCB_URL,STALE_HOURS
from src.core.data import latest_observations,now_local
from src.dashboard.data_access import load_run
from src.dashboard.components import chart,line,number,station_map,table

st.set_page_config(page_title='CIVISCOPE | Delhi intelligence',page_icon='◉',layout='wide',initial_sidebar_state='auto')
st.markdown('''<style>
.stApp {background:#f5f7fa;color:#172e46;}
.block-container {max-width:1500px;padding:4rem 2.6rem 3rem;}
[data-testid="stAppDeployButton"] {display:none;}
[data-testid="stSidebar"] {background:#10263e;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] span {color:#ecf3f7;}
[data-testid="stSidebar"] [data-baseweb="select"] span {color:#172e46;}
[data-testid="stSidebar"] button p,[data-testid="stSidebar"] button span {color:#172e46;}
[data-testid="stSidebar"] [data-testid^="stBaseLinkButton"] p,[data-testid="stSidebar"] [data-testid^="stBaseLinkButton"] span {color:#172e46;}
h1 {font-size:2.2rem!important;letter-spacing:-.065rem;font-weight:750!important;}
h2 {font-size:1.35rem!important;margin-top:1rem!important;}
h3 {font-size:1.08rem!important;}
[data-testid="stMetric"] {background:white;border:1px solid #dce4ed;border-radius:10px;padding:18px 20px;min-height:112px;}
[data-testid="stMetricValue"] {font-size:1.6rem;}
[data-testid="stMetricLabel"] {color:#53677a;}
[data-testid="stAlert"] {border-radius:8px;}
.eyebrow {font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#087f83;font-weight:750;}
.hero {background:#10263e;color:#fff;border-radius:12px;padding:26px 30px;margin:10px 0 24px;}
.hero h2 {color:#fff!important;margin:0!important;font-size:1.7rem!important;}
.hero p {color:#c9d8e7;margin-bottom:0;max-width:800px;}
.brand {font-size:23px;font-weight:800;letter-spacing:2px;color:white;}
@media(max-width:700px){.block-container{padding:3.75rem 1rem 1rem;} .hero{padding:20px;} h1{font-size:1.8rem!important;} [data-testid="stMetric"]{padding:12px;}}
</style>''',unsafe_allow_html=True)

DEMO_TIME=os.getenv('CIVISCOPE_DEMO_TIME')
AQI_PAGE='Snapshot AQI' if DEMO_TIME else 'Live AQI'
PAGES=['Overview',AQI_PAGE,'Stations','Forecast','Trends','Risk & Warnings','Spatial Intelligence','Data Quality','Methodology','About']
with st.sidebar:
    st.markdown('<div class="brand">CIVISCOPE</div>',unsafe_allow_html=True)
    st.caption('DELHI · ENVIRONMENTAL INTELLIGENCE')
    page=st.radio('Workspace',PAGES,label_visibility='collapsed',key='navigation')
    st.divider()

st.markdown('<div class="eyebrow">Urban intelligence / Delhi, India</div>',unsafe_allow_html=True)
st.title(page if page!='Overview' else 'Delhi air quality intelligence')

# A timed fragment reloads the saved manifest and recomputes freshness every minute.
# Network collection stays in a separate process, never in widget interactions.
st.session_state['_monitor_render_at']=time.monotonic()

@st.fragment(run_every='60s')
def monitor_panel():
    if time.monotonic()-st.session_state['_monitor_render_at']>=55:
        st.rerun()
    path=Path(os.getenv('CIVISCOPE_DATA_DIR',str(DATA)))/'runtime'/'monitor_status.json'
    try:
        status=json.loads(path.read_text(encoding='utf-8'))
        updated=pd.Timestamp(status.get('updated_at') or status['checked_at'])
        deadline=pd.Timestamp(status['next_check_at']) if status.get('next_check_at') else updated
        inactive=status['state']=='Stopped' or now_local()>deadline+pd.Timedelta(minutes=10)
        state='Collector inactive' if inactive else status['state']
        message=f"Automatic monitoring · {state} · {status.get('reason','Awaiting source check')}"
        if state=='Monitoring': st.success(message)
        else: st.warning(message)
        st.caption(f"Last source check: {status.get('checked_at','Not checked')} · Last successful update: {status.get('last_success_at') or 'None from this collector'} · Screen refresh: every 60 seconds · Screen checked at: {now_local().isoformat()}")
    except (OSError,ValueError,KeyError,TypeError):
        st.caption('Automatic collector status unavailable · Screen refresh: every 60 seconds. Saved observations do not establish a live connection.')

if DEMO_TIME:
    st.info('Historical interactive demo · saved government observations from October 9, 2026. This is not a live pollution feed. AQI estimates and freshness below are evaluated at the recorded snapshot time.')
    st.caption(f'Snapshot evaluation time: {pd.Timestamp(DEMO_TIME).strftime("%d %b %Y, %H:%M IST")} · Forecasts remain withheld when evidence is insufficient.')
    with st.sidebar:
        st.link_button('View source & methodology','https://github.com/Mayank98-sudo/CIVISCOPE',width='stretch')
else:
    monitor_panel()

@st.cache_data(ttl=60,show_spinner=False)
def cached_run(folder,signature):
    return load_run(Path(folder),json.loads(signature))

processed=Path(os.getenv('CIVISCOPE_DATA_DIR',str(DATA)))/'processed'
try:
    manifest=json.loads((processed/'latest_run.json').read_text(encoding='utf-8'))
    frames,quality,report=cached_run(str(processed),json.dumps(manifest,sort_keys=True))
except (OSError,ValueError,KeyError,TypeError) as error:
    st.warning('Data unavailable: no complete, readable analytical run is available.')
    st.caption('The last successful run, if present, has not been modified. Refresh the analytical pipeline to restore this view.')
    with st.expander('Setup and diagnostic details'):
        st.code('.\\.venv\\Scripts\\python.exe -m src.pipeline.run_pipeline')
        st.caption(f'Diagnostic: {type(error).__name__}')
    st.stop()

obs=frames['observations'].copy()
now=pd.Timestamp(DEMO_TIME) if DEMO_TIME else now_local()
obs['age_hours']=(now-obs.observation_time).dt.total_seconds()/3600
obs['freshness']=np.where(obs.age_hours>STALE_HOURS,'Stale','Fresh')
latest=latest_observations(obs)
if obs.empty:
    st.info('Data unavailable: no valid observation identities in this run. Review source records and the quality report.')
    st.json(quality)
    st.stop()
stations=frames['stations'].copy()
stale_station=(now-stations.latest_measurement).dt.total_seconds()>STALE_HOURS*3600
stations.loc[stale_station,'station_aqi']=np.nan
stations.loc[stale_station,'station_category']='Data unavailable'
stations.loc[stale_station,'freshness']='Stale'
forecasts=frames['forecasts'].copy()
expired=forecasts.forecast_target_time<=now
expired_available=expired & forecasts.forecast_value.notna()
forecasts.loc[expired,'forecast_value']=np.nan
forecasts.loc[expired_available,'forecast_status']='Expired forecast; refresh required'
forecasts.loc[expired,'confidence']='Unavailable'

with st.sidebar:
    st.subheader('Explore observations')
    station=st.selectbox('Station',['All stations']+sorted(obs.station.unique()),key='station_filter')
    pollutants=sorted(obs.pollutant_id.unique())
    pollutant=st.selectbox('Pollutant',pollutants,index=pollutants.index('PM2.5') if 'PM2.5' in pollutants else 0)
    horizon=st.selectbox('Forecast horizon (hours)',HORIZONS)
    dates=st.date_input('Historical date range',value=(obs.observation_time.min().date(),obs.observation_time.max().date()),min_value=obs.observation_time.min().date(),max_value=obs.observation_time.max().date())
    st.caption('Date range applies to historical charts. Current views use the latest source records.')
    if st.button('Reload saved analysis',width='stretch'):
        cached_run.clear(); st.rerun()
    st.divider()
    st.caption('SOURCE · CPCB / OGD INDIA')
    st.caption('CIVISCOPE calculations and forecasts are analytical outputs, not official health classifications.')

last_time=obs.observation_time.max()
st.caption(f'Latest source observation · {last_time.strftime("%d %b %Y, %H:%M IST")}  |  {obs.station.nunique()} stations in history')
if latest.freshness.eq('Stale').any():
    st.warning(f'{latest.loc[latest.freshness.eq("Stale"),"station"].nunique()} stations have stale pollutant observations. Saved data must not be interpreted as live conditions.')

selected=obs[obs.pollutant_id.eq(pollutant)].copy()
current=latest[latest.pollutant_id.eq(pollutant)].copy()
station_rows=stations.copy()
if station!='All stations':
    selected=selected[selected.station.eq(station)]
    current=current[current.station.eq(station)]
    station_rows=station_rows[station_rows.station.eq(station)]
if isinstance(dates,(tuple,list)) and len(dates)==2:
    selected=selected[selected.observation_time.dt.date.between(dates[0],dates[1])]


def current_table(data):
    table(data,['station','pollutant_id','avg_value','unit','value_kind','observation_time','freshness','quality_status'])


def timeline(data,key):
    # Each line remains station-specific; no comparisons across pollutant units.
    cohorts=data.groupby(['unit','value_kind'],dropna=False) if {'unit','value_kind'}.issubset(data) else [(('unknown','unverified'),data)]
    for index,((unit,kind),cohort) in enumerate(cohorts):
        line(cohort.sort_values('observation_time'),'observation_time','avg_value',f'{pollutant} · {kind} · {unit}','station' if station=='All stations' else None,key+str(index))
    st.caption('Measurement bases are plotted separately. CPCB table concentrations carry explicit units; the older OGD archive remains unverified. Lines connect recorded observations without filling gaps.')


def station_detail(name):
    g=latest[latest.station.eq(name)]
    st.subheader(name)
    row=stations[stations.station.eq(name)].iloc[0]
    cols=st.columns(3)
    cols[0].metric('Current AQI estimate',number(row.station_aqi))
    cols[1].metric('Observed pollutants',len(g))
    cols[2].metric('Hourly coverage',number(row.coverage_percent,1)+'%')
    st.caption(str(row.aqi_status))
    current_table(g)
    details=frames['aqi'][frames['aqi'].station.eq(name)]
    with st.expander('AQI eligibility and provenance'):
        table(details,['pollutant_id','aqi_sub_index','aqi_status','aqi_reason','source','source_file'])

if page=='Overview':
    st.markdown('<div class="hero"><h2>Understand the city. Inspect the evidence.</h2><p>Station observations, temporal patterns and forecast readiness — with data quality and scientific limitations visible at every step.</p></div>',unsafe_allow_html=True)
    valid=station_rows.station_aqi.dropna()
    cols=st.columns(4)
    cols[0].metric('Median station AQI estimate',number(valid.median() if len(valid) else None))
    cols[1].metric('Stations in view',len(station_rows))
    cols[2].metric('Fresh at snapshot' if DEMO_TIME else 'Fresh pollutant observations',int(current.freshness.eq('Fresh').sum()))
    cols[3].metric('Available station forecasts',int(forecasts[forecasts.station.isin(station_rows.station)].forecast_value.notna().sum()))
    st.caption('Median is a CIVISCOPE station statistic, not an official city AQI. AQI and risk are withheld where source meaning or units are unverified.')
    left,right=st.columns([1.5,1])
    with left:
        st.subheader(f'{pollutant} monitoring network')
        picked=station_map(current,'overview_map')
    with right:
        st.subheader('Evidence at a glance')
        st.info('AQI eligibility is checked per record. Verified CPCB concentrations can supply trailing averaging windows; unverified OGD values remain excluded from conversion.')
        st.markdown(f'**{quality["unique_observations"]:,}** distinct observation keys retained from **{quality["records"]:,}** retrieved records.')
        st.markdown(f'**{quality["duplicate_observation_keys"]:,}** repeated observation keys removed from analytical history.')
        st.markdown(f'**{quality["conflicting_records"]:,}** conflicting source rows quarantined.')
        st.markdown('**Forecast readiness:** each station and pollutant is assessed independently. Short or stale histories remain unavailable.')
    if picked:
        station_detail(picked)
    st.subheader('Observed history')
    timeline(selected,'overview_history')
    st.subheader(f'Latest reported {pollutant} values')
    current_table(current.sort_values('avg_value',ascending=False).head(12))

elif page==AQI_PAGE:
    st.info('AQI estimates use eligible concentration inputs and their averaging coverage. Unverified or stale inputs remain unavailable. These are CIVISCOPE calculations, not official published station AQI.')
    aqi=frames['aqi'].copy()
    if station!='All stations': aqi=aqi[aqi.station.eq(station)]
    table(aqi,['station','pollutant_id','avg_value','unit','averaging_hours','valid_hours','aqi_sub_index','category','aqi_status','aqi_reason','observation_time'])
    st.caption('Sub-indices in this table, when eligible, describe their recorded observation time. Current station AQI additionally requires fresh, aligned observations of at least three pollutants including PM2.5 or PM10.')

elif page=='Stations':
    st.subheader('Station directory')
    table(station_rows,['station','station_aqi','station_category','dominant_pollutant','latest_measurement','freshness','coverage_percent','forecast_status'])
    detail=st.selectbox('Inspect station',station_rows.station.tolist())
    if detail: station_detail(detail)
    station_map(current,'stations_map',detail_picker=False)

elif page=='Forecast':
    st.caption('Station-specific source-value forecasts · horizons measured on the hourly clock · no city forecast is copied to a station.')
    options=sorted(obs.station.unique())
    forecast_station=station if station!='All stations' else st.selectbox('Forecast station',options)
    f=forecasts[(forecasts.station==forecast_station)&(forecasts.pollutant_id==pollutant)&(forecasts.horizon_hours==horizon)]
    if f.empty:
        st.info('Data unavailable: selected station has no records for this pollutant.')
    else:
        r=f.iloc[0]
        st.info(r.forecast_status)
        cols=st.columns(4)
        cols[0].metric('Forecast source value',number(r.forecast_value,1))
        cols[1].metric('Model',str(r.forecast_method))
        cols[2].metric('Confidence',str(r.confidence))
        cols[3].metric('Held-out samples',number(r.validation_samples))
        st.caption(f'Target · {r.forecast_target_time} | {int(r.historical_observations)} usable source observations')
        cols=st.columns(3)
        for c,label,value in zip(cols,['MAE','RMSE','MAPE (%)'],[r.MAE,r.RMSE,r.MAPE_percent]): c.metric(label,number(value,2))
        history=obs[(obs.station==forecast_station)&(obs.pollutant_id==pollutant)].sort_values('observation_time')
        fig=go.Figure(go.Scatter(x=history.observation_time,y=history.avg_value,name='Observed source value',mode='lines+markers',line_color='#087f83'))
        if pd.notna(r.forecast_value): fig.add_trace(go.Scatter(x=[r.forecast_target_time],y=[r.forecast_value],name='Experimental forecast',mode='markers',marker=dict(size=12,symbol='diamond',color='#c67822')))
        fig.update_layout(title=f'{forecast_station} · {pollutant}',yaxis_title='Source-reported value',xaxis_title='Observation / target time · IST')
        chart(fig,'forecast_chart')
        v=frames['validation']; v=v[(v.station==forecast_station)&(v.pollutant_id==pollutant)&(v.horizon_hours==horizon)]
        if len(v):
            held=v[(v.split=='Held-out evaluation')&(v.method==r.forecast_method)]
            fig=go.Figure()
            for column,label in [('actual_value','Actual'),('forecast_value','Held-out prediction')]: fig.add_trace(go.Scatter(x=held.target_time,y=held[column],name=label,mode='lines+markers'))
            fig.update_layout(title='Chronological held-out evaluation',yaxis_title='Source value',xaxis_title='Target time · IST'); chart(fig,'holdout_chart')
            with st.expander('Model comparison and validation records'): table(v)
        else: st.caption('No valid backtest metrics are available. Repeated retrievals are not independent history.')

elif page=='Trends':
    bases=selected[['unit','value_kind']].drop_duplicates().sort_values('value_kind')
    basis_labels=[f'{r.value_kind} · {r.unit}' for r in bases.itertuples()]
    if len(basis_labels)>1:
        basis=st.selectbox('Measurement basis',basis_labels)
        chosen=bases.iloc[basis_labels.index(basis)]
        selected=selected[selected.unit.eq(chosen.unit) & selected.value_kind.eq(chosen.value_kind)].copy()
    aggregation=st.radio('Aggregation',['Recorded observations','Daily','Weekly'],horizontal=True)
    view=selected.copy()
    if aggregation!='Recorded observations':
        frequency='D' if aggregation=='Daily' else 'W'
        view=view.set_index('observation_time').groupby(['station','unit','value_kind']).resample(frequency).avg_value.mean().reset_index()
    timeline(view,'trends_history')
    if not selected.empty:
        left,right=st.columns(2)
        with left:
            pattern=selected.assign(hour=selected.observation_time.dt.hour).groupby('hour',as_index=False).avg_value.mean()
            chart(px.bar(pattern,x='hour',y='avg_value',title='Observed hour-of-day pattern',color_discrete_sequence=['#087f83']),'hour_pattern')
        with right:
            chart(px.histogram(selected,x='avg_value',nbins=24,title='Recorded-value distribution',color_discrete_sequence=['#546987']),'distribution')
        st.caption('Patterns describe available observations, not causes. Sparse and changing station coverage can bias averages; this archive cannot establish seasonal effects.')
        station_choice=station if station!='All stations' else st.selectbox('Rolling mean station',sorted(selected.station.unique()))
        rolling=selected[selected.station.eq(station_choice)].sort_values('observation_time').copy()
        rolling['rolling_mean']=rolling.set_index('observation_time').avg_value.rolling('24h',min_periods=3).mean().to_numpy()
        line(rolling,'observation_time','rolling_mean','24-hour rolling mean · at least 3 recorded values',key='rolling')
        st.caption('Rolling mean is descriptive and does not establish the required coverage for official AQI.')
        table(selected.groupby('station',as_index=False).agg(observations=('avg_value','count'),minimum=('avg_value','min'),maximum=('avg_value','max'),mean=('avg_value','mean'),volatility=('avg_value','std')))

elif page=='Risk & Warnings':
    st.info('CIVISCOPE analytical risk is not an official CPCB health classification. Missing risk scores or warnings do not establish safe conditions.')
    risk=frames['risk'].copy(); warnings=frames['warnings'].copy()
    risk.loc[(now-risk.observation_time).dt.total_seconds()>STALE_HOURS*3600,['risk_score']]=np.nan
    risk.loc[risk.risk_score.isna(),'risk_level']='Data unavailable'
    warnings.loc[(now-warnings.timestamp).dt.total_seconds()>STALE_HOURS*3600,'status']=np.where(warnings.loc[(now-warnings.timestamp).dt.total_seconds()>STALE_HOURS*3600,'severity'].eq('Data quality'),'Active','Historical')
    for col in ['station','pollutant_id']:
        value=station if col=='station' else pollutant
        if value!='All stations':
            risk=risk[risk[col].eq(value)]; warnings=warnings[warnings[col].eq(value)]
    status=st.radio('Warning status',['Active','Historical','All'],horizontal=True)
    visible=warnings if status=='All' else warnings[warnings.status.eq(status)]
    st.subheader('Warnings with evidence')
    table(visible,['timestamp','station','pollutant_id','condition','severity','evidence','status'])
    st.subheader('Station / pollutant analytical risk')
    table(risk,['station','pollutant_id','risk_score','risk_level','trend','components'])
    with st.expander('How is this calculated?'):
        st.markdown('AQI tiers map to base scores 10, 25, 50, 70, 85 and 100. A comparable observed increase above 5% adds 15; a decrease below −5% subtracts 10. The result is clipped to 0–100. Comparisons more than three hours apart are unavailable. Missing trends contribute no adjustment and are explicitly disclosed. Stale or unavailable AQI produces no risk score. Forecast adjustment is withheld until averaging-window eligibility is established.')

elif page=='Spatial Intelligence':
    st.caption('Compare the same pollutant across monitoring locations. No interpolated pollution surface is shown.')
    spatial_time=st.selectbox('Observation time',['Latest available']+sorted(obs.observation_time.astype(str).unique().tolist(),reverse=True))
    mapped=current if spatial_time=='Latest available' else obs[(obs.pollutant_id==pollutant)&(obs.observation_time.astype(str)==spatial_time)]
    if station!='All stations': mapped=mapped[mapped.station.eq(station)]
    picked=station_map(mapped,'spatial_map')
    if picked: station_detail(picked)
    current_table(mapped.sort_values('avg_value',ascending=False))
    if mapped.avg_value.notna().any():
        cols=st.columns(3)
        cols[0].metric('Mapped stations',int(mapped[['latitude','longitude']].notna().all(axis=1).sum()))
        cols[1].metric('Median reported value',number(mapped.avg_value.median(),1))
        cols[2].metric('Reported-value range',f'{number(mapped.avg_value.min(),1)} – {number(mapped.avg_value.max(),1)}')

elif page=='Data Quality':
    cols=st.columns(4)
    for c,label,key in zip(cols,['Retrieved records','Unique observation keys','Repeated keys','Conflicting records'],['records','unique_observations','duplicate_observation_keys','conflicting_records']): c.metric(label,number(quality[key]))
    st.subheader('Validation results')
    checks=['invalid_values','invalid_identity','future_observations','invalid_coordinates','invalid_ranges','unknown_units','usable_values']
    table(pd.DataFrame([{'check':k.replace('_',' '),'records':quality[k]} for k in checks]))
    st.subheader('Observed hourly coverage')
    coverage=frames['coverage']; coverage=coverage[coverage.pollutant_id.eq(pollutant)]
    if station!='All stations': coverage=coverage[coverage.station.eq(station)]
    table(coverage)
    st.caption('Coverage = hours with a usable value / elapsed hourly bins between first and last records, per station and pollutant. It is not a forecast confidence score.')
    st.subheader('Source and freshness')
    st.markdown(f'[Official source catalog]({SOURCE_URL})')
    st.write(f'Latest source observation: {last_time}. Analytical run: {manifest["generated_at"]}.')
    st.caption('Source connectivity is not inferred from local file availability. Live API status is unverified unless a collection succeeds.')
    st.subheader('Live readiness check')
    diagnostic=processed.parent/'diagnostics'/'live_readiness.json'
    try:
        readiness=json.loads(diagnostic.read_text(encoding='utf-8'))
        if readiness.get('schema_version')!=1 or not isinstance(readiness.get('gates'),list):
            raise ValueError('Unsupported diagnostic report')
        st.caption(f'Last explicit check: {readiness["checked_at"]}. This is a saved check, not a continuous connection monitor.')
        table(pd.DataFrame(readiness['gates']))
        st.caption(readiness['scope'])
    except (OSError,ValueError,KeyError,TypeError):
        st.info('Live readiness has not been checked, or the saved diagnostic report is unreadable.')
    with st.expander('Recheck live prerequisites'):
        st.code('.\\.venv\\Scripts\\python.exe -m src.readiness')
        st.caption('Runs one bounded authenticated sample request and checks the integrity and freshness of saved analytics. Credentials are never displayed.')
    with st.expander('Input provenance and checksums'): st.json(quality.get('input_files',{}))
    with st.expander('Missing values before cleaning'): st.json(quality.get('missing_values',{}))
    export=current.to_csv(index=False).encode('utf-8')
    st.download_button('Download selected source observations',export,'civiscope_observations.csv','text/csv')

elif page=='Methodology':
    st.markdown('### Verified CPCB table imports\nOfficial concentration headers establish units. Completed hourly readings remain distinct from the unverified OGD archive. AQI inputs use trailing 24-hour or 8-hour windows, with reported-hour coverage disclosed. NO is not treated as NO2. Newly downloaded historical records are not assumed to have been available at past forecast origins.')
    st.markdown('### From source records to accountable analysis\nRaw government snapshots are preserved. Observation time is distinct from retrieval time. Exact source-key repeats are deduplicated; conflicting values are quarantined. Missing values are never filled.')
    st.markdown(f'### AQI eligibility\n[CPCB methodology]({CPCB_URL}) specifies pollutant concentration units and averaging periods. The local OGD archive does not establish these fields or whether reported values are concentrations or indices. CIVISCOPE therefore withholds derived AQI for those records.')
    st.latex(r'I=I_{lo}+(C-C_{lo})\frac{I_{hi}-I_{lo}}{C_{hi}-C_{lo}}')
    st.markdown('For explicitly verified concentrations, one shared engine interpolates finite CPCB bands. Decimal gaps use a disclosed analytical bridge. Open-ended severe bands do not receive an invented numeric upper bound; higher ozone categories require separate one-hour methodology. An overall station estimate requires three aligned pollutants including particulate matter. All estimates remain CIVISCOPE results.')
    st.markdown('### Forecasting and validation\nEach station/pollutant has its own hourly series. No missing hours are filled. Naive, rolling-mean and linear-trend models are compared using early chronological origins; later origins, separated by a horizon embargo, provide held-out metrics. Training excludes observations retrieved after the forecast origin. At least 24 consecutive training hours and 12 origins in each evaluation segment are required. Live predictions are withheld for stale or insufficient histories.')
    st.markdown('### Confidence and uncertainty\nConfidence is a qualitative analytical rule: High requires at least 168 held-out samples and normalized MAE ≤10%; Medium requires at least 48 and ≤20%; otherwise available models are Low. These thresholds are project policy, not calibrated probabilities. Prediction intervals and seasonal effects are not claimed.')
    st.markdown('### Interpretation\nTrends compare matching station/pollutant records within three hours and unchanged metadata. MAD anomalies use preceding observations only. Warnings expose thresholds and evidence and do not diagnose sensor failure or give medical advice. City summaries are labelled station statistics; they are not official city AQI.')

elif page=='About':
    st.markdown('### CIVISCOPE\nAn urban environmental intelligence platform designed to transform real-world air-quality data into interpretable city, station and forecast intelligence.')
    st.markdown('**Architecture:** government snapshots → validation and provenance → shared AQI eligibility → station time series → chronological forecasting → risk and warnings → versioned analytical run → dashboard.')
    st.markdown('**Technology:** Python, pandas, NumPy, Plotly and Streamlit. Simple models are retained when they perform best; model complexity is not a goal.')
    st.markdown('**Research directions:** longer independent station histories, verified units, weather integration, calibrated prediction intervals and drift evaluation. These are extensions, not existing validated capabilities.')
    st.markdown(f'[Government data catalog]({SOURCE_URL}) · [CPCB methodology]({CPCB_URL})')
    st.caption('The current archive is a limited historical sample. Software validation does not certify measurement accuracy or forecast skill.')

st.divider()
st.caption('CIVISCOPE / Delhi · Source observations, analytical calculations and model forecasts are distinct. All timestamps displayed in IST.')
