import streamlit as st

st.title("Meta Developers App Access Token Refresh")
st.write("This app does the following:")
st.write("1. Creates the URL to generate the user access token for a Meta Developers App (short-lived-token)")
st.write("2. Makes the API request with that token to generate the long-lived-token")
st.write("3. Updates the long-lived-token in the exectuion environment variable of a GCP function")
st.write("4. Adds to Google Calendar an event the day before the expire date of the long-lived-token (usually 60 days)")