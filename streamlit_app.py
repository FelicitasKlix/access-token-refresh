'''
import streamlit as st
import os
import json
import requests
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.cloud import functions_v2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import tempfile

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
def update_function_env_var_gen2(project_id, location, function_names, env_vars):
    credentials = load_gcp_credentials()
    client = functions_v2.FunctionServiceClient(credentials=credentials)
    
    results = []
    
    if isinstance(function_names, str):
        function_names = [function_names]
    
    for function_name in function_names:
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
            results.append((True, f"Función {function_name} actualizada exitosamente"))
        except Exception as e:
            results.append((False, f"Error al actualizar la función {function_name}: {str(e)}"))
    
    return results
# def update_function_env_var_gen2(project_id, location, function_name, env_vars):
#     credentials = load_gcp_credentials()
#     client = functions_v2.FunctionServiceClient(credentials=credentials)
    
#     function_path = f"projects/{project_id}/locations/{location}/functions/{function_name}"
    
#     try:
#         function = client.get_function(name=function_path)
#         if not function.service_config.environment_variables:
#             function.service_config.environment_variables = {}
#         function.service_config.environment_variables.update(env_vars)
        
#         update_mask = {"paths": ["service_config.environment_variables"]}
#         operation = client.update_function(
#             function=function,
#             update_mask=update_mask
#         )
#         updated_function = operation.result()
#         return True, "Función actualizada exitosamente"
#     except Exception as e:
#         return False, f"Error al actualizar la función: {str(e)}"

def create_calendar_event(reminder_date, calendar_ids):
    # Verificar si ya tenemos credenciales en la sesión
    if 'calendar_credentials' not in st.session_state:
        st.session_state.calendar_credentials = None

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
            redirect_uri="https://meta-access-token-refresh.streamlit.app/_oauth-callback"
        )

        # Verificar si tenemos un código en la URL
        query_params = st.experimental_get_query_params()
        #query_params = st.query_params()
        if "code" in query_params:
            try:
                flow.fetch_token(code=query_params["code"][0])
                st.session_state.calendar_credentials = flow.credentials
                # Limpiar la URL
                st.experimental_set_query_params()
            except Exception as e:
                st.error(f"Error al obtener el token: {str(e)}")
                return [f"Error en la autenticación: {str(e)}"]

        if not st.session_state.calendar_credentials:
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            st.markdown(f"[Click aquí para autorizar la aplicación]({auth_url})")
            return ["Esperando autorización..."]
        
        try:
            service = build('calendar', 'v3', credentials=st.session_state.calendar_credentials)

            # Usar las credenciales para crear el servicio
            #service = build('calendar', 'v3', credentials=creds)

            # Crear el evento
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
        except Exception as e:
            return [f"Error en la autenticación: {str(e)}"]
        
        return ["Esperando autorización..."]

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
    explorer_url = f"https://developers.facebook.com/tools/explorer/{app_config['client_id']}/"
    st.markdown(f"[Obtener user_access_token para {selected_app}]({explorer_url})")
    
    # Input para el token actual
    current_token = st.text_input("Token actual de Facebook", type="password")
    
    if st.button("Procesar Token"):
        if current_token:
            # Obtener nuevo token de larga duración
            fb_url = "https://graph.facebook.com/v12.0/oauth/access_token"
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
                    # Update Cloud Function(s)
                    function_names = app_config["function_name"]
                    results = update_function_env_var_gen2(
                        project_id="analytix-313619",
                        location="us-central1",
                        function_names=function_names,
                        env_vars={"LONG_LIVED_TOKEN": new_token}
                    )
                    # Display results
                    st.subheader("Resumen de la operación")
                    st.write(f"**Nuevo token expira el:** {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Recordatorio programado para:** {reminder_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    for success, message in results:
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    
                    # Create calendar events
                    #calendar_ids = ['felicitas@bullmetrix.com', 'data@bullmetrix.com']
                    #calendar_results = create_calendar_event(reminder_date, calendar_ids)
                    
                    #for result in calendar_results:
                        #st.write(result)
                else:
                    st.error("Error al obtener el nuevo token de Facebook")
        else:
            st.warning("Por favor, ingresa el token actual")
                    # success, message = update_function_env_var_gen2(
                    #     project_id="analytix-313619",
                    #     location="us-central1",
                    #     function_name=app_config["function_name"],
                    #     env_vars={"LONG_LIVED_TOKEN": new_token}
                    # )
                    
        #             if success:
        #                 st.success("Token actualizado en Cloud Function")
                        
        #                 # Crear eventos en calendario
        #                 calendar_ids = ['felicitas@bullmetrix.com', 'data@bullmetrix.com']
        #                 calendar_results = create_calendar_event(reminder_date, calendar_ids)
                        
        #                 # Mostrar resumen
        #                 st.subheader("Resumen de la operación")
        #                 st.write(f"**Nuevo token expira el:** {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        #                 st.write(f"**Recordatorio programado para:** {reminder_date.strftime('%Y-%m-%d %H:%M:%S')}")
                        
        #                 for result in calendar_results:
        #                     st.write(result)
        #             else:
        #                 st.error(message)
        #         else:
        #             st.error("Error al obtener el nuevo token de Facebook")
        # else:
        #     st.warning("Por favor, ingresa el token actual")


import streamlit as st
import os
import json
import requests
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.cloud import run_v2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import tempfile

# Configuración de página
st.set_page_config(page_title="Facebook Token Manager", layout="wide")

# Función para cargar las credenciales de GCP
def load_gcp_credentials():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_credentials"],
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    return credentials

# Función para determinar si es Cloud Function o Cloud Run basado en la URL
def is_cloud_run_service(url):
    return 'run.app' in url

# Función para actualizar variables de entorno en Cloud Run
def update_cloudrun_env_var(project_id, location, service_name, env_vars):
    credentials = load_gcp_credentials()
    client = run_v2.ServicesClient(credentials=credentials)
    
    service_path = f"projects/{project_id}/locations/{location}/services/{service_name}"
    
    try:
        # Obtener el servicio actual
        service = client.get_service(name=service_path)
        
        # Actualizar las variables de entorno
        if not service.spec.template.spec.template.spec.containers[0].env:
            service.spec.template.spec.template.spec.containers[0].env = []
        
        # Crear un diccionario de las variables existentes
        existing_env = {}
        for env_var in service.spec.template.spec.template.spec.containers[0].env:
            existing_env[env_var.name] = env_var.value
        
        # Actualizar con las nuevas variables
        existing_env.update(env_vars)
        
        # Reconstruir la lista de variables de entorno
        new_env_list = []
        for key, value in existing_env.items():
            env_var = run_v2.EnvVar()
            env_var.name = key
            env_var.value = value
            new_env_list.append(env_var)
        
        # Asignar la nueva lista al contenedor
        service.spec.template.spec.template.spec.containers[0].env = new_env_list
        
        # Actualizar el servicio
        operation = client.update_service(service=service)
        updated_service = operation.result()
        
        return True, f"Servicio Cloud Run {service_name} actualizado exitosamente"
    except Exception as e:
        return False, f"Error al actualizar el servicio Cloud Run {service_name}: {str(e)}"

# Función para actualizar variables de entorno en Cloud Function (mantener para compatibilidad)
def update_function_env_var_gen2(project_id, location, function_name, env_vars):
    from google.cloud import functions_v2
    credentials = load_gcp_credentials()
    client = functions_v2.FunctionServiceClient(credentials=credentials)
    
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
        return True, f"Cloud Function {function_name} actualizada exitosamente"
    except Exception as e:
        return False, f"Error al actualizar la Cloud Function {function_name}: {str(e)}"

# Función unificada para actualizar servicios (Cloud Run o Cloud Functions)
def update_service_env_vars(project_id, location, service_configs, env_vars):
    results = []
    
    if isinstance(service_configs, str):
        service_configs = [service_configs]
    elif isinstance(service_configs, dict):
        service_configs = [service_configs]
    
    for config in service_configs:
        if isinstance(config, str):
            # Si es solo un string, asumir que es Cloud Function por compatibilidad
            success, message = update_function_env_var_gen2(project_id, location, config, env_vars)
            results.append((success, message))
        elif isinstance(config, dict):
            service_name = config.get('name')
            service_type = config.get('type', 'cloudfunction')  # default a cloudfunction
            service_url = config.get('url', '')
            
            if service_type == 'cloudrun' or is_cloud_run_service(service_url):
                success, message = update_cloudrun_env_var(project_id, location, service_name, env_vars)
            else:
                success, message = update_function_env_var_gen2(project_id, location, service_name, env_vars)
            
            results.append((success, message))
    
    return results

def create_calendar_event(reminder_date, calendar_ids):
    # Verificar si ya tenemos credenciales en la sesión
    if 'calendar_credentials' not in st.session_state:
        st.session_state.calendar_credentials = None

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
            redirect_uri="https://meta-access-token-refresh.streamlit.app/_oauth-callback"
        )

        # Verificar si tenemos un código en la URL
        query_params = st.experimental_get_query_params()
        if "code" in query_params:
            try:
                flow.fetch_token(code=query_params["code"][0])
                st.session_state.calendar_credentials = flow.credentials
                # Limpiar la URL
                st.experimental_set_query_params()
            except Exception as e:
                st.error(f"Error al obtener el token: {str(e)}")
                return [f"Error en la autenticación: {str(e)}"]

        if not st.session_state.calendar_credentials:
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            st.markdown(f"[Click aquí para autorizar la aplicación]({auth_url})")
            return ["Esperando autorización..."]
        
        try:
            service = build('calendar', 'v3', credentials=st.session_state.calendar_credentials)

            # Crear el evento
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
        except Exception as e:
            return [f"Error en la autenticación: {str(e)}"]

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
        # Determinar si son servicios múltiples
        if isinstance(app_config.get("services"), list):
            service_names = [s.get("name", s) if isinstance(s, dict) else s for s in app_config["services"]]
            st.write("**Services:**", ", ".join(service_names))
        else:
            # Compatibilidad con configuración anterior
            service_name = app_config.get("function_name", app_config.get("service_name", "No definido"))
            st.write("**Service:**", service_name)
    
    st.write("Se deben asignar los siguientes permisos: read_insights, ads_read, business_management, ads_management")

    # Agregar enlace directo a Graph API Explorer
    explorer_url = f"https://developers.facebook.com/tools/explorer/{app_config['client_id']}/"
    st.markdown(f"[Obtener user_access_token para {selected_app}]({explorer_url})")
    
    # Input para el token actual
    current_token = st.text_input("Token actual de Facebook", type="password")
    
    if st.button("Procesar Token"):
        if current_token:
            # Obtener nuevo token de larga duración
            fb_url = "https://graph.facebook.com/v12.0/oauth/access_token"
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
                    
                    # Actualizar servicios (Cloud Run o Cloud Functions)
                    services = app_config.get("services", app_config.get("function_name"))
                    results = update_service_env_vars(
                        project_id="analytix-313619",
                        location="us-central1",
                        service_configs=services,
                        env_vars={"LONG_LIVED_TOKEN": new_token}
                    )
                    
                    # Mostrar resultados
                    st.subheader("Resumen de la operación")
                    st.write(f"**Nuevo token expira el:** {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Recordatorio programado para:** {reminder_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    for success, message in results:
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    
                    # Opcional: Crear eventos en calendario
                    # calendar_ids = ['felicitas@bullmetrix.com', 'data@bullmetrix.com']
                    # calendar_results = create_calendar_event(reminder_date, calendar_ids)
                    # for result in calendar_results:
                    #     st.write(result)
                else:
                    st.error("Error al obtener el nuevo token de Facebook")
        else:
            st.warning("Por favor, ingresa el token actual")

'''
import streamlit as st
import os
import json
import requests
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.cloud import run_v2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import tempfile

# Configuración de página
st.set_page_config(page_title="Facebook Token Manager", layout="wide")

# Función para cargar las credenciales de GCP
def load_gcp_credentials():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_credentials"],
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    return credentials

# Función para determinar si es Cloud Function o Cloud Run basado en la URL o nombre
def is_cloud_run_service(service_name, url=None):
    # Si tenemos URL, verificar si es run.app
    if url and 'run.app' in url:
        return True
    # Si el nombre del servicio contiene patrones típicos de Cloud Run
    # Cloud Run services suelen tener nombres como: service-name-hash o project-id-hash
    if '-' in service_name and len(service_name.split('-')) > 2:
        return True
    # También verificar si contiene números largos (típico de Cloud Run)
    import re
    if re.search(r'\d{10,}', service_name):
        return True
    return False

# Función para actualizar variables de entorno en Cloud Run
def update_cloudrun_env_var(project_id, location, service_name, env_vars):
    credentials = load_gcp_credentials()
    client = run_v2.ServicesClient(credentials=credentials)
    
    service_path = f"projects/{project_id}/locations/{location}/services/{service_name}"
    
    try:
        # Obtener el servicio actual
        service = client.get_service(name=service_path)
        
        # Actualizar las variables de entorno
        if not service.spec.template.spec.template.spec.containers[0].env:
            service.spec.template.spec.template.spec.containers[0].env = []
        
        # Crear un diccionario de las variables existentes
        existing_env = {}
        for env_var in service.spec.template.spec.template.spec.containers[0].env:
            existing_env[env_var.name] = env_var.value
        
        # Actualizar con las nuevas variables
        existing_env.update(env_vars)
        
        # Reconstruir la lista de variables de entorno
        new_env_list = []
        for key, value in existing_env.items():
            env_var = run_v2.EnvVar()
            env_var.name = key
            env_var.value = value
            new_env_list.append(env_var)
        
        # Asignar la nueva lista al contenedor
        service.spec.template.spec.template.spec.containers[0].env = new_env_list
        
        # Actualizar el servicio
        operation = client.update_service(service=service)
        updated_service = operation.result()
        
        return True, f"Servicio Cloud Run {service_name} actualizado exitosamente"
    except Exception as e:
        return False, f"Error al actualizar el servicio Cloud Run {service_name}: {str(e)}"

# Función para actualizar variables de entorno en Cloud Function (mantener para compatibilidad)
def update_function_env_var_gen2(project_id, location, function_name, env_vars):
    from google.cloud import functions_v2
    credentials = load_gcp_credentials()
    client = functions_v2.FunctionServiceClient(credentials=credentials)
    
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
        return True, f"Cloud Function {function_name} actualizada exitosamente"
    except Exception as e:
        return False, f"Error al actualizar la Cloud Function {function_name}: {str(e)}"

# Función unificada para actualizar servicios (Cloud Run o Cloud Functions)
def update_service_env_vars(project_id, location, service_configs, env_vars):
    results = []
    
    if isinstance(service_configs, str):
        service_configs = [service_configs]
    elif isinstance(service_configs, dict):
        service_configs = [service_configs]
    
    for config in service_configs:
        if isinstance(config, str):
            # Determinar el tipo basado en el nombre del servicio
            service_name = config
            if is_cloud_run_service(service_name):
                st.info(f"Detectado como Cloud Run: {service_name}")
                success, message = update_cloudrun_env_var(project_id, location, service_name, env_vars)
            else:
                st.info(f"Detectado como Cloud Function: {service_name}")
                success, message = update_function_env_var_gen2(project_id, location, service_name, env_vars)
            results.append((success, message))
        elif isinstance(config, dict):
            service_name = config.get('name')
            service_type = config.get('type', 'auto')  # default a auto-detección
            service_url = config.get('url', '')
            
            if service_type == 'cloudrun' or (service_type == 'auto' and is_cloud_run_service(service_name, service_url)):
                st.info(f"Procesando como Cloud Run: {service_name}")
                success, message = update_cloudrun_env_var(project_id, location, service_name, env_vars)
            else:
                st.info(f"Procesando como Cloud Function: {service_name}")
                success, message = update_function_env_var_gen2(project_id, location, service_name, env_vars)
            
            results.append((success, message))
    
    return results

def create_calendar_event(reminder_date, calendar_ids):
    # Verificar si ya tenemos credenciales en la sesión
    if 'calendar_credentials' not in st.session_state:
        st.session_state.calendar_credentials = None

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
            redirect_uri="https://meta-access-token-refresh.streamlit.app/_oauth-callback"
        )

        # Verificar si tenemos un código en la URL
        query_params = st.experimental_get_query_params()
        if "code" in query_params:
            try:
                flow.fetch_token(code=query_params["code"][0])
                st.session_state.calendar_credentials = flow.credentials
                # Limpiar la URL
                st.experimental_set_query_params()
            except Exception as e:
                st.error(f"Error al obtener el token: {str(e)}")
                return [f"Error en la autenticación: {str(e)}"]

        if not st.session_state.calendar_credentials:
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            st.markdown(f"[Click aquí para autorizar la aplicación]({auth_url})")
            return ["Esperando autorización..."]
        
        try:
            service = build('calendar', 'v3', credentials=st.session_state.calendar_credentials)

            # Crear el evento
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
        except Exception as e:
            return [f"Error en la autenticación: {str(e)}"]

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
        # Determinar si son servicios múltiples
        if isinstance(app_config.get("services"), list):
            service_names = [s.get("name", s) if isinstance(s, dict) else s for s in app_config["services"]]
            st.write("**Services:**", ", ".join(service_names))
        else:
            # Compatibilidad con configuración anterior
            service_name = app_config.get("function_name", app_config.get("service_name", "No definido"))
            st.write("**Service:**", service_name)
    
    st.write("Se deben asignar los siguientes permisos: read_insights, ads_read, business_management, ads_management")

    # Agregar enlace directo a Graph API Explorer
    explorer_url = f"https://developers.facebook.com/tools/explorer/{app_config['client_id']}/"
    st.markdown(f"[Obtener user_access_token para {selected_app}]({explorer_url})")
    
    # Input para el token actual
    current_token = st.text_input("Token actual de Facebook", type="password")
    
    if st.button("Procesar Token"):
        if current_token:
            # Obtener nuevo token de larga duración
            fb_url = "https://graph.facebook.com/v12.0/oauth/access_token"
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
                    
                    # Actualizar servicios (Cloud Run o Cloud Functions)
                    services = app_config.get("services", app_config.get("function_name"))
                    results = update_service_env_vars(
                        project_id="analytix-313619",
                        location="us-central1",
                        service_configs=services,
                        env_vars={"LONG_LIVED_TOKEN": new_token}
                    )
                    
                    # Mostrar el nuevo token
                    st.subheader("Nuevo Token Generado")
                    st.code(new_token, language="text")
                    
                    # Mostrar resultados
                    st.subheader("Resumen de la operación")
                    st.write(f"**Nuevo token expira el:** {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Recordatorio programado para:** {reminder_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    for success, message in results:
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    
                    # Opcional: Crear eventos en calendario
                    # calendar_ids = ['felicitas@bullmetrix.com', 'data@bullmetrix.com']
                    # calendar_results = create_calendar_event(reminder_date, calendar_ids)
                    # for result in calendar_results:
                    #     st.write(result)
                else:
                    st.error("Error al obtener el nuevo token de Facebook")
        else:
            st.warning("Por favor, ingresa el token actual")