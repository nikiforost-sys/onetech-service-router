import streamlit as st
import pandas as pd
import urllib.request
import urllib.error
import pypdf
import io
import re
import json
import email
from email import policy
import extract_msg
from PIL import Image
import base64

st.set_page_config(page_title="Onetech Service Station Router & Discrepancy Audit", layout="wide")

st.title("Onetech Marine Service Assistant & Discrepancy Audit")
st.markdown("Automated RFQ Parsing, Global Port Matching & Cross-Source Discrepancy Detection.")

raw_groq_key = st.secrets.get("GROQ_API_KEY", "")
groq_api_key = str(raw_groq_key).strip().strip('"').strip("'")

PORT_TO_COUNTRY = {
    # --- THAILAND ---
    "kohsichang": "THAILAND", "sichang": "THAILAND", "bangkok": "THAILAND",
    "laem chabang": "THAILAND", "map ta phut": "THAILAND", "songkhla": "THAILAND",

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
    "tanjung pelepas": "MALAYSIA", "miri": "MALAYSIA", "bintulu": "MALAYSIA",
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
    "thailand": ["singapore", "malaysia", "vietnam"],
    "uae": ["oman", "saudi arabia", "qatar", "bahrain"],
    "morocco": ["spain", "portugal", "gibraltar", "algeria"],
    "algeria": ["morocco", "spain", "italy", "tunisia"]
}

KNOWN_MAKERS = [
    "sperry marine", "sperry", "jrc", "alphatron", "furuno",
    "tokyo keiki", "anschutz", "raytheon", "yokogawa", "ydk",
    "macgregor", "danelec", "headway", "consilium", "highlander",
    "wartsila", "cobham", "sailor", "jotron", "netwave", "simrad", "entel"
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
    return extracted_text[:10000]

def clean_json(text):
    text = text.strip()
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

def clean_signatures(text):
    cleaned = re.sub(r"(?i)vasilikon\s*51[^\n]*piraeus[^\n]*greece", "", text)
    cleaned = re.sub(r"(?i)akti\s*moutsopoulou[^\n]*piraeus[^\n]*greece", "", cleaned)
    cleaned = re.sub(r"(?i)piraeus\s*185\d\d\s*greece", "", cleaned)
    return cleaned

def parse_manual_inputs(manual_text):
    overrides = {}
    if not manual_text:
        return overrides

    country_match = re.search(r"(?i)country\s*[:=]\s*([a-zA-Z\s]+)", manual_text)
    if country_match:
        overrides["country"] = country_match.group(1).strip().upper()
    else:
        for c in ["thailand", "brazil", "turkey", "greece", "singapore", "china", "spain", "netherlands"]:
            if c in manual_text.lower():
                overrides["country"] = c.upper()
                break

    port_match = re.search(r"(?i)port\s*[:=]\s*([a-zA-Z0-9\s-]+)", manual_text)
    if port_match:
        overrides["port"] = port_match.group(1).strip().title()

    vessel_match = re.search(r"(?i)vessel\s*[:=]\s*([a-zA-Z0-9\s-]+)", manual_text)
    if vessel_match:
        overrides["vessel_name"] = clean_vessel_name(vessel_match.group(1))

    return overrides

def smart_local_parser(manual_override_text, files_text):
    cleaned_files = clean_signatures(files_text)
    combined = manual_override_text + "\n" + cleaned_files
    text_lower = combined.lower()

    vessel_name = "Not specified"
    vessel_match = re.search(r"(?:vessel|m/v|m/t|ship)[:\s]+([a-zA-Z0-9\s-]+)", text_lower)
    if vessel_match:
        vessel_name = clean_vessel_name(vessel_match.group(1))

    detected_port = "Not specified"
    detected_country = "Not specified"
    for port_key, country_val in PORT_TO_COUNTRY.items():
        if port_key in text_lower:
            detected_port = port_key.title()
            detected_country = country_val
            break

    found_makers = []
    for maker in KNOWN_MAKERS:
        if maker in text_lower:
            if maker in vessel_name.lower():
                continue
            found_makers.append(maker.upper())

    scope_text = "Standard technical attendance inquiry."
    if "annual" in text_lower:
        scope_text = "Annual Radio / VDR / Navigation Survey"
    elif "re-programming" in text_lower or "reprogramming" in text_lower:
        scope_text = "Re-programming of Radio and Navigation Equipment"
    elif "spare" in text_lower:
        scope_text = "Spare parts supply"

    result = {
        "vessel_name": vessel_name,
        "eta": "Not specified",
        "port": detected_port,
        "country": detected_country,
        "makers": list(set(found_makers)),
        "scope": scope_text,
        "spares_requested": "Inquired per inquiry",
        "discrepancies": [],
        "missing_critical_data": []
    }

    overrides = parse_manual_inputs(manual_override_text)
    for k, v in overrides.items():
        result[k] = v

    return result

def analyze_rfq(manual_override_text, files_text, image_files):
    cleaned_files = clean_signatures(files_text)
    res_json = None

    if groq_api_key:
        api_url = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
        api_url = api_url.strip("[]'\" ")

        prompt_text = f"""
You are an expert maritime technical coordinator. Parse the commercial RFQ and extract facts into JSON.

CRITICAL INSTRUCTIONS:
1. 'MANUAL OVERRIDE' IS ABSOLUTE GROUND TRUTH. If a country, port, or vessel is stated there, use it unconditionally.
2. DO NOT extract 'Piraeus' or 'Greece' if it comes from company footers or office addresses (OneTech or Mega Shipping).
3. If an inquiry states 'MV KIRRIBILLI TBN SEA GRACE', the vessel name is 'Kirribilli' (or 'Kirribilli / Sea Grace').
4. List any conflicting facts found across sources in 'discrepancies'.

MANUAL OVERRIDE:
\"\"\"{manual_override_text}\"\"\"

INQUIRY TEXT:
\"\"\"{cleaned_files}\"\"\"

Return ONLY valid JSON matching this schema:
{{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA or 'Not specified'",
  "port": "Port or 'Not specified'",
  "country": "Country or 'Not specified'",
  "makers": ["Maker requiring service"],
  "scope": "Summary",
  "spares_requested": "Spares",
  "discrepancies": [],
  "missing_critical_data": []
}}
"""

        messages_content = [{"type": "text", "text": prompt_text}]

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
            "messages": [{"role": "user", "content": messages_content if image_files else prompt_text}],
            "temperature": 0.1
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=req_data,
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_dict = json.loads(resp_body)
                content = resp_dict["choices"][0]["message"]["content"]
                res_json = json.loads(clean_json(content))
                if "vessel_name" in res_json:
                    res_json["vessel_name"] = clean_vessel_name(res_json["vessel_name"])
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            st.error(f"Groq HTTP Error {e.code}: {err_body}")
        except Exception as e:
            st.warning(f"Groq API Request failed: {e}. Executing local rule engine.")
    else:
        st.info("GROQ_API_KEY not detected in secrets. Running local parser.")

    if not res_json:
        res_json = smart_local_parser(manual_override_text, files_text)

    overrides = parse_manual_inputs(manual_override_text)
    for k, v in overrides.items():
        res_json[k] = v

    return res_json

@st.cache_data
def load_directory():
    return pd.read_csv("directory.csv")

try:
    df = load_directory()
    st.sidebar.success(f"Connected to Directory. Loaded {len(df)} stations.")
except Exception as e:
    st.sidebar.error(f"Error loading directory.csv: {e}")
    df = pd.DataFrame()

st.subheader("1. Ingestion & Manual Override")
col1, col2 = st.columns([1, 1])

with col1:
    rfq_pasted_text = st.text_area(
        "Manual Override / Priority Info (Port, Vessel, etc.):",
        height=180,
        placeholder="e.g. Country: Thailand\nPort: Kohsichang\nVessel: Kirribilli"
    )

with col2:
    uploaded_files = st.file_uploader(
        "Upload customer files & photos (PDF, EML, MSG, TXT, JPG, PNG):",
        type=["pdf", "eml", "msg", "txt", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

doc_files = [f for f in uploaded_files if not f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []
image_files = [f for f in uploaded_files if f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []

files_combined_text = ""
if doc_files:
    for f in doc_files:
        files_combined_text += f"\n--- Content from {f.name} ---\n"
        files_combined_text += extract_text_from_file(f)

if st.button("Process RFQ & Audit Discrepancies", type="primary"):
    if not rfq_pasted_text.strip() and not uploaded_files:
        st.warning("Please provide manual text or upload at least one file/image.")
    else:
        with st.spinner("Processing inquiry and running station audit..."):
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
            st.subheader("3. Discrepancy & Conflict Audit (Cross-Source Check)")
            discrepancies = parsed.get("discrepancies", [])
            if discrepancies:
                st.error("Discrepancies / Conflicts Detected Across Sources:")
                for d in discrepancies:
                    st.warning(f"- {d}")
            else:
                st.success("No discrepancies or conflicts detected between manual input, documents, and photo evidence.")

            st.markdown("---")
            st.subheader("4. Recommended Service Stations")

            target_country = str(parsed.get("country", "")).strip().lower()
            target_makers = [m.lower() for m in parsed.get("makers", [])]

            if not df.empty and target_country and target_country != "not specified":
                country_match = df[df["Country"].str.strip().str.lower() == target_country]

                final_df = pd.DataFrame()
                matched_location_label = target_country.upper()

                def maker_filter(approved_str):
                    app_lower = str(approved_str).lower()
                    return any(m in app_lower for m in target_makers)

                if not country_match.empty:
                    if target_makers:
                        filtered = country_match[country_match["Approved Makers"].apply(maker_filter)]
                        final_df = filtered if not filtered.empty else country_match
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
                st.warning("Target country is not specified or no stations matched.")

            with st.expander("Show Parsed Raw Inputs"):
                st.write("**Manual Override Text:**")
                st.text(rfq_pasted_text)
                st.write("**Files Text:**")
                st.text(files_combined_text)
