import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pypdf
import io
import re
import email
from email import policy
import extract_msg

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("Automated RFQ completeness audit and approved service station matching.")

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
                        extracted_text += f"\n--- Embedded PDF in EML: {att_name} ---\n"
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
                        extracted_text += f"\n--- Embedded PDF in MSG: {att_name} ---\n"
                        for page in pdf_reader.pages:
                            extracted_text += page.extract_text() or ""
                    except Exception as err:
                        extracted_text += f"\n[Could not parse PDF attachment {att_name}: {err}]\n"
        elif file_name.endswith(".txt"):
            extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
    return extracted_text

def parse_rfq_brief(primary_text, full_text):
    brief = {
        "vessel": "Not specified",
        "eta": "Not specified",
        "port": "Not specified",
        "defect": "Not clearly identified",
        "spares": "None explicitly requested"
    }
    
    # Clean text to avoid brand interference with ports
    scrubbed_primary = re.sub(r'\btokyo\s+keiki\b', 'maker_keiki', primary_text, flags=re.IGNORECASE)
    scrubbed_full = re.sub(r'\btokyo\s+keiki\b', 'maker_keiki', full_text, flags=re.IGNORECASE)
    
    # 1. Vessel extraction (check full text)
    vessel_match = re.search(r'(?:vessel|m/v|m\.v\.|mt|m\.t\.)\s*[:\-]?\s*([A-Za-z0-9\s\-]+?)(?=[,\.\n\r]|\s+(?:is|has|calling|arriving|eta|imo))', full_text, re.IGNORECASE)
    if vessel_match:
        name = vessel_match.group(1).strip()
        if len(name) > 2 and len(name) < 30 and name.lower() not in ["s", "name", "the"]:
            brief["vessel"] = name.upper()

    # 2. ETA extraction (check primary message first, then full text)
    eta_match = re.search(r'(?:eta|arrival|arriving|calling\s+on)\s*[:\-]?\s*(?:is\s+on\s+the|is\s+on|on\s+the|on)?\s*([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:\s+[0-9]{2,4})?(?:\s+agw\s+wp|\s+agw|\s+wp)?|[0-9]{1,2}[\/\.\-][0-9]{1,2}(?:[\/\.\-][0-9]{2,4})?(?:\s+agw\s+wp|\s+agw|\s+wp)?|[0-9]{1,2}(?:st|nd|rd|th)?(?:\s+agw\s+wp|\s+agw|\s+wp)?)', primary_text, re.IGNORECASE)
    if not eta_match:
        eta_match = re.search(r'(?:eta|arrival|arriving|calling\s+on)\s*[:\-]?\s*(?:is\s+on\s+the|is\s+on|on\s+the|on)?\s*([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:\s+[0-9]{2,4})?(?:\s+agw\s+wp|\s+agw|\s+wp)?|[0-9]{1,2}[\/\.\-][0-9]{1,2}(?:[\/\.\-][0-9]{2,4})?(?:\s+agw\s+wp|\s+agw|\s+wp)?|[0-9]{1,2}(?:st|nd|rd|th)?(?:\s+agw\s+wp|\s+agw|\s+wp)?)', full_text, re.IGNORECASE)
    if eta_match:
        val = eta_match.group(1).strip()
        if len(val) >= 2:
            brief["eta"] = val.upper()

    # 3. Port extraction: Give priority to primary text
    found_port = False
    for port, country in PORT_TO_COUNTRY.items():
        if re.search(r'\b' + re.escape(port) + r'\b', scrubbed_primary, re.IGNORECASE):
            brief["port"] = f"{port.title()} ({country.upper()})"
            found_port = True
            break
            
    if not found_port:
        for port, country in PORT_TO_COUNTRY.items():
            if re.search(r'\b' + re.escape(port) + r'\b', scrubbed_full, re.IGNORECASE):
                brief["port"] = f"{port.title()} ({country.upper()})"
                break

    # 4. Defect / Scope extraction
    defect_sentences = []
    lines = full_text.splitlines()
    for line in lines:
        l_lower = line.lower()
        if any(w in l_lower for w in ["defect", "fault", "alarm", "error", "malfunction", "apt", "annual test", "gyro", "radar", "vdr", "not working", "fails", "failure"]):
            clean_line = line.strip()
            if len(clean_line) > 10 and len(clean_line) < 250:
                defect_sentences.append(clean_line)
                if len(defect_sentences) == 2:
                    break
    if defect_sentences:
        brief["defect"] = " | ".join(defect_sentences)

    # 5. Spares extraction
    spares_found = []
    for line in lines:
        l_lower = line.lower()
        if any(w in l_lower for w in ["spare", "part", "p/n", "part number", "replacement", "battery", "magnetron"]):
            clean_line = line.strip()
            if len(clean_line) > 5 and len(clean_line) < 200:
                spares_found.append(clean_line)
                if len(spares_found) == 2:
                    break
    if spares_found:
        brief["spares"] = " | ".join(spares_found)

    return brief

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
        pasted_lower = rfq_pasted_text.lower()
        
        # 2. RFQ Executive Brief
        brief_data = parse_rfq_brief(rfq_pasted_text, combined_text)
        st.markdown("---")
        st.subheader("2. RFQ Executive Brief")
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            st.info(f"**Vessel Name:** {brief_data['vessel']}")
            st.info(f"**Vessel ETA:** {brief_data['eta']}")
        with col_b2:
            st.info(f"**Port / Destination:** {brief_data['port']}")
            st.warning(f"**Spares Inquired:** {brief_data['spares']}")
        with col_b3:
            st.warning(f"**Reported Problem / Scope:** {brief_data['defect']}")

        # 3. Completeness Audit
        st.markdown("---")
        st.subheader("3. RFQ Completeness Audit")
        
        missing_items = []
        if not any(k in text_lower for k in ["eta", "etd", "arrival", "departure", "calling", "date"]):
            missing_items.append("Vessel Schedule (ETA / ETD / Date of Attendance)")
        if not any(k in text_lower for k in ["agent", "agency", "husbandry", "pic", "contact"]):
            missing_items.append("Local Port Agent details")
        if not any(k in text_lower for k in ["maker", "model", "type", "s/n", "serial", "jrc", "furuno", "sperry", "yokogawa", "anschutz", "tokyo keiki", "danelec", "macgregor"]):
            missing_items.append("Equipment Maker, Model, or Serial Number")
        if not any(k in text_lower for k in ["alarm", "fault", "defect", "error", "malfunction", "survey", "apt", "annual", "issue", "problem"]):
            missing_items.append("Fault Description / Alarm Codes / Scope of Attendance")

        if missing_items:
            st.error("Missing critical operational data. Revert to client requesting:")
            for item in missing_items:
                st.write(f"- **{item}**")
        else:
            st.success("All operational essentials detected in the customer inquiry.")

        # 4. Station Matching from Google Sheet Directory
        st.markdown("---")
        st.subheader("4. Recommended Service Stations")

        if not df.empty:
            target_countries = set()
            
            # Remove Tokyo Keiki brand noise so it doesn't trigger Japan
            search_primary = re.sub(r'\btokyo\s+keiki\b', 'maker_keiki', pasted_lower)
            search_full = re.sub(r'\btokyo\s+keiki\b', 'maker_keiki', text_lower)
            
            # Step A: Check ports in pasted message first
            for port, country in PORT_TO_COUNTRY.items():
                pattern = r'\b' + re.escape(port) + r'\b'
                if re.search(pattern, search_primary):
                    target_countries.add(country)
            
            # Step B: If no port in pasted text, check full text
            if not target_countries:
                for port, country in PORT_TO_COUNTRY.items():
                    pattern = r'\b' + re.escape(port) + r'\b'
                    if re.search(pattern, search_full):
                        target_countries.add(country)

            # Step C: Fallback to country names only if still no port matched
            if not target_countries:
                for val in df["Country"].dropna().unique():
                    c_str = str(val).strip().lower()
                    if c_str and len(c_str) > 2:
                        pattern = r'\b' + re.escape(c_str) + r'\b'
                        if re.search(pattern, search_primary):
                            target_countries.add(c_str)
                            
                if not target_countries:
                    for val in df["Country"].dropna().unique():
                        c_str = str(val).strip().lower()
                        if c_str and len(c_str) > 2:
                            pattern = r'\b' + re.escape(c_str) + r'\b'
                            if re.search(pattern, search_full):
                                target_countries.add(c_str)

            if target_countries:
                st.info(f"Target scope locked to: {', '.join([c.upper() for c in target_countries])}")
                matched_indices = []
                for idx, row in df.iterrows():
                    row_country = str(row.get("Country", "")).strip().lower()
                    if row_country in target_countries:
                        matched_indices.append(idx)
                results_df = df.loc[matched_indices]
                st.dataframe(results_df, use_container_width=True)
            else:
                st.info("No specific service location detected. Showing full directory below:")
                st.dataframe(df, use_container_width=True)
                
            with st.expander("Show Extracted Text from Message & Attachments"):
                st.text(combined_text)
        else:
            st.warning("Service station directory is empty or inaccessible.")
