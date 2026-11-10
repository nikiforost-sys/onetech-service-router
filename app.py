import streamlit as st
import pandas as pd
import requests
import pypdf
import io
import re
import json
import email
from email import policy
import extract_msg
from PIL import Image
import base64

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("High-Speed Maritime RFQ Parser with Manual Override & Image Support (Groq AI).")

groq_api_key = st.secrets.get("GROQ_API_KEY")

PORT_TO_COUNTRY = {
    # --- BRAZIL ---
    "sao francisco do sul": "BRAZIL", "santos": "BRAZIL", "paranagua": "BRAZIL",
    "rio grande": "BRAZIL", "itajai": "BRAZIL", "imbituba": "BRAZIL",
    "tubarao": "BRAZIL", "vitoria": "BRAZIL", "suape": "BRAZIL",
    "rio de janeiro": "BRAZIL", "salvador": "BRAZIL", "manaus": "BRAZIL",
    "paranaagua": "BRAZIL", "pecem": "BRAZIL", "fortaleza": "BRAZIL",

    # --- TURKEY ---
    "tutunciftlik": "TURKEY", "tüpraş": "TURKEY", "tupras": "TURKEY",
    "izmit": "TURKEY", "yalova": "TURKEY", "tuzla": "TURKEY",
    "istanbul": "TURKEY", "aliaga": "TURKEY", "iskenderun": "TURKEY",
    "mersin": "TURKEY", "canakkale": "TURKEY", "nemrut": "TURKEY",
    "ambarli": "TURKEY", "gemlik": "TURKEY", "bandirma": "TURKEY",
    "samsun": "TURKEY", "trabzon": "TURKEY", "eregli": "TURKEY",
    "tekirdag": "TURKEY", "zeytinburnu": "TURKEY", "haydarpasa": "TURKEY",

    # --- GREECE ---
    "piraeus": "GREECE", "thessaloniki": "GREECE", "eleusis": "GREECE",
    "perama": "GREECE", "agios theodoroi": "GREECE", "corinth": "GREECE",
    "patras": "GREECE", "volos": "GREECE", "heraklion": "GREECE",
    "syros": "GREECE", "rhodes": "GREECE", "lavrio": "GREECE",
    "megara": "GREECE", "astakos": "GREECE", "kavala": "GREECE",

    # --- NETHERLANDS, BELGIUM & GERMANY ---
    "rotterdam": "NETHERLANDS", "amsterdam": "NETHERLANDS", "vlissingen": "NETHERLANDS",
    "terneuzen": "NETHERLANDS", "ijmuiden": "NETHERLANDS", "moerdijk": "NETHERLANDS",
    "antwerp": "BELGIUM", "zeebrugge": "BELGIUM", "ghent": "BELGIUM",
    "ostend": "BELGIUM", "brussels": "BELGIUM",
    "hamburg": "GERMANY", "bremen": "GERMANY", "bremerhaven": "GERMANY",
    "wilhelmshaven": "GERMANY", "rostock": "GERMANY", "kiel": "GERMANY",

    # --- SPAIN, GIBRALTAR & PORTUGAL ---
    "algeciras": "SPAIN", "valencia": "SPAIN", "barcelona": "SPAIN",
    "las palmas": "SPAIN", "bilbao": "SPAIN", "cartagena": "SPAIN",
    "huelva": "SPAIN", "tarragona": "SPAIN", "malaga": "SPAIN",
    "vigo": "SPAIN", "cadiz": "SPAIN", "castellon": "SPAIN",
    "gibraltar": "GIBRALTAR",
    "lisbon": "PORTUGAL", "sines": "PORTUGAL", "leixoes": "PORTUGAL", "setubal": "PORTUGAL",

    # --- ITALY & FRANCE ---
    "genoa": "ITALY", "augusta": "ITALY", "trieste": "ITALY",
    "venice": "ITALY", "ravenna": "ITALY", "livorno": "ITALY",
    "naples": "ITALY", "cagliari": "ITALY", "gioia tauro": "ITALY",
    "taranto": "ITALY", "savona": "ITALY", "la spezia": "ITALY",
    "marseilles": "FRANCE", "le havre": "FRANCE", "dunkirk": "FRANCE",
    "fayard": "FRANCE", "bordeaux": "FRANCE", "st nazaire": "FRANCE",

    # --- MIDDLE EAST & UAE ---
    "dubai": "UAE", "fujairah": "UAE", "jebel ali": "UAE",
    "khor fakkan": "UAE", "abu dhabi": "UAE", "sharjah": "UAE",
    "ras al khaimah": "UAE", "hamriyah": "UAE",
    "sohar": "OMAN", "salalah": "OMAN", "muscat": "OMAN",
    "dammam": "SAUDI ARABIA", "jeddah": "SAUDI ARABIA", "jubail": "SAUDI ARABIA",
    "yanbu": "SAUDI ARABIA", "ras tanura": "SAUDI ARABIA",
    "doha": "QATAR", "ras laffan": "QATAR", "umesaid": "QATAR",
    "bahrain": "BAHRAIN", "mina sulman": "BAHRAIN",
    "kuwait": "KUWAIT", "shuwaikh": "KUWAIT", "shuaiba": "KUWAIT",
    "bandar abbas": "IRAN", "khark island": "IRAN",
    "basrah": "IRAQ", "um qasr": "IRAQ",

    # --- NORTH & WEST AFRICA ---
    "casablanca": "MOROCCO", "tangier": "MOROCCO", "agadir": "MOROCCO",
    "jorf lasfar": "MOROCCO", "nador": "MOROCCO", "mohammedia": "MOROCCO",
    "algiers": "ALGERIA", "oran": "ALGERIA", "annaba": "ALGERIA", "arzew": "ALGERIA",
    "alexandria": "EGYPT", "port said": "EGYPT", "suez": "EGYPT", "damietta": "EGYPT",
    "cairo": "EGYPT", "safaga": "EGYPT",
    "tunis": "TUNISIA", "sfax": "TUNISIA", "bizerte": "TUNISIA", "la goulette": "TUNISIA",
    "tripoli": "LIBYA", "benghazi": "LIBYA", "misurata": "LIBYA", "tobruk": "LIBYA",
    "lagos": "NIGERIA", "port harcourt": "NIGERIA", "onne": "NIGERIA",
    "dakar": "SENEGAL", "abidjan": "IVORY COAST", "accra": "GHANA", "tema": "GHANA",

    # --- ASIA & FAR EAST ---
    "singapore": "SINGAPORE",
    "shanghai": "CHINA", "ningbo": "CHINA", "shenzhen": "CHINA",
    "guangzhou": "CHINA", "qingdao": "CHINA", "tianjin": "CHINA",
    "hong kong": "CHINA", "dalian": "CHINA", "xiamen": "CHINA",
    "rizhao": "CHINA", "yingkou": "CHINA",
    "busan": "SOUTH KOREA", "ulsan": "SOUTH KOREA", "incheon": "SOUTH KOREA",
    "yeosu": "SOUTH KOREA", "pohang": "SOUTH KOREA", "daesan": "SOUTH KOREA",
    "tokyo": "JAPAN", "yokohama": "JAPAN", "nagoya": "JAPAN",
    "osaka": "JAPAN", "kobe": "JAPAN", "chiba": "JAPAN", "kitakyushu": "JAPAN",
    "port kelang": "MALAYSIA", "penang": "MALAYSIA", "pasir gudang": "MALAYSIA",
    "tanjung pelepas": "MALAYSIA", "kohsichang": "THAILAND", "sichang": "THAILAND",
    "miri": "MALAYSIA", "bintulu": "MALAYSIA",
    "bangkok": "THAILAND", "laem chabang": "THAILAND", "map ta phut": "THAILAND",
    "jakarta": "INDONESIA", "surabaya": "INDONESIA", "belawan": "INDONESIA",
    "batam": "INDONESIA", "balikpapan": "INDONESIA", "semarang": "INDONESIA",
    "manila": "PHILIPPINES", "cebu": "PHILIPPINES", "subic bay": "PHILIPPINES",
    "ho chi minh": "VIETNAM", "haiphong": "VIETNAM", "danang": "VIETNAM",
    "mumbai": "INDIA", "chennai": "INDIA", "kolkata": "INDIA",
    "cochin": "INDIA", "visakhapatnam": "INDIA", "mormugao": "INDIA",
    "kandla": "INDIA", "mundra": "INDIA", "nhava sheva": "INDIA",
    "colombo": "SRI LANKA", "galle": "SRI LANKA", "trincomalee": "SRI LANKA",
    "karachi": "PAKISTAN", "port qasim": "PAKISTAN",
    "chittagong": "BANGLADESH", "mongla": "BANGLADESH",

    # --- AMERICAS & CARIBBEAN ---
    "houston": "USA", "new orleans": "USA", "new york": "USA",
    "los angeles": "USA", "long beach": "USA", "savannah": "USA",
    "miami": "USA", "baltimore": "USA", "seattle": "USA",
    "philadelphia": "USA", "charleston": "USA", "port arthur": "USA",
    "galveston": "USA", "corpus christi": "USA", "baton rouge": "USA",
    "vancouver": "CANADA", "montreal": "CANADA", "halifax": "CANADA",
    "quebec": "CANADA", "prince rupert": "CANADA", "toronto": "CANADA",
    "panama": "PANAMA", "balboa": "PANAMA", "cristobal": "PANAMA",
    "colon": "PANAMA", "manzanillo": "PANAMA",
    "buenos aires": "ARGENTINA", "rosario": "ARGENTINA", "bahia blanca": "ARGENTINA",
    "la plata": "ARGENTINA", "san lorenzo": "ARGENTINA",
    "valparaiso": "CHILE", "san antonio": "CHILE", "antofagasta": "CHILE",
    "concepcion": "CHILE", "iquique": "CHILE", "talcahuano": "CHILE",
    "callao": "PERU", "paita": "PERU", "marcona": "PERU",
    "cartagena": "COLOMBIA", "barranquilla": "COLOMBIA", "santa marta": "COLOMBIA",
    "puerto cabello": "VENEZUELA", "maracaibo": "VENEZUELA",

    # --- AUSTRALIA & OCEANIA ---
    "sydney": "AUSTRALIA", "melbourne": "AUSTRALIA", "brisbane": "AUSTRALIA",
    "fremantle": "AUSTRALIA", "newcastle": "AUSTRALIA", "port hedland": "AUSTRALIA",
    "adelaide": "AUSTRALIA", "darwin": "AUSTRALIA",
    "auckland": "NEW ZEALAND", "wellington": "NEW ZEALAND", "lyttelton": "NEW ZEALAND"
}

NEIGHBORING_COUNTRIES = {
    "brazil": ["argentina", "uruguay", "panama"],
    "turkey": ["greece", "bulgaria", "cyprus", "italy"],
    "greece": ["turkey", "cyprus", "italy", "malta"],
    "netherlands": ["belgium", "germany", "france", "uk"],
    "belgium": ["netherlands", "france", "germany", "uk"],
    "germany": ["netherlands", "poland", "denmark", "france"],
    "spain": ["portugal", "france", "italy", "gibraltar", "morocco"],
    "italy": ["greece", "france", "spain", "malta"],
    "china": ["south korea", "japan", "taiwan", "singapore"],
    "south korea": ["china", "japan"],
    "thailand": ["malaysia", "singapore", "vietnam"],
    "uae": ["oman", "saudi arabia", "qatar", "bahrain"],
    "morocco": ["spain", "portugal", "gibraltar", "algeria"],
    "algeria": ["morocco", "spain", "italy", "tunisia"]
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
    if not raw_name or raw_name.lower() == "not specified":
        return "Not specified"
    stop_words_pattern = r"\b(will|at|eta|port|call|calling|arr|arriving|due|to|for|is|and|the|in|on|sailing)\b"
    cleaned = re.split(stop_words_pattern, raw_name, flags=re.IGNORECASE)[0]
    words = cleaned.strip().split()
    if len(words) > 3:
        words = words[:3]
    return " ".join(words).strip().title()

def smart_local_parser(manual_override_text, files_text):
    # Συνδυασμός: Το manual override μπαίνει ΠΡΩΤΟ για να έχει απόλυτη προτεραιότητα σε σύγκρουση
    combined = manual_override_text + "\n" + files_text
    text_lower = combined.lower()
    
    body_text = text_lower
    if "best regards" in text_lower:
        body_text = text_lower.split("best regards")[0]
    elif "regards" in text_lower:
        body_text = text_lower.split("regards")[0]

    vessel_name = "Not specified"
    vessel_match = re.search(r"(?:vessel|m/v|m/t|ship)[:\s]+([a-zA-Z0-9\s-]+)", body_text)
    if vessel_match:
        vessel_name = clean_vessel_name(vessel_match.group(1))
    else:
        vessel_match_gen = re.search(r"(?:m/v|m/t)\s+([a-zA-Z0-9\s]+)", body_text)
        if vessel_match_gen:
            vessel_name = clean_vessel_name(vessel_match_gen.group(1))

    detected_port = "Not specified"
    detected_country = "Not specified"
    for port_key, country_val in PORT_TO_COUNTRY.items():
        if port_key in body_text:
            detected_port = port_key.title()
            detected_country = country_val
            break
            
    found_makers = []
    for maker in KNOWN_MAKERS:
        if maker in body_text:
            if maker in vessel_name.lower():
                continue
            found_makers.append(maker.upper())
            
    scope_text = "Standard service / inquiry inspection requested."
    if "annual" in body_text:
        scope_text = "Annual Radio / VDR / Navigation Survey"
    elif "spare" in body_text or "spares" in body_text:
        scope_text = "Supply of spare parts / hardware component inquiry"
    elif "repair" in body_text or "defect" in body_text or "malfunction" in body_text:
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

def analyze_rfq(manual_override_text, files_text, image_files):
    if groq_api_key:
        url = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        messages_content = [
            {
                "type": "text",
                "text": f"""
Parse the following commercial RFQ / technical inquiry and extract operational facts into JSON.
CRITICAL OVERRIDE RULE: Information provided in the 'MANUAL OVERRIDE' section takes absolute priority over attached files or emails if there is any conflict (e.g., overriding port, vessel, or scope).
CRITICAL: Do NOT list a brand as a maker if it is part of the vessel's name (e.g. 'HTM Highlander' -> ignore Highlander).

MANUAL OVERRIDE (User priority input):
\"\"\"{manual_override_text}\"\"\"

ATTACHED FILES / EMAIL TEXT:
\"\"\"{files_text}\"\"\"

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
            }
        ]

        # Προσθήκη εικόνων αν ανέβασε ο χρήστης (Vision API)
        if image_files:
            for img_file in image_files:
                img_bytes = img_file.read()
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                messages_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })

        payload = {
            "model": "llama-3.2-11b-vision-preview" if image_files else "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": messages_content if image_files else messages_content[0]["text"]}] if image_files else [{"role": "user", "content": messages_content[0]["text"]}],
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                res_json = json.loads(clean_json(content))
                if "vessel_name" in res_json:
                    res_json["vessel_name"] = clean_vessel_name(res_json["vessel_name"])
                return res_json
        except Exception:
            pass
            
    return smart_local_parser(manual_override_text, files_text)

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
        "Paste RFQ text / email body or MANUAL OVERRIDE (Port/Vessel/etc):",
        height=180,
        placeholder="e.g. PORT: KOHSICHANG THAILAND or additional notes..."
    )

with col2:
    uploaded_files = st.file_uploader(
        "Upload customer files (PDF, EML, MSG, TXT, JPG, PNG):",
        type=["pdf", "eml", "msg", "txt", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

# Διαχωρισμός αρχείων κειμένου/pdf και εικόνων
doc_files = [f for f in uploaded_files if not f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []
image_files = [f for f in uploaded_files if f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []

files_combined_text = ""
if doc_files:
    for f in doc_files:
        files_combined_text += f"\n--- Content from {f.name} ---\n"
        files_combined_text += extract_text_from_file(f)

if st.button("Process RFQ & Find Service Stations", type="primary"):
    if not rfq_pasted_text.strip() and not uploaded_files:
        st.warning("Please provide manual text or upload at least one file/image.")
    else:
        with st.spinner("Processing RFQ with manual override & image analysis..."):
            parsed = analyze_rfq(rfq_pasted_text, files_combined_text, image_files)

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

            if not df.empty and target_country:
                country_match = df[df["Country"].str.strip().str.lower() == target_country]
                
                final_df = pd.DataFrame()
                matched_location_label = target_country.upper()
                
                def maker_filter(approved_str):
                    app_lower = str(approved_str).lower()
                    return any(m in app_lower for m in target_makers)

                if not country_match.empty:
                    if target_makers:
                        filtered = country_match[country_match["Approved Makers"].apply(maker_filter)]
                        if not filtered.empty:
                            final_df = filtered
                        else:
                            final_df = country_match
                    else:
                        final_df = country_match
                
                if final_df.empty and target_country in NEIGHBORING_COUNTRIES:
                    neighbors = NEIGHBORING_COUNTRIES[target_country]
                    for neigh in neighbors:
                        neigh_match = df[df["Country"].str.strip().str.lower() == neigh]
                        if not neigh_match.empty:
                            if target_makers:
                                filtered_neigh = neigh_match[neigh_match["Approved Makers"].apply(maker_filter)]
                                if not filtered_neigh.empty:
                                    final_df = filtered_neigh
                                    matched_location_label = f"{neigh.upper()} (Neighboring Country to {target_country.upper()})"
                                    break
                            else:
                                final_df = neigh_match
                                matched_location_label = f"{neigh.upper()} (Neighboring Country to {target_country.upper()})"
                                break

                makers_formatted = ', '.join([m.upper() for m in target_makers]) if target_makers else "ALL"
                
                if not final_df.empty:
                    st.success(f"Matched stations in **{matched_location_label}** for makers: {makers_formatted}")
                    st.dataframe(final_df, use_container_width=True)
                else:
                    st.warning(f"No approved stations found in {target_country.upper()} or neighboring regions. Showing full directory:")
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning("Directory is empty or target country is not specified.")

            with st.expander("Show Parsed Raw Inputs"):
                st.write("**Manual Override Text:**")
                st.text(rfq_pasted_text)
                st.write("**Files Text:**")
                st.text(files_combined_text)
