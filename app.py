import streamlit as st
import pandas as pd
import pypdf
import io
import re
import json
import email
import base64
import unicodedata
import html as html_lib
from email import policy

import extract_msg
import groq
from groq import Groq
from PIL import Image, ImageOps

st.set_page_config(page_title="Onetech Service Station Router & Discrepancy Audit", layout="wide")

st.title("Onetech Marine Service Assistant & Discrepancy Audit")
st.markdown("Automated RFQ Parsing, Global Port Matching & Cross-Source Discrepancy Detection.")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "llama-3.2-11b-vision-preview"
# Groq decommissioned the 3.2 vision preview models in 2025. If VISION_MODEL is
# rejected, the app automatically retries with this replacement, and finally
# falls back to a text-only analysis.
VISION_FALLBACK_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

MAX_CHARS_PER_FILE = 10000
MAX_TOTAL_CHARS = 24000
MAX_IMAGES = 5
MAX_IMAGE_SIDE = 1600


def get_groq_api_key():
    try:
        raw_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        raw_key = ""
    return str(raw_key or "").strip().strip('"').strip("'")


groq_api_key = get_groq_api_key()
client = Groq(api_key=groq_api_key, timeout=30.0, max_retries=2) if groq_api_key else None

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

# NOTE: "cartagena" appears twice in PORT_TO_COUNTRY above (SPAIN and COLOMBIA).
# In a Python dict the last entry wins (COLOMBIA). The app therefore treats it as
# an ambiguous port: it uses country hints found in the text and otherwise flags
# the case for manual verification.
AMBIGUOUS_PORTS = {
    "cartagena": ["SPAIN", "COLOMBIA"]
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

# Alternative spellings of country names (canonical key -> aliases). Used to
# normalise what the LLM / the user types and to match the "Country" column of
# directory.csv, whichever spelling the CSV uses.
COUNTRY_ALIASES = {
    "uae": ["united arab emirates", "u.a.e.", "emirates"],
    "usa": ["united states", "united states of america", "u.s.a.", "u.s.", "us", "america"],
    "uk": ["united kingdom", "great britain", "britain", "england", "u.k."],
    "south korea": ["korea", "republic of korea", "rok", "s. korea"],
    "turkey": ["türkiye", "turkiye"],
    "netherlands": ["the netherlands", "holland"],
    "ivory coast": ["cote d'ivoire", "côte d'ivoire"],
    "saudi arabia": ["ksa", "saudi", "kingdom of saudi arabia"],
    "philippines": ["the philippines"],
    "vietnam": ["viet nam"],
    "brazil": ["brasil"],
    "greece": ["hellas", "ellada"],
    "germany": ["deutschland"],
    "spain": ["espana", "españa"],
    "italy": ["italia"],
    "iran": ["islamic republic of iran"],
    "china": ["prc", "people's republic of china"],
}

# Aliases that are too ambiguous to be detected inside free-form manual text.
FREEFORM_SKIP_ALIASES = {
    "us", "u.s.", "emirates", "america", "britain", "saudi", "rok", "korea", "s. korea", "england"
}

# Words that mark a vessel-name capture as generic text instead of a real name.
GENERIC_VESSEL_WORDS = {"name", "names", "details", "particulars", "info", "information", "s", "is"}


# ---------------------------------------------------------------------------
# GENERIC TEXT HELPERS
# ---------------------------------------------------------------------------
def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text)) if not unicodedata.combining(c))


def _as_text(value, default="Not specified"):
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value if v)
    elif isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text if text else default


def _as_list(value, split=False):
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[,;\n]", value) if split else [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    result = []
    for item in items:
        if isinstance(item, dict):
            item = json.dumps(item, ensure_ascii=False)
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _add_note(notes, text):
    if text and text not in notes:
        notes.append(text)


def _same_text(a, b):
    na = strip_accents(a).lower().strip()
    nb = strip_accents(b).lower().strip()
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def html_to_text(raw_html):
    raw_html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    raw_html = re.sub(r"(?s)<[^>]+>", " ", raw_html)
    raw_html = html_lib.unescape(raw_html)
    return re.sub(r"[ \t]+", " ", raw_html)


# ---------------------------------------------------------------------------
# COUNTRY HELPERS
# ---------------------------------------------------------------------------
_ALIAS_TO_CANONICAL = {}
for _canonical, _aliases in COUNTRY_ALIASES.items():
    _ALIAS_TO_CANONICAL[strip_accents(_canonical).lower()] = _canonical
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[strip_accents(_alias).lower()] = _canonical


def normalize_country(raw):
    if raw is None:
        return "Not specified"
    value = re.sub(r"\s+", " ", strip_accents(str(raw)).strip().lower())
    if not value or value in ("not specified", "none", "n/a", "na", "unknown", "null", "-"):
        return "Not specified"
    canonical = _ALIAS_TO_CANONICAL.get(value, value)
    return canonical.upper()


def country_variants(country_name):
    key = strip_accents(country_name).strip().lower()
    key = _ALIAS_TO_CANONICAL.get(key, key)
    variants = {key}
    for alias in COUNTRY_ALIASES.get(key, []):
        variants.add(strip_accents(alias).strip().lower())
    return variants


def get_country_matches(frame, country_name):
    variants = country_variants(country_name)
    normalized_column = frame["Country"].astype(str).map(lambda v: strip_accents(v).strip().lower())
    return frame[normalized_column.isin(variants)]


def _build_freeform_country_patterns():
    terms = {}
    for country in set(PORT_TO_COUNTRY.values()):
        terms[strip_accents(country).lower()] = country
    for canonical, aliases in COUNTRY_ALIASES.items():
        for alias in [canonical] + aliases:
            alias_norm = strip_accents(alias).lower()
            if alias_norm in FREEFORM_SKIP_ALIASES:
                continue
            terms[alias_norm] = canonical.upper()
    ordered = sorted(terms.items(), key=lambda item: len(item[0]), reverse=True)
    return [(re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)"), canon) for term, canon in ordered]


FREEFORM_COUNTRY_PATTERNS = _build_freeform_country_patterns()


def detect_country_in_text(text_lower):
    plain = strip_accents(text_lower)
    for pattern, canonical in FREEFORM_COUNTRY_PATTERNS:
        if pattern.search(plain):
            return canonical
    return None


# ---------------------------------------------------------------------------
# PORT HELPERS
# ---------------------------------------------------------------------------
PORT_PATTERNS = {
    key: re.compile(r"(?<!\w)" + re.escape(key) + r"(?!\w)") for key in PORT_TO_COUNTRY
}

PORT_CONTEXT_PATTERN = re.compile(
    r"(?i)(calling|call at|port call|port of|arriv\w*|\beta\b|berth\w*|anchorage|discharg\w*|"
    r"attend\w*|service at|will be at|bound for|en ?route|alongside|next port|last port|destination)"
)


def find_ports(text_lower):
    hits = []
    for key, pattern in PORT_PATTERNS.items():
        match = pattern.search(text_lower)
        if match:
            hits.append((match.start(), key))
    hits.sort()
    return hits


def detect_port(text_lower):
    hits = find_ports(text_lower)
    if not hits:
        return None

    def score(hit):
        pos, _key = hit
        window = text_lower[max(0, pos - 60):pos]
        return (0 if PORT_CONTEXT_PATTERN.search(window) else 1, pos)

    return min(hits, key=score)[1]


def country_for_port(port_key, text_lower=""):
    key = str(port_key).lower()
    if key in AMBIGUOUS_PORTS:
        for candidate in AMBIGUOUS_PORTS[key]:
            for variant in country_variants(candidate):
                if re.search(r"(?<!\w)" + re.escape(variant) + r"(?!\w)", strip_accents(text_lower)):
                    return candidate
    return PORT_TO_COUNTRY.get(key)


def normalize_port(raw):
    text = _as_text(raw)
    if text == "Not specified" or text.lower() in ("none", "n/a", "na", "unknown", "null", "-"):
        return "Not specified"
    key = detect_port(text.lower())
    if key:
        return key.title()
    first_part = re.split(r"[,(/]", text)[0].strip()
    return first_part.title() if first_part else "Not specified"


# ---------------------------------------------------------------------------
# OFFICE ADDRESS / SIGNATURE FILTERING (Piraeus is NOT a service port by default)
# ---------------------------------------------------------------------------
PIRAEUS_PATTERN = re.compile(r"(?i)piraeus|pireas|peiraias|πειραι")
GREECE_WORD_PATTERN = re.compile(r"(?i)(?<!\w)(greece|hellas|ellada|ελλάδα|ελλαδα)(?!\w)")
GREECE_ONLY_LINE_PATTERN = re.compile(r"(?i)\W*(greece|hellas|ellada|ελλάδα|ελλαδα)\W*")
STRONG_ADDRESS_PATTERN = re.compile(
    r"(?i)(\btel\b|\bfax\b|\bphone\b|\bmob(?:ile)?\b|@|www\.|https?://|\+30|\b18[0-9]{3}\b|"
    r"\bstr(?:eet)?\b|\bst\.|\bakti\b|\bave(?:nue)?\b|\bblvd\b|vasilikon|moutsopoulou|"
    r"p\.?\s?o\.?\s?box|\boffice\b|\bfloor\b|\bflr\b)"
)


def clean_signatures(text):
    if not text:
        return ""

    cleaned = re.sub(r"(?i)vasilikon\s*51[^\n]*piraeus[^\n]*greece", "", text)
    cleaned = re.sub(r"(?i)akti\s*moutsopoulou[^\n]*piraeus[^\n]*greece", "", cleaned)
    cleaned = re.sub(r"(?i)piraeus\s*185\d\d\s*greece", "", cleaned)

    kept_lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        has_piraeus = bool(PIRAEUS_PATTERN.search(line))
        has_greece = bool(GREECE_WORD_PATTERN.search(line))
        if has_piraeus or has_greece:
            has_call_context = bool(PORT_CONTEXT_PATTERN.search(line))
            if GREECE_ONLY_LINE_PATTERN.fullmatch(stripped):
                continue
            if STRONG_ADDRESS_PATTERN.search(line) and not has_call_context:
                continue
            if has_piraeus and not has_call_context and len(stripped) < 90:
                continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


# ---------------------------------------------------------------------------
# VESSEL NAME / JSON HELPERS
# ---------------------------------------------------------------------------
STOP_WORDS_PATTERN = r"\b(will|at|eta|port|call|calling|arr|arriving|due|to|for|is|and|the|in|on|sailing)\b"


def _clean_single_vessel_part(part):
    part = re.sub(r"(?i)^\s*the\s+", "", part)
    cleaned = re.split(STOP_WORDS_PATTERN, part, flags=re.IGNORECASE)[0]
    words = cleaned.strip(" -–,.;:/").split()
    if len(words) > 3:
        words = words[:3]
    return " ".join(words).strip().title()


def clean_vessel_name(raw_name):
    if not raw_name:
        return "Not specified"
    raw = str(raw_name).strip()
    if not raw or raw.lower() in ("not specified", "none", "n/a", "na", "unknown", "null"):
        return "Not specified"

    raw = re.sub(r"(?i)^(?:m/?v|m/?t|mt|mv|vessel|ship)\b\.?\s*[:\-]?\s+(?=\S)", "", raw)
    raw = re.split(r"(?i)\s+(?:ex|a\.?k\.?a\.?|formerly)[\s\-]+", raw)[0]

    parts = re.split(r"(?i)\s+tbn\s+|\s*/\s*", raw)
    cleaned_parts = []
    for part in parts:
        cleaned = _clean_single_vessel_part(part)
        if cleaned and cleaned.lower() not in GENERIC_VESSEL_WORDS:
            if cleaned.lower() not in [p.lower() for p in cleaned_parts]:
                cleaned_parts.append(cleaned)
    if not cleaned_parts:
        return "Not specified"
    return " / ".join(cleaned_parts)


def clean_json(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def extract_json(text):
    if not text:
        return None
    cleaned = clean_json(text)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(cleaned[start:end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# FILE INGESTION
# ---------------------------------------------------------------------------
def read_pdf_stream(stream):
    text = ""
    reader = pypdf.PdfReader(stream)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass
    for page in reader.pages[:15]:
        text += (page.extract_text() or "") + "\n"
    return text


def extract_text_from_file(uploaded_file):
    extracted_text = ""
    file_name = uploaded_file.name.lower()
    try:
        data = uploaded_file.getvalue()
        if file_name.endswith(".pdf"):
            extracted_text += read_pdf_stream(io.BytesIO(data))
        elif file_name.endswith(".eml"):
            msg = email.message_from_bytes(data, policy=policy.default)
            extracted_text += f"\nSubject: {msg.get('subject', '')}\n"
            body = msg.get_body(preferencelist=('plain', 'html'))
            if body:
                content = body.get_content()
                if body.get_content_type() == "text/html":
                    content = html_to_text(content)
                extracted_text += content
            for part in msg.iter_attachments():
                att_name = (part.get_filename() or "").lower()
                if att_name.endswith(".pdf"):
                    pdf_data = part.get_payload(decode=True)
                    if pdf_data:
                        extracted_text += f"\n--- Embedded PDF: {att_name} ---\n"
                        extracted_text += read_pdf_stream(io.BytesIO(pdf_data))
        elif file_name.endswith(".msg"):
            msg = extract_msg.Message(io.BytesIO(data))
            try:
                extracted_text += f"\nSubject: {msg.subject}\nBody:\n{msg.body or ''}\n"
                for attachment in msg.attachments:
                    att_name = str(
                        getattr(attachment, 'longFilename', '') or getattr(attachment, 'shortFilename', '')
                    ).lower()
                    att_data = getattr(attachment, 'data', None)
                    if att_name.endswith(".pdf") and att_data:
                        try:
                            extracted_text += f"\n--- Embedded PDF: {att_name} ---\n"
                            extracted_text += read_pdf_stream(io.BytesIO(att_data))
                        except Exception as err:
                            extracted_text += f"\n[Could not parse PDF attachment {att_name}: {err}]\n"
            finally:
                try:
                    msg.close()
                except Exception:
                    pass
        elif file_name.endswith(".txt"):
            extracted_text = data.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
    return extracted_text[:MAX_CHARS_PER_FILE]


def build_files_text(doc_files):
    combined = ""
    for f in doc_files:
        combined += f"\n--- Content from {f.name} ---\n"
        combined += extract_text_from_file(f)
    if len(combined) > MAX_TOTAL_CHARS:
        st.warning(
            f"Document text was truncated to {MAX_TOTAL_CHARS} characters to stay within the API limits."
        )
        combined = combined[:MAX_TOTAL_CHARS]
    return combined


def prepare_images(image_files):
    encoded = []
    if len(image_files) > MAX_IMAGES:
        st.warning(f"Only the first {MAX_IMAGES} photos are analysed (API limit).")
    for img_file in image_files[:MAX_IMAGES]:
        try:
            img = Image.open(io.BytesIO(img_file.getvalue()))
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            encoded.append({
                "name": img_file.name,
                "b64": base64.b64encode(buffer.getvalue()).decode("utf-8"),
            })
        except Exception as err:
            st.warning(f"Could not read image {img_file.name}: {err}")
    return encoded


# ---------------------------------------------------------------------------
# MANUAL OVERRIDE PARSING (absolute priority over documents and photos)
# ---------------------------------------------------------------------------
def _find_labeled(text, label_pattern):
    match = re.search(
        r"(?i)(?:^|[\s,;|])(?:" + label_pattern + r")\s*[:=]\s*([^\n\r,;|]+)",
        text,
    )
    if match:
        value = match.group(1).strip().strip("\"'").strip()
        return value or None
    return None


def parse_manual_inputs(manual_text):
    """Returns only what the user explicitly typed: country / port / vessel_name."""
    overrides = {}
    if not manual_text or not manual_text.strip():
        return overrides

    text = manual_text.strip()
    text_lower = text.lower()

    port_raw = _find_labeled(text, r"port|λιμάνι|λιμανι")
    country_raw = _find_labeled(text, r"country|χώρα|χωρα")
    vessel_raw = _find_labeled(text, r"vessel|ship|πλοίο|πλοιο|m/v|mv")

    # Port
    if port_raw:
        overrides["port"] = port_raw.title()
    else:
        port_key = detect_port(text_lower)
        if port_key:
            overrides["port"] = port_key.title()

    # Country
    if country_raw:
        country_value = normalize_country(country_raw)
        if country_value != "Not specified":
            overrides["country"] = country_value
    else:
        country_found = detect_country_in_text(text_lower)
        if country_found:
            overrides["country"] = country_found

    # Vessel
    if vessel_raw:
        vessel_value = clean_vessel_name(vessel_raw)
        if vessel_value != "Not specified":
            overrides["vessel_name"] = vessel_value
    else:
        vessel_match = re.search(
            r"(?i)(?<![A-Za-z0-9])m/?[vt]\.?\s+([A-Za-z0-9][A-Za-z0-9 \t\-/]{1,60})", text
        )
        if vessel_match:
            vessel_value = clean_vessel_name(vessel_match.group(1))
            if vessel_value != "Not specified":
                overrides["vessel_name"] = vessel_value

    return overrides


def apply_manual_overrides(parsed, overrides, cleaned_files=""):
    """Manual values always win. Conflicts with documents/photos are reported."""
    if not overrides:
        return parsed

    notes = parsed.setdefault("discrepancies", [])
    labels = {"country": "Country", "port": "Port", "vessel_name": "Vessel"}
    cleaned_lower = cleaned_files.lower()

    # Derive the country from a manual port when the user did not type one.
    effective = dict(overrides)
    if "port" in overrides and "country" not in overrides:
        derived = country_for_port(overrides["port"].lower(), cleaned_lower)
        if derived:
            effective["country"] = normalize_country(derived)

    for key, value in effective.items():
        old = parsed.get(key, "Not specified")
        if old and old != "Not specified":
            if key == "country":
                conflict = normalize_country(old) != normalize_country(value)
            else:
                conflict = not _same_text(old, value)
            if conflict:
                _add_note(
                    notes,
                    f"{labels[key]}: manual override says '{value}' but documents/photos say '{old}' "
                    f"— manual override used.",
                )
        parsed[key] = value

    # A document port that belongs to another country than the manual country is dropped.
    if "country" in overrides and "port" not in overrides:
        port_key = parsed.get("port", "").lower()
        if port_key in PORT_TO_COUNTRY and port_key not in AMBIGUOUS_PORTS:
            port_country = PORT_TO_COUNTRY[port_key]
            if normalize_country(port_country) != overrides["country"]:
                _add_note(
                    notes,
                    f"Port '{parsed['port']}' from documents belongs to {port_country}, which conflicts "
                    f"with the manual country {overrides['country']} — port discarded (manual override wins).",
                )
                parsed["port"] = "Not specified"

    # Manual port unknown to the dictionary and no manual country: keep the document country, ask to verify.
    if "port" in overrides and "country" not in effective:
        if parsed.get("country", "Not specified") != "Not specified":
            _add_note(
                notes,
                f"Manual port '{overrides['port']}' is not in the port dictionary; country "
                f"'{parsed['country']}' comes from the documents — please verify.",
            )

    return parsed


def guard_office_piraeus(parsed, cleaned_files, overrides, has_images):
    """Rejects Piraeus/Greece when it only came from an office address or signature."""
    notes = parsed.setdefault("discrepancies", [])
    port_rejected = False

    if "port" not in overrides and PIRAEUS_PATTERN.search(parsed.get("port", "")):
        if not PIRAEUS_PATTERN.search(cleaned_files):
            if has_images:
                _add_note(
                    notes,
                    "Port 'Piraeus' does not appear in the document text once office addresses/signatures "
                    "are removed. It may come from a photo — verify it is not the OneTech / shipping company office.",
                )
            else:
                parsed["port"] = "Not specified"
                port_rejected = True
                _add_note(
                    notes,
                    "Piraeus ignored as service port — it only appeared in an office address/signature.",
                )

    if "country" not in overrides and parsed.get("country") == "GREECE":
        if port_rejected or parsed.get("port", "Not specified") == "Not specified":
            cleaned_lower = cleaned_files.lower()
            greece_mentioned = bool(GREECE_WORD_PATTERN.search(cleaned_files))
            greek_port_mentioned = any(
                PORT_TO_COUNTRY.get(key) == "GREECE" for _pos, key in find_ports(cleaned_lower)
            )
            if not greece_mentioned and not greek_port_mentioned and not has_images:
                parsed["country"] = "Not specified"
                _add_note(
                    notes,
                    "Country 'Greece' ignored — it only appeared in an office address/signature.",
                )
    return parsed


def add_cross_source_checks(parsed, cleaned_files, overrides):
    notes = parsed.setdefault("discrepancies", [])
    cleaned_lower = cleaned_files.lower()

    port_key = parsed.get("port", "").lower()

    # Ambiguous port names (e.g. Cartagena: Spain / Colombia)
    if port_key in AMBIGUOUS_PORTS and "country" not in overrides:
        _add_note(
            notes,
            f"Port '{parsed['port']}' exists in several countries "
            f"({' / '.join(c.title() for c in AMBIGUOUS_PORTS[port_key])}) — verify the country.",
        )

    # Port vs. country consistency (dictionary based)
    if port_key in PORT_TO_COUNTRY and port_key not in AMBIGUOUS_PORTS:
        expected = normalize_country(PORT_TO_COUNTRY[port_key])
        current = parsed.get("country", "Not specified")
        if current != "Not specified" and normalize_country(current) != expected:
            _add_note(
                notes,
                f"Port '{parsed['port']}' is normally in {expected}, but the country is set to "
                f"{current} — please verify.",
            )

    # Several countries mentioned in the documents
    if "port" not in overrides and "country" not in overrides:
        countries = []
        ports_seen = []
        for _pos, key in find_ports(cleaned_lower):
            country = country_for_port(key, cleaned_lower)
            if country:
                country = normalize_country(country)
                if country not in countries:
                    countries.append(country)
                    ports_seen.append(f"{key.title()} ({country})")
        if len(countries) > 1:
            _add_note(
                notes,
                "Documents mention ports in several countries: " + ", ".join(ports_seen) +
                " — verify which one is the service port.",
            )
    return parsed


# ---------------------------------------------------------------------------
# RESULT NORMALISATION
# ---------------------------------------------------------------------------
def normalize_result(res):
    out = {
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
    if isinstance(res, dict):
        for key in out:
            if key in res and res[key] is not None:
                out[key] = res[key]

    out["vessel_name"] = clean_vessel_name(out["vessel_name"])
    out["eta"] = _as_text(out["eta"])
    out["port"] = normalize_port(out["port"])
    out["country"] = normalize_country(out["country"])
    out["scope"] = _as_text(out["scope"], "Standard technical attendance inquiry.")
    out["spares_requested"] = _as_text(out["spares_requested"], "Inquired per inquiry")

    if out["country"] == "Not specified" and out["port"].lower() in PORT_TO_COUNTRY:
        out["country"] = normalize_country(PORT_TO_COUNTRY[out["port"].lower()])

    makers = []
    for maker in _as_list(out["makers"], split=True):
        maker_upper = maker.upper()
        if maker_upper in ("NOT SPECIFIED", "NONE", "N/A", "NA", "UNKNOWN", "NULL"):
            continue
        if maker_upper not in makers:
            makers.append(maker_upper)
    out["makers"] = makers

    out["discrepancies"] = _as_list(out["discrepancies"])
    out["missing_critical_data"] = _as_list(out["missing_critical_data"])
    return out


# ---------------------------------------------------------------------------
# LOCAL RULE ENGINE (fallback when Groq is not available)
# ---------------------------------------------------------------------------
def smart_local_parser(manual_override_text, files_text):
    cleaned_files = clean_signatures(files_text)
    combined = (manual_override_text or "") + "\n" + cleaned_files
    text_lower = combined.lower()
    files_lower = cleaned_files.lower()

    vessel_name = "Not specified"
    for vessel_match in re.finditer(
        r"(?i)(?:\bm/?v\b|\bm/?t\b|\bvessel\b|\bship\b)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9 \t\-]{1,60})",
        cleaned_files,
    ):
        candidate = clean_vessel_name(vessel_match.group(1))
        if candidate != "Not specified":
            vessel_name = candidate
            break

    eta = "Not specified"
    eta_match = re.search(r"(?i)\beta\b\s*[:\-]?\s*([^\n\r]{3,40})", cleaned_files)
    if eta_match:
        eta = eta_match.group(1).strip(" .,;")

    detected_port = "Not specified"
    detected_country = "Not specified"
    port_key = detect_port(files_lower)
    if port_key:
        detected_port = port_key.title()
        detected_country = normalize_country(country_for_port(port_key, files_lower))

    found_makers = []
    for maker in KNOWN_MAKERS:
        if re.search(r"(?<!\w)" + re.escape(maker) + r"(?!\w)", text_lower):
            if maker in vessel_name.lower():
                continue
            found_makers.append(maker.upper())
    found_makers = [
        m for m in found_makers
        if not any(m != other and m in other for other in found_makers)
    ]

    scope_text = "Standard technical attendance inquiry."
    if "annual" in text_lower:
        scope_text = "Annual Radio / VDR / Navigation Survey"
    elif "re-programming" in text_lower or "reprogramming" in text_lower:
        scope_text = "Re-programming of Radio and Navigation Equipment"
    elif "spare" in text_lower:
        scope_text = "Spare parts supply"

    missing = []
    if detected_port == "Not specified":
        missing.append("Port / location of service")
    if vessel_name == "Not specified":
        missing.append("Vessel name")
    if eta == "Not specified":
        missing.append("ETA")
    if not found_makers:
        missing.append("Equipment maker / model")

    return {
        "vessel_name": vessel_name,
        "eta": eta,
        "port": detected_port,
        "country": detected_country,
        "makers": list(dict.fromkeys(found_makers)),
        "scope": scope_text,
        "spares_requested": "Inquired per inquiry",
        "discrepancies": [],
        "missing_critical_data": missing,
    }


# ---------------------------------------------------------------------------
# GROQ (official SDK)
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """You are an expert maritime technical coordinator working for a ship-supply and technical-service company.
Parse the commercial RFQ (request for quotation) below and extract the facts into JSON.

CRITICAL INSTRUCTIONS:
1. 'MANUAL OVERRIDE' IS ABSOLUTE GROUND TRUTH. If a country, port or vessel is stated there, use it unconditionally, even if the documents or photos say something different (still report the conflict in 'discrepancies').
2. DO NOT extract 'Piraeus' or 'Greece' as the service port/country when it comes from company footers, signatures or office addresses (OneTech, Mega Shipping, ship managers, agents, etc.). Piraeus is only valid if the text explicitly says the vessel is calling at / attending / arriving in Piraeus, or if the MANUAL OVERRIDE says so.
3. If an inquiry states 'MV KIRRIBILLI TBN SEA GRACE', the vessel name is 'Kirribilli / Sea Grace'.
4. 'port' must be the port where the vessel will be serviced (port of call / attendance). It is not the sender's office and not a previous or next port unless stated as the service port.
5. If photos are attached, read all visible information (vessel name, equipment makers and models, serial numbers, alarm or error messages, port names on documents) and treat it as an additional source.
6. Compare ALL sources (manual override, email / PDF text, photos). List every conflicting fact in 'discrepancies' as one short plain-English sentence naming both sources and both values. If there are no conflicts, return an empty list.
7. List essential information that is missing from all sources in 'missing_critical_data' (for example 'ETA', 'port', 'equipment model').
8. Do not invent facts. Use "Not specified" for unknown values.
9. 'makers' must contain only equipment manufacturers requiring service. Known makers include: <<MAKERS>>. You may add others if they appear in the sources.

MANUAL OVERRIDE:
\"\"\"<<MANUAL_OVERRIDE>>\"\"\"

INQUIRY TEXT:
\"\"\"<<INQUIRY_TEXT>>\"\"\"

PHOTOS ATTACHED: <<PHOTOS>>

Return ONLY valid JSON (no markdown, no commentary) matching this schema:
{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA or 'Not specified'",
  "port": "Port or 'Not specified'",
  "country": "Country or 'Not specified'",
  "makers": ["Maker requiring service"],
  "scope": "Summary",
  "spares_requested": "Spares",
  "discrepancies": [],
  "missing_critical_data": []
}
"""


def build_prompt(manual_text, cleaned_files, image_names):
    manual_block = manual_text.strip() if manual_text and manual_text.strip() else "(none)"
    files_block = cleaned_files.strip() if cleaned_files and cleaned_files.strip() else "(no document text)"
    photos_block = ", ".join(image_names) if image_names else "(none)"
    return (
        PROMPT_TEMPLATE
        .replace("<<MAKERS>>", ", ".join(KNOWN_MAKERS))
        .replace("<<MANUAL_OVERRIDE>>", manual_block)
        .replace("<<INQUIRY_TEXT>>", files_block)
        .replace("<<PHOTOS>>", photos_block)
    )


def build_message_content(prompt_text, images):
    content = [{"type": "text", "text": prompt_text}]
    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img['b64']}"}
        })
    return content


def is_model_unavailable(err):
    message = str(err).lower()
    return any(
        marker in message
        for marker in ("decommission", "model_not_found", "does not exist", "no longer supported", "deprecated")
    )


def describe_groq_error(err):
    if isinstance(err, groq.AuthenticationError):
        return "Authentication failed (401) — GROQ_API_KEY is missing, invalid or revoked."
    if isinstance(err, groq.PermissionDeniedError):
        return "Access denied (403) — check the Groq organisation / project permissions."
    if isinstance(err, groq.RateLimitError):
        return "Rate limit reached (429) — wait a moment or reduce the amount of text / photos."
    if isinstance(err, groq.APITimeoutError):
        return "The request to Groq timed out."
    if isinstance(err, groq.APIConnectionError):
        return "Could not reach api.groq.com — check the network / firewall."
    if isinstance(err, groq.APIStatusError):
        return f"HTTP {err.status_code}: {getattr(err, 'message', err)}"
    return str(err)


def run_groq_chat(model, content):
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 1500,
    }
    try:
        completion = client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
    except groq.BadRequestError as err:
        message = str(err).lower()
        if is_model_unavailable(err):
            raise
        if "json" in message or "response_format" in message:
            completion = client.chat.completions.create(**kwargs)
        else:
            raise
    return completion.choices[0].message.content


def run_groq_parser(manual_text, cleaned_files, images):
    prompt_text = build_prompt(manual_text, cleaned_files, [img["name"] for img in images])

    attempts = []
    if images:
        attempts.append((VISION_MODEL, True))
        if VISION_FALLBACK_MODEL and VISION_FALLBACK_MODEL != VISION_MODEL:
            attempts.append((VISION_FALLBACK_MODEL, True))
        if (manual_text and manual_text.strip()) or (cleaned_files and cleaned_files.strip()):
            attempts.append((TEXT_MODEL, False))
    else:
        attempts.append((TEXT_MODEL, False))

    for model, with_images in attempts:
        content = build_message_content(prompt_text, images) if with_images else prompt_text
        try:
            raw_output = run_groq_chat(model, content)
            parsed = extract_json(raw_output)
            if parsed is None:
                st.warning(f"Model `{model}` did not return valid JSON. Trying the next option.")
                continue
            if images and not with_images:
                st.warning(
                    "The photos could not be analysed (no vision model was available) — "
                    "the result is based on the text and manual input only."
                )
            return parsed, model
        except (groq.AuthenticationError, groq.PermissionDeniedError) as err:
            st.error(f"Groq: {describe_groq_error(err)}")
            return None, None
        except (groq.BadRequestError, groq.NotFoundError) as err:
            if is_model_unavailable(err):
                st.warning(f"Model `{model}` is no longer available on Groq. Trying the next option.")
            else:
                st.warning(f"Groq rejected the request for `{model}`: {describe_groq_error(err)}")
            continue
        except groq.RateLimitError as err:
            st.warning(f"Model `{model}`: {describe_groq_error(err)}")
            continue
        except groq.APIError as err:
            st.warning(f"Model `{model}`: {describe_groq_error(err)}")
            continue
        except Exception as err:
            st.warning(f"Unexpected error with model `{model}`: {err}")
            continue

    st.warning("Groq analysis failed for all models. Executing local rule engine.")
    return None, None


def analyze_rfq(manual_override_text, files_text, image_files):
    manual_overrides = parse_manual_inputs(manual_override_text)
    cleaned_files = clean_signatures(files_text)
    images = prepare_images(image_files) if image_files else []

    res_json = None
    engine = "Local rule engine"

    if client is not None:
        res_json, used_model = run_groq_parser(manual_override_text, cleaned_files, images)
        if res_json:
            engine = f"Groq / {used_model}"
    else:
        st.info("GROQ_API_KEY not detected in secrets. Running local parser.")

    if not res_json:
        res_json = smart_local_parser(manual_override_text, files_text)
        engine = "Local rule engine"

    parsed = normalize_result(res_json)
    parsed = guard_office_piraeus(parsed, cleaned_files, manual_overrides, bool(images))
    parsed = apply_manual_overrides(parsed, manual_overrides, cleaned_files)
    parsed = add_cross_source_checks(parsed, cleaned_files, manual_overrides)
    parsed["discrepancies"] = list(dict.fromkeys(parsed["discrepancies"]))
    parsed["engine"] = engine
    return parsed


def test_groq_connection():
    try:
        response = client.models.list()
        model_ids = sorted(m.id for m in response.data)
        st.sidebar.success(f"Groq connection OK — {len(model_ids)} models available.")
        for label, model_name in (
            ("Text", TEXT_MODEL),
            ("Vision", VISION_MODEL),
            ("Vision fallback", VISION_FALLBACK_MODEL),
        ):
            if model_name in model_ids:
                st.sidebar.write(f"✅ {label}: `{model_name}`")
            else:
                st.sidebar.write(f"❌ {label}: `{model_name}` (not listed by Groq)")
    except Exception as err:
        st.sidebar.error(f"Groq connection failed: {describe_groq_error(err)}")


# ---------------------------------------------------------------------------
# DIRECTORY / ROUTING
# ---------------------------------------------------------------------------
@st.cache_data
def load_directory():
    try:
        return pd.read_csv("directory.csv", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv("directory.csv", encoding="cp1252")


def show_dataframe(data):
    try:
        st.dataframe(data, width="stretch")
    except Exception:
        st.dataframe(data, use_container_width=True)


def maker_terms(maker):
    normalized = strip_accents(maker).lower().strip()
    terms = {normalized}
    tokens = normalized.split()
    if tokens and len(tokens[0]) >= 3:
        terms.add(tokens[0])
    return terms


def make_maker_filter(target_makers):
    term_sets = [maker_terms(m) for m in target_makers]

    def maker_filter(approved_str):
        approved = strip_accents(str(approved_str)).lower()
        return any(any(term in approved for term in terms) for terms in term_sets)

    return maker_filter


def render_station_routing(directory_df, parsed):
    target_country = str(parsed.get("country", "")).strip().lower()
    target_makers = [str(m).lower() for m in parsed.get("makers", [])]

    if directory_df.empty or not target_country or target_country == "not specified":
        st.warning("Target country is not specified or no stations matched.")
        return

    if "Country" not in directory_df.columns:
        st.error("directory.csv has no 'Country' column.")
        return

    has_maker_column = "Approved Makers" in directory_df.columns
    use_maker_filter = bool(target_makers) and has_maker_column
    if target_makers and not has_maker_column:
        st.warning("directory.csv has no 'Approved Makers' column — maker filtering is skipped.")

    maker_filter = make_maker_filter(target_makers)

    final_df = pd.DataFrame()
    matched_location_label = target_country.upper()
    maker_fallback = False

    country_match = get_country_matches(directory_df, target_country)

    if not country_match.empty:
        if use_maker_filter:
            filtered = country_match[country_match["Approved Makers"].apply(maker_filter)]
            if filtered.empty:
                final_df = country_match
                maker_fallback = True
            else:
                final_df = filtered
        else:
            final_df = country_match

    if final_df.empty:
        canonical = _ALIAS_TO_CANONICAL.get(strip_accents(target_country), target_country)
        if canonical in NEIGHBORING_COUNTRIES:
            for neigh in NEIGHBORING_COUNTRIES[canonical]:
                neigh_match = get_country_matches(directory_df, neigh)
                if neigh_match.empty:
                    continue
                if use_maker_filter:
                    filtered_neigh = neigh_match[neigh_match["Approved Makers"].apply(maker_filter)]
                    if not filtered_neigh.empty:
                        final_df = filtered_neigh
                        matched_location_label = (
                            f"{neigh.upper()} (Neighboring Country to {target_country.upper()})"
                        )
                        break
                else:
                    final_df = neigh_match
                    matched_location_label = (
                        f"{neigh.upper()} (Neighboring Country to {target_country.upper()})"
                    )
                    break

    makers_formatted = ', '.join([m.upper() for m in target_makers]) if target_makers else "ALL"

    if not final_df.empty:
        st.success(f"Matched stations in **{matched_location_label}** for makers: {makers_formatted}")
        if maker_fallback:
            st.warning(
                f"No station in {target_country.upper()} lists {makers_formatted} as an approved maker — "
                f"showing all stations in the country."
            )
        show_dataframe(final_df)
    else:
        st.warning(
            f"No approved stations found in {target_country.upper()} or neighboring regions. "
            f"Showing full directory:"
        )
        show_dataframe(directory_df)


# ---------------------------------------------------------------------------
# USER INTERFACE
# ---------------------------------------------------------------------------
try:
    df = load_directory()
    st.sidebar.success(f"Connected to Directory. Loaded {len(df)} stations.")
except Exception as e:
    st.sidebar.error(f"Error loading directory.csv: {e}")
    df = pd.DataFrame()

st.sidebar.markdown("---")
st.sidebar.markdown("**Groq API**")
if client is None:
    st.sidebar.warning("GROQ_API_KEY not found in st.secrets — the local rule engine will be used.")
else:
    st.sidebar.success("GROQ_API_KEY detected.")
    if st.sidebar.button("Test Groq connection"):
        test_groq_connection()

st.subheader("1. Ingestion & Manual Override")
col1, col2 = st.columns([1, 1])

with col1:
    rfq_pasted_text = st.text_area(
        "Manual Override / Priority Info (Port, Vessel, etc.):",
        height=180,
        placeholder="e.g. Country: Thailand\nPort: Kohsichang\nVessel: Kirribilli",
        help="Anything typed here (country, port, vessel) overrides the attached files and photos."
    )

with col2:
    uploaded_files = st.file_uploader(
        "Upload customer files & photos (PDF, EML, MSG, TXT, JPG, PNG):",
        type=["pdf", "eml", "msg", "txt", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

doc_files = [f for f in uploaded_files if not f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []
image_files = [f for f in uploaded_files if f.name.lower().endswith(('jpg', 'jpeg', 'png'))] if uploaded_files else []

if st.button("Process RFQ & Audit Discrepancies", type="primary"):
    if not rfq_pasted_text.strip() and not uploaded_files:
        st.warning("Please provide manual text or upload at least one file/image.")
    else:
        with st.spinner("Processing inquiry and running station audit..."):
            files_combined_text = build_files_text(doc_files)
            parsed = analyze_rfq(rfq_pasted_text, files_combined_text, image_files)

        if parsed:
            st.markdown("---")
            st.subheader("2. RFQ Executive Brief")
            st.caption(f"Parsed by: {parsed.get('engine', 'n/a')}")
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

            missing_data = parsed.get("missing_critical_data", [])
            if missing_data:
                st.info("Missing critical data: " + "; ".join(missing_data))

            st.markdown("---")
            st.subheader("4. Recommended Service Stations")
            render_station_routing(df, parsed)

            with st.expander("Show Parsed Raw Inputs"):
                st.write("**Manual Override Text:**")
                st.text(rfq_pasted_text)
                st.write("**Files Text:**")
                st.text(files_combined_text)
                st.write("**Parsed Result (JSON):**")
                st.json(parsed)
