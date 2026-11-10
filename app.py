import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pypdf
import email
from email import policy
import extract_msg

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("Automated RFQ completeness audit and approved service station matching.")

def extract_text_from_file(uploaded_file):
    text = ""
    file_name = uploaded_file.name.lower()
    
    try:
        if file_name.endswith(".pdf"):
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif file_name.endswith(".eml"):
            msg = email.message_from_bytes(uploaded_file.read(), policy=policy.default)
            text += f"Subject: {msg.get('subject', '')}\n"
            body = msg.get_body(preferencelist=('plain', 'html'))
            if body:
                text += body.get_content()
        elif file_name.endswith(".msg"):
            msg = extract_msg.Message(uploaded_file)
            text += f"Subject: {msg.subject}\n{msg.body}"
        elif file_name.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
        
    return text

@st.cache_data(ttl=300)
def load_directory():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet_id = "1Z9VuuqCRE_qcy89aHgzmY34up0oQSUB4fLxeCz_82IQ"
    sheet = client.open_by_key(sheet_id).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

try:
    df = load_directory()
    st.sidebar.success(f"Connected to Directory. Loaded {len(df)} stations.")
except Exception as e:
    st.sidebar.error(f"Connection error: {e}")
    df = pd.DataFrame()

st.subheader("1. Ingestion")
col1, col2 = st.columns([1, 1])

with col1:
    rfq_pasted_text = st.text_area(
        "Paste RFQ text / email body here:",
        height=180,
        placeholder="Vessel name, port, equipment maker/model, defect description..."
    )

with col2:
    uploaded_files = st.file_uploader(
        "Upload customer files (PDF, EML, MSG, TXT):",
        type=["pdf", "eml", "msg", "txt"],
        accept_multiple_files=True
    )

combined_text = rfq_pasted_text + "\n"
if uploaded_files:
    for f in uploaded_files:
        combined_text += f"\n--- Content from {f.name} ---\n"
        combined_text += extract_text_from_file(f)

if st.button("Process RFQ & Find Service Stations", type="primary"):
    if not combined_text.strip():
        st.warning("Please provide RFQ text or upload at least one inquiry file.")
    else:
        text_lower = combined_text.lower()
        
        missing_items = []
        if not any(k in text_lower for k in ["eta", "etd", "arrival", "departure", "calling", "date"]):
            missing_items.append("Vessel Schedule (ETA / ETD / Date of Attendance)")
        if not any(k in text_lower for k in ["agent", "agency", "husbandry", "pic", "contact"]):
            missing_items.append("Local Port Agent details")
        if not any(k in text_lower for k in ["maker", "model", "type", "s/n", "serial", "jrc", "furuno", "sperry", "yokogawa", "anschutz", "tokyo keiki", "danelec", "macgregor"]):
            missing_items.append("Equipment Maker, Model, or Serial Number")
        if not any(k in text_lower for k in ["alarm", "fault", "defect", "error", "malfunction", "survey", "apt", "annual", "issue", "problem"]):
            missing_items.append("Fault Description / Alarm Codes / Scope of Attendance")

        st.markdown("---")
        st.subheader("2. RFQ Completeness Audit")
        
        if missing_items:
            st.error("Missing critical operational data. Revert to client requesting:")
            for item in missing_items:
                st.write(f"- **{item}**")
        else:
            st.success("All operational essentials detected in the customer inquiry.")

        st.markdown("---")
        st.subheader("3. Recommended Service Stations")

        if not df.empty:
            matched_indices = []
            for idx, row in df.iterrows():
                port_val = str(row.get("Port", "")).strip().lower()
                country_val = str(row.get("Country", "")).strip().lower()
                
                if (port_val and len(port_val) > 2 and port_val in text_lower) or (country_val and len(country_val) > 2 and country_val in text_lower):
                    matched_indices.append(idx)

            if matched_indices:
                results_df = df.loc[matched_indices]
                st.dataframe(results_df, use_container_width=True)
            else:
                st.info("No direct port or country match detected in the inquiry. Showing full directory below:")
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("Service station directory is empty or inaccessible.")
