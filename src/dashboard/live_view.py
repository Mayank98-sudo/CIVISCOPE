"""Public read-only view of cloud-collected, attributed PM2.5 sensor data."""
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from src.core.config import ROOT


@st.fragment(run_every='60s')
def render():
    st.info('Near-real-time PM2.5 sensor monitoring · OpenAQ / AirGradient · four selected Delhi locations. These are low-cost sensor readings, not official CPCB stations or official Delhi AQI. Government archive pages remain historical.')
    now=pd.Timestamp.now(tz='UTC')
    try:
        data=json.loads((ROOT/'live/latest.json').read_text(encoding='utf-8'))
        status=json.loads((ROOT/'live/status.json').read_text(encoding='utf-8'))
        if data['schema_version']!=1: raise ValueError('Unknown live data schema')
        frame=pd.DataFrame(data['latest'])
        frame['Observed (IST)']=pd.to_datetime(frame.observation_time,utc=True).dt.tz_convert('Asia/Kolkata')
        frame['Age (hours)']=(now-frame['Observed (IST)']).dt.total_seconds()/3600
        frame['Status']=frame['Age (hours)'].map(lambda age:'Fresh' if 0<=age<=3 else 'Stale')
        frame.loc[frame.value.isna(),'Status']='Missing'
    except (OSError,ValueError,KeyError,AttributeError):
        st.warning('Live feed unavailable. No saved government values are being substituted as live readings.')
        return
    fresh=frame[(frame.Status=='Fresh') & frame.value.notna()]
    checked=pd.Timestamp(status['checked_at'])
    if not status['ok']: st.warning(status['reason'])
    elif now-checked>pd.Timedelta(hours=3): st.warning('Automatic collector check is overdue; examine measurement timestamps before using these readings.')
    else: st.success(f'Feed connected · {len(fresh)} sensors have usable measurements within the last 3 hours.')
    if fresh.empty: st.warning('No fresh PM2.5 measurements are currently available.')
    a,b,c=st.columns(3)
    a.metric('Fresh PM2.5 sensors',len(fresh))
    b.metric('Locations monitored',len(data['locations']))
    c.metric('Latest observation (IST)',frame['Observed (IST)'].max().strftime('%d %b, %H:%M'))
    st.caption(f'Collected: {pd.Timestamp(data["collected_at"]).tz_convert("Asia/Kolkata").strftime("%d %b %Y, %H:%M IST")} · Last collector check: {checked.tz_convert("Asia/Kolkata").strftime("%d %b, %H:%M IST")} · Collection scheduled hourly; cloud scheduling and provider reporting may be delayed. Screen refreshes every minute.')
    station=st.selectbox('Live sensor location',['All locations']+frame.station.tolist(),key='live_sensor_location')
    view=frame if station=='All locations' else frame[frame.station==station]
    st.dataframe(view[['station','value','unit','Observed (IST)','Age (hours)','Status']].rename(columns={'station':'Location','value':'Reported PM2.5','unit':'Unit'}),hide_index=True,width='stretch')
    st.caption('Stale readings remain labelled with their original time. No city AQI, risk category or forecast is derived from this limited sensor feed.')
    history=pd.DataFrame(data['history'])
    if not history.empty:
        if station!='All locations': history=history[history.station==station]
        history['Observed (IST)']=pd.to_datetime(history.observation_time,utc=True).dt.tz_convert('Asia/Kolkata')
        history=history[history['Observed (IST)'].between(now-pd.Timedelta(hours=48),now)]
        breaks=[]
        for name,group in history.groupby('station'):
            times=group['Observed (IST)'].sort_values()
            for previous,current in zip(times.iloc[:-1],times.iloc[1:]):
                if current-previous>pd.Timedelta(hours=1):
                    breaks.append({'station':name,'Observed (IST)':previous+pd.Timedelta(hours=1),'value':float('nan')})
        plotted=pd.concat([history,pd.DataFrame(breaks)],ignore_index=True)
        chart=px.line(plotted.sort_values('Observed (IST)'),x='Observed (IST)',y='value',color='station',labels={'value':'Hourly PM2.5 (µg/m³)','station':'Location'},title='Last 48 hours · reported hourly averages')
        chart.update_traces(connectgaps=False)
        st.plotly_chart(chart,width='stretch',key='live_history')
        st.caption('Latest readings and hourly averages are distinct source resources. Flagged or invalid hourly values are missing; gaps are not filled.')
    points=[]
    for location in data['locations']:
        row=frame[frame.location_id==location['id']]
        if not row.empty:
            points.append({'Location':location['name'],**location['coordinates'],'PM2.5':row.iloc[0].value,'Status':row.iloc[0].Status})
    if points:
        chart=px.scatter_map(pd.DataFrame(points),lat='latitude',lon='longitude',hover_name='Location',hover_data=['PM2.5','Status'],color='Status',zoom=10,map_style='carto-positron')
        st.plotly_chart(chart,width='stretch',key='live_sensor_map')
    with st.expander('Sources, instruments and attribution'):
        for location in data['locations']:
            st.markdown(f'**[{location["name"]}]({location["source_url"]})** · OpenAQ / {location["provider"]["name"]}')
            for license in location['licenses']:
                st.caption(f'{license["attribution"]["name"]} · {license["name"]} · https://creativecommons.org/licenses/by/4.0/ · displayed with timezone and quality labels; no concentration adjustment applied.')
            st.caption('Instruments: '+', '.join(item['name'] for item in location['instruments']))
