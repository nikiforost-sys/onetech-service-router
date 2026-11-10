import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import pypdf
import io
import json
import email
from email import policy
import extract_msg

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("Automated RFQ semantic audit and approved service station matching.")

# Secure API configuration via Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Missing GEMINI_API_KEY in Streamlit Secrets. Please check your app settings.")
    st.stop()

genai.configure(api_key=api_key)

# Strictly enforce free-tier Flash models (avoids 429 quota limits on Pro)
@st.cache_resource
def get_working_model():
    flash_candidates = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    try:
        available = [
            m.name for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]
        for cand in flash_candidates:
            for av in available:
                if cand in av:
                    return genai.GenerativeModel(av)
    except Exception:
        pass
    
    return genai.GenerativeModel("gemini-2.5-flash")

model = get_working_model()

def extract_text_from_file(uploaded_file):
    extracted_text = ""
    file_name = uploaded_file.name.lower()
    try:
        if file_name.endswith(".pdf"):
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                extracted_text += page.extract_text() or ""
        elif file_name.endswith(".eml"):
            msg = email.message_from_bytes(uploaded_file.read(), policy=policy.default)
            extracted_text += f"\nSubject: {msg.get('subject', '')}\n"
            body = msg.get_body(preferencelist=('plain', 'html'))
            if body:
                extracted_text += body.get_content()
            for part in msg.iter_attachments():
                att_name = (part.get_filename() or "").lower()
                if att_name.endswith(".pdf"):
                    pdf_data = part.get_payload(decode=True)
                    if pdf_data:
                        pdf_stream = io.BytesIO(pdf_data)
                        pdf_reader = pypdf.PdfReader(pdf_stream)
                        extracted_text += f"\n--- Embedded PDF: {att_name} ---\n"
                        for page in pdf_reader.pages:
                            extracted_text += page.extract_text() or ""
        elif file_name.endswith(".msg"):
            msg = extract_msg.Message(uploaded_file)
            extracted_text += f"\nSubject: {msg.subject}\nBody:\n{msg.body}\n"
            for attachment in msg.attachments:
                att_name = str(getattr(attachment, 'longFilename', '') or getattr(attachment, 'shortFilename', '')).lower()
                att_data = getattr(attachment, 'data', None)
                if att_name.endswith(".pdf") and att_data:
                    try:
                        pdf_stream = io.BytesIO(att_data)
                        pdf_reader = pypdf.PdfReader(pdf_stream)
                        extracted_text += f"\n--- Embedded PDF: {att_name} ---\n"
                        for page in pdf_reader.pages:
                            extracted_text += page.extract_text() or ""
                    except Exception as err:
                        extracted_text += f"\n[Could not parse PDF attachment {att_name}: {err}]\n"
        elif file_name.endswith(".txt"):
            extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
    return extracted_text

def analyze_rfq_with_llm(full_text):
    prompt = f"""
You are a senior maritime technical operations coordinator. Extract key operational details from the RFQ inquiry below.
Carefully analyze semantic context:
- Do NOT confuse vessel names with equipment makers (e.g. 'HTM Highlander' is a vessel, not the maker Highlander).
- Do NOT confuse sender/receiver company locations with the actual vessel port of call.
- Extract the exact maker requiring service (e.g., YOKOGAWA, SPERRY, JRC, etc.).

Inquiry Text:
\"\"\"{full_text}\"\"\"

Return ONLY a valid JSON object without markdown formatting or code fences, with these exact keys:
{{
  "vessel_name": "String or 'Not specified'",
  "eta": "String or 'Not specified'",
  "port": "String or 'Not specified'",
  "country": "String or 'Not specified' (Target country where attendance is required)",
  "makers": ["List of makers needing service/overhaul/survey, e.g. 'YOKOGAWA', 'SPERRY MARINE'"],
  "scope": "Clear summary of defect, survey, overhaul, or requested scope of work",
  "spares_requested": "Summary of spares requested or 'None explicitly requested'",
  "missing_critical_data": ["List of missing essentials among: Vessel Schedule, Port Agent, Equipment Maker/Model, Clear Scope"]
}}
"""
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        return json.loads(raw_text.strip())
    except Exception as e:
        st.error(f"Semantic parsing error: {e}")
        return None

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
        with st.spinner("Analyzing RFQ semantics with Gemini Flash..."):
            parsed = analyze_rfq_with_llm(combined_text)

        if parsed:
            # 2. Executive Brief
            st.markdown("---")
            st.subheader("2. RFQ Executive Brief")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                st.info(f"**Vessel Name:** {parsed.get('vessel_name')}")
                st.info(f"**Vessel ETA:** {parsed.get('eta')}")
            with col_b2:
                port_disp = parsed.get('port')
                country_disp = parsed.get('country')
                st.info(f"**Port / Destination:** {port_disp} ({country_disp})")
                makers_str = ", ".join(parsed.get('makers', [])) or "None detected"
                st.warning(f"**Maker Detected:** {makers_str}")
            with col_b3:
                st.warning(f"**Reported Problem / Scope:** {parsed.get('scope')}")
                st.warning(f"**Spares Inquired:** {parsed.get('spares_requested')}")

            # 3. Completeness Audit
            st.markdown("---")
            st.subheader("3. RFQ Completeness Audit")
            missing = parsed.get("missing_critical_data", [])
            if missing:
                st.error("Missing critical operational data. Revert to client requesting:")
                for m in missing:
                    st.write(f"- **{m}**")
            else:
                st.success("All operational essentials detected in the customer inquiry.")

            # 4. Service Station Matching
            st.markdown("---")
            st.subheader("4. Recommended Service Stations")
            
            target_country = str(parsed.get("country", "")).strip().lower()
            target_makers = [m.lower() for m in parsed.get("makers", [])]

            if not df.empty:
                country_match = df[df["Country"].str.strip().str.lower() == target_country]
                
                if not country_match.empty:
                    if target_makers:
                        def maker_filter(approved_str):
                            app_lower = str(approved_str).lower()
                            return any(m in app_lower for m in target_makers)

                        final_df = country_match[country_match["Approved Makers"].apply(maker_filter)]
                        
                        if not final_df.empty:
                            st.success(f"Matched authorized stations in {target_country.upper()} for: {', '.join([m.upper() for m in target_makers])}")
                            st.dataframe(final_df, use_container_width=True)
                        else:
                            st.warning(f"Stations found in {target_country.upper()}, but none explicitly approved for {', '.join([m.upper() for m in target_makers])}. Showing all stations in country:")
                            st.dataframe(country_match, use_container_width=True)
                    else:
                        st.info(f"Showing all approved stations in {target_country.upper()} (No specific maker identified):")
                        st.dataframe(country_match, use_container_width=True)
                else:
                    st.warning(f"No service stations found in directory for country: {target_country.upper()}. Showing full directory:")
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning("Directory is empty or inaccessible.")

            with st.expander("Show Extracted Raw Text"):
                st.text(combined_text)
