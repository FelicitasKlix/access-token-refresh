import streamlit as st
import os
import json
import requests
from datetime import datetime, timedelta
from google.oauth2 import service_account
#from google.cloud.functions_v2 import FunctionsServiceClient
from google.cloud import functions_v2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import tempfile
import pickle

# Configuración de página
st.set_page_config(page_title="Facebook Token Manager", layout="wide")

# Función para cargar las credenciales de GCP
def load_gcp_credentials():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_credentials"],
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    return credentials

# Función para actualizar variables de entorno en Cloud Function
def update_function_env_var_gen2(project_id, location, function_name, env_vars):
    credentials = load_gcp_credentials()
    client = functions_v2.FunctionServiceClient(credentials=credentials)
    #client = FunctionsServiceClient(credentials=credentials)
    
    function_path = f"projects/{project_id}/locations/{location}/functions/{function_name}"
    
    try:
        function = client.get_function(name=function_path)
        if not function.service_config.environment_variables:
            function.service_config.environment_variables = {}
        function.service_config.environment_variables.update(env_vars)
        
        update_mask = {"paths": ["service_config.environment_variables"]}
        operation = client.update_function(
            function=function,
            update_mask=update_mask
        )
        updated_function = operation.result()
        return True, "Función actualizada exitosamente"
    except Exception as e:
        return False, f"Error al actualizar la función: {str(e)}"

def create_calendar_event(reminder_date, calendar_ids):
    # Crear la estructura correcta del diccionario
    client_secrets = {
        "web": {
            "client_id": st.secrets["calendar_api"]["client_id"],
            "project_id": st.secrets["calendar_api"]["project_id"],
            "auth_uri": st.secrets["calendar_api"]["auth_uri"],
            "token_uri": st.secrets["calendar_api"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["calendar_api"]["auth_provider_x509_cert_url"],
            "client_secret": st.secrets["calendar_api"]["client_secret"],
            "redirect_uris": ["https://meta-access-token-refresh.streamlit.app/_oauth-callback"],
            "javascript_origins": ["https://meta-access-token-refresh.streamlit.app"]
        }
    }

    # Crear un archivo temporal con las credenciales
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        json.dump(client_secrets, temp)
        temp.flush()

        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Usar Flow con la URL de redirección correcta
        flow = Flow.from_client_secrets_file(
            temp.name,
            scopes=SCOPES,
            redirect_uri='https://meta-access-token-refresh.streamlit.app/_oauth-callback'
        )

        # Generar URL de autorización
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        # Mostrar el link de autorización al usuario
        st.markdown(f"[Click aquí para autorizar la aplicación]({auth_url})")
        
        # Esperar el código de autorización del usuario
        code = st.text_input("Ingresa el código de autorización:")
        
        if code:
            flow.fetch_token(code=code)
            creds = flow.credentials

            # Usar las credenciales para crear el servicio
            service = build('calendar', 'v3', credentials=creds)
            
            # Resto de tu código para crear eventos...
            year = reminder_date.year
            month = reminder_date.month
            day = reminder_date.day
            
            start_date = f"{year}-{month:02d}-{day:02d}"
            end_date = f"{year}-{month:02d}-{day:02d}"
            
            event = {
                'summary': 'Facebook Token Refresh Reminder',
                'description': 'Es necesario refrescar el token de Facebook',
                'start': {
                    'date': start_date,
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'date': end_date,
                    'timeZone': 'America/Los_Angeles',
                },
                'colorId': '4',
            }
            
            results = []
            for calendar_id in calendar_ids:
                try:
                    event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
                    results.append(f"Evento creado en {calendar_id}")
                except Exception as e:
                    results.append(f"Error al crear evento en {calendar_id}: {str(e)}")
            
            return results
        
        return ["Esperando autorización..."]

# Función para crear evento en Google Calendar
# def create_calendar_event(reminder_date, calendar_ids):

#     # # Convertir el AttrDict en un diccionario regular
#     # calendar_api_dict = dict(st.secrets["calendar_api"])
#     # st.write(calendar_api_dict)

#     # # Crear un archivo temporal con las credenciales de calendario
#     # with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
#     #     #json.dump(st.secrets["calendar_api"], temp)
#     #     json.dump(calendar_api_dict, temp)
#     #     temp.flush()  # Asegúrate de que los datos se escriban

#     #     # Definir los alcances que necesitamos para Google Calendar
#     #     SCOPES = ['https://www.googleapis.com/auth/calendar']
        
#     #     # Iniciar el flujo OAuth con las credenciales temporales
#     #     flow = InstalledAppFlow.from_client_secrets_file(temp.name, SCOPES)
#     #     creds = flow.run_local_server(port=0)

#     # Crear la estructura correcta del diccionario
#     client_secrets = {
#         "installed": {
#             "client_id": st.secrets["calendar_api"]["client_id"],
#             "project_id": st.secrets["calendar_api"]["project_id"],
#             "auth_uri": st.secrets["calendar_api"]["auth_uri"],
#             "token_uri": st.secrets["calendar_api"]["token_uri"],
#             "auth_provider_x509_cert_url": st.secrets["calendar_api"]["auth_provider_x509_cert_url"],
#             "client_secret": st.secrets["calendar_api"]["client_secret"],
#             "redirect_uris": ["http://localhost"]
#         }
#     }

#     # Crear un archivo temporal con las credenciales de calendario
#     with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
#         json.dump(client_secrets, temp)
#         temp.flush()

#         SCOPES = ['https://www.googleapis.com/auth/calendar']
#         flow = InstalledAppFlow.from_client_secrets_file(temp.name, SCOPES)
#         creds = flow.run_local_server(port=0)

#     # Conectar al servicio de Google Calendar usando las credenciales obtenidas
#     service = build('calendar', 'v3', credentials=creds)
    
#     year = reminder_date.year
#     month = reminder_date.month
#     day = reminder_date.day
    
#     start_date = f"{year}-{month:02d}-{day:02d}"
#     end_date = f"{year}-{month:02d}-{day:02d}"
    
#     event = {
#         'summary': 'Facebook Token Refresh Reminder',
#         'description': 'Es necesario refrescar el token de Facebook',
#         'start': {
#             'date': start_date,
#             'timeZone': 'America/Los_Angeles',
#         },
#         'end': {
#             'date': end_date,
#             'timeZone': 'America/Los_Angeles',
#         },
#         'colorId': '4',
#     }
    
#     results = []
#     for calendar_id in calendar_ids:
#         try:
#             event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
#             results.append(f"Evento creado en {calendar_id}")
#         except Exception as e:
#             results.append(f"Error al crear evento en {calendar_id}: {str(e)}")
    
#     return results

# # Función para crear evento en Google Calendar
# def create_calendar_event(reminder_date, calendar_ids):
#     # Crear credenciales temporales para el calendario
#     # creds = service_account.Credentials.from_service_account_info(
#     #     st.secrets["calendar_api"],
#     #     scopes=['https://www.googleapis.com/auth/calendar']
#     # )

#     # Definir el alcance
#     SCOPES = ['https://www.googleapis.com/auth/calendar']

#     # Autenticación y obtención de credenciales
#     creds = None
#     # El archivo token.pickle almacena las credenciales de acceso de usuario
#     try:
#         with open('token.pickle', 'rb') as token:
#             creds = pickle.load(token)
#     except FileNotFoundError:
#         # Si no hay archivo de token, solicita el acceso del usuario
#         flow = InstalledAppFlow.from_client_secrets_file(st.secrets["calendar_api"], SCOPES)
#         creds = flow.run_local_server(port=0)
#         # Guarda las credenciales para la próxima vez
#         with open('token.pickle', 'wb') as token:
#             pickle.dump(creds, token)
    
#     service = build('calendar', 'v3', credentials=creds)
    
#     year = reminder_date.year
#     month = reminder_date.month
#     day = reminder_date.day
    
#     start_date = f"{year}-{month:02d}-{day:02d}"
#     end_date = f"{year}-{month:02d}-{day:02d}"
    
#     event = {
#         'summary': 'Facebook Token Refresh Reminder',
#         'description': 'Es necesario refrescar el token de Facebook',
#         'start': {
#             'date': start_date,
#             'timeZone': 'America/Los_Angeles',
#         },
#         'end': {
#             'date': end_date,
#             'timeZone': 'America/Los_Angeles',
#         },
#         'colorId': '4',
#     }
    
#     results = []
#     for calendar_id in calendar_ids:
#         try:
#             event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
#             results.append(f"Evento creado en {calendar_id}")
#         except Exception as e:
#             results.append(f"Error al crear evento en {calendar_id}: {str(e)}")
    
#     return results

# Sidebar para selección de app
st.sidebar.title("Facebook Token Manager")
facebook_apps = st.secrets["facebook_apps"]
app_names = list(facebook_apps.keys())
selected_app = st.sidebar.selectbox("Selecciona una aplicación", app_names)

# Mostrar información de la app seleccionada
if selected_app:
    app_config = facebook_apps[selected_app]
    
    st.title(f"Configuración de {selected_app}")
    
    # Mostrar detalles de la configuración
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Client ID:**", app_config["client_id"])
    with col2:
        st.write("**Function Name:**", app_config["function_name"])
    
    st.write("Se deben asignar los siguientes permisos: read_insights, ads_read, business_management, ads_management")

    # Agregar enlace directo a Graph API Explorer
    explorer_url = f"https://developers.facebook.com/tools/explorer/{app_config["client_id"]}/"
    st.markdown(f"[Obtener user_access_token para {selected_app}]({explorer_url})")
    
    # Input para el token actual
    current_token = st.text_input("Token actual de Facebook", type="password")
    
    if st.button("Procesar Token"):
        if current_token:
            # Obtener nuevo token de larga duración
            fb_url = f"https://graph.facebook.com/v12.0/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": app_config["client_id"],
                "client_secret": app_config["client_secret"],
                "fb_exchange_token": current_token
            }
            
            with st.spinner("Obteniendo nuevo token..."):
                response = requests.get(fb_url, params=params)
                
                if response.status_code == 200:
                    resp = response.json()
                    new_token = resp['access_token']
                    expires_in = resp['expires_in']
                    
                    # Calcular fechas
                    expiry_date = datetime.now() + timedelta(seconds=expires_in)
                    reminder_date = expiry_date - timedelta(days=1)
                    
                    # Actualizar Cloud Function
                    success, message = update_function_env_var_gen2(
                        project_id="analytix-313619",
                        location="us-central1",
                        function_name=app_config["function_name"],
                        env_vars={"LONG_LIVED_TOKEN": new_token}
                    )
                    
                    if success:
                        st.success("Token actualizado en Cloud Function")
                        
                        # Crear eventos en calendario
                        calendar_ids = ['felicitas@bullmetrix.com', 'data@bullmetrix.com']
                        calendar_results = create_calendar_event(reminder_date, calendar_ids)
                        
                        # Mostrar resumen
                        st.subheader("Resumen de la operación")
                        st.write(f"**Nuevo token expira el:** {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**Recordatorio programado para:** {reminder_date.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        for result in calendar_results:
                            st.write(result)
                    else:
                        st.error(message)
                else:
                    st.error("Error al obtener el nuevo token de Facebook")
        else:
            st.warning("Por favor, ingresa el token actual")