import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pymongo as pm
from collections import defaultdict

# Set page configuration
st.set_page_config(page_title="Fitbit Scheduler", layout="centered")

def get_watches_from_mongodb(client, project):
    """Fetch watches for specific project from MongoDB"""
    db = client['lab']
    collection = db['labFitbits']
    watches = list(collection.find({"project": project.lower()}))
    return watches

def get_watch_token(watch_data):
    """Get token from watch data"""
    return watch_data.get('token', '')

# Define a function to select a profile
def select_profile(name, client):

    db = client['lab']
    collection = db['labFitbits']

    # find all the documents in the collection with the specified "project" 
    try:
        documents_fibro = collection.find({"project": "fibro"})
        documents_nova = collection.find({"project": "nova"})
        documents_mdma = collection.find({"project": "mdma"})
        documents_idf = collection.find({"project": "idf"})
    except:
        st.error("Failed to fetch data from the database.")
        return None

    profile = None
    if name == 'FibroAdmon':
        profile = 'Fibro Study'
    elif name == 'NovaAdmon':
        profile = 'Nova Study'
    elif name == 'MDMAStudy':
        profile = 'mdma Study'
    elif name == 'IDFStudy':
        profile = 'idf'
        
    if profile == 'Nova Study':
        return documents_nova
    elif profile == 'Fibro Study':
        return documents_fibro
    elif profile == 'mdma Study':
        return documents_mdma
    elif profile == 'idf':
        return documents_idf

# Streamlit app UI
st.title("Fitbit Scheduler Setup")

if 'client' not in st.session_state:
    st.session_state.client = pm.MongoClient('mongodb+srv://edenEldar:Eden1996@cluster0.rwebk7f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')

# Add project selection before the form
selected_project = st.selectbox("Select Project:", ["Fibro", "Nova", "MDMA", "IDF"])
project_watches = get_watches_from_mongodb(st.session_state.client, selected_project)
watch_names = [watch['name'] for watch in project_watches]

with st.form(key='scheduler_form'):
    # Update watch selection to use filtered watch names
    selected_watch = st.selectbox("Select your watch:", watch_names) if watch_names else st.error("No watches found for selected project")

    # Email input
    email = st.text_input("Enter your email address:")

    # Sync frequency selection
    st.write("Select sync frequencies:")
    morning_scan = st.checkbox("Morning", value=False)
    noon_scan = st.checkbox("Noon", value=False)
    evening_scan = st.checkbox("Evening", value=False)
    st.write("Note: The watch will be scanned at the selected times only.")
    # Fail threshold input
    fail_threshold = st.slider("Set fail threshold (1-5):", min_value=1, max_value=5, value=3)

    st.divider()

    ema_enable = st.checkbox("Enable EMA", value=False)
    st.write("Note: Enabling EMA only for fibro project")

    fail_threshold_ema = st.slider("Set fail threshold for EMA (1-5):", min_value=1, max_value=5, value=3)

    st.divider()

    reset_prev_data = st.checkbox("Reset previous data", value=False)

    end_date = st.date_input("End date for scheduler", value=None)

    # Submit button
    submit_button = st.form_submit_button(label='Submit')

if submit_button:
    if not email:
        st.error("Please enter your email address.")
    else:
        # Update token retrieval
        selected_watch_data = next((w for w in project_watches if w['name'] == selected_watch), None)
        if selected_watch_data:
            token = selected_watch_data['token']
            # Prepare data to update the Google Sheet

            # Authenticate with Google Sheets API
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]

            credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )

            client = gspread.authorize(credentials)

            # Open the Google Sheet
            spreadsheet = client.open_by_key("1jb1siFl0o7R9JsKy1gbvwshesu7Ksw2BJzNqg7Z-m1E")
            sheet = spreadsheet.sheet1

            # Check if the watch already exists in the sheet
            records = sheet.get_all_records()
            df = pd.DataFrame(records)

            # Find the watch in the dataframe
            matching_rows = df.index[(df['watch name'] == selected_watch) & (df['email'] == email)].tolist()
            
            if not df.empty and matching_rows:
                # Get the row index (add 2 to account for header and 1-indexing)
                row_index = matching_rows[0] + 2
                
                if reset_prev_data:
                    st.warning("This watch is already registered. Resetting existing entry.")
                    # Reset the existing row
                    sheet.update_cell(row_index, df.columns.get_loc("last updated") + 1, '')
                    sheet.update_cell(row_index, df.columns.get_loc("last sync") + 1, '')
                    sheet.update_cell(row_index, df.columns.get_loc("last hr value") + 1, '')
                    sheet.update_cell(row_index, df.columns.get_loc("last battery") + 1, '')
                    sheet.update_cell(row_index, df.columns.get_loc("fail count") + 1, 0)
                    sheet.update_cell(row_index, df.columns.get_loc("ema_enabled") + 1, str(ema_enable))
                    sheet.update_cell(row_index, df.columns.get_loc("fail threshold") + 1, fail_threshold)
                    sheet.update_cell(row_index, df.columns.get_loc("fail threshold ema") + 1, fail_threshold_ema)
                    sheet.update_cell(row_index, df.columns.get_loc("fail count ema") + 1, 0)
                    sheet.update_cell(row_index, df.columns.get_loc("last ema time") + 1, '')
                    sheet.update_cell(row_index, df.columns.get_loc("finish date") + 1, str(end_date))

                st.warning("This watch is already registered. Updating existing entry.")

                # Update the existing row - don't display the indices list to avoid confusion
                sheet.update_cell(row_index, df.columns.get_loc("email") + 1, email)
                sheet.update_cell(row_index, df.columns.get_loc("morning_scan") + 1, str(morning_scan))
                sheet.update_cell(row_index, df.columns.get_loc("noon_scan") + 1, str(noon_scan))
                sheet.update_cell(row_index, df.columns.get_loc("evening_scan") + 1, str(evening_scan))
                sheet.update_cell(row_index, df.columns.get_loc("fail threshold") + 1, fail_threshold)
                sheet.update_cell(row_index, df.columns.get_loc("ema_enabled") + 1, str(ema_enable))
                sheet.update_cell(row_index, df.columns.get_loc("fail threshold ema") + 1, fail_threshold_ema)
                sheet.update_cell(row_index, df.columns.get_loc("finish date") + 1, str(end_date))
            else:
                # Append a new row
                new_row = {
                    'email': email,
                    'token': token,
                    'last updated': '',
                    'watch name': selected_watch,
                    'last sync': '',
                    'last hr value': '',
                    'last battery': '',
                    'fail count': 0,
                    'morning_scan': str(morning_scan),
                    'noon_scan': str(noon_scan),
                    'evening_scan': str(evening_scan),
                    'fail threshold': fail_threshold,
                    'ema_enabled': str(ema_enable),
                    'fail threshold ema': fail_threshold_ema,
                    'fail count ema': 0,
                    'last ema time': '',
                    'finish date': str(end_date)
                }
                sheet.append_row(list(new_row.values()))

            st.success("Your preferences have been saved successfully!")
        else:
            st.error("Could not find the selected watch. Please try again.")

def get_watches_by_project(project_name, watch_tokens):
    project_prefix = project_name.lower()
    return [watch for watch in watch_tokens.keys() if watch.startswith(project_prefix)]

st.header("Scheduler Logs")
st.write("Select a project to view logs:")
selected_project_logs = st.selectbox("Select a project:", ["Fibro", "Nova", "MDMA", "IDF"], key="logs_project")

# Add spreadsheet data display section
if selected_project_logs:
    project_watches = get_watches_from_mongodb(st.session_state.client, selected_project_logs)
    watch_names = [watch['name'] for watch in project_watches]
    
    if watch_names:
        st.subheader(f"{selected_project_logs} Project Watches")
        
        # Get spreadsheet data
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key("1jb1siFl0o7R9JsKy1gbvwshesu7Ksw2BJzNqg7Z-m1E")
        sheet = spreadsheet.sheet1
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        # Filter records for the selected project
        project_data = df[df['watch name'].isin(watch_names)]
        
        if not project_data.empty:
            display_columns = ['watch name', 'email', 'last updated', 'last sync', 
                             'last hr value', 'last battery', 'fail count', 
                             'morning_scan', 'noon_scan', 'evening_scan', 'finish date']
            
            st.dataframe(project_data[display_columns])
        else:
            st.info(f"No registered watches found for {selected_project_logs} project.")
    else:
        st.info(f"No watches configured for {selected_project_logs} project.")