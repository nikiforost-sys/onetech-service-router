import streamlit as st
import pandas as pd
from google import genai
import pypdf
import io
import re
import json
import email
from email import policy
import extract_msg

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("High-Speed Maritime RFQ Parser & Station Router.")

# Προαιρετικό Gemini (αν είναι διαθέσιμο, αλλιώς εκτελείται ακαριαία ο τοπικός έξυπνος αναλυτής)
api_key = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

PORT_TO_COUNTRY = {
    "tutunciftlik": "TURKEY", "tüpraş": "TURKEY", "tupras": "TURKEY",
    "izmit": "TURKEY", "yalova": "TURKEY", "tuzla": "TURKEY",
    "istanbul": "TURKEY", "aliaga": "TURKEY", "iskenderun": "TURKEY",
    "mersin": "TURKEY", "canakkale": "TURKEY", "nemrut": "TURKEY",
    "piraeus": "GREECE", "thessaloniki": "GREECE", "eleusis": "GREECE",
    "rotterdam": "NETHERLANDS", "antwerp": "BELGIUM", "hamburg": "GERMANY",
    "algeciras": "SPAIN", "gibraltar": "GIBRALTAR", "valencia": "SPAIN",
    "barcelona": "SPAIN", "las palmas": "SPAIN", "genoa": "ITALY",
    "dubai": "UAE", "fujairah": "UAE", "jebel ali": "UAE",
    "singapore": "SINGAPORE", "shanghai": "CHINA", "ningbo": "CHINA",
    "shenzhen": "CHINA", "guangzhou": "CHINA", "qingdao": "CHINA",
    "tianjin": "CHINA", "hong kong": "CHINA", "busan": "SOUTH KOREA",
    "houston": "USA", "new orleans": "USA", "new york": "USA",
    "panama": "PANAMA", "santos": "BRAZIL"
}

KNOWN_MAKERS = [
    "sperry marine", "sperry", "jrc", "alphatron", "furuno",
    "tokyo keiki", "anschutz", "raytheon", "yokogawa", "ydk",
    "macgregor", "danelec", "headway", "consilium", "highlander",
    "wartsila", "cobham", "sailor", "jotron", "netwave", "simrad"
]

def extract_text_from_file(uploaded_file):
    extracted_text = ""
    file_name = uploaded_file.name.lower()
    try:
        if file_name.endswith(".pdf"):
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages[:15]:
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
                        for page in pdf_reader.pages[:15]:
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
                        for page in pdf_reader.pages[:15]:
                            extracted_text += page.extract_text() or ""
                    except Exception as err:
                        extracted_text += f"\n[Could not parse PDF attachment {att_name}: {err}]\n"
        elif file_name.endswith(".txt"):
            extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
    return extracted_text[:6000]

def clean_json(text):
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def clean_vessel_name(raw_name):
    """Γενικός καθαρισμός: κρατάει έως 3 λέξεις και κόβει οτιδήποτε ακολουθεί (π.χ. will, at, eta, κλπ.)"""
    if not raw_name or raw_name.lower() == "not specified":
        return "Not specified"
    
    # Λίστα διαχωριστικών λέξεων που συναντώνται μετά το όνομα του πλοίου στα RFQ
    stop_words_pattern = r"\b(will|at|eta|port|call|calling|arr|arriving|due|to|for|is|and|the|in|on|sailing)\b"
    cleaned = re.split(stop_words_pattern, raw_name, flags=re.IGNORECASE)[0]
    
    # Περιορισμός στις πρώτες 3 λέξεις μέγιστο για αποφυγή ρύπανσης
    words = cleaned.strip().split()
    if len(words) > 3:
        words = words[:3]
        
    return " ".join(words).strip().title()

def smart_local_parser(full_text):
    text_lower = full_text.lower()
    
    # 1. Εντοπισμός ονόματος πλοίου γενικά
    vessel_name = "Not specified"
    vessel_match = re.search(r"(?:vessel|m/v|m/t|ship)[:\s]+([a-zA-Z0-9\s-]+)", text_lower)
    if vessel_match:
        vessel_name = clean_vessel_name(vessel_match.group(1))
    else:
        # Fallback στις πρώτες λέξεις του κειμένου
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        if lines:
            vessel_name = clean_vessel_name(lines[0][:30])

    # 2. Εντοπισμός λιμανιού και χώρας
    detected_port = "Not specified"
    detected_country = "Not specified"
    for port_key, country_val in PORT_TO_COUNTRY.items():
        if port_key in text_lower:
            detected_port = port_key.capitalize()
            detected_country = country_val
            break
            
    # 3. Έξυπνος εντοπισμός κατασκευαστή με αποκλεισμό αν ανήκει στο όνομα του πλοίου
    found_makers = []
    for maker in KNOWN_MAKERS:
        if maker in text_lower:
            if maker in vessel_name.lower():
                continue
            found_makers.append(maker.upper())
            
    # 4. Εντοπισμός εργασίας / scope
    scope_text = "Standard service / inquiry inspection requested."
    if "annual" in text_lower:
        scope_text = "Annual Radio / VDR / Navigation Survey"
    elif "spare" in text_lower or "spares" in text_lower:
        scope_text = "Supply of spare parts / hardware component inquiry"
    elif "repair" in text_lower or "defect" in text_lower or "malfunction" in text_lower:
        scope_text = "Technical troubleshooting and defect rectification"

    return {
        "vessel_name": vessel_name,
        "eta": "Not specified",
        "port": detected_port,
        "country": detected_country,
        "makers": list(set(found_makers)),
        "scope": scope_text,
        "spares_requested": "Inquired per RFQ text",
        "missing_critical_data": []
    }

def analyze_rfq(full_text):
    if client:
        prompt = f"""
Parse the following commercial RFQ / technical inquiry and extract operational facts into JSON.
CRITICAL: Do NOT list a brand as a maker if it is part of the vessel's name (e.g. 'HTM Highlander' -> ignore Highlander).

Inquiry:
\"\"\"{full_text}\"\"\"

Return ONLY a raw JSON dictionary using these exact keys:
{{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA or 'Not specified'",
  "port": "Port or 'Not specified'",
  "country": "Country or 'Not specified'",
  "makers": ["Maker requiring service"],
  "scope": "Summary",
  "spares_requested": "Spares",
  "missing_critical_data": []
}}
"""
        try:
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            res_json = json.loads(clean_json(response.text.strip()))
            # Καθαρισμός και στο αποτέλεσμα του AI για απόλυτη ασφάλεια
            if "vessel_name" in res_json:
                res_json["vessel_name"] = clean_vessel_name(res_json["vessel_name"])
            return res_json
        except Exception:
            pass
            
    return smart_local_parser(full_text)

@st.cache_data
def load_directory():
    return pd.read_csv("directory.csv")

try:
    df = load_directory()
    st.sidebar.success(f"Connected to Directory. Loaded {len(df)} stations.")
except Exception as e:
    st.sidebar.error(f"Error loading directory.csv: {e}")
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
        with st.spinner("Processing RFQ instantly..."):
            parsed = analyze_rfq(combined_text)

        if parsed:
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

            st.markdown("---")
            st.subheader("3. RFQ Completeness Audit")
            missing = parsed.get("missing_critical_data", [])
            if missing:
                st.error("Missing critical operational data. Revert to client requesting:")
                for m in missing:
                    st.write(f"- **{m}**")
            else:
                st.success("All operational essentials detected in the customer inquiry.")

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
                        
                        makers_formatted = ', '.join([m.upper() for m in target_makers])
                        if not final_df.empty:
                            st.success(f"Matched stations in {target_country.upper()} for: {makers_formatted}")
                            st.dataframe(final_df, use_container_width=True)
                        else:
                            st.warning(f"Stations found in {target_country.upper()}, but none with explicit approval for {makers_formatted}. Showing all stations in country:")
                            st.dataframe(country_match, use_container_width=True)
                    else:
                        st.info(f"Showing all stations in {target_country.upper()} (No specific maker detected):")
                        st.dataframe(country_match, use_container_width=True)
                else:
                    st.warning(f"No service stations found in directory for country: {target_country.upper()}. Showing full directory:")
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning("Directory is empty or inaccessible.")

            with st.expander("Show Extracted Raw Text"):
                st.text(combined_text)
