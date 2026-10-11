"""Public historical demo entrypoint. No API keys or background collector needed."""
import os
from pathlib import Path
import runpy
import streamlit as st
from src.demo import prepare_demo


@st.cache_resource
def demo_configuration():
    return prepare_demo()


directory,reference_time=demo_configuration()
os.environ['CIVISCOPE_DATA_DIR']=str(directory)
os.environ['CIVISCOPE_DEMO_TIME']=reference_time
runpy.run_path(str(Path(__file__).parent/'src'/'dashboard'/'app.py'),run_name='__main__')
