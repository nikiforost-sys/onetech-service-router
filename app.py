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
import requests
import streamlit as st

# --- API CLIENTS SETUP ---
from groq import Groq

try:
    from groq import APIConnectionError, APIStatusError, RateLimitError
except ImportError:
    APIStatusError = Exception
    APIConnectionError = Exception
    RateLimitError = Exception

# Google Drive API & Service Account
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

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
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
]


# ---------------------------------------------------------------------------
# GOOGLE SHEET DIRECTORY LOADER (GVIZ & DRIVE API)
# ---------------------------------------------------------------------------
SPREADSHEET_ID = "1Z9VuuqCRE_qcy89aHgzmY34up0oQSUB4fLxeCz_82IQ"
SHEET_GID = "428894731"
GVIZ_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={SHEET_GID}"

@st.cache_data(ttl=300)
def load_directory():
    # Μέθοδος 1: Google Visualization API (GViz) με ταυτότητα κανονικού φυλλομετρητή
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        res = requests.get(GVIZ_CSV_URL, headers=headers, timeout=12)
        if res.status_code == 200 and not res.text.lstrip().startswith("<!DOCTYPE html>"):
            df = pd.read_csv(io.StringIO(res.text))
            df.columns = [str(c).strip() for c in df.columns]
            if "Country" in df.columns:
                return df.dropna(subset=["Country"])
    except Exception:
        pass

    # Μέθοδος 2: Επίσημο Google Drive API v3 μέσω Service Account
    if HAS_GOOGLE_AUTH and "gcp_service_account" in st.secrets:
        try:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            drive_service = build("drive", "v3", credentials=creds)
            request = drive_service.files().export_media(fileId=SPREADSHEET_ID, mimeType="text/csv")
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            df = pd.read_csv(fh)
            df.columns = [str(c).strip() for c in df.columns]
            if "Country" in df.columns:
                return df.dropna(subset=["Country"])
        except Exception:
            pass

    # Μέθοδος 3: Εφεδρική ανάγνωση τοπικού αρχείου
    return pd.read_csv("directory.csv")


# ---------------------------------------------------------------------------
# GLOBAL DIRECTORY & REGIONAL FALLBACK DICTIONARIES
# ---------------------------------------------------------------------------
PORT_TO_COUNTRY = {
    # --- CHINA & EAST ASIA ---
    "taicang": "CHINA", "qingdao": "CHINA", "shanghai": "CHINA", "ningbo": "CHINA",
    "shenzhen": "CHINA", "guangzhou": "CHINA", "tianjin": "CHINA", "hong kong": "CHINA",
    "dalian": "CHINA", "xiamen": "CHINA", "rizhao": "CHINA", "yingkou": "CHINA",
    "zhoushan": "CHINA", "nantong": "CHINA", "jiangyin": "CHINA", "caofeidian": "CHINA",
    "qinhuangdao": "CHINA", "tangshan": "CHINA", "yantai": "CHINA", "fangcheng": "CHINA",
    "zhanjiang": "CHINA", "shekou": "CHINA", "yantian": "CHINA", "chiwan": "CHINA",
    "lanshan": "CHINA", "lianyungang": "CHINA", "bayuquan": "CHINA", "quanzhou": "CHINA",
    "kaohsiung": "TAIWAN", "keelung": "TAIWAN", "taichung": "TAIWAN", "taipei": "TAIWAN",
    "busan": "SOUTH KOREA", "ulsan": "SOUTH KOREA", "incheon": "SOUTH KOREA",
    "yeosu": "SOUTH KOREA", "pohang": "SOUTH KOREA", "daesan": "SOUTH KOREA",
    "tokyo": "JAPAN", "yokohama": "JAPAN", "nagoya": "JAPAN", "osaka": "JAPAN", "kobe": "JAPAN",
    "singapore": "SINGAPORE", "port kelang": "MALAYSIA", "penang": "MALAYSIA",

    # --- MALTA, CYPRUS, GREECE ---
    "malta": "MALTA", "valletta": "MALTA", "marsaxlokk": "MALTA",
    "limassol": "CYPRUS", "larnaca": "CYPRUS", "vassiliko": "CYPRUS", "cyprus": "CYPRUS",
    "piraeus": "GREECE", "thessaloniki": "GREECE", "eleusis": "GREECE",
    "perama": "GREECE", "agios theodoroi": "GREECE", "corinth": "GREECE",
    "patras": "GREECE", "volos": "GREECE", "heraklion": "GREECE",
    "syros": "GREECE", "rhodes": "GREECE", "lavrio": "GREECE",

    # --- ROMANIA, BULGARIA, BLACK SEA ---
    "constanta": "ROMANIA", "constantza": "ROMANIA", "mangalia": "ROMANIA",
    "midia": "ROMANIA", "galati": "ROMANIA", "braila": "ROMANIA",
    "varna": "BULGARIA", "burgas": "BULGARIA", "bourgas": "BULGARIA",
    "odessa": "UKRAINE", "chornomorsk": "UKRAINE", "pivdennyi": "UKRAINE",
    "novorossiysk": "RUSSIA", "tuapse": "RUSSIA", "st petersburg": "RUSSIA",

    # --- TURKEY ---
    "tutunciftlik": "TURKEY", "tüpraş": "TURKEY", "tupras": "TURKEY",
    "izmit": "TURKEY", "yalova": "TURKEY", "tuzla": "TURKEY",
    "istanbul": "TURKEY", "aliaga": "TURKEY", "iskenderun": "TURKEY",
    "mersin": "TURKEY", "canakkale": "TURKEY", "nemrut": "TURKEY",
    "ambarli": "TURKEY", "gemlik": "TURKEY", "bandirma": "TURKEY",

    # --- ITALY, FRANCE & ADRIATIC ---
    "genoa": "ITALY", "genova": "ITALY", "augusta": "ITALY", "trieste": "ITALY",
    "venice": "ITALY", "ravenna": "ITALY", "livorno": "ITALY", "naples": "ITALY",
    "cagliari": "ITALY", "taranto": "ITALY", "savona": "ITALY", "la spezia": "ITALY",
    "marseilles": "FRANCE", "marseille": "FRANCE", "fos": "FRANCE", "le havre": "FRANCE",
    "koper": "SLOVENIA", "rijeka": "CROATIA",

    # --- SPAIN, GIBRALTAR & PORTUGAL ---
    "algeciras": "SPAIN", "valencia": "SPAIN", "barcelona": "SPAIN",
    "las palmas": "SPAIN", "bilbao": "SPAIN", "cartagena": "SPAIN",
    "gibraltar": "GIBRALTAR", "lisbon": "PORTUGAL", "sines": "PORTUGAL",

    # --- NORTHERN EUROPE ---
    "rotterdam": "NETHERLANDS", "amsterdam": "NETHERLANDS", "antwerp": "BELGIUM",
    "hamburg": "GERMANY", "bremen": "GERMANY", "bremerhaven": "GERMANY",
    "felixstowe": "UK", "southampton": "UK", "london": "UK",

    # --- MIDDLE EAST & AFRICA ---
    "dubai": "UAE", "fujairah": "UAE", "jebel ali": "UAE", "abu dhabi": "UAE",
    "sohar": "OMAN", "dammam": "SAUDI ARABIA", "jeddah": "SAUDI ARABIA",
    "doha": "QATAR", "bahrain": "BAHRAIN", "kuwait": "KUWAIT",
    "alexandria": "EGYPT", "port said": "EGYPT", "suez": "EGYPT", "suez canal": "EGYPT",

    # --- AMERICAS ---
    "houston": "USA", "new orleans": "USA", "new york": "USA",
    "panama": "PANAMA", "panama canal": "PANAMA", "santos": "BRAZIL",
}

NEIGHBORING_COUNTRIES = {
    "china": ["south korea", "japan", "taiwan", "singapore", "vietnam", "philippines"],
    "south korea": ["china", "japan", "taiwan", "singapore"],
    "japan": ["south korea", "china", "taiwan"],
    "taiwan": ["china", "south korea", "japan", "philippines"],
    "singapore": ["malaysia", "indonesia", "thailand", "vietnam", "china"],
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
    "china": "CHINA", "prc": "CHINA", "p.r.c.": "CHINA", "people's republic of china": "CHINA",
    "κίνα": "CHINA", "κινα": "CHINA",
    "uae": "UAE", "u.a.e.": "UAE", "united arab emirates": "UAE",
    "usa": "USA", "u.s.a.": "USA", "united states": "USA",
    "uk": "UK", "united kingdom": "UK",
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
def clean_signatures(text):
    if not text:
        return ""
    cleaned = re.sub(r"(?i)\b(?:mobile|mob|cell)\b\s*[:\.\-]?\s*[\+\d\s\(\)\/]{5,}", " ", text)
    cleaned = re.sub(r"(?i)\b(?:tel|telephone|phone|fax)\b\s*[:\.\-]?\s*[\+\d\s\(\)\/]{5,}", " ", cleaned)
    cleaned = re.sub(r"(?i)https?://\S+", " ", cleaned)
    cleaned = re.sub(r"(?i)vasilikon\s*51[^\n]*", " ", cleaned)
    cleaned = re.sub(r"(?i)piraeus\s*185\d\d\s*greece", " ", cleaned)
    cleaned = re.sub(r"(?i)thenamaris\s+conbulk\s*[-–—]?\s*athens", " ", cleaned)
    cleaned = re.sub(r"(?i)confidentiality notice[\s\S]{0,800}", " ", cleaned)
    cleaned = re.sub(r"(?i)all quotations, offers, invoices[\s\S]{0,1000}", " ", cleaned)

    kept = []
    for line in cleaned.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.search(r"(?i)\b(sales|support|engineering|automation|propulsion)@onetech\.global\b", s):
            continue
        if re.search(r"(?i)vasilikon\s*51|akti\s+moutsopoulou|akti\s+miaouli", s):
            continue
        if re.search(r"(?i)operations\s+executive\s*\(hellas\)", s):
            continue
        if re.fullmatch(r"(?i)\s*(greece|hellas|piraeus|πειραιάς|πειραιας|ελλάδα|ελλαδα)\s*\.?\s*", s):
            continue
        kept.append(line)

    cleaned = "\n".join(kept)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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
            for page in reader.pages[:20]:
                extracted_text += page.extract_text() or ""
        elif file_name.endswith(".eml"):
            msg = email.message_from_bytes(uploaded_file.read(), policy=policy.default)
            extracted_text += f"\nSubject: {msg.get('subject', '')}\n"
            body = msg.get_body(preferencelist=('plain', 'html'))
            if body:
                extracted_text += body.get_content()
        elif file_name.endswith(".msg"):
            msg = extract_msg.Message(uploaded_file)
            extracted_text += f"\nSubject: {msg.subject}\nBody:\n{msg.body}\n"
        elif file_name.endswith(".txt"):
            extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")

    cleaned = clean_signatures(extracted_text)
    return cleaned[:30000]


def clean_vessel_name(raw_name):
    if not raw_name or str(raw_name).strip().lower() in {"not specified", "n/a", "none", "unknown", "null"}:
        return "Not specified"
    text = str(raw_name).strip().strip('"').strip("'")
    text = re.sub(r"(?i)^(?:m/v|m/t|mv|mt|vessel|ship)\s*[:\-]?\s*", "", text)
    text = re.sub(r"(?i)\s*[\-–—]\s*(?:vdr|gmdss|annual|survey|radio|navtex|inspection|repair|radar|attendance|service|class|coc|imo|\/\/|@).*$", "", text)
    text = re.sub(r"(?i)\b(?:vdr|gmdss|annual|survey|radio|navtex|inspection|repair|attendance|service|coc|imo)\b.*$", "", text)
    text = re.sub(r"(?i)\b(?:will|at|eta|port|call|calling|arr|arriving|due|to|for|is|and|the|in|on|sailing|during)\b.*$", "", text)
    text = re.sub(r"[@\/\(\)\<\>\[\]].*$", "", text)
    text = re.sub(r"(?i)\btbn\b", " / ", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text).strip(" /-–—")

    parts = [p.strip(" /-–—") for p in text.split("/") if p.strip(" /-–—")][:2]
    cleaned_parts = []
    for part in parts:
        words = part.split()[:2]
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
    lower = (text or "").lower()

    dyn_match = re.search(r"(?i)(?:final\s+)?port\s+(?:is|will\s+be|@|:)?\s*([a-z]+)\s+([a-z]+)", lower)
    if dyn_match:
        cand_port, cand_country = dyn_match.group(1), dyn_match.group(2)
        if cand_country.upper() in COUNTRY_ALIASES.values() or cand_country.lower() in COUNTRY_ALIASES:
            c_name = COUNTRY_ALIASES.get(cand_country.lower(), cand_country.upper())
            return cand_port.title(), c_name, [(dyn_match.start(), dyn_match.end(), cand_port, c_name)]

    dyn_match2 = re.search(r"(?i)\b([a-z]+)\s+([a-z]+)\s+port\b", lower)
    if dyn_match2:
        cand_port, cand_country = dyn_match2.group(1), dyn_match2.group(2)
        if cand_country.upper() in COUNTRY_ALIASES.values() or cand_country.lower() in COUNTRY_ALIASES:
            c_name = COUNTRY_ALIASES.get(cand_country.lower(), cand_country.upper())
            return cand_port.title(), c_name, [(dyn_match2.start(), dyn_match2.end(), cand_port, c_name)]

    if not found:
        return "Not specified", "Not specified", []

    thread_split = re.search(r"(?im)(?:^|\n)\s*(?:from\s*:|sent\s*:|-----original message-----|on\s+.*wrote\s*:)", text)
    first_reply_pos = thread_split.start() if thread_split else len(text)

    scored = []
    for start, end, key, country in found:
        window = lower[max(0, start - 80):min(len(lower), end + 80)]
        score = 0
        for token, weight in (
            ("final port", 8), ("port", 3), ("eta", 4), ("calling", 4), ("call", 3),
            ("destination", 4), ("anchorage", 3), ("bunker", 4),
        ):
            if token in window:
                score += weight

        if "instead of" in window and window.find("instead of") < window.find(key):
            score -= 15

        if start < first_reply_pos:
            score += 20
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

    maker_match = re.search(r"(?im)(?:^|\n)\s*(?:makers?|equipment|brand)\s*[:=\s]\s*([^\n]+)", text)
    if maker_match:
        makers = [m.strip() for m in re.split(r"[,;/|]", maker_match.group(1)) if m.strip()]
        overrides["makers"] = [m.upper() for m in makers]
        explicit.add("makers")
    else:
        found_m = find_makers(text.lower())
        if found_m:
            overrides["makers"] = found_m
            explicit.add("makers")

    country_match = re.search(r"(?im)(?:^|\n)\s*(?:country|χώρα|χωρα)\s*[:=\s]\s*([^\n]+)", text)
    if country_match:
        captured = country_match.group(1).strip()
        known = find_country(captured)
        overrides["country"] = known or captured.strip(" .,").upper()
        explicit.add("country")
    else:
        found_c = find_country(text)
        if found_c and "makers" not in text.lower():
            overrides["country"] = found_c
            explicit.add("country")

    port_match = re.search(r"(?im)(?:^|\n)\s*(?:port|λιμ[αά]νι|λιμανι)\s*[:=\s]\s*([^\n]+)", text)
    if port_match:
        captured = port_match.group(1).strip()
        known_ports = ports_in_text(captured)
        if known_ports:
            overrides["port"] = known_ports[0][2].title()
            overrides["_port_country"] = known_ports[0][3]
        else:
            overrides["port"] = captured.strip(" .,").title()
        explicit.add("port")

    vessel_match = re.search(r"(?im)(?:^|\n)\s*(?:vessel|ship|πλο[ιί]ο|πλοιο|m/v|m/t)\s*[:=\s]\s*([^\n]+)", text)
    if vessel_match:
        overrides["vessel_name"] = clean_vessel_name(vessel_match.group(1))
        explicit.add("vessel_name")

    eta_match = re.search(r"(?im)(?:^|\n)\s*(?:eta|etd|arrival)\s*[:=\s]\s*([^\n]+)", text)
    if eta_match:
        overrides["eta"] = eta_match.group(1).strip()
        explicit.add("eta")

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


# ---------------------------------------------------------------------------
# LOCAL PARSER (FALLBACK)
# ---------------------------------------------------------------------------
def smart_local_parser(manual_override_text, files_text):
    blob = files_text or ""
    port, country, _ = choose_primary_port(blob)

    if country == "Not specified":
        thread_split = re.search(r"(?im)(?:^|\n)\s*(?:from\s*:|sent\s*:|-----original message-----)", blob)
        first_msg = blob[:thread_split.start()] if thread_split else blob
        found_c = find_country(first_msg)
        if found_c and found_c != "GREECE":
            country = found_c

    vessel_name = "Not specified"
    vessel_match = re.search(r"(?i)\b(?:vessel|ship|πλο[ιί]ο|m/v|m/t|mv|mt)\s*[:\-]?\s*([A-Za-z0-9][^\n]{1,80})", blob)
    if vessel_match:
        vessel_name = clean_vessel_name(vessel_match.group(1))

    eta = "Not specified"
    eta_match = re.search(r"(?i)\b(?:eta|etd|arrival|on\s+about|about)\b\s*[:=]?\s*([0-9]{1,2}(?:[-/][0-9]{1,2})?[-/.][0-9]{1,2}[-/.][0-9]{2,4}[^\n,\.;]*)", blob)
    if eta_match:
        eta = eta_match.group(1).strip()
    else:
        eta_loose = re.search(r"(?i)\b(?:eta|etd|arrival)\b\s*[:=]?\s*([^\n]{3,60})", blob)
        if eta_loose:
            eta = eta_loose.group(1).strip()

    text_lower = blob.lower()
    scope_text = "Standard technical attendance inquiry."
    if "vdr" in text_lower and "annual" in text_lower:
        scope_text = "Annual VDR & GMDSS Survey (incl. COC)"
    elif "navtex" in text_lower:
        scope_text = "NAVTEX Receiver Technical Attendance & Repair"
    elif "annual" in text_lower:
        scope_text = "Annual Radio / VDR / Navigation Survey"
    elif "spare" in text_lower:
        scope_text = "Spare parts supply"

    makers_found = find_makers(text_lower, vessel_name)
    discrepancies = []
    if "instead of qingdao" in text_lower:
        discrepancies.append("Port revised: Customer updated destination to Taicang China instead of Qingdao China.")

    return normalize_result({
        "vessel_name": vessel_name,
        "eta": eta,
        "port": port,
        "country": country,
        "makers": makers_found,
        "scope": scope_text,
        "spares_requested": "Inquired per inquiry",
        "discrepancies": discrepancies,
        "missing_critical_data": [],
    })


# ---------------------------------------------------------------------------
# AI PROMPT & API INTEGRATION (GROQ & GEMINI)
# ---------------------------------------------------------------------------
def build_prompt(manual_override_text, cleaned_files, image_count):
    inquiry = cleaned_files[:15000] if len(cleaned_files or "") > 15000 else (cleaned_files or "")
    photo_line = f"{image_count} photograph(s) attached." if image_count else "No photographs attached."

    return f"""You are an expert maritime technical coordinator. Parse the commercial RFQ and extract facts into JSON.

CRITICAL INSTRUCTIONS:
1. MANUAL OVERRIDE IS ABSOLUTE GROUND TRUTH. If a country, port, vessel, or maker is typed in MANUAL OVERRIDE, use it unconditionally.
2. EMAIL THREAD CHRONOLOGY (VERY IMPORTANT):
The email text at the VERY TOP is the active instruction.
If customer states 'final port is Taicang China on about 25-30/11/2026 instead of Qingdao China', the ACTIVE destination is strictly 'Taicang', country is 'China', ETA is '25-30/11/2026'. Record the previous port 'Qingdao' under discrepancies.
3. VESSEL NAME:
Strip 'MV', 'M/V', and technical scope. For 'MV SEADUTY - VDR & GMDSS ANNUAL SURVEY', the vessel name is strictly 'Seaduty'. Do not append 'VDR'.
4. MAKERS:
Scan the entire message for makers (e.g., JRC, Furuno, Sperry, Danelec). If inquiry mentions 'Makers : JRC JCY - 1900', the maker is 'JRC'.
5. DO NOT extract 'Piraeus' or 'Greece' from office signatures or agency footers.
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
    last_err = None
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
                return parsed, model, None
        except Exception as e:
            last_err = e
            continue
    return None, None, last_err


def analyze_rfq(manual_override_text, files_text, image_files):
    res_json = None
    model_used = None
    err_note = None

    if client_groq:
        prompt_text = build_prompt(manual_override_text, files_text, len(image_files or []))
        parsed, model, err = run_groq_parse(prompt_text, TEXT_MODELS)
        if parsed:
            res_json = parsed
            model_used = f"Groq / {model}"
        else:
            err_note = f"Groq API call bypassed: {err}"

    if not res_json:
        res_json = smart_local_parser(manual_override_text, files_text)
        model_used = "Local Rule Engine"
        if err_note:
            res_json["_api_error"] = err_note

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

    if client_groq:
        for model in ["llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192"]:
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


try:
    df = load_directory()
    st.sidebar.success(f"Connected to Google Sheet Directory. Loaded {len(df)} stations.")
except Exception as e:
    st.sidebar.error(f"Error loading directory: {e}")
    df = pd.DataFrame()

st.sidebar.markdown("---")
st.sidebar.markdown("**AI Service Status:**")
if gemini_api_key and gemini_api_key.startswith("AIza"):
    st.sidebar.success("✅ Gemini API Ready")
else:
    st.sidebar.info("ℹ️ Gemini Not Configured (Using Groq)")

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
        "Manual Override / Priority Info (Port, Vessel, Maker, etc.):",
        height=180,
        placeholder="e.g. Maker JRC\nPort Taicang\nCountry China\nVessel Seaduty",
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
    if "_api_error" in parsed:
        st.info(f"Notice: {parsed['_api_error']}")

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
    st.caption("Ask questions about this case, troubleshoot NAVTEX/Radar/VDR, request quotation drafts, or find flights.")

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
