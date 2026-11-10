import streamlit as st
import pandas as pd
from google import genai
import openai
import pypdf
import io
import re
import json
import email
from email import policy
import extract_msg

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("Automated RFQ semantic audit with Gemini & OpenAI Fallback Engine.")

gemini_api_key = st.secrets.get("GEMINI_API_KEY")
openai_api_key = st.secrets.get("OPENAI_API_KEY")

if not gemini_api_key:
    st.error("Missing GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

client_gemini = genai.Client(api_key=gemini_api_key)
client_openai = openai.OpenAI(api_key=openai_api_key) if openai_api_key else None

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

def analyze_rfq_with_fallback(full_text):
    prompt = f"""
You are an expert technical coordinator in maritime navigation and communication equipment supply.
Parse the following commercial RFQ / technical inquiry and extract all operational facts into JSON.

Strict Operational Guidelines:
1. Contextual Distinction: Distinguish between the vessel's identity and makers. If a vessel is named after a brand (e.g. 'HTM Highlander', 'Sperry Spirit'), do NOT list that brand as a required maker unless that equipment on board is genuinely malfunctioning or being serviced.
2. Port & Country: Identify the destination port where attendance is required, and resolve its country (e.g. Tutunciftlik -> Turkey, Piraeus -> Greece).
3. Equipment Maker: Identify ONLY the equipment maker(s) requiring attendance, overhaul, annual survey, or spares.
4. Scope of Attendance: Accurately summarize the required service, overhaul, or defect.

Inquiry:
\"\"\"{full_text}\"\"\"

Return ONLY a raw JSON dictionary without Markdown formatting or fences, using these exact keys:
{{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA / attendance schedule or 'Not specified'",
  "port": "Port of attendance or 'Not specified'",
  "country": "Country of attendance or 'Not specified'",
  "makers": ["Maker requiring service, e.g. YOKOGAWA, FURUNO"],
  "scope": "Operational summary of the requested job",
  "spares_requested": "Spares mentioned or 'None explicitly requested'",
  "missing_critical_data": ["List of missing essentials among: Schedule/ETA, Port Agent details, Maker/Model, Scope of attendance"]
}}
"""

    # 1. Δοκιμή με Gemini Flash
    try:
        response = client_gemini.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return json.loads(clean_json(response.text.strip()))
    except Exception:
        pass

    # 2. Δοκιμή με Gemini Pro
    try:
        response = client_gemini.models.generate_content(model="gemini-1.5-pro", contents=prompt)
        return json.loads(clean_json(response.text.strip()))
    except Exception:
        pass

    # 3. Εφεδρεία με OpenAI (εφόσον υπάρχει το κλειδί)
    if client_openai:
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.choices[0].message.content.strip()
            return json.loads(clean_json(raw_text))
        except Exception as e:
            st.error(f"OpenAI Fallback Error: {e}")

    st.error("Όλα τα συστήματα AI (Gemini & OpenAI) απέτυχαν προσωρινά. Δοκιμάστε ξανά.")
    return {}

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
        with st.spinner("Analyzing inquiry semantics with AI Fallback Engine..."):
            parsed = analyze_rfq_with_fallback(combined_text)

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
