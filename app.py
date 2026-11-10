import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pypdf
import io
import email
from email import policy
import extract_msg

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("Automated RFQ completeness audit and approved service station matching.")

# Dictionary mapping major ports to their respective country in your directory
PORT_TO_COUNTRY = {
    # USA
    "houston": "usa",
    "new orleans": "usa",
    "los angeles": "usa",
    "long beach": "usa",
    "new york": "usa",
    "miami": "usa",
    "seattle": "usa",
    "savannah": "usa",
    # Europe
    "rotterdam": "netherlands",
    "antwerp": "belgium",
    "hamburg": "germany",
    "bremerhaven": "germany",
    "valencia": "spain",
    "barcelona": "spain",
    "algeciras": "spain",
    "piraeus": "greece",
    "genoa": "italy",
    "trieste": "italy",
    "le havre": "france",
    "marseille": "france",
    # Asia & Middle East
    "singapore": "singapore",
    "shanghai": "china",
    "ningbo": "china",
    "shenzhen": "china",
    "guangzhou": "china",
    "qingdao": "china",
    "tianjin": "china",
    "hong kong": "china",
    "busan": "south korea",
    "ulsan": "south korea",
    "tokyo": "japan",
    "yokohama": "japan",
    "kobe": "japan",
    "dubai": "uae",
    "jebel ali": "uae",
    "fujairah": "uae",
    # Others
    "santos": "brazil",
    "buenos aires": "argentina",
    "sydney": "australia",
    "melbourne": "australia",
    "chittagong": "bangladesh",
    "panama": "panama",
    "gibraltar": "gibraltar"
}

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
            text += f"Subject: {msg.subject}\nBody:\n{msg.body}\n"
            
            for attachment in msg.attachments:
                att_name = str(getattr(attachment, 'longFilename', '') or getattr(attachment, 'shortFilename', '')).lower()
                if att_name.endswith(".pdf") and hasattr(attachment, 'data'):
                    try:
                        pdf_stream = io.BytesIO(attachment.data)
                        pdf_reader = pypdf.PdfReader(pdf_stream)
                        text += f"\n--- Embedded PDF: {att_name} ---\n"
                        for page in pdf_reader.pages:
                            text += page.extract_text() or ""
                    except Exception as err:
                        text += f"\n[Could not parse nested PDF {att_name}: {err}]\n"
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

st.subheader("1. In
