"""Reusable Streamlit presentation components."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

COLOR='#087f83'


def number(value,digits=0):
    try:
        return f'{float(value):,.{digits}f}' if pd.notna(value) else 'Data unavailable'
    except (TypeError,ValueError):
        return 'Data unavailable'


def chart(figure,key=None,height=340):
    figure.update_layout(template='plotly_white',font=dict(family='Arial',color='#23354b'),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=12,r=12,t=44,b=24),height=height,legend=dict(orientation='h',y=1.12),hovermode='closest')
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor='#e8edf2',zeroline=False)
    st.plotly_chart(figure,width='stretch',key=key,config={'displaylogo':False})


def table(frame,columns=None,key=None):
    if frame.empty:
        st.info('Data unavailable for this selection.')
        return
    if columns:
        frame=frame[[c for c in columns if c in frame]].copy()
    names={c:c.replace('_',' ').capitalize() for c in frame.columns}
    st.dataframe(frame.rename(columns=names),hide_index=True,width='stretch',height=min(440,38+len(frame)*35),key=key)


def line(frame,x,y,title,color=None,key=None):
    valid=frame.dropna(subset=[x,y])
    if valid.empty:
        st.info('Data unavailable for this chart.')
        return
    fig=px.line(valid,x=x,y=y,color=color,title=title,markers=True,color_discrete_sequence=[COLOR,'#546987','#c67822','#7b6d98'])
    units=valid.unit.dropna().unique() if 'unit' in valid else []
    label='Concentration ('+str(units[0])+')' if len(units)==1 and units[0]!='unknown' else 'Source-reported value (unit unverified)'
    fig.update_yaxes(title=label if y in ('avg_value','average_value','rolling_mean') else y.replace('_',' ').capitalize())
    fig.update_xaxes(title='Observation time · IST')
    chart(fig,key)


def station_map(frame,key='map',detail_picker=True):
    mapped=frame.dropna(subset=['latitude','longitude']).copy()
    if mapped.empty:
        st.info('Coordinates unavailable for this selection.')
        return None
    mapped['Station']=mapped.station
    mapped['Source value']=mapped.avg_value
    # Do not colour old unverified scales alongside verified concentrations.
    concentration_view='value_kind' in mapped and mapped.value_kind.eq('concentration').any()
    if concentration_view:
        mapped.loc[~mapped.value_kind.eq('concentration'),'Source value']=float('nan')
    mapped['Observed']=mapped.observation_time.astype(str)
    mapped['Unit']=mapped.unit
    mapped['Freshness']=mapped.freshness
    usable=mapped[mapped['Source value'].notna()]
    base=usable if len(usable) else mapped
    fig=px.scatter_map(base,lat='latitude',lon='longitude',hover_name='Station',hover_data={'Source value':True,'Observed':True,'Unit':True,'Freshness':True,'latitude':False,'longitude':False},color='Source value' if len(usable) else None,color_continuous_scale=['#489b9c','#137d87','#18394d'],custom_data=['station'],zoom=9,center={'lat':28.64,'lon':77.18},map_style='carto-positron')
    missing=mapped[mapped['Source value'].isna()]
    if len(usable) and len(missing):
        fig.add_trace(go.Scattermap(lat=missing.latitude,lon=missing.longitude,mode='markers',name='Value unavailable',marker={'size':12,'color':'#6b7788'},text=missing.station,hovertemplate='%{text}<br>Source value unavailable<extra></extra>'))
    fig.update_traces(marker={'size':12})
    fig.update_layout(height=430,margin=dict(l=0,r=0,t=0,b=0),coloraxis_colorbar=dict(title='Source value',thickness=10,len=.65))
    st.plotly_chart(fig,width='stretch',key=key,config={'displaylogo':False,'scrollZoom':True})
    st.caption('Monitoring locations only. Colour represents the selected pollutant’s source-reported value, not AQI. Missing values are grey. Hover a marker for source details; use pan/zoom controls to explore. No spatial interpolation.')
    if concentration_view:
        st.caption('Verified concentration view: unverified source scales are grey and are not compared on the concentration colour scale.')
    if detail_picker:
        selected=st.selectbox('Map station detail',['Choose a station']+sorted(mapped.station.unique()),key=key+'_detail')
        return selected if selected!='Choose a station' else None
    return None
