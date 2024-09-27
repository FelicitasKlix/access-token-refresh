import streamlit as st
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import functions_v1
from datetime import datetime, timedelta
import json

# Cargar las aplicaciones de Facebook desde los secrets
apps = st.secrets["facebook_apps"]

# Configuración de Streamlit
st.set_page_config(layout="wide")
st.title("Actualizador de Token de Facebook")

# Menú lateral para seleccionar la app
selected_app = st.sidebar.selectbox("Selecciona una aplicación", list(apps.keys()))