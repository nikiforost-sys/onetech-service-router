import base64
import email
from email import policy
import io
import json
import os
import re
import urllib.request
import extract_msg
import pandas as pd
from PIL import Image
import pypdf
import streamlit as st
from groq import Groq

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

st.set_page_config(
    page_title="Onetech Service Router & Copilot",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# CUSTOM CSS: FLOATING BUTTON, STICKY COPILOT & CLEAN CARDS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 4.5rem !important;
}

div.st-key-floating_copilot_btn {
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: auto !important;
}
div.st-key-floating_copilot_btn button {
    border-radius: 999px !important;
    padding: 0.65rem 1.35rem !important;
    font-weight: 700 !important;
    font-size: 0.98rem !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2):has(.copilot-panel-marker) {
    position: sticky !important;
    top: 3.2rem !important;
    align-self: flex-start !important;
    max-height: calc(100vh - 5rem) !important;
}

.clean-header {
    font-size: 1.15rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
    color: #1f2937;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SECRETS & ACTIVE MODELS
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

GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.8-pro",
    "gemini-2.0-flash",
]

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen3-32b",
]


@st.cache_data(ttl=600)
def get_active_groq_models():
    models = list(GROQ_MODELS)
    if client_groq:
        try:
            resp = client_groq.models.list()
            for m in getattr(resp, "data", []):
                mid = getattr(m, "id", "")
                if mid and not any(x in mid.lower() for x in ("whisper", "tts", "guard", "allam")):
                    if mid not in models:
                        models.append(mid)
        except Exception:
            pass
    return models


# ---------------------------------------------------------------------------
# GOOGLE SHEET LIVE DIRECTORY LOADER
# ---------------------------------------------------------------------------
_SHEET_ID = base64.b64decode("MVo5VnV1cUNSRV9xY3k4OWFIZ3ptWTM0dXAwb1FTVUI0Zkx4ZUN6XzgySVE=").decode("utf-8")
_SHEET_GID = "428894731"

FALLBACK_STATIONS = [
    {"Country": "United Arab Emirates", "Service Station Name": "Radio Holland Middle East LLC (Dubai)", "Approved Makers": "Danelec*, Furuno*, JRC*, Sperry Marine*, Yokogawa (YDK)*"},
    {"Country": "United Arab Emirates", "Service Station Name": "Master Systems LLC (Dubai)", "Approved Makers": "Danelec, Furuno, Highlander*, JRC, MacGregor*, Yokogawa (YDK)*"},
    {"Country": "United Arab Emirates", "Service Station Name": "Marintel FZC / Oceanic Marine LLC (UAE)", "Approved Makers": "AMI, Danelec, Furuno, JRC, Netwave, Samsung*, Sperry Marine*, Totem Plus"},
    {"Country": "United Arab Emirates", "Service Station Name": "Alfa Marine Electronics FZC", "Approved Makers": "Furuno, Highlander, JRC, Yokogawa (YDK)"},
    {"Country": "China", "Service Station Name": "COSCO MEEC Shanghai", "Approved Makers": "Danelec, Furuno, JRC, Samsung*, Tokyo Keiki*, Yokogawa (YDK)*"},
    {"Country": "China", "Service Station Name": "Mackay Marine (China) Ltd. (Shanghai, Ningbo, Shenzhen, Qingdao, Guangzhou, Tianjin)", "Approved Makers": "Danelec*, Furuno*, Jotron, JRC*, Netwave*, Sperry Marine*"},
    {"Country": "China", "Service Station Name": "Seven Seas Electronic Co., Ltd. (Shanghai, Qingdao, Guangzhou, Tianjin)", "Approved Makers": "Cobham SAILOR, Danelec, Highlander*, JRC"},
    {"Country": "Malta", "Service Station Name": "Aage Hempel Marine Electronics Malta Ltd (Valletta)", "Approved Makers": "Anschütz*, Cobham SAILOR*, Danelec*, Furuno*, JRC, Sperry Marine*"},
    {"Country": "Malta", "Service Station Name": "Medcomms Ltd (Malta)", "Approved Makers": "Cobham SAILOR, Furuno*, Garmin, Netwave*, Simrad"},
    {"Country": "Cyprus", "Service Station Name": "Onetech Services Ltd (Limassol HQ)", "Approved Makers": "Consilium, Danelec*, Highlander*, Hyundai*, JRC, MacGregor*, Sperry Marine*"},
    {"Country": "Netherlands", "Service Station Name": "JRC / Alphatron Marine B.V. (Rotterdam HQ)", "Approved Makers": "Jotron, JRC / Alphatron Marine*, Wärtsilä*, Yokogawa (YDK)*"},
    {"Country": "Singapore", "Service Station Name": "Jason Electronics (Pte) Ltd (Singapore HQ)", "Approved Makers": "Cobham SAILOR*, Danelec*, Furuno, Highlander*, JRC*, Netwave*, Sperry Marine*"},
]


def _clean_df(df):
    if df is None or df.empty:
        return None
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    if "Country" not in df.columns:
        for idx, row in df.head(5).iterrows():
            vals = [str(v).strip() for v in row.values]
            if "Country" in vals:
                df.columns = vals
                df = df.iloc[idx + 1:].reset_index(drop=True)
                break
    if "Country" in df.columns and "Service Station Name" in df.columns:
        df = df.dropna(subset=["Country", "Service Station Name"])
        df = df[df["Country"].astype(str).str.strip().str.lower() != "country"]
        return df.reset_index(drop=True)
    return None


@st.cache_data(ttl=300)
def load_directory():
    urls = [
        f"https://docs.google.com/spreadsheets/d/{_SHEET_ID}/gviz/tq?tqx=out:csv&gid={_SHEET_GID}",
        f"https://docs.google.com/spreadsheets/d/{_SHEET_ID}/export?format=csv&gid={_SHEET_GID}",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw_text = resp.read().decode("utf-8-sig", errors="replace")
            if raw_text and "<html" not in raw_text[:300].lower() and "<!doctype" not in raw_text[:300].lower():
                df = _clean_df(pd.read_csv(io.StringIO(raw_text), on_bad_lines="skip"))
                if df is not None and not df.empty:
                    return df, "Google Sheets (Live)"
        except Exception:
            continue

    if HAS_GOOGLE_AUTH and "gcp_service_account" in st.secrets:
        try:
            sa_info = dict(st.secrets["gcp_service_account"])
            pk = sa_info.get("private_key", "")
            sa_info["private_key"] = pk.replace("btw6r\n", "btw6\n").replace("btw6r-----", "btw6-----")
            creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            drive_service = build("drive", "v3", credentials=creds)
            request = drive_service.files().export_media(fileId=_SHEET_ID, mimeType="text/csv")
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            raw_text = fh.getvalue().decode("utf-8-sig", errors="replace")
            df = _clean_df(pd.read_csv(io.StringIO(raw_text), on_bad_lines="skip"))
            if df is not None and not df.empty:
                return df, "Google Drive API (Live)"
        except Exception:
            pass

    if os.path.exists("directory.csv"):
        try:
            df_local = _clean_df(pd.read_csv("directory.csv", on_bad_lines="skip"))
            if df_local is not None and not df_local.empty:
                return df_local, "Local directory.csv"
        except Exception:
            pass

    return pd.DataFrame(FALLBACK_STATIONS), "Built-in Directory Backup"


# ---------------------------------------------------------------------------
# PORTS, COUNTRIES & MAKERS
# ---------------------------------------------------------------------------
PORT_TO_COUNTRY = {
    "taicang": "CHINA", "qingdao": "CHINA", "shanghai": "CHINA", "ningbo": "CHINA",
    "shenzhen": "CHINA", "guangzhou": "CHINA", "tianjin": "CHINA", "hong kong": "HONG KONG",
    "dalian": "CHINA", "xiamen": "CHINA", "rizhao": "CHINA", "yingkou": "CHINA",
    "zhoushan": "CHINA", "nantong": "CHINA", "jiangyin": "CHINA", "caofeidian": "CHINA",
    "qinhuangdao": "CHINA", "tangshan": "CHINA", "yantai": "CHINA", "fangcheng": "CHINA",
    "zhanjiang": "CHINA", "shekou": "CHINA", "yantian": "CHINA", "lianyungang": "CHINA",
    "kaohsiung": "TAIWAN", "keelung": "TAIWAN", "taichung": "TAIWAN", "taipei": "TAIWAN",
    "busan": "SOUTH KOREA", "ulsan": "SOUTH KOREA", "incheon": "SOUTH KOREA", "yeosu": "SOUTH KOREA",
    "tokyo": "JAPAN", "yokohama": "JAPAN", "nagoya": "JAPAN", "osaka": "JAPAN", "kobe": "JAPAN",
    "singapore": "SINGAPORE", "port kelang": "MALAYSIA", "port klang": "MALAYSIA",
    "malta": "MALTA", "valletta": "MALTA", "marsaxlokk": "MALTA",
    "limassol": "CYPRUS", "larnaca": "CYPRUS", "vassiliko": "CYPRUS", "cyprus": "CYPRUS",
    "piraeus": "GREECE", "thessaloniki": "GREECE", "eleusis": "GREECE", "perama": "GREECE",
    "agios theodoroi": "GREECE", "corinth": "GREECE", "patras": "GREECE", "lavrio": "GREECE",
    "constanta": "ROMANIA", "constantza": "ROMANIA", "mangalia": "ROMANIA", "midia": "ROMANIA",
    "varna": "BULGARIA", "burgas": "BULGARIA", "bourgas": "BULGARIA",
    "odessa": "UKRAINE", "novorossiysk": "RUSSIA", "st petersburg": "RUSSIA",
    "tutunciftlik": "TURKEY", "tupras": "TURKEY", "izmit": "TURKEY", "yalova": "TURKEY",
    "tuzla": "TURKEY", "istanbul": "TURKEY", "aliaga": "TURKEY", "iskenderun": "TURKEY",
    "mersin": "TURKEY", "canakkale": "TURKEY", "ambarli": "TURKEY", "gemlik": "TURKEY",
    "genoa": "ITALY", "genova": "ITALY", "augusta": "ITALY", "trieste": "ITALY",
    "venice": "ITALY", "ravenna": "ITALY", "livorno": "ITALY", "naples": "ITALY",
    "gioia tauro": "ITALY", "taranto": "ITALY", "la spezia": "ITALY", "civitavecchia": "ITALY",
    "marseilles": "FRANCE", "marseille": "FRANCE", "fos": "FRANCE", "le havre": "FRANCE",
    "koper": "SLOVENIA", "rijeka": "CROATIA",
    "algeciras": "SPAIN", "valencia": "SPAIN", "barcelona": "SPAIN", "las palmas": "SPAIN",
    "bilbao": "SPAIN", "cartagena": "SPAIN", "huelva": "SPAIN", "tarragona": "SPAIN",
    "gibraltar": "GIBRALTAR", "lisbon": "PORTUGAL", "sines": "PORTUGAL",
    "rotterdam": "NETHERLANDS", "amsterdam": "NETHERLANDS", "vlissingen": "NETHERLANDS",
    "antwerp": "BELGIUM", "zeebrugge": "BELGIUM", "ghent": "BELGIUM",
    "hamburg": "GERMANY", "bremen": "GERMANY", "bremerhaven": "GERMANY", "wilhelmshaven": "GERMANY",
    "felixstowe": "UK", "southampton": "UK", "london": "UK", "immingham": "UK", "liverpool": "UK",
    "dubai": "UAE", "fujairah": "UAE", "jebel ali": "UAE", "abu dhabi": "UAE", "khor fakkan": "UAE",
    "sharjah": "UAE", "hamriyah": "UAE", "ras al khaimah": "UAE", "ruwais": "UAE",
    "sohar": "OMAN", "salalah": "OMAN", "muscat": "OMAN", "duqm": "OMAN",
    "dammam": "SAUDI ARABIA", "jeddah": "SAUDI ARABIA", "jubail": "SAUDI ARABIA", "yanbu": "SAUDI ARABIA",
    "doha": "QATAR", "ras laffan": "QATAR", "mesaieed": "QATAR",
    "bahrain": "BAHRAIN", "kuwait": "KUWAIT",
    "alexandria": "EGYPT", "port said": "EGYPT", "suez": "EGYPT", "suez canal": "EGYPT",
    "casablanca": "MOROCCO", "tanger med": "MOROCCO", "durban": "SOUTH AFRICA", "cape town": "SOUTH AFRICA",
    "houston": "USA", "new orleans": "USA", "new york": "USA", "los angeles": "USA",
    "panama": "PANAMA", "balboa": "PANAMA", "cristobal": "PANAMA",
    "santos": "BRAZIL", "paranagua": "BRAZIL", "rio de janeiro": "BRAZIL", "buenos aires": "ARGENTINA",
}

NEIGHBORING_COUNTRIES = {
    "china": ["hong kong", "south korea", "japan", "taiwan", "singapore", "vietnam", "philippines"],
    "hong kong": ["china", "taiwan", "singapore", "south korea", "philippines"],
    "south korea": ["china", "japan", "taiwan", "singapore"],
    "japan": ["south korea", "china", "taiwan"],
    "taiwan": ["china", "hong kong", "south korea", "japan", "philippines"],
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
    "uk": ["netherlands", "belgium", "france", "ireland", "germany"],
    "uae": ["oman", "saudi arabia", "qatar", "bahrain", "kuwait"],
    "oman": ["uae", "saudi arabia", "qatar", "bahrain", "kuwait"],
    "saudi arabia": ["uae", "bahrain", "qatar", "kuwait", "oman", "egypt"],
    "qatar": ["uae", "bahrain", "saudi arabia", "oman", "kuwait"],
    "bahrain": ["saudi arabia", "qatar", "uae", "kuwait", "oman"],
    "kuwait": ["saudi arabia", "bahrain", "qatar", "uae", "oman"],
    "brazil": ["argentina", "uruguay", "chile", "panama"],
    "usa": ["canada", "mexico", "panama", "bahamas"],
}

KNOWN_MAKERS = [
    "sperry marine", "sperry", "jrc", "alphatron", "furuno",
    "tokyo keiki", "anschutz", "raytheon", "yokogawa", "ydk",
    "macgregor", "danelec", "headway", "consilium", "highlander",
    "wartsila", "cobham", "sailor", "jotron", "netwave", "simrad", "entel", "kelvin hughes",
    "samsung", "totem plus", "ami", "hyundai", "garmin"
]

PART_NUMBER_TO_MAKER = [
    (r"(?i)\b(?:03p\d{4}|ru-\d{4}|far-\d{3,4}|fmd-\d{3,4}|vr-\d{4}|fe-\d{3}|gp-\d{2,3}|fs-\d{4}|felcom)\b", "FURUNO"),
    (r"(?i)\b(?:jcy-\d{3,4}|ncr-\d{3}|jma-\d{3,4}|jhs-\d{3}|jax-\d{2}|jlr-\d{2,3}|jue-\d{2,3}|jan-\d{3,4})\b", "JRC"),
    (r"(?i)\b(?:visionmaster|vmft|navigat\s*\d+|navipilot|naviknot|mk\s*37|658\d{2}|659\d{2})\b", "SPERRY MARINE"),
    (r"(?i)\b(?:dm100|dm-100|vr5000)\b", "DANELEC"),
    (r"(?i)\b(?:std\s*22|std-22|anschuetz)\b", "ANSCHUTZ"),
    (r"(?i)\b(?:cmz\d{3}|pt\d{3}|uz\d{3})\b", "YOKOGAWA"),
    (r"(?i)\b(?:tg-\d{4}|pr-\d{4}|es-\d{4})\b", "TOKYO KEIKI"),
    (r"(?i)\b(?:tr-8000|tron\s*\d{2})\b", "JOTRON"),
    (r"(?i)\b(?:sailor\s*\d{4}|tt-\d{4})\b", "COBHAM"),
]

COUNTRY_ALIASES = {c.lower(): c for c in set(PORT_TO_COUNTRY.values())}
for _k, _v in NEIGHBORING_COUNTRIES.items():
    COUNTRY_ALIASES[_k.lower()] = _k.upper()
    for _n in _v:
        COUNTRY_ALIASES[_n.lower()] = _n.upper()

COUNTRY_ALIASES.update({
    "china": "CHINA", "prc": "CHINA", "p.r.c.": "CHINA", "κίνα": "CHINA", "κινα": "CHINA",
    "uae": "UAE", "u.a.e.": "UAE", "united arab emirates": "UAE",
    "usa": "USA", "u.s.a.": "USA", "u.s.": "USA", "united states": "USA",
    "united states (usa)": "USA", "united states of america": "USA",
    "uk": "UK", "u.k.": "UK", "united kingdom": "UK", "great britain": "UK", "england": "UK",
    "south korea": "SOUTH KOREA", "korea": "SOUTH KOREA", "republic of korea": "SOUTH KOREA",
    "hellas": "GREECE", "ελλάδα": "GREECE", "ελλαδα": "GREECE",
    "μάλτα": "MALTA", "μαλτα": "MALTA", "ρουμανία": "ROMANIA", "τουρκία": "TURKEY",
    "türkiye": "TURKEY", "turkiye": "TURKEY", "κύπρος": "CYPRUS", "brasil": "BRAZIL",
    "the netherlands": "NETHERLANDS", "holland": "NETHERLANDS",
})


def canonical_country(raw_value):
    s = str(raw_value or "").strip().lower()
    if not s or s in {"not specified", "n/a", "none", "null"}:
        return ""
    if s in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[s].lower()
    s_clean = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
    if s_clean in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[s_clean].lower()
    return s


def _norm_maker_str(s):
    s = str(s or "").lower()
    return s.replace("ü", "u").replace("ä", "a").replace("ö", "o")


def evaluate_station_maker_status(approved_str, target_makers):
    if not target_makers:
        has_star = "*" in str(approved_str or "")
        return "✅ Maker Approved (*)" if has_star else "🔧 Non-Maker Approved"

    tokens = [t.strip() for t in re.split(r"[,;]", str(approved_str or "")) if t.strip()]
    has_star_approval = False
    has_unstarred_brand = False

    for m in target_makers:
        m_norm = _norm_maker_str(m).replace("*", "").strip()
        if not m_norm:
            continue
        m_first = m_norm.split()[0] if m_norm.split() else m_norm

        for tok in tokens:
            tok_has_star = "*" in tok
            tok_clean = _norm_maker_str(tok).replace("*", "").strip()

            matched = False
            if re.search(rf"(?<![a-z0-9]){re.escape(m_norm)}(?![a-z0-9])", tok_clean):
                matched = True
            elif len(m_first) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(m_first)}(?![a-z0-9])", tok_clean):
                matched = True

            if matched:
                if tok_has_star:
                    has_star_approval = True
                else:
                    has_unstarred_brand = True

    if has_star_approval:
        return "✅ Maker Approved"
    if has_unstarred_brand:
        return "🔧 Non-Maker Approved"
    return "🔧 Non-Maker Approved (Other Brands)"


def extract_matched_maker_badges(approved_str, target_makers):
    if not target_makers:
        return "All Makers"
    tokens = [t.strip() for t in re.split(r"[,;]", str(approved_str or "")) if t.strip()]
    badges = []
    for tok in tokens:
        tok_clean = _norm_maker_str(tok).replace("*", "").strip()
        for m in target_makers:
            m_norm = _norm_maker_str(m).replace("*", "").strip()
            m_first = m_norm.split()[0] if m_norm.split() else m_norm
            if re.search(rf"(?<![a-z0-9]){re.escape(m_norm)}(?![a-z0-9])", tok_clean) or (
                len(m_first) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(m_first)}(?![a-z0-9])", tok_clean)
            ):
                if "*" in tok:
                    badges.append(f"⭐ {tok}")
                else:
                    badges.append(f"🔧 {tok} (No *)")
                break
    return ", ".join(badges) if badges else "—"


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
# TEXT EXTRACTION & CLEANING
# ---------------------------------------------------------------------------
def clean_signatures(text):
    if not text:
        return ""
    cleaned = re.sub(r"(?i)\b(?:mobile|mob|cell|tel|telephone|phone|fax)\b\s*[:\.\-]?\s*[\+\d\s\(\)\/]{5,}", " ", text)
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
        if re.search(r"(?i)vasilikon\s*51|akti\s+moutsopoulou|akti\s+miaouli|operations\s+executive\s*\(hellas\)", s):
            continue
        if re.fullmatch(r"(?i)\s*(greece|hellas|piraeus|πειραιάς|πειραιας|ελλάδα|ελλαδα)\s*\.?\s*", s):
            continue
        kept.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def extract_text_from_file(uploaded_file):
    extracted_text = ""
    file_name = uploaded_file.name.lower()
    try:
        uploaded_file.seek(0)
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

    return clean_signatures(extracted_text)[:30000]


def clean_vessel_name(raw_name):
    if not raw_name or str(raw_name).strip().lower() in {"not specified", "n/a", "none", "unknown", "null"}:
        return "Not specified"
    text = str(raw_name).strip().strip('"').strip("'")
    text = re.sub(r"(?i)^(?:m/v|m/t|mv|mt|vessel|ship)\s*[:\-]?\s*", "", text)
    text = re.sub(r"(?i)\s*[\-–—]\s*(?:vdr|gmdss|annual|survey|radio|navtex|inspection|repair|radar|attendance|service|class|coc|imo|\/\/|@).*$", "", text)
    text = re.sub(r"(?i)\b(?:vdr|gmdss|annual|survey|radio|navtex|inspection|repair|attendance|service|coc|imo)\b.*$", "", text)
    text = re.sub(r"(?i)\b(?:will|at|eta|port|call|calling|arr|arriving|due|to|for|is|and|the|in|on|sailing|during|while)\b.*$", "", text)
    text = re.sub(r"[@\/\(\)\<\>\[\]].*$", "", text)
    text = re.sub(r"(?i)\btbn\b", " / ", text)
    text = re.sub(r"\s+", " ", text).strip(" /-–—")

    parts = [p.strip(" /-–—") for p in text.split("/") if p.strip(" /-–—")][:2]
    cleaned_parts = [" ".join(p.split()[:2]) for p in parts if p.split()]
    return " / ".join(cleaned_parts).title() if cleaned_parts else "Not specified"


def ports_in_text(text):
    if not text:
        return []
    lower = text.lower()
    found, taken = [], []
    for port_key in PORT_KEYS_BY_LENGTH:
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(port_key)}(?![a-z0-9])", lower):
            s, e = match.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            found.append((s, e, port_key, PORT_TO_COUNTRY[port_key]))
    found.sort(key=lambda item: item[0])
    return found


def find_country(text):
    if not text:
        return None
    lower = text.lower()
    for alias in COUNTRY_KEYS_BY_LENGTH:
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lower):
            return COUNTRY_ALIASES[alias]
    return None


def choose_primary_port(text):
    lower = (text or "").lower()
    dyn_match = re.search(r"(?i)(?:final\s+)?port\s+(?:is|will\s+be|@|:)?\s*([a-z]+)\s+([a-z]+)", lower)
    if dyn_match:
        cand_port, cand_country = dyn_match.group(1), dyn_match.group(2)
        if cand_country.lower() in COUNTRY_ALIASES:
            c_name = COUNTRY_ALIASES[cand_country.lower()]
            return cand_port.title(), c_name, [(0, 1, cand_port, c_name)]

    found = ports_in_text(text)
    if not found:
        return "Not specified", "Not specified", []

    thread_split = re.search(r"(?im)(?:^|\n)\s*(?:from\s*:|sent\s*:|-----original message-----|on\s+.*wrote\s*:)", text)
    first_reply_pos = thread_split.start() if thread_split else len(text)

    scored = []
    for start, end, key, country in found:
        window = lower[max(0, start - 80):min(len(lower), end + 80)]
        score = sum(w for tok, w in (("final port", 8), ("port", 3), ("eta", 4), ("calling", 4), ("bunker", 4)) if tok in window)
        if "instead of" in window and window.find("instead of") < window.find(key):
            score -= 15
        score += 20 if start < first_reply_pos else -5
        if key == "piraeus" and score <= 0:
            score = -10
        scored.append((score, start, key, country))

    scored.sort(key=lambda item: (-item[0], item[1]))
    _, _, key, country = scored[0]
    return key.title(), country, found


def find_makers(text_lower, vessel_name=""):
    found = []
    vessel_lower = (vessel_name or "").lower()
    raw = text_lower or ""
    for maker in KNOWN_MAKERS:
        if re.search(rf"(?<![a-z0-9]){re.escape(maker)}(?![a-z0-9])", raw) and maker not in vessel_lower:
            found.append(maker.upper())

    for pattern, inferred_maker in PART_NUMBER_TO_MAKER:
        if re.search(pattern, raw):
            found.append(inferred_maker)

    unique = []
    for m in sorted(set(found), key=len, reverse=True):
        if not any(m != o and m in o for o in unique):
            unique.append(m)
    return unique


def parse_manual_inputs(manual_text):
    overrides, explicit = {}, set()
    if not manual_text or not str(manual_text).strip():
        return overrides, explicit
    text = str(manual_text)

    maker_match = re.search(r"(?im)(?:^|\n)\s*(?:makers?|equipment|brand)\s*[:=\s]\s*([^\n]+)", text)
    if maker_match:
        overrides["makers"] = [m.strip().upper() for m in re.split(r"[,;/|]", maker_match.group(1)) if m.strip()]
        explicit.add("makers")
    else:
        found_m = find_makers(text.lower())
        if found_m:
            overrides["makers"] = found_m
            explicit.add("makers")

    country_match = re.search(r"(?im)(?:^|\n)\s*(?:country|χώρα|χωρα)\s*[:=\s]\s*([^\n]+)", text)
    if country_match:
        captured = country_match.group(1).strip()
        overrides["country"] = find_country(captured) or captured.strip(" .,").upper()
        explicit.add("country")

    port_match = re.search(r"(?im)(?:^|\n)\s*(?:port|λιμ[αά]νι|λιμανι)\s*[:=\s]\s*([^\n]+)", text)
    if port_match:
        captured = port_match.group(1).strip()
        kp = ports_in_text(captured)
        if kp:
            overrides["port"] = kp[0][2].title()
            overrides["country"] = kp[0][3]
            explicit.add("country")
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
    for k in RESULT_DEFAULTS:
        if k in data and data.get(k) is not None:
            result[k] = data.get(k)

    makers = result.get("makers")
    if isinstance(makers, str):
        result["makers"] = [m.strip().upper() for m in re.split(r"[,;/|]", makers) if m.strip()]
    elif isinstance(makers, list):
        result["makers"] = [str(m).strip().upper() for m in makers if str(m).strip()]
    else:
        result["makers"] = []

    result["vessel_name"] = clean_vessel_name(result.get("vessel_name"))
    if str(result.get("country", "")).strip():
        c = find_country(str(result["country"]))
        result["country"] = c if c else str(result["country"]).upper()

    p_key = str(result.get("port", "")).strip().lower()
    if p_key in PORT_TO_COUNTRY and result.get("country") in ("Not specified", ""):
        result["country"] = PORT_TO_COUNTRY[p_key]

    return result


# ---------------------------------------------------------------------------
# LOCAL PARSER & AI PARSING
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
    elif "radar" in text_lower:
        scope_text = "Radar Technical Attendance & Spare Parts Supply"
    elif "annual" in text_lower:
        scope_text = "Annual Radio / VDR / Navigation Survey"

    discrepancies = []
    if "instead of qingdao" in text_lower:
        discrepancies.append("Port revised: Final destination changed to Taicang China instead of Qingdao China.")

    return normalize_result({
        "vessel_name": vessel_name,
        "eta": eta,
        "port": port,
        "country": country,
        "makers": find_makers(text_lower, vessel_name),
        "scope": scope_text,
        "spares_requested": "Inquired per inquiry",
        "discrepancies": discrepancies,
        "missing_critical_data": [],
    })


def build_prompt(manual_override_text, cleaned_files, image_count):
    inquiry = (cleaned_files or "")[:15000]
    return f"""You are an expert maritime technical coordinator. Parse the commercial RFQ and extract facts into JSON.

CRITICAL INSTRUCTIONS:
1. MANUAL OVERRIDE IS ABSOLUTE GROUND TRUTH.
2. EMAIL THREAD CHRONOLOGY: The email at the VERY TOP is the active instruction. If it updates the port (e.g. 'Taicang China instead of Qingdao China' or 'Malta instead of Genova'), use the NEW port and list the old port in discrepancies.
3. VESSEL NAME: Strip 'MV', 'M/V', and scope words. For 'MV SEADUTY - VDR & GMDSS ANNUAL SURVEY', vessel_name is strictly 'Seaduty'.
4. MAKERS & PART NUMBERS: Scan the full text for makers (e.g., JRC, Furuno, Sperry, Danelec). Also infer the maker from OEM part numbers: e.g., '03P9335-66' or 'RU-9427' or 'FAR-2137' is 'FURUNO'; 'JCY-1900' or 'NCR-333' is 'JRC'; 'DM100' is 'DANELEC'.
5. DO NOT extract 'Piraeus' or 'Greece' from office signatures.

MANUAL OVERRIDE:
\"\"\"{manual_override_text or ""}\"\"\"

INQUIRY TEXT:
\"\"\"{inquiry}\"\"\"

Return ONLY valid JSON:
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


def parse_model_json(content):
    text = (content or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return json.loads(match.group(0) if match else text)


def analyze_rfq(manual_override_text, files_text, image_files):
    res_json = None
    model_used = None
    prompt_text = build_prompt(manual_override_text, files_text, len(image_files or []))

    if gemini_api_key and HAS_GOOGLE_GENAI:
        ai_client = genai.Client(api_key=gemini_api_key)
        for g_model in GEMINI_MODELS:
            try:
                resp = ai_client.models.generate_content(
                    model=g_model,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                parsed = normalize_result(parse_model_json(resp.text))
                if parsed:
                    res_json = parsed
                    model_used = f"Gemini ({g_model})"
                    break
            except Exception:
                continue

    if not res_json and client_groq:
        for model in get_active_groq_models():
            try:
                completion = client_groq.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You extract maritime RFQ facts. Reply with valid JSON only."},
                        {"role": "user", "content": prompt_text}
                    ],
                    temperature=0.1,
                )
                content = completion.choices[0].message.content or ""
                parsed = normalize_result(parse_model_json(content))
                if parsed:
                    res_json = parsed
                    model_used = f"Groq ({model})"
                    break
            except Exception:
                continue

    if not res_json:
        res_json = smart_local_parser(manual_override_text, files_text)
        model_used = "Local Rule Engine"

    local_check = smart_local_parser(manual_override_text, files_text)
    inferred_from_spares = find_makers(
        f"{res_json.get('scope', '')} {res_json.get('spares_requested', '')}".lower(),
        res_json.get("vessel_name", "")
    )
    combined_makers = list(res_json.get("makers") or [])
    for m in (local_check.get("makers") or []) + inferred_from_spares:
        if m not in combined_makers:
            combined_makers.append(m)
    res_json["makers"] = combined_makers

    if res_json.get("port") in ("Not specified", "") and local_check.get("port") != "Not specified":
        res_json["port"] = local_check["port"]
        res_json["country"] = local_check["country"]

    overrides, explicit = parse_manual_inputs(manual_override_text)
    for key in ("country", "port", "vessel_name", "eta", "makers"):
        if key in overrides and key in explicit:
            res_json[key] = overrides[key]

    res_json["_model_used"] = model_used
    return res_json


# ---------------------------------------------------------------------------
# GEMINI 3.8 / GROQ COPILOT CHATBOT
# ---------------------------------------------------------------------------
def ask_ai_assistant(user_message, rfq_context):
    ctx = rfq_context or RESULT_DEFAULTS
    system_instruction = f"""You are the Onetech Marine Service Assistant AI Copilot.
You assist maritime technical coordinators with RFQs, service attendances, maker authorizations, and spare parts.
Current Active RFQ Context:
- Vessel Name: {ctx.get('vessel_name', 'Not specified')}
- Port & Country: {ctx.get('port', 'Not specified')} ({ctx.get('country', 'Not specified')})
- ETA: {ctx.get('eta', 'Not specified')}
- Makers: {', '.join(ctx.get('makers', [])) or 'None detected'}
- Scope: {ctx.get('scope', 'Standard')}
- Spares: {ctx.get('spares_requested', 'None')}
- Discrepancies: {'; '.join(ctx.get('discrepancies', [])) or 'None'}

Format key vessel names, ports, part numbers, and dates inside square brackets [...] when drafting commercial messages.
Answer clearly, politely, and professionally in the requested language (English or Greek)."""

    errors = []

    if gemini_api_key and HAS_GOOGLE_GENAI:
        try:
            ai_client = genai.Client(api_key=gemini_api_key)
            candidate_models = list(GEMINI_MODELS)
            try:
                for m in ai_client.models.list():
                    m_name = getattr(m, "name", "").replace("models/", "")
                    if "gemini" in m_name and "flash" in m_name and m_name not in candidate_models:
                        candidate_models.append(m_name)
            except Exception:
                pass

            for g_model in candidate_models:
                try:
                    response = ai_client.models.generate_content(
                        model=g_model,
                        contents=user_message,
                        config=types.GenerateContentConfig(system_instruction=system_instruction)
                    )
                    if response and response.text:
                        return response.text, f"Gemini ({g_model})"
                except Exception as e:
                    errors.append(f"{g_model}: {e}")
        except Exception as e:
            errors.append(f"Gemini Client: {e}")

    if client_groq:
        for model in get_active_groq_models():
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
                return completion.choices[0].message.content, f"Groq ({model})"
            except Exception as e:
                errors.append(f"Groq ({model}): {e}")
                continue

    return f"Σφάλμα σύνδεσης: {' | '.join(errors[:2])}", "Offline"


# ---------------------------------------------------------------------------
# SESSION STATE MANAGEMENT
# ---------------------------------------------------------------------------
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0
if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "copilot_open" not in st.session_state:
    st.session_state.copilot_open = False
if "global_include_non_approved" not in st.session_state:
    st.session_state.global_include_non_approved = False


def reset_everything():
    st.session_state.reset_count += 1
    st.session_state.parsed_data = None
    st.session_state.chat_history = []
    st.session_state.global_
