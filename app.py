import base64
import email
from email import policy
import io
import json
import os
import re
import extract_msg
import pandas as pd
from PIL import Image
import pypdf
import streamlit as st

# --- API CLIENTS SETUP ---
from groq import Groq

try:
    from groq import APIConnectionError, APIStatusError, RateLimitError
except ImportError:
    APIStatusError = Exception
    APIConnectionError = Exception
    RateLimitError = Exception

# Optional Google APIs
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_DRIVE = True
except ImportError:
    HAS_GOOGLE_DRIVE = False

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False

try:
    import google.generativeai as legacy_genai
    HAS_LEGACY_GENAI = True
except ImportError:
    HAS_LEGACY_GENAI = False

st.set_page_config(page_title="Onetech Service Station Router & Discrepancy Audit", layout="wide")
st.title("Onetech Marine Service Assistant & Discrepancy Audit")
st.markdown("Automated RFQ Parsing, Global Port Matching, Cross-Source Discrepancy Detection & AI Copilot.")


# ---------------------------------------------------------------------------
# SECRETS & KEYS
# ---------------------------------------------------------------------------
def read_secret(key_name):
    raw = ""
    try:
        raw = st.secrets.get(key_name, "") or ""
    except Exception:
        raw = ""
    if not raw:
        raw = os.environ.get(key_name, "") or ""
    return str(raw).strip().strip('"').strip("'")


groq_api_key = read_secret("GROQ_API_KEY")
gemini_api_key = read_secret("GEMINI_API_KEY")

client_groq = Groq(api_key=groq_api_key, timeout=60.0, max_retries=2) if groq_api_key else None

TEXT_MODELS = [
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
]

VISION_MODELS = [
    "llama-3.2-11b-vision-preview",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]


# ---------------------------------------------------------------------------
# GLOBAL DIRECTORY & REGIONAL FALLBACK DICTIONARIES
# ---------------------------------------------------------------------------
PORT_TO_COUNTRY = {
    # --- MALTA, CYPRUS, GREECE ---
    "malta": "MALTA", "valletta": "MALTA", "marsaxlokk": "MALTA",
    "limassol": "CYPRUS", "larnaca": "CYPRUS", "vassiliko": "CYPRUS", "cyprus": "CYPRUS",
    "piraeus": "GREECE", "thessaloniki": "GREECE", "eleusis": "GREECE",
    "perama": "GREECE", "agios theodoroi": "GREECE", "corinth": "GREECE",
    "patras": "GREECE", "volos": "GREECE", "heraklion": "GREECE",
    "syros": "GREECE", "rhodes": "GREECE", "lavrio": "GREECE",
    "megara": "GREECE", "astakos": "GREECE", "kavala": "GREECE",
    "chalkis": "GREECE", "alexandroupolis": "GREECE", "kalamata": "GREECE",

    # --- ROMANIA, BULGARIA, BLACK SEA ---
    "constanta": "ROMANIA", "constantza": "ROMANIA", "mangalia": "ROMANIA",
    "midia": "ROMANIA", "galati": "ROMANIA", "braila": "ROMANIA",
    "tulcea": "ROMANIA", "sulina": "ROMANIA",
    "varna": "BULGARIA", "burgas": "BULGARIA", "bourgas": "BULGARIA",
    "odessa": "UKRAINE", "chornomorsk": "UKRAINE", "pivdennyi": "UKRAINE",
    "yuzhny": "UKRAINE", "mykolaiv": "UKRAINE", "izmail": "UKRAINE",
    "poti": "GEORGIA", "batumi": "GEORGIA",
    "novorossiysk": "RUSSIA", "tuapse": "RUSSIA", "kavkaz": "RUSSIA",
    "taman": "RUSSIA", "st petersburg": "RUSSIA", "ust-luga": "RUSSIA",

    # --- TURKEY ---
    "tutunciftlik": "TURKEY", "tüpraş": "TURKEY", "tupras": "TURKEY",
    "izmit": "TURKEY", "yalova": "TURKEY", "tuzla": "TURKEY",
    "istanbul": "TURKEY", "aliaga": "TURKEY", "iskenderun": "TURKEY",
    "mersin": "TURKEY", "canakkale": "TURKEY", "nemrut": "TURKEY",
    "ambarli": "TURKEY", "gemlik": "TURKEY", "bandirma": "TURKEY",
    "samsun": "TURKEY", "trabzon": "TURKEY", "eregli": "TURKEY",
    "tekirdag": "TURKEY", "zeytinburnu": "TURKEY", "haydarpasa": "TURKEY",
    "diliskelesi": "TURKEY", "ceyhan": "TURKEY", "antalya": "TURKEY",
    "izmir": "TURKEY", "gulluk": "TURKEY", "derince": "TURKEY",

    # --- ITALY, FRANCE & ADRIATIC ---
    "genoa": "ITALY", "genova": "ITALY", "augusta": "ITALY", "trieste": "ITALY",
    "venice": "ITALY", "ravenna": "ITALY", "livorno": "ITALY",
    "naples": "ITALY", "cagliari": "ITALY", "gioia tauro": "ITALY",
    "taranto": "ITALY", "savona": "ITALY", "la spezia": "ITALY",
    "civitavecchia": "ITALY", "bari": "ITALY", "brindisi": "ITALY",
    "ancona": "ITALY", "palermo": "ITALY", "messina": "ITALY", "milazzo": "ITALY",
    "marseilles": "FRANCE", "marseille": "FRANCE", "fos": "FRANCE",
    "le havre": "FRANCE", "dunkirk": "FRANCE", "fayard": "FRANCE",
    "bordeaux": "FRANCE", "st nazaire": "FRANCE", "nantes": "FRANCE",
    "koper": "SLOVENIA", "rijeka": "CROATIA", "split": "CROATIA",

    # --- SPAIN, GIBRALTAR & PORTUGAL ---
    "algeciras": "SPAIN", "valencia": "SPAIN", "barcelona": "SPAIN",
    "las palmas": "SPAIN", "bilbao": "SPAIN", "cartagena": "SPAIN",
    "huelva": "SPAIN", "tarragona": "SPAIN", "malaga": "SPAIN",
    "vigo": "SPAIN", "cadiz": "SPAIN", "castellon": "SPAIN",
    "gibraltar": "GIBRALTAR",
    "lisbon": "PORTUGAL", "sines": "PORTUGAL", "leixoes": "PORTUGAL",

    # --- NORTHERN EUROPE ---
    "rotterdam": "NETHERLANDS", "amsterdam": "NETHERLANDS", "antwerp": "BELGIUM",
    "hamburg": "GERMANY", "bremen": "GERMANY", "bremerhaven": "GERMANY",
    "felixstowe": "UK", "southampton": "UK", "london": "UK",

    # --- MIDDLE EAST & AFRICA ---
    "dubai": "UAE", "fujairah": "UAE", "jebel ali": "UAE", "abu dhabi": "UAE",
    "sohar": "OMAN", "salalah": "OMAN", "muscat": "OMAN",
    "dammam": "SAUDI ARABIA", "jeddah": "SAUDI ARABIA", "jubail": "SAUDI ARABIA",
    "doha": "QATAR", "bahrain": "BAHRAIN", "kuwait": "KUWAIT",
    "alexandria": "EGYPT", "port said": "EGYPT", "suez": "EGYPT", "suez canal": "EGYPT",
    "casablanca": "MOROCCO", "tangier": "MOROCCO", "algiers": "ALGERIA", "tunis": "TUNISIA",

    # --- ASIA & AMERICAS ---
    "singapore": "SINGAPORE", "shanghai": "CHINA", "ningbo": "CHINA",
    "busan": "SOUTH KOREA", "tokyo": "JAPAN", "yokohama": "JAPAN",
    "houston": "USA", "new orleans": "USA", "new york": "USA", "panama": "PANAMA",
    "panama canal": "PANAMA", "santos": "BRAZIL", "paranagua": "BRAZIL",
}

NEIGHBORING_COUNTRIES = {
    "malta": ["italy", "greece", "tunisia", "cyprus", "spain"],
    "italy": ["malta", "greece", "france", "croatia", "spain", "turkey"],
    "greece": ["malta", "cyprus", "turkey", "italy", "bulgaria", "romania", "egypt"],
    "cyprus": ["greece", "turkey", "egypt", "israel", "lebanon", "malta"],
    "romania": ["bulgaria", "turkey", "greece", "ukraine", "italy"],
    "bulgaria": ["romania", "turkey", "greece", "cyprus", "italy"],
    "turkey": ["greece", "bulgaria", "romania", "cyprus", "italy", "egypt"],
    "spain": ["gibraltar", "portugal", "france", "morocco", "italy"],
    "portugal": ["spain", "gibraltar", "france", "morocco"],
    "gibraltar": ["spain", "portugal", "morocco", "france"],
    "netherlands": ["belgium", "germany", "uk", "france"],
    "belgium": ["netherlands", "germany", "france", "uk"],
    "germany": ["netherlands", "belgium", "denmark", "poland"],
    "uae": ["oman", "saudi arabia", "qatar", "bahrain", "kuwait"],
    "saudi arabia": ["uae", "bahrain", "qatar", "kuwait", "oman", "egypt"],
    "singapore": ["malaysia", "indonesia", "thailand", "vietnam"],
    "china": ["south korea", "japan", "taiwan", "singapore"],
    "south korea": ["china", "japan", "singapore"],
    "brazil": ["argentina", "uruguay", "chile", "panama"],
}

KNOWN_MAKERS = [
    "sperry marine", "sperry", "jrc", "alphatron", "furuno",
    "tokyo keiki", "anschutz", "raytheon", "yokogawa", "ydk",
    "macgregor", "danelec", "headway", "consilium", "highlander",
    "wartsila", "cobham", "sailor", "jotron", "netwave", "simrad", "entel"
]

COUNTRY_ALIASES = {}
for _country_name in set(PORT_TO_COUNTRY.values()):
    COUNTRY_ALIASES[_country_name.lower()] = _country_name
for _country_key, _neighs in NEIGHBORING_COUNTRIES.items():
    COUNTRY_ALIASES[_country_key.lower()] = _country_key.upper()
    for _neigh in _neighs:
        COUNTRY_ALIASES[_neigh.lower()] = _neigh.upper()

COUNTRY_ALIASES.update({
    "uae": "UAE", "u.a.e.": "UAE", "united arab emirates": "UAE",
    "usa": "USA", "u.s.a.": "USA", "united states": "USA",
    "uk": "UK", "united kingdom": "UK", "great britain": "UK",
    "south korea": "SOUTH KOREA", "korea": "SOUTH KOREA",
    "hellas": "GREECE", "ελλάδα": "GREECE", "ελλαδα": "GREECE",
    "μάλτα": "MALTA", "μαλτα": "MALTA",
    "ρουμανία": "ROMANIA", "ρουμανια": "ROMANIA",
    "τουρκία": "TURKEY", "τουρκια": "TURKEY", "türkiye": "TURKEY",
    "κύπρος": "CYPRUS", "κυπρος": "CYPRUS", "brasil": "BRAZIL",
})

RESULT_DEFAULTS = {
    "vessel_name": "Not specified",
    "eta": "Not specified",
    "port": "Not specified",
    "country": "Not specified",
    "makers": [],
    "scope": "Standard technical attendance inquiry.",
    "spares_requested": "Inquired per inquiry",
    "discrepancies": [],
    "missing_critical_data": [],
}

PORT_KEYS_BY_LENGTH = sorted(PORT_TO_COUNTRY.keys(), key=len, reverse=True)
COUNTRY_KEYS_BY_LENGTH = sorted(COUNTRY_ALIASES.keys(), key=len, reverse=True)


# ---------------------------------------------------------------------------
# TEXT EXTRACTION & SANITIZATION
# ---------------------------------------------------------------------------
def extract_text_from_file(uploaded_file):
    extracted_text = ""
    file_name = uploaded_file.name.lower()
    try:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
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
                        for page in pdf_reader.pages[:15]:
                            extracted_text += page.extract_text() or ""
                    except Exception:
                        pass
        elif file_name.endswith(".txt"):
            extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
    return extracted_text[:12000]


def is_office_address_line(line):
    s = (line or "").strip()
    if not s:
        return False
    has_piraeus = re.search(r"(?i)piraeus|πειραι", s) is not None
    has_postal = re.search(r"\b18[0-9]\s*\d{2}\b", s) is not None
    has_contact = re.search(r"(?i)\b(tel|telephone|phone|fax|mobile|email|e-mail|web|website)\b|www\.|https?://|@", s) is not None
    has_greece = re.search(r"(?i)\b(greece|hellas)\b|ελλ[αά]δ", s) is not None
    has_company = re.search(r"(?i)\bonetech\b|one[\s\-]*tech|mega\s+shipping|aage\s+hempel", s) is not None
    has_street = re.search(r"(?i)vasilikon\s*51|akti\s+moutsopoulou|akti\s+miaouli|fuerteventura", s) is not None
    operational = re.search(r"(?i)^\s*(port|λιμ[αά]νι|λιμανι)\b|\b(eta|etd|berth|calling|call at|arrival|arriving|anchorage|destination|bunker|vessel)\b", s) is not None
    if operational and not has_street and not has_postal:
        return False
    if has_street or (has_piraeus and (has_postal or has_contact)) or (has_company and (has_piraeus or has_postal or has_contact or has_greece)):
        return True
    return False


def clean_signatures(text):
    if not text:
        return ""
    cleaned = re.sub(r"(?i)\b(?:mobile|mob|cell)\b\s*[:\.\-]?\s*[\+\d\s\(\)\/]{5,}", " ", text)
    cleaned = re.sub(r"(?i)\b(?:tel|telephone|phone|fax)\b\s*[:\.\-]?\s*[\+\d\s\(\)\/]{5,}", " ", cleaned)
    cleaned = re.sub(r"(?i)vasilikon\s*51[^\n]*", " ", cleaned)
    cleaned = re.sub(r"(?i)piraeus\s*185\d\d\s*greece", " ", cleaned)
    kept = []
    skip_bare_country = False
    for line in cleaned.splitlines():
        if is_office_address_line(line):
            skip_bare_country = True
            continue
        if skip_bare_country and re.fullmatch(r"(?i)\s*(greece|hellas|piraeus|πειραιάς|πειραιας|ελλάδα|ελλαδα)\s*\.?\s*", line):
            skip_bare_country = False
            continue
        skip_bare_country = False
        kept.append(line)
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clean_vessel_name(raw_name):
    if not raw_name or str(raw_name).strip().lower() in {"not specified", "n/a", "none", "unknown", "null"}:
        return "Not specified"
    text = str(raw_name).strip().strip('"').strip("'")
    text = re.sub(r"(?i)^(m/v|m/t|mv|mt|vessel|ship)\s*[:\-]?\s*", "", text)
    text = re.sub(r"(?i)\b(will|at|eta|port|call|calling|arr|arriving|due|to|for|is|and|the|in|on|sailing)\b.*$", "", text)
    text = re.sub(r"(?i)\btbn\b", " / ", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text).strip(" /-")
    parts = [p.strip(" /-") for p in text.split("/") if p.strip(" /-")][:2]
    cleaned_parts = []
    for part in parts:
        words = part.split()[:3]
        if words:
            cleaned_parts.append(" ".join(words))
    return " / ".join(cleaned_parts).title() if cleaned_parts else "Not specified"


def _overlaps(span, spans):
    start, end = span
    for s, e in spans:
        if start < e and end > s:
            return True
    return False


def ports_in_text(text):
    if not text:
        return []
    lower = text.lower()
    found = []
    taken = []
    for port_key in PORT_KEYS_BY_LENGTH:
        pattern = rf"(?<![a-z0-9]){re.escape(port_key)}(?![a-z0-9])"
        for match in re.finditer(pattern, lower):
            span = match.span()
            if _overlaps(span, taken):
                continue
            if port_key == "mobile":
                after_snippet = lower[span[1]:span[1]+25]
                before_snippet = lower[max(0, span[0]-25):span[0]]
                if re.match(r"^\s*[:\.\-\+]?\s*\d", after_snippet) or re.search(r"(?:tel|phone|fax|cell|contact|mob)\s*[:\.\-]?\s*$", before_snippet):
                    continue
            taken.append(span)
            found.append((span[0], span[1], port_key, PORT_TO_COUNTRY[port_key]))
    found.sort(key=lambda item: item[0])
    return found


def find_country(text):
    if not text:
        return None
    lower = text.lower()
    for alias in COUNTRY_KEYS_BY_LENGTH:
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        if re.search(pattern, lower):
            return COUNTRY_ALIASES[alias]
    return None


def choose_primary_port(text):
    found = ports_in_text(text)
    if not found:
        return "Not specified", "Not specified", []
    lower = (text or "").lower()

    thread_split = re.search(r"(?im)(?:^|\n)\s*(?:from\s*:|sent\s*:|-----original message-----|on\s+.*wrote\s*:)", text)
    first_reply_pos = thread_split.start() if thread_split else len(text)

    scored = []
    for start, end, key, country in found:
        window = lower[max(0, start - 80):min(len(lower), end + 80)]
        score = 0
        for token, weight in (
            ("port", 3), ("eta", 4), ("calling", 4), ("call", 3), ("berth", 3),
            ("arrival", 3), ("destination", 3), ("anchorage", 3), ("bunker", 4), ("λιμ", 3),
        ):
            if token in window:
                score += weight

        if start < first_reply_pos:
            score += 15
        else:
            score -= 5

        if key == "piraeus" and score <= 0:
            score = -10

        scored.append((score, start, key, country))

    scored.sort(key=lambda item: (-item[0], item[1]))
    _, _, key, country = scored[0]
    return key.title(), country, found


def find_makers(text_lower, vessel_name=""):
    found = []
    vessel_lower = (vessel_name or "").lower()
    for maker in KNOWN_MAKERS:
        if not re.search(rf"(?<![a-z0-9]){re.escape(maker)}(?![a-z0-9])", text_lower or ""):
            continue
        if maker in vessel_lower:
            continue
        found.append(maker.upper())
    unique = []
    for maker in sorted(set(found), key=len, reverse=True):
        if any(maker != other and maker in other for other in unique):
            continue
        unique.append(maker)
    return unique


def parse_manual_inputs(manual_text):
    overrides = {}
    explicit = set()
    if not manual_text or not str(manual_text).strip():
        return overrides, explicit
    text = str(manual_text)

    country_match = re.search(r"(?im)(?:^|\n)\s*(?:country|χώρα|χωρα)\s*[:=]\s*([^\n]+)", text)
    if country_match:
        captured = country_match.group(1).strip()
        known = find_country(captured)
        overrides["country"] = known or captured.strip(" .,").upper()
        explicit.add("country")

    port_match = re.search(r"(?im)(?:^|\n)\s*(?:port|λιμ[αά]νι|λιμανι)\s*[:=]\s*([^\n]+)", text)
    if port_match:
        captured = port_match.group(1).strip()
        known_ports = ports_in_text(captured)
        if known_ports:
            overrides["port"] = known_ports[0][2].title()
            overrides["_port_country"] = known_ports[0][3]
        else:
            found_c = find_country(captured)
            if found_c and "country" not in explicit:
                overrides["country"] = found_c
                explicit.add("country")
                overrides["port"] = "Not specified"
            else:
                overrides["port"] = captured.strip(" .,").title()
        explicit.add("port")

    vessel_match = re.search(r"(?im)(?:^|\n)\s*(?:vessel|ship|πλο[ιί]ο|πλοιο|m/v|m/t)\s*[:=]\s*([^\n]+)", text)
    if vessel_match:
        overrides["vessel_name"] = clean_vessel_name(vessel_match.group(1))
        explicit.add("vessel_name")

    eta_match = re.search(r"(?im)(?:^|\n)\s*(?:eta|etd|arrival)\s*[:=]\s*([^\n]+)", text)
    if eta_match:
        overrides["eta"] = eta_match.group(1).strip()
        explicit.add("eta")

    maker_match = re.search(r"(?im)(?:^|\n)\s*(?:makers?|equipment|brand)\s*[:=]\s*([^\n]+)", text)
    if maker_match:
        makers = [m.strip() for m in re.split(r"[,;/|]", maker_match.group(1)) if m.strip()]
        overrides["makers"] = [m.upper() for m in makers]
        explicit.add("makers")

    if "port" not in explicit:
        known_ports = ports_in_text(text)
        if known_ports:
            overrides["port"] = known_ports[0][2].title()
            overrides["_port_country"] = known_ports[0][3]
            explicit.add("port")

    if "country" not in explicit:
        found_country = find_country(text)
        if found_country:
            overrides["country"] = found_country
            explicit.add("country")

    if "vessel_name" not in explicit:
        loose_vessel = re.search(r"(?i)\b(?:vessel|ship|πλο[ιί]ο|\bm/v\b|\bm/t\b|\bmv\b|\bmt\b)\b\s*[:\-]?\s*([A-Za-z0-9][^\n]{1,80})", text)
        if loose_vessel:
            overrides["vessel_name"] = clean_vessel_name(loose_vessel.group(1))
            explicit.add("vessel_name")

    if "country" not in explicit and overrides.get("_port_country"):
        overrides["country"] = overrides["_port_country"]

    return overrides, explicit


def normalize_result(data):
    if not isinstance(data, dict):
        return None
    result = dict(RESULT_DEFAULTS)
    for key in RESULT_DEFAULTS:
        if key in data and data.get(key) is not None:
            result[key] = data.get(key)

    makers = result.get("makers")
    if isinstance(makers, str):
        result["makers"] = [m.strip().upper() for m in re.split(r"[,;/|]", makers) if m.strip()]
    elif isinstance(makers, list):
        result["makers"] = [str(m).strip().upper() for m in makers if str(m).strip()]
    else:
        result["makers"] = []

    result["vessel_name"] = clean_vessel_name(result.get("vessel_name"))
    if str(result.get("country", "")).strip():
        canonical_c = find_country(str(result["country"]))
        result["country"] = canonical_c if canonical_c else str(result["country"]).upper()

    p_key = str(result.get("port", "")).strip().lower()
    if p_key in PORT_TO_COUNTRY and result.get("country") in ("Not specified", ""):
        result["country"] = PORT_TO_COUNTRY[p_key]

    return result


def dedupe_keep_order(items):
    seen = set()
    out = []
    for item in items:
        text = str(item).strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        out.append(text)
    return out


# ---------------------------------------------------------------------------
# LOCAL PARSER (FALLBACK)
# ---------------------------------------------------------------------------
def smart_local_parser(manual_override_text, files_text):
    cleaned_files = clean_signatures(files_text)
    blob = cleaned_files or ""
    port, country, ports = choose_primary_port(blob)
    if country == "Not specified":
        found_c = find_country(blob)
        if found_c:
            country = found_c

    vessel_name = "Not specified"
    vessel_match = re.search(r"(?i)(?:vessel|ship|πλο[ιί]ο|\bm/v\b|\bm/t\b|\bmv\b|\bmt\b)\s*[:\-]?\s*([A-Za-z0-9][^\n]{1,80})", blob)
    if vessel_match:
        vessel_name = clean_vessel_name(vessel_match.group(1))

    eta = "Not specified"
    eta_match = re.search(r"(?i)\b(?:eta|etd|arrival)\b\s*[:=]?\s*([^\n]{3,60})", blob)
    if eta_match:
        eta = eta_match.group(1).strip()

    text_lower = blob.lower()
    scope_text = "Standard technical attendance inquiry."
    if "navtex" in text_lower:
        scope_text = "NAVTEX Receiver Technical Attendance & Repair"
    elif "annual" in text_lower:
        scope_text = "Annual Radio / VDR / Navigation Survey"
    elif "spare" in text_lower:
        scope_text = "Spare parts supply"

    return normalize_result({
        "vessel_name": vessel_name,
        "eta": eta,
        "port": port,
        "country": country,
        "makers": find_makers(text_lower, vessel_name),
        "scope": scope_text,
        "spares_requested": "Inquired per inquiry",
        "discrepancies": [],
        "missing_critical_data": [],
    })


# ---------------------------------------------------------------------------
# AI PROMPT & API INTEGRATION (GROQ & GEMINI)
# ---------------------------------------------------------------------------
def build_prompt(manual_override_text, cleaned_files, image_count):
    inquiry = cleaned_files[:12000] if len(cleaned_files or "") > 12000 else (cleaned_files or "")
    photo_line = f"{image_count} photograph(s) attached." if image_count else "No photographs attached."

    return f"""You are an expert maritime technical coordinator. Parse the commercial RFQ and extract facts into JSON.

CRITICAL INSTRUCTIONS:
1. MANUAL OVERRIDE IS ABSOLUTE GROUND TRUTH. If a country, port, or vessel is typed in MANUAL OVERRIDE, use it unconditionally.
2. EMAIL THREAD CHRONOLOGY (VERY IMPORTANT):
In forwarded email chains (with 'From:', 'Sent:', 'Subject:', or 'wrote:'), the text AT THE VERY TOP is the most recent and active message.
If older emails mention an earlier port (e.g. Genova, Italy) where attendance was declined, passed, or impossible, but the latest email at the top requests service at a new port/country (e.g. Malta bunkering call), the ACTIVE service location is strictly the NEW location from the top email. Record the historical port change under "discrepancies".
3. DO NOT extract 'Piraeus' or 'Greece' from office signatures, footers, or OneTech company details.
4. If an inquiry states 'MV KIRRIBILLI TBN SEA GRACE', the vessel name is 'Kirribilli / Sea Grace'.
5. Do not mistake telephone labels ('Mob', 'Mobile') for the port of Mobile USA.
{photo_line}

MANUAL OVERRIDE:
\"\"\"{manual_override_text or ""}\"\"\"

INQUIRY TEXT:
\"\"\"{inquiry}\"\"\"

Return ONLY valid JSON matching this schema:
{{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA or 'Not specified'",
  "port": "Service port or 'Not specified'",
  "country": "Service country or 'Not specified'",
  "makers": ["Maker requiring service"],
  "scope": "Summary",
  "spares_requested": "Spares",
  "discrepancies": ["Source A says X; source B says Y"],
  "missing_critical_data": ["What is missing"]
}}"""


def clean_json(text):
    text = (text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def parse_model_json(content):
    cleaned = clean_json(content)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def run_groq_parse(prompt_text, models):
    for model in models:
        try:
            completion = client_groq.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You extract maritime RFQ facts. Reply with JSON only."},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content or ""
            parsed = normalize_result(parse_model_json(content))
            if parsed:
                return parsed, model
        except Exception:
            continue
    return None, None


def analyze_rfq(manual_override_text, files_text, image_files):
    cleaned_files = clean_signatures(files_text)
    res_json = None
    model_used = None

    if client_groq:
        prompt_text = build_prompt(manual_override_text, cleaned_files, len(image_files or []))
        parsed, model = run_groq_parse(prompt_text, TEXT_MODELS)
        if parsed:
            res_json = parsed
            model_used = f"Groq / {model}"

    if not res_json:
        res_json = smart_local_parser(manual_override_text, files_text)
        model_used = "Local Rule Engine"

    overrides, explicit = parse_manual_inputs(manual_override_text)
    for key in ("country", "port", "vessel_name", "eta", "makers"):
        if key in overrides and key in explicit:
            res_json[key] = overrides[key]

    res_json["_model_used"] = model_used
    return res_json


# ---------------------------------------------------------------------------
# GEMINI / GROQ COPILOT CHATBOT
# ---------------------------------------------------------------------------
def ask_ai_assistant(user_message, rfq_context):
    system_instruction = f"""You are the Onetech Marine Service Assistant AI Copilot.
You assist maritime technical coordinators with RFQs, service attendances, maker authorizations, and spare parts.
Current Active RFQ Context:
- Vessel Name: {rfq_context.get('vessel_name', 'Not specified')}
- Port & Country: {rfq_context.get('port', 'Not specified')} ({rfq_context.get('country', 'Not specified')})
- ETA: {rfq_context.get('eta', 'Not specified')}
- Makers: {', '.join(rfq_context.get('makers', [])) or 'None detected'}
- Scope: {rfq_context.get('scope', 'Standard')}
- Spares: {rfq_context.get('spares_requested', 'None')}
- Discrepancies: {'; '.join(rfq_context.get('discrepancies', [])) or 'None'}

Answer clearly, politely, and professionally in the requested language (English or Greek)."""

    # 1. Try Gemini first if key exists and starts with valid prefix
    if gemini_api_key and gemini_api_key.startswith("AIza"):
        if HAS_GOOGLE_GENAI:
            try:
                ai_client = genai.Client(api_key=gemini_api_key)
                response = ai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_message,
                    config=types.GenerateContentConfig(system_instruction=system_instruction)
                )
                return response.text, "Gemini 2.5 Flash"
            except Exception:
                pass
        if HAS_LEGACY_GENAI:
            try:
                legacy_genai.configure(api_key=gemini_api_key)
                model = legacy_genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction)
                response = model.generate_content(user_message)
                return response.text, "Gemini 1.5 Flash"
            except Exception:
                pass

    # 2. Call Groq with active, supported models (no hardcoded decommissioned models)
    if client_groq:
        groq_models = ["llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]
        for model in groq_models:
            try:
                completion = client_groq.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.2,
                    max_tokens=1000
                )
                return completion.choices[0].message.content, f"Groq / {model}"
            except Exception:
                continue

    return "No AI model could answer. Please verify your API keys.", "Offline"


# ---------------------------------------------------------------------------
# STREAMLIT UI & STATE MANAGEMENT
# ---------------------------------------------------------------------------
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0
if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def reset_everything():
    st.session_state.reset_count += 1
    st.session_state.parsed_data = None
    st.session_state.chat_history = []
    st.rerun()


@st.cache_data(ttl=600)
def load_directory():
    sheet_title = "Global Marine Service Station Directory - Verified Service Providers (Final Master 200)"
    if HAS_GOOGLE_DRIVE and "gcp_service_account" in st.secrets:
        try:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=["[https://www.googleapis.com/auth/drive.readonly](https://www.googleapis.com/auth/drive.readonly)"]
            )
            drive_service = build("drive", "v3", credentials=creds)
            query = f"name = '{sheet_title}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get("files", [])
            if files:
                file_id = files[0]["id"]
                request = drive_service.files().export_media(fileId=file_id, mimeType="text/csv")
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                fh.seek(0)
                return pd.read_csv(fh)
        except Exception:
            pass

    return pd.read_csv("directory.csv")


try:
    df = load_directory()
    st.sidebar.success(f"Connected to Directory. Loaded {len(df)} stations.")
except Exception as e:
    st.sidebar.error(f"Error loading directory: {e}")
    df = pd.DataFrame()

st.sidebar.markdown("---")
st.sidebar.markdown("**AI Service Status:**")
if gemini_api_key and gemini_api_key.startswith("AIza"):
    st.sidebar.success("✅ Gemini API Ready")
else:
    st.sidebar.info("ℹ️ Gemini Key Missing or Incomplete (Using Groq)")

if client_groq:
    st.sidebar.success("✅ Groq API Ready")
else:
    st.sidebar.warning("⚠️ Groq API Not Set")

if st.sidebar.button("🔄 Reset / Start New RFQ", use_container_width=True):
    reset_everything()

# Section 1: Ingestion
st.subheader("1. Ingestion & Manual Override")
col1, col2 = st.columns([1, 1])

curr_key = st.session_state.reset_count

with col1:
    rfq_pasted_text = st.text_area(
        "Manual Override / Priority Info (Port, Vessel, etc.):",
        height=180,
        placeholder="e.g. Country: Malta\nMaker: JRC",
        key=f"manual_input_{curr_key}"
    )

with col2:
    uploaded_files = st.file_uploader(
        "Upload customer files & photos (PDF, EML, MSG, TXT, JPG, PNG):",
        type=["pdf", "eml", "msg", "txt", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"file_uploader_{curr_key}"
    )

doc_files = [f for f in uploaded_files if not f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []
image_files = [f for f in uploaded_files if f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []

files_combined_text = ""
if doc_files:
    for f in doc_files:
        files_combined_text += f"\n--- Content from {f.name} ---\n"
        files_combined_text += extract_text_from_file(f)

col_btn1, col_btn2 = st.columns([2, 1])
with col_btn1:
    process_pressed = st.button("🚀 Process RFQ & Audit Discrepancies", type="primary", use_container_width=True)
with col_btn2:
    st.button("🗑️ Reset All", on_click=reset_everything, use_container_width=True)

if process_pressed:
    if not rfq_pasted_text.strip() and not uploaded_files:
        st.warning("Please provide manual text or upload at least one file/email.")
    else:
        with st.spinner("Analyzing email thread, stripping signatures, and auditing stations..."):
            st.session_state.parsed_data = analyze_rfq(rfq_pasted_text, files_combined_text, image_files)

parsed = st.session_state.parsed_data

# Section 2, 3, 4: Display Results
if parsed:
    st.markdown("---")
    st.subheader("2. RFQ Executive Brief")
    st.caption(f"Engine: {parsed.get('_model_used', 'N/A')}")

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        st.info(f"**Vessel Name:** {parsed.get('vessel_name')}")
        st.info(f"**Vessel ETA:** {parsed.get('eta')}")
    with col_b2:
        port_disp = parsed.get('port')
        country_disp = parsed.get('country')
        st.info(f"**Active Port / Destination:** {port_disp} ({country_disp})")
        makers_str = ", ".join(parsed.get('makers', [])) or "None detected"
        st.warning(f"**Maker Detected:** {makers_str}")
    with col_b3:
        st.warning(f"**Scope of Work:** {parsed.get('scope')}")
        st.warning(f"**Spares Inquired:** {parsed.get('spares_requested')}")

    st.markdown("---")
    st.subheader("3. Discrepancy & Conflict Audit (Cross-Source Check)")
    discrepancies = parsed.get("discrepancies", [])
    if discrepancies:
        st.error("Discrepancies / Historical Changes Detected Across Sources:")
        for d in discrepancies:
            st.warning(f"- {d}")
    else:
        st.success("No discrepancies detected between active instructions and attachments.")

    missing = parsed.get("missing_critical_data") or []
    if missing:
        st.info("Missing critical data: " + "; ".join(missing))

    st.markdown("---")
    st.subheader("4. Recommended Service Stations")
    target_country = str(parsed.get("country", "")).strip().lower()
    target_makers = [m.lower() for m in parsed.get("makers", [])]

    if not df.empty and target_country and target_country != "not specified":
        country_match = df[df["Country"].astype(str).str.strip().str.lower() == target_country]
        final_df = pd.DataFrame()
        matched_location_label = target_country.upper()

        def maker_filter(approved_str):
            app_lower = str(approved_str).lower()
            for m in target_makers:
                if m in app_lower or (len(m.split()) > 0 and len(m.split()[0]) >= 3 and m.split()[0] in app_lower):
                    return True
            return False

        if not country_match.empty:
            if target_makers:
                filtered = country_match[country_match["Approved Makers"].apply(maker_filter)]
                if not filtered.empty:
                    final_df = filtered
            else:
                final_df = country_match

        if final_df.empty and target_country in NEIGHBORING_COUNTRIES:
            neighbors = NEIGHBORING_COUNTRIES[target_country]
            neighbor_matches = []
            matched_neighbors = []
            for neigh in neighbors:
                neigh_match = df[df["Country"].astype(str).str.strip().str.lower() == neigh]
                if not neigh_match.empty:
                    if target_makers:
                        filtered_neigh = neigh_match[neigh_match["Approved Makers"].apply(maker_filter)]
                        if not filtered_neigh.empty:
                            neighbor_matches.append(filtered_neigh)
                            matched_neighbors.append(neigh.upper())
                    else:
                        neighbor_matches.append(neigh_match)
                        matched_neighbors.append(neigh.upper())
                        break
            if neighbor_matches:
                final_df = pd.concat(neighbor_matches, ignore_index=True)
                matched_location_label = f"{', '.join(matched_neighbors)} (Neighboring Countries to {target_country.upper()})"

        makers_formatted = ', '.join([m.upper() for m in target_makers]) if target_makers else "ALL"
        if not final_df.empty:
            if matched_location_label != target_country.upper():
                st.info(f"No approved station in **{target_country.upper()}** supports **{makers_formatted}**. Showing approved stations in neighboring countries:")
            st.success(f"Matched stations in **{matched_location_label}** for makers: {makers_formatted}")
            st.dataframe(final_df, use_container_width=True)
        else:
            st.warning(f"No approved stations found for **{makers_formatted}** in {target_country.upper()} or neighboring regions.")
            st.dataframe(df, use_container_width=True)
    else:
        st.warning("Target country is not specified or no stations matched.")

    # Section 5: AI Copilot Chatbot
    st.markdown("---")
    st.subheader("5. AI Maritime Copilot & Chatbot")
    st.caption("Ask questions about this case, troubleshoot NAVTEX/Radar, request quotation drafts, or find flights.")

    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    user_query = st.chat_input("Ask about this RFQ, equipment, or station...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("AI Copilot analyzing..."):
                reply, engine_used = ask_ai_assistant(user_query, parsed)
                st.markdown(reply)
                st.caption(f"Powered by: {engine_used}")
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

    with st.expander("Show Parsed Raw Data"):
        st.json(parsed)
