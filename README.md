# Meta Developers App Access Token Refresh

This app does the following:

1. Creates the URL to generate the user access token for a Meta Developers App (short-lived-token)
2. Makes the API request with that token to generate the long-lived-token
3. Updates the long-lived-token in the exectuion environment variable of a GCP function
4. Adds to Google Calendar an event the day before the expire date of the long-lived-token (usually 60 days)


## Running the Streamlit App Locally

To run the Streamlit app, use the following command:

```bash
streamlit run streamlit_app.py
```
or

```bash
python -m streamlit run streamlit_app.py 
```
## App URL