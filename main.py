import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Set page configuration
st.set_page_config(page_title="Fitbit Scheduler", layout="centered")

# Load watch names and tokens from the txt file
@st.cache
def load_watch_tokens():
    watch_tokens = {}
    with open('watch_tokens.txt', 'r') as file:
        for line in file:
            watch_name, token = line.strip().split(',')
            watch_tokens[watch_name] = token
    return watch_tokens

watch_tokens = st.secrets["watch_tokens"]
watch_names = list(watch_tokens.keys())

# Streamlit app UI
st.title("Fitbit Scheduler Setup")

with st.form(key='scheduler_form'):
    # Watch selection
    selected_watch = st.selectbox("Select your watch:", watch_names)

    

    # Email input
    email = st.text_input("Enter your email address:")

    # Sync frequency selection
    st.write("Select sync frequencies:")
    morning_scan = st.checkbox("Morning", value=False)
    noon_scan = st.checkbox("Noon", value=False)
    evening_scan = st.checkbox("Evening", value=False)
    st.write("Note: The watch will be scanned at the selected times only.")
    st.divider()
    
    ema_enable = st.checkbox("Enable EMA", value=False)
    st.write("Note: Enabling EMA only for fibro project")

    # Fail threshold input
    fail_threshold = st.slider("Set fail threshold (1-5):", min_value=1, max_value=5, value=3)

    fail_threshold_ema = st.slider("Set fail threshold for EMA (1-5):", min_value=1, max_value=5, value=3)

    st.divider()

    reset_prev_data = st.checkbox("Reset previous data", value=False)

    # Submit button
    submit_button = st.form_submit_button(label='Submit')

if submit_button:
    if not email:
        st.error("Please enter your email address.")
    else:
        # Prepare data to update the Google Sheet
        token = watch_tokens[selected_watch]

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

        if not df.empty and selected_watch in df['watch name'].values:
            if reset_prev_data:
                st.warning("This watch is already registered. Resetting existing entry.")
                # Reset the existing row
                row_index = df.index[df['watch name'] == selected_watch].tolist()[0] + 2
                sheet.update_cell(row_index, df.columns.get_loc("last updated") + 1, '')
                sheet.update_cell(row_index, df.columns.get_loc("last sync") + 1, '')
                sheet.update_cell(row_index, df.columns.get_loc("last hr value") + 1, '')
                sheet.update_cell(row_index, df.columns.get_loc("last battery") + 1, '')
                sheet.update_cell(row_index, df.columns.get_loc("fail count") + 1, 0)
                sheet.update_cell(row_index, df.columns.get_loc("ema_enabled") + 1, str(ema_enable))
                sheet.update_cell(row_index, df.columns.get_loc("fail threshold") + 1, fail_threshold)
                sheet.update_cell(row_index, df.columns.get_loc("fail threshold ema") + 1, fail_threshold_ema)

            st.warning("This watch is already registered. Updating existing entry.")

            # Update the existing row
            row_index = df.index[df['watch name'] == selected_watch].tolist()[0] + 2  # +2 to account for header and 1-indexing
            sheet.update_cell(row_index, df.columns.get_loc("email") + 1, email)
            sheet.update_cell(row_index, df.columns.get_loc("morning_scan") + 1, str(morning_scan))
            sheet.update_cell(row_index, df.columns.get_loc("noon_scan") + 1, str(noon_scan))
            sheet.update_cell(row_index, df.columns.get_loc("evening_scan") + 1, str(evening_scan))
            sheet.update_cell(row_index, df.columns.get_loc("fail threshold") + 1, fail_threshold)
            sheet.update_cell(row_index, df.columns.get_loc("ema_enabled") + 1, str(ema_enable))
            sheet.update_cell(row_index, df.columns.get_loc("fail threshold ema") + 1, fail_threshold_ema)
            
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
                'last ema time': ''

            }
            sheet.append_row(list(new_row.values()))

        st.success("Your preferences have been saved successfully!")
