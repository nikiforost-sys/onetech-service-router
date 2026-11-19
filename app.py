import base64
import email
from email import policy
import html
import io
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
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
# ENTERPRISE SAAS UI/UX STYLESHEET: FLOATING BUTTON, STICKY COPILOT & CARDS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
    --ot-navy: #0f172a;
    --ot-slate: #1e293b;
    --ot-primary: #0284c7;
    --ot-accent: #2563eb;
    --ot-border: #e2e8f0;
    --ot-text-main: #0f172a;
    --ot-text-muted: #64748b;
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 5rem !important;
    max-width: 1560px !important;
}

.ot-hero-bar {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0c4a6e 100%);
    border-radius: 14px;
    padding: 1.15rem 1.5rem;
    margin-bottom: 1.2rem;
    color: #ffffff;
    box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}
.ot-hero-left { display: flex; align-items: center; gap: 0.95rem; }
.ot-brand-logo {
    width: 44px; height: 44px; border-radius: 11px;
    background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; box-shadow: 0 4px 12px rgba(14, 165, 233, 0.35);
}
.ot-hero-title { font-size: 1.3rem; font-weight: 800; letter-spacing: -0.02em; margin: 0; color: #ffffff; line-height: 1.2; }
.ot-hero-subtitle { font-size: 0.82rem; color: #cbd5e1; margin: 0.18rem 0 0 0; }
.ot-hero-badges { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
.ot-pill {
    display: inline-flex; align-items: center; gap: 0.38rem;
    padding: 0.32rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
    background: rgba(255, 255, 255, 0.1); color: #f8fafc; border: 1px solid rgba(255, 255, 255, 0.16);
}
.ot-pill-live { background: rgba(16, 185, 129, 0.18); color: #6ee7b7; border-color: rgba(16, 185, 129, 0.35); }
.ot-dot-live { width: 7px; height: 7px; border-radius: 50%; background: #10b981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25); display: inline-block; }

.ot-section-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--ot-border);
}
.ot-section-title-wrap { display: flex; align-items: center; gap: 0.6rem; }
.ot-step-badge {
    background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
    color: #ffffff; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700;
    padding: 0.2rem 0.5rem; border-radius: 6px; letter-spacing: 0.04em;
}
.clean-header { font-size: 1.06rem; font-weight: 700; margin: 0; color: var(--ot-text-main); letter-spacing: -0.01em; }
.ot-section-caption { font-size: 0.76rem; color: var(--ot-text-muted); font-weight: 500; }

.ot-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin-bottom: 0.95rem; }
@media (max-width: 992px) { .ot-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 576px) { .ot-kpi-grid { grid-template-columns: 1fr; } }

.ot-kpi-card {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid var(--ot-border); border-left: 4px solid var(--ot-primary);
    border-radius: 10px; padding: 0.75rem 0.95rem; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}
.ot-kpi-label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ot-text-muted); margin-bottom: 0.22rem; }
.ot-kpi-value { font-size: 0.98rem; font-weight: 700; color: var(--ot-text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ot-kpi-sub { font-size: 0.72rem; color: var(--ot-text-muted); margin-top: 0.12rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.ot-badge-row { display: flex; flex-wrap: wrap; gap: 0.48rem; margin: 0.35rem 0 0.8rem 0; }
.ot-stat-badge { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.28rem 0.68rem; border-radius: 8px; font-size: 0.76rem; font-weight: 600; }
.ot-stat-onestop { background: #f5f3ff; color: #6d28d9; border: 1px solid #ddd6fe; }
.ot-stat-approved { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.ot-stat-unstarred { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.ot-stat-other { background: #f8fafc; color: #475569; border: 1px solid #cbd5e1; }
.ot-stat-neutral { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

.ot-alert-box { border-radius: 10px; padding: 0.7rem 0.95rem; margin-bottom: 0.8rem; font-size: 0.82rem; line-height: 1.45; }
.ot-alert-warn { background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; color: #92400e; }
.ot-alert-danger { background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444; color: #b91c1c; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    border-color: #e2e8f0 !important;
    box-shadow: 0 2px 6px -1px rgba(15, 23, 42, 0.04) !important;
}

button[kind="primary"] {
    background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
    border: none !important; font-weight: 600 !important; border-radius: 8px !important;
    box-shadow: 0 3px 10px rgba(37, 99, 235, 0.22) !important;
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
    font-size: 0.95rem !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.35) !important;
    border: 1px solid rgba(56, 189, 248, 0.4) !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2):has(.copilot-panel-marker) {
    position: sticky !important;
    top: 3.2rem !important;
    align-self: flex-start !important;
    max-height: calc(100vh - 5rem) !important;
}

.ot-copilot-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    color: #ffffff; padding: 0.8rem 1rem; border-radius: 10px; margin-bottom: 0.7rem;
}
.ot-copilot-title { font-size: 0.95rem; font-weight: 700; margin: 0; }
.ot-copilot-sub { font-size: 0.72rem; color: #93c5fd; margin-top: 0.1rem; }
.ot-sidebar-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.7rem 0.85rem; margin-bottom: 0.7rem; font-size: 0.8rem; }
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
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]

GROQ_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
]

GROQ_VISION_MODELS = {
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
}


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
# PORTS, COUNTRIES & MAKERS (ALL MARINE ELECTRONICS MAKERS & PART PATTERNS)
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
    "tokyo keiki", "raytheon anschutz", "anschutz", "raytheon",
    "yokogawa", "ydk", "macgregor", "danelec", "headway",
    "consilium", "highlander", "wartsila", "sam electronics", "transas",
    "cobham", "sailor", "thrane & thrane", "jotron", "netwave",
    "simrad", "kongsberg", "navico", "entel", "kelvin hughes", "hensoldt",
    "samsung", "totem plus", "ami", "hyundai", "garmin", "skipper",
    "mcmurdo", "kannad", "intellian", "kns", "seatel", "icom",
    "saab", "koden", "taiyo", "musasino", "nabtesco", "autronica", "deif"
]

PART_NUMBER_TO_MAKER = [
    (r"(?i)\b(?:03p\d{4}|ru-\d{4}|far-\d{3,4}|fmd-\d{3,4}|vr-\d{4}|fe-\d{3}|gp-\d{2,3}|fs-\d{4}|fm-\d{4}|fa-\d{3}|nx-\d{3}|ds-\d{2}|felcom)\b", "FURUNO"),
    (r"(?i)\b(?:jcy-\d{3,4}|ncr-\d{3}|jma-\d{3,4}|jhs-\d{3}|jax-\d{2}|jlr-\d{2,3}|jue-\d{2,3}|jan-\d{3,4}|jfe-\d{3}|jln-\d{3}|jsb-\d{3})\b", "JRC"),
    (r"(?i)\b(?:visionmaster|vmft|navigat\s*(?:x(?:\s*mk\s*\d+)?|\d+)|navipilot|naviknot|mk\s*37|658\d{2}|659\d{2}|020672-0000-000|044877-0000-000|074829-0000-000|044810-0000-000|025963-0000-000)\b", "SPERRY MARINE"),
    (r"(?i)\b(?:dm100|dm-100|dm200|vr5000|130\d{4})\b", "DANELEC"),
    (r"(?i)\b(?:std\s*22|std-22|standard\s*22|nautopilot|synapsis|anschuetz|110-\d{3})\b", "ANSCHUTZ"),
    (r"(?i)\b(?:cmz\d{3}|pt\d{3}|uz\d{3}|eml\d{3}|mkm\d{3})\b", "YOKOGAWA"),
    (r"(?i)\b(?:tg-\d{4}|pr-\d{4}|es-\d{4}|br-\d{4}|ec-\d{4})\b", "TOKYO KEIKI"),
    (r"(?i)\b(?:tr-8000|tron\s*\d{2}|tron\s*sart|tron\s*ais|fb-\d{2})\b", "JOTRON"),
    (r"(?i)\b(?:sailor\s*\d{4}|tt-\d{4}|fleetbroadband\s*\d{3}|sp35\d{2})\b", "COBHAM"),
    (r"(?i)\b(?:nw-?\d{4}|nw6000|nw4000|vdr-?g2)\b", "NETWAVE"),
    (r"(?i)\b(?:sal\s*r1|sal\s*t2|s-vdr\s*m\d|vdr\s*f2|selesmar)\b", "CONSILIUM"),
    (r"(?i)\b(?:hld-?vdr|hld-?s\d|hld-?ecdis)\b", "HIGHLANDER"),
    (r"(?i)\b(?:manta\s*digital|sharp\s*eye|kh-\d{3,4})\b", "KELVIN HUGHES"),
    (r"(?i)\b(?:gds\s*101|dl\s*850|dl\s*21|emln|es\s*n\d{3})\b", "SKIPPER"),
    (r"(?i)\b(?:chartpilot|radarpilot|nacoss|platinum|ns\s*4000)\b", "WARTSILA"),
    (r"(?i)\b(?:v\d{2,3}nx|fb\d{3}|t\d{3}w)\b", "INTELLIAN"),
    (r"(?i)\b(?:smartfind\s*(?:g8|e8|s5|s20))\b", "MCMURDO"),
    (r"(?i)\b(?:ap\d{2}|gc\d{2}|mx\d{3}|r\d{4})\b", "SIMRAD"),
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
    "korea, south": "SOUTH KOREA",
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


def _maker_matches_token(maker_raw, token_clean):
    m_norm = _norm_maker_str(maker_raw).replace("*", "").strip()
    if not m_norm:
        return False
    m_first = m_norm.split()[0] if m_norm.split() else m_norm
    if re.search(rf"(?<![a-z0-9]){re.escape(m_norm)}(?![a-z0-9])", token_clean):
        return True
    if len(m_first) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(m_first)}(?![a-z0-9])", token_clean):
        return True
    return False


def evaluate_station_coverage(approved_str, target_makers):
    """
    Evaluate 3-tier approval status + One-Stop-Shop multi-maker coverage.
    Returns dict with:
      - status: '✅ Maker Approved (*)' | '🟡 Maker Listed (No *)' | '🔧 Other Stations (Different Makers)'
      - coverage_label: e.g. '🏆 One-Stop (3/3 *)' | '🏆 One-Stop (3/3, 2*)' | '🔹 Partial (2/3, 1*)'
      - matched_badges: formatted string of matched makers
      - sort_rank: 0 (approved *), 1 (listed no *), 2 (other)
      - is_one_stop: bool (covers ALL target makers when len(target_makers) > 1)
      - star_count: int (how many distinct target makers have *)
      - matched_count: int (how many distinct target makers are listed at all)
    """
    tokens = [t.strip() for t in re.split(r"[,;]", str(approved_str or "")) if t.strip()]
    clean_targets = []
    for m in (target_makers or []):
        m_clean = str(m).replace("*", "").strip()
        if m_clean and m_clean.upper() not in [x.upper() for x in clean_targets]:
            clean_targets.append(m_clean)

    if not clean_targets:
        has_star = "*" in str(approved_str or "")
        return {
            "status": "✅ Maker Approved (*)" if has_star else "🟡 Maker Listed (No *)",
            "coverage_label": "All Makers",
            "matched_badges": "All Makers",
            "sort_rank": 0 if has_star else 1,
            "is_one_stop": False,
            "star_count": 1 if has_star else 0,
            "matched_count": 1,
        }

    star_count = 0
    matched_count = 0
    badges = []

    for m in clean_targets:
        m_has_star = False
        m_found = False
        matched_tok_display = None
        for tok in tokens:
            tok_clean = _norm_maker_str(tok).replace("*", "").strip()
            if _maker_matches_token(m, tok_clean):
                m_found = True
                if "*" in tok:
                    m_has_star = True
                    matched_tok_display = f"⭐ {tok}"
                    break
                elif matched_tok_display is None:
                    matched_tok_display = f"🟡 {tok} (No *)"
        if m_found:
            matched_count += 1
            if m_has_star:
                star_count += 1
            if matched_tok_display and matched_tok_display not in badges:
                badges.append(matched_tok_display)

    total_targets = len(clean_targets)
    is_multi = total_targets > 1
    is_one_stop = is_multi and (matched_count == total_targets)

    if star_count > 0:
        status = "✅ Maker Approved (*)"
        sort_rank = 0
    elif matched_count > 0:
        status = "🟡 Maker Listed (No *)"
        sort_rank = 1
    else:
        status = "🔧 Other Stations (Different Makers)"
        sort_rank = 2

    if is_multi:
        if star_count == total_targets:
            coverage_label = f"🏆 One-Stop ({star_count}/{total_targets} *)"
        elif matched_count == total_targets:
            coverage_label = f"🏆 One-Stop ({matched_count}/{total_targets}, {star_count}*)"
        elif matched_count > 0:
            coverage_label = f"🔹 Partial ({matched_count}/{total_targets}, {star_count}*)"
        else:
            coverage_label = f"— (0/{total_targets})"
    else:
        if star_count == 1:
            coverage_label = "⭐ 1/1 (*)"
        elif matched_count == 1:
            coverage_label = "🟡 1/1 (No *)"
        else:
            coverage_label = "—"

    return {
        "status": status,
        "coverage_label": coverage_label,
        "matched_badges": ", ".join(badges) if badges else "—",
        "sort_rank": sort_rank,
        "is_one_stop": is_one_stop,
        "star_count": star_count,
        "matched_count": matched_count,
    }


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
# UNIVERSAL ATTACHMENT EXTRACTOR (MSG, EML, PDF, EXCEL, DOCX, ZIP, IMAGES)
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


def _prepare_pil_image(img, max_dim=1800):
    """Normalize image to RGB and downscale gently so Vision API calls stay fast."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    return img


def _pil_to_jpeg_base64(img, quality=85):
    buf = io.BytesIO()
    _prepare_pil_image(img, max_dim=1600).save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _detect_extension_from_bytes(raw_bytes):
    if not raw_bytes or len(raw_bytes) < 8:
        return ""
    if raw_bytes.startswith(b"%PDF"):
        return ".pdf"
    if raw_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if raw_bytes.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if raw_bytes.startswith(b"RIFF") and raw_bytes[8:12] == b"WEBP":
        return ".webp"
    if raw_bytes.startswith((b"II*\x00", b"MM\x00*")):
        return ".tif"
    if raw_bytes.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                names = set(zf.namelist())
                if "word/document.xml" in names:
                    return ".docx"
                if any(n.startswith("xl/") for n in names):
                    return ".xlsx"
                return ".zip"
        except Exception:
            return ".zip"
    return ""


def _extract_docx_native(raw_bytes):
    """Pure-Python extractor for .docx paragraphs and tables (zero extra dependencies)."""
    lines = []
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        xml_targets = [n for n in zf.namelist() if n in ("word/document.xml", "word/header1.xml", "word/footer1.xml")]
        for target in xml_targets:
            root = ET.fromstring(zf.read(target))
            for elem in root.iter():
                tag = elem.tag.split("}")[-1]
                if tag == "p":
                    texts = [t.text for t in elem.iter() if t.tag.split("}")[-1] == "t" and t.text]
                    line = "".join(texts).strip()
                    if line:
                        lines.append(line)
    return "\n".join(lines)


def _extract_xlsx_native(raw_bytes):
    """Pure-Python fallback for .xlsx files if openpyxl is not installed."""
    out_lines = []
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        shared_strings = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.iter():
                if si.tag.endswith("}si") or si.tag == "si":
                    parts = [t.text for t in si.iter() if (t.tag.endswith("}t") or t.tag == "t") and t.text]
                    shared_strings.append("".join(parts))

        sheet_files = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        for sf in sheet_files:
            out_lines.append(f"--- Worksheet: {os.path.basename(sf)} ---")
            s_root = ET.fromstring(zf.read(sf))
            for row_el in s_root.iter():
                if row_el.tag.endswith("}row") or row_el.tag == "row":
                    row_vals = []
                    for c_el in row_el:
                        if not (c_el.tag.endswith("}c") or c_el.tag == "c"):
                            continue
                        c_type = c_el.attrib.get("t", "")
                        val_text = ""
                        for child in c_el:
                            if child.tag.endswith("}v") or child.tag == "v":
                                raw_v = child.text or ""
                                if c_type == "s" and raw_v.isdigit() and int(raw_v) < len(shared_strings):
                                    val_text = shared_strings[int(raw_v)]
                                else:
                                    val_text = raw_v
                            elif child.tag.endswith("}is") or child.tag == "is":
                                t_parts = [t.text for t in child.iter() if (t.tag.endswith("}t") or t.tag == "t") and t.text]
                                val_text = "".join(t_parts)
                        if str(val_text).strip():
                            row_vals.append(str(val_text).strip())
                    if row_vals:
                        out_lines.append(" | ".join(row_vals))
    return "\n".join(out_lines)


def _extract_xls_fallback(raw_bytes):
    """Fallback for legacy .xls / HTML / XML files when xlrd is not installed."""
    text_utf8 = raw_bytes.decode("utf-8", errors="ignore")
    if "<table" in text_utf8.lower() or "<row" in text_utf8.lower() or "<cell" in text_utf8.lower():
        stripped = re.sub(r"<[^>]+>", " ", text_utf8)
        return re.sub(r"\s+", " ", stripped).strip()
    utf16_chunks = re.findall(r"(?:[ -~]\x00){4,}", raw_bytes.decode("latin-1"))
    decoded_u16 = [c.encode("latin-1").decode("utf-16le", errors="ignore").strip() for c in utf16_chunks]
    ascii_chunks = re.findall(r"[A-Za-z0-9_\-\./:,;()@#&+ ]{5,}", raw_bytes.decode("latin-1", errors="ignore"))
    combined = [x for x in (decoded_u16 + ascii_chunks) if x and not x.startswith("Root Entry")]
    return "\n".join(combined)


def _extract_pdf_content(raw_bytes, source_name="document.pdf", max_pages=25, max_vision_pages=8):
    """Extract text from PDF; for scanned/image-only pages, extract page images for Vision AI."""
    extracted_text_parts = []
    extracted_images = []
    notes = []

    reader = pypdf.PdfReader(io.BytesIO(raw_bytes))

    for page_idx, page in enumerate(reader.pages[:max_pages]):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            extracted_text_parts.append(page_text)

        if len(page_text) < 40 and len(extracted_images) < max_vision_pages:
            page_imgs_found = 0
            try:
                page_img_objs = list(getattr(page, "images", []))
                for img_obj in page_img_objs:
                    if len(extracted_images) >= max_vision_pages:
                        break
                    img_bytes = getattr(img_obj, "data", None)
                    if not img_bytes:
                        continue
                    try:
                        pil_img = Image.open(io.BytesIO(img_bytes))
                        if len(page_img_objs) > 1 and min(pil_img.size) < 150:
                            continue
                        extracted_images.append((f"{source_name} (p.{page_idx + 1})", _prepare_pil_image(pil_img)))
                        page_imgs_found += 1
                    except Exception:
                        continue
            except Exception:
                pass

            if page_imgs_found == 0 and len(extracted_images) < max_vision_pages:
                try:
                    import pypdfium2 as pdfium
                    pdf_doc = pdfium.PdfDocument(raw_bytes)
                    pil_page = pdf_doc[page_idx].render(scale=2.0).to_pil()
                    extracted_images.append((f"{source_name} (p.{page_idx + 1})", _prepare_pil_image(pil_page)))
                except Exception:
                    pass

    if extracted_images:
        notes.append(f"Scanned PDF '{source_name}': {len(extracted_images)} page(s) sent to AI Vision")

    return "\n\n".join(extracted_text_parts), extracted_images, notes


def _strip_html_to_text(html_str):
    if not html_str:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html_str)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|li|h[1-6])>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def extract_content_from_bytes(raw_bytes, file_name, _depth=0):
    """
    Recursively extract text AND Vision images from:
    MSG, EML (incl. all attachments & inline images), PDF (text + scanned),
    Excel (XLSX/XLS), CSV, Word (DOCX), ZIP archives, HTML/XML/TXT, and JPEG/PNG/TIFF/WEBP.
    Returns: (cleaned_text, list_of_(label, PIL.Image), list_of_notes)
    """
    if not raw_bytes or _depth > 4:
        return "", [], []

    orig_name = str(file_name or "").strip()
    fname_lower = orig_name.lower()
    if "." not in os.path.basename(fname_lower):
        inferred_ext = _detect_extension_from_bytes(raw_bytes)
        if inferred_ext:
            orig_name = (orig_name or "inline_attachment") + inferred_ext
            fname_lower = orig_name.lower()

    extracted_text = ""
    extracted_images = []
    notes = []

    try:
        if fname_lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif")):
            pil_img = Image.open(io.BytesIO(raw_bytes))
            is_tiny_sig = _depth > 0 and (min(pil_img.size) < 160 or (pil_img.size[0] * pil_img.size[1] < 35000))
            if not is_tiny_sig:
                extracted_images.append((orig_name, _prepare_pil_image(pil_img)))
                if _depth > 0:
                    notes.append(f"Image '{orig_name}' sent to AI Vision")

        elif fname_lower.endswith(".pdf"):
            pdf_txt, pdf_imgs, pdf_notes = _extract_pdf_content(raw_bytes, source_name=orig_name)
            extracted_text += pdf_txt
            extracted_images.extend(pdf_imgs)
            notes.extend(pdf_notes)

        elif fname_lower.endswith(".docx"):
            doc_txt = _extract_docx_native(raw_bytes)
            if doc_txt:
                extracted_text += doc_txt
                if _depth > 0:
                    notes.append(f"Word '{orig_name}' parsed")

        elif fname_lower.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                for zinfo in zf.infolist()[:25]:
                    if zinfo.is_dir() or zinfo.filename.startswith("__MACOSX"):
                        continue
                    try:
                        zbytes = zf.read(zinfo.filename)
                    except Exception:
                        continue
                    z_txt, z_imgs, z_notes = extract_content_from_bytes(zbytes, os.path.basename(zinfo.filename), _depth + 1)
                    if z_txt:
                        extracted_text += f"\n--- ZIP ENTRY: {zinfo.filename} ---\n{z_txt}\n"
                    extracted_images.extend(z_imgs)
                    notes.extend(z_notes)
                notes.append(f"ZIP '{orig_name}' unpacked")

        elif fname_lower.endswith(".eml"):
            msg = email.message_from_bytes(raw_bytes, policy=policy.default)
            extracted_text += f"\nSubject: {msg.get('subject', '')}\n"
            body = msg.get_body(preferencelist=("plain", "html"))
            if body:
                content = body.get_content()
                if body.get_content_type() == "text/html":
                    content = _strip_html_to_text(content)
                extracted_text += f"{content}\n"

            for part in msg.walk():
                if part.is_multipart():
                    continue
                ctype = (part.get_content_type() or "").lower()
                cdisp = str(part.get("Content-Disposition", "")).lower()
                att_name = part.get_filename() or ""
                is_attachment_or_inline_img = (
                    "attachment" in cdisp
                    or bool(att_name)
                    or ctype.startswith("image/")
                    or ctype == "application/pdf"
                )
                if not is_attachment_or_inline_img:
                    continue
                if ctype in ("text/plain", "text/html") and not att_name:
                    continue
                att_payload = part.get_payload(decode=True)
                if not att_payload:
                    continue
                if not att_name:
                    ext_guess = _detect_extension_from_bytes(att_payload)
                    att_name = f"inline_part{ext_guess}" if ext_guess else ""
                if not att_name:
                    continue
                att_txt, att_imgs, att_notes = extract_content_from_bytes(att_payload, att_name, _depth + 1)
                if att_txt:
                    extracted_text += f"\n--- EMBEDDED ATTACHMENT: {att_name} ---\n{att_txt}\n"
                extracted_images.extend(att_imgs)
                notes.extend(att_notes)
                if not att_notes and (att_txt or att_imgs):
                    notes.append(f"Attachment '{att_name}' parsed from EML")

        elif fname_lower.endswith(".msg"):
            msg = extract_msg.Message(io.BytesIO(raw_bytes))
            try:
                body_txt = msg.body or ""
                if not body_txt.strip() and getattr(msg, "htmlBody", None):
                    raw_html = msg.htmlBody
                    if isinstance(raw_html, bytes):
                        raw_html = raw_html.decode("utf-8", errors="ignore")
                    body_txt = _strip_html_to_text(raw_html)
                extracted_text += f"\nSubject: {msg.subject or ''}\nBody:\n{body_txt}\n"

                for idx, att in enumerate(getattr(msg, "attachments", []) or [], 1):
                    att_name = (
                        getattr(att, "longFilename", None)
                        or getattr(att, "shortFilename", None)
                        or getattr(att, "name", None)
                        or ""
                    )
                    att_name = str(att_name).strip()
                    att_data = getattr(att, "data", None)
                    if att_data is None:
                        continue

                    if hasattr(att_data, "subject") and hasattr(att_data, "body"):
                        nested_subj = getattr(att_data, "subject", "") or ""
                        nested_body = getattr(att_data, "body", "") or ""
                        extracted_text += f"\n--- EMBEDDED EMAIL: {att_name or nested_subj} ---\nSubject: {nested_subj}\n{nested_body}\n"
                        notes.append(f"Nested email '{att_name or nested_subj}' parsed")
                        continue

                    if isinstance(att_data, (bytes, bytearray)):
                        raw_att = bytes(att_data)
                        if not att_name:
                            ext_guess = _detect_extension_from_bytes(raw_att)
                            if ext_guess:
                                att_name = f"msg_attachment_{idx}{ext_guess}"
                        if not att_name:
                            continue
                        att_txt, att_imgs, att_notes = extract_content_from_bytes(raw_att, att_name, _depth + 1)
                        if att_txt:
                            extracted_text += f"\n--- EMBEDDED ATTACHMENT: {att_name} ---\n{att_txt}\n"
                        extracted_images.extend(att_imgs)
                        notes.extend(att_notes)
                        if not att_notes and (att_txt or att_imgs):
                            notes.append(f"Attachment '{att_name}' parsed from MSG")
            finally:
                try:
                    msg.close()
                except Exception:
                    pass

        elif fname_lower.endswith((".xlsx", ".xls")):
            parsed_ok = False
            try:
                excel_sheets = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=None)
                for sheet_name, sheet_df in excel_sheets.items():
                    if sheet_df is not None and not sheet_df.empty:
                        extracted_text += f"\n--- Excel Sheet: {sheet_name} ---\n"
                        extracted_text += sheet_df.fillna("").to_string(index=False) + "\n"
                if extracted_text.strip():
                    parsed_ok = True
            except Exception:
                parsed_ok = False

            if not parsed_ok and zipfile.is_zipfile(io.BytesIO(raw_bytes)):
                try:
                    extracted_text += _extract_xlsx_native(raw_bytes)
                    parsed_ok = bool(extracted_text.strip())
                except Exception:
                    parsed_ok = False

            if not parsed_ok:
                try:
                    html_tables = pd.read_html(io.BytesIO(raw_bytes))
                    for idx, tbl_df in enumerate(html_tables, 1):
                        if tbl_df is not None and not tbl_df.empty:
                            extracted_text += f"\n--- Table {idx} ---\n"
                            extracted_text += tbl_df.fillna("").to_string(index=False) + "\n"
                    parsed_ok = bool(extracted_text.strip())
                except Exception:
                    parsed_ok = False

            if not parsed_ok:
                extracted_text += _extract_xls_fallback(raw_bytes)

            if _depth > 0 and extracted_text.strip():
                notes.append(f"Excel '{orig_name}' parsed")

        elif fname_lower.endswith(".csv"):
            raw_csv = raw_bytes.decode("utf-8-sig", errors="replace")
            try:
                csv_df = pd.read_csv(io.StringIO(raw_csv), sep=None, engine="python", on_bad_lines="skip")
            except Exception:
                csv_df = pd.read_csv(io.StringIO(raw_csv), on_bad_lines="skip")
            if csv_df is not None and not csv_df.empty:
                extracted_text += csv_df.fillna("").to_string(index=False) + "\n"
                if _depth > 0:
                    notes.append(f"CSV '{orig_name}' parsed")

        elif fname_lower.endswith((".html", ".htm")):
            extracted_text = _strip_html_to_text(raw_bytes.decode("utf-8", errors="ignore"))

        elif fname_lower.endswith((".txt", ".md", ".xml", ".json", ".log", ".rtf")):
            raw_txt = raw_bytes.decode("utf-8", errors="ignore")
            if fname_lower.endswith(".rtf"):
                raw_txt = re.sub(r"\\[a-z]+\d* ?|[{}]", " ", raw_txt)
            extracted_text = raw_txt

        else:
            decoded = raw_bytes.decode("utf-8", errors="ignore")
            printable_ratio = sum(ch.isprintable() or ch.isspace() for ch in decoded[:2000]) / max(1, len(decoded[:2000]))
            if printable_ratio > 0.85 and len(decoded.strip()) > 10:
                extracted_text = decoded
                if _depth > 0:
                    notes.append(f"File '{orig_name}' read as text")
    except Exception as e:
        if _depth == 0:
            st.error(f"Error parsing {orig_name}: {e}")

    cleaned = clean_signatures(extracted_text)[:35000] if _depth == 0 else extracted_text
    return cleaned, extracted_images[:8], notes


def extract_content_from_file(uploaded_file):
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    return extract_content_from_bytes(raw_bytes, uploaded_file.name, _depth=0)


def extract_text_from_file(uploaded_file):
    txt, _, _ = extract_content_from_file(uploaded_file)
    return txt


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
    raw_country = str(result.get("country", "")).strip()
    if raw_country and raw_country.lower() not in {"not specified", "n/a", "none", "null", "unknown"}:
        c = find_country(raw_country)
        result["country"] = c if c else raw_country.upper()
    else:
        result["country"] = "Not specified"

    port_str = str(result.get("port", "")).strip()
    if port_str and port_str.lower() not in {"not specified", "n/a", "none", "null", "unknown"}:
        matched_ports = ports_in_text(port_str)
        if matched_ports:
            result["port"] = matched_ports[0][2].title()
            if result.get("country") in ("Not specified", ""):
                result["country"] = matched_ports[0][3]
    else:
        result["port"] = "Not specified"

    for list_key in ("discrepancies", "missing_critical_data"):
        val = result.get(list_key)
        if isinstance(val, str):
            result[list_key] = [val.strip()] if val.strip() and val.strip().lower() != "none" else []
        elif isinstance(val, list):
            result[list_key] = [str(x).strip() for x in val if str(x).strip() and str(x).strip().lower() != "none"]
        else:
            result[list_key] = []

    return result


# ---------------------------------------------------------------------------
# LOCAL PARSER & MULTIMODAL AI PARSING
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
    elif "gyro" in text_lower:
        scope_text = "Gyro Compass Technical Attendance & Service"
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
    inquiry = (cleaned_files or "")[:24000]
    vision_note = (
        f"\n7. ATTACHED IMAGES / SCANNED PDF PAGES ({image_count} image(s) attached): "
        f"Carefully read EVERY attached photo, screenshot, nameplate, parts list, or scanned PDF page (including prior Service Reports extracted from email attachments). "
        f"Extract the equipment maker(s), model(s), serial numbers, and ALL requested/recommended spare parts with their part numbers and quantities. "
        f"CRITICAL FOR SERVICE REPORTS: Ignore the service station's letterhead / 'Authorised Dealership' list of brands — "
        f"extract ONLY the maker(s) of the vessel's actual equipment requiring service or spares."
        if image_count
        else ""
    )
    return f"""You are an expert maritime technical coordinator. Parse the commercial RFQ and ALL extracted attachments (emails, PDFs, Excel tables, Word docs, images, and scanned reports) into structured JSON.

CRITICAL INSTRUCTIONS:
1. MANUAL OVERRIDE IS ABSOLUTE GROUND TRUTH.
2. EMAIL THREAD CHRONOLOGY: The email at the VERY TOP is the active instruction. If it updates the port (e.g. 'Taicang China instead of Qingdao China' or 'Malta instead of Genova'), use the NEW port and list the old port in discrepancies. A prior Service Report attached to the email may show an older port (e.g. Weihai, China); always use the NEW requested attendance port from the email body.
3. VESSEL NAME: Strip 'MV', 'M/V', 'MT', 'M/T', and scope words. For 'MV SEADUTY - VDR & GMDSS ANNUAL SURVEY', vessel_name is strictly 'Seaduty'.
4. ALL MAKERS, MODELS & SPARE PARTS: Identify EVERY marine electronics maker involved across the email, Excel/CSV tables, Word/PDF attachments, and attached images (e.g., Furuno, JRC, Alphatron, Sperry Marine, Danelec, Yokogawa/YDK, Tokyo Keiki, Anschutz, Cobham/SAILOR, Jotron, Netwave, Consilium, Highlander, MacGregor, Wartsila/SAM/Transas, Kelvin Hughes, Simrad, Skipper, Intellian, McMurdo, etc.). Infer the maker from ANY model or OEM part number — NOT just one brand.
5. SPARES REQUESTED: Extract a clean, concise list of ALL requested or recommended spare parts (including description, OEM part number, and quantity if shown) across ALL makers and attachments.
6. DO NOT extract 'Piraeus' or 'Greece' from office signatures.{vision_note}

MANUAL OVERRIDE:
\"\"\"{manual_override_text or ""}\"\"\"

INQUIRY & ATTACHMENTS TEXT:
\"\"\"{inquiry}\"\"\"

Return ONLY valid JSON:
{{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA or 'Not specified'",
  "port": "Service port or 'Not specified'",
  "country": "Service country or 'Not specified'",
  "makers": ["All OEM makers requiring service or spares"],
  "scope": "Concise technical scope summary including equipment model",
  "spares_requested": "Exact list of spares & part numbers requested/recommended, or 'None / Attendance only'",
  "discrepancies": ["Source A says X; source B says Y"],
  "missing_critical_data": ["What is missing"]
}}"""


def parse_model_json(content):
    text = (content or "").strip()
    text = re.sub(r"^`{3}(?:json)?|`{3}$", "", text, flags=re.MULTILINE).strip()
    try:
        return normalize_result(json.loads(text))
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return normalize_result(json.loads(match.group(0)))
            except Exception:
                pass
    return None


def call_gemini_model(prompt, pil_images, preferred_model=None):
    if not gemini_api_key:
        return None, None
    candidates = ([preferred_model] if preferred_model in GEMINI_MODELS else []) + [
        m for m in GEMINI_MODELS if m != preferred_model
    ]
    for model_name in candidates:
        if HAS_GOOGLE_GENAI:
            try:
                client = genai.Client(api_key=gemini_api_key)
                contents = [prompt] + (list(pil_images) if pil_images else [])
                resp = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.1),
                )
                parsed = parse_model_json(getattr(resp, "text", ""))
                if parsed:
                    return parsed, f"Gemini ({model_name})"
            except Exception:
                pass
        if HAS_LEGACY_GENAI:
            try:
                legacy_genai.configure(api_key=gemini_api_key)
                model = legacy_genai.GenerativeModel(model_name)
                contents = [prompt] + (list(pil_images) if pil_images else [])
                resp = model.generate_content(contents)
                parsed = parse_model_json(getattr(resp, "text", ""))
                if parsed:
                    return parsed, f"Gemini ({model_name})"
            except Exception:
                pass
    return None, None


def call_groq_model(prompt, pil_images=None, preferred_model=None):
    if not client_groq:
        return None, None
    active_models = get_active_groq_models()
    if pil_images:
        vision_candidates = [m for m in active_models if m in GROQ_VISION_MODELS or "vision" in m.lower() or "llama-4" in m.lower()]
        other_candidates = [m for m in active_models if m not in vision_candidates]
        ordered = vision_candidates + other_candidates
    else:
        ordered = active_models

    candidates = ([preferred_model] if preferred_model in ordered else []) + [
        m for m in ordered if m != preferred_model
    ]
    for model_name in candidates:
        try:
            is_vision = model_name in GROQ_VISION_MODELS or "vision" in model_name.lower() or "llama-4" in model_name.lower()
            if pil_images and is_vision:
                user_content = [{"type": "text", "text": prompt}]
                for img in list(pil_images)[:5]:
                    b64_img = _pil_to_jpeg_base64(img)
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                    })
                messages = [
                    {"role": "system", "content": "You are a precise maritime RFQ extraction engine. Output strictly valid JSON."},
                    {"role": "user", "content": user_content},
                ]
            else:
                messages = [
                    {"role": "system", "content": "You are a precise maritime RFQ extraction engine. Output strictly valid JSON."},
                    {"role": "user", "content": prompt},
                ]

            resp = client_groq.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=2000,
            )
            parsed = parse_model_json(resp.choices[0].message.content)
            if parsed:
                return parsed, f"Groq ({model_name})"
        except Exception:
            continue
    return None, None


def reconcile_results(ai_result, local_result, manual_override_text):
    base = dict(local_result or RESULT_DEFAULTS)
    if ai_result:
        for k in ("vessel_name", "eta", "port", "country", "scope", "spares_requested"):
            ai_val = str(ai_result.get(k, "")).strip()
            if ai_val and ai_val.lower() not in {"not specified", "n/a", "none", "null", "unknown"}:
                base[k] = ai_result[k]

        combined_makers = []
        for m in (ai_result.get("makers") or []) + (local_result.get("makers") or []):
            m_up = str(m).strip().upper()
            if m_up and m_up not in combined_makers:
                combined_makers.append(m_up)
        base["makers"] = combined_makers

        for list_k in ("discrepancies", "missing_critical_data"):
            merged = []
            for item in (ai_result.get(list_k) or []) + (local_result.get(list_k) or []):
                s = str(item).strip()
                if s and s not in merged:
                    merged.append(s)
            base[list_k] = merged

    if str(base.get("port", "")).lower() == "piraeus" and str(local_result.get("port", "")).lower() not in ("piraeus", "not specified"):
        base["port"] = local_result["port"]
        base["country"] = local_result["country"]

    overrides, explicit = parse_manual_inputs(manual_override_text)
    for k, v in overrides.items():
        if k in explicit and v:
            base[k] = v

    normalized = normalize_result(base)
    missing = []
    if normalized.get("vessel_name") in ("Not specified", ""):
        missing.append("Vessel Name is not specified")
    if normalized.get("port") in ("Not specified", "") and normalized.get("country") in ("Not specified", ""):
        missing.append("Destination Port / Country is missing")
    if normalized.get("eta") in ("Not specified", ""):
        missing.append("Vessel ETA / Schedule is not specified")
    if not normalized.get("makers"):
        missing.append("Equipment Maker / OEM Brand is not specified")
    normalized["missing_critical_data"] = missing
    return normalized


def analyze_inquiry(manual_override_text, cleaned_files, pil_images, selected_engine):
    local_res = smart_local_parser(manual_override_text, cleaned_files)
    prompt = build_prompt(manual_override_text, cleaned_files, len(pil_images or []))
    ai_res, used_engine = None, "Smart Local Parser"

    if selected_engine == "Local Deterministic Only":
        return reconcile_results(None, local_res, manual_override_text), "Smart Local Parser"

    if selected_engine.startswith("Gemini ::"):
        pref = selected_engine.split("::", 1)[1].strip()
        ai_res, used_engine = call_gemini_model(prompt, pil_images, preferred_model=pref)
        if not ai_res:
            ai_res, used_engine = call_groq_model(prompt, pil_images=pil_images)
    elif selected_engine.startswith("Groq ::"):
        pref = selected_engine.split("::", 1)[1].strip()
        if pil_images and pref not in GROQ_VISION_MODELS and gemini_api_key:
            ai_res, used_engine = call_gemini_model(prompt, pil_images)
        if not ai_res:
            ai_res, used_engine = call_groq_model(prompt, pil_images=pil_images, preferred_model=pref)
            if not ai_res:
                ai_res, used_engine = call_gemini_model(prompt, pil_images)
    else:
        if pil_images and gemini_api_key:
            ai_res, used_engine = call_gemini_model(prompt, pil_images)
        if not ai_res and client_groq:
            ai_res, used_engine = call_groq_model(prompt, pil_images=pil_images)
        if not ai_res and gemini_api_key:
            ai_res, used_engine = call_gemini_model(prompt, pil_images)

    if not used_engine:
        used_engine = "Smart Local Parser"
    return reconcile_results(ai_res, local_res, manual_override_text), used_engine


# ---------------------------------------------------------------------------
# 3-TIER DIRECTORY ROUTING + ONE-STOP-SHOP MULTI-MAKER COVERAGE
# ---------------------------------------------------------------------------
def get_approved_makers_col(df):
    if df is None or df.empty:
        return "Approved Makers"
    for c in df.columns:
        if c.strip().lower() == "approved makers":
            return c
    for c in df.columns:
        if "maker" in c.lower() or "brand" in c.lower():
            return c
    return df.columns[-1]


def route_service_stations(
    df_dir,
    target_country,
    target_makers,
    include_maker_unstarred=False,
    include_other_stations=False,
    one_stop_only=False,
):
    """
    3-tier station routing with Multi-Maker One-Stop-Shop ranking:
      Tier 0 (always shown):   Maker Approved (*)
      Tier 1 (optional toggle): Maker Listed without * (capable, not OEM approved)
      Tier 2 (optional toggle): Other stations in the same country (different makers)
    Returns: (primary_df, neighbor_df, neighbor_countries, tier_counts)
    """
    empty_counts = {"approved": 0, "unstarred": 0, "other": 0, "one_stop": 0}
    if df_dir is None or df_dir.empty:
        return pd.DataFrame(), pd.DataFrame(), [], empty_counts

    target_canon = canonical_country(target_country)
    if not target_canon:
        return pd.DataFrame(), pd.DataFrame(), [], empty_counts

    maker_col = get_approved_makers_col(df_dir)
    work_df = df_dir.copy()
    work_df["_canon_country"] = work_df["Country"].apply(canonical_country)

    evals = work_df[maker_col].apply(lambda s: evaluate_station_coverage(s, target_makers))
    work_df["Approval Status"] = evals.apply(lambda r: r["status"])
    work_df["Maker Coverage"] = evals.apply(lambda r: r["coverage_label"])
    work_df["Matched Makers"] = evals.apply(lambda r: r["matched_badges"])
    work_df["_sort_rank"] = evals.apply(lambda r: r["sort_rank"])
    work_df["_is_one_stop"] = evals.apply(lambda r: 1 if r["is_one_stop"] else 0)
    work_df["_star_count"] = evals.apply(lambda r: r["star_count"])
    work_df["_matched_count"] = evals.apply(lambda r: r["matched_count"])

    primary_pool = work_df[work_df["_canon_country"] == target_canon].copy()
    tier_counts = {
        "approved": int((primary_pool["_sort_rank"] == 0).sum()),
        "unstarred": int((primary_pool["_sort_rank"] == 1).sum()),
        "other": int((primary_pool["_sort_rank"] == 2).sum()),
        "one_stop": int((primary_pool["_is_one_stop"] == 1).sum()),
    }

    allowed_primary_ranks = {0}
    if include_maker_unstarred:
        allowed_primary_ranks.add(1)
    if include_other_stations:
        allowed_primary_ranks.add(2)

    primary_matched = primary_pool[primary_pool["_sort_rank"].isin(allowed_primary_ranks)].copy()
    if one_stop_only and len(target_makers or []) > 1:
        primary_matched = primary_matched[primary_matched["_is_one_stop"] == 1].copy()

    primary_matched = primary_matched.sort_values(
        by=["_is_one_stop", "_sort_rank", "_star_count", "_matched_count", "Country", "Service Station Name"],
        ascending=[False, True, False, False, True, True],
    ).reset_index(drop=True)

    neighbors = NEIGHBORING_COUNTRIES.get(target_canon, [])
    neighbor_matched = pd.DataFrame()
    if neighbors:
        neighbor_pool = work_df[work_df["_canon_country"].isin(neighbors)].copy()
        allowed_neighbor_ranks = {0}
        if include_maker_unstarred:
            allowed_neighbor_ranks.add(1)
        neighbor_matched = neighbor_pool[neighbor_pool["_sort_rank"].isin(allowed_neighbor_ranks)].copy()
        if one_stop_only and len(target_makers or []) > 1:
            neighbor_matched = neighbor_matched[neighbor_matched["_is_one_stop"] == 1].copy()

        n_order = {n: idx for idx, n in enumerate(neighbors)}
        neighbor_matched["_n_order"] = neighbor_matched["_canon_country"].map(lambda c: n_order.get(c, 99))
        neighbor_matched = neighbor_matched.sort_values(
            by=["_is_one_stop", "_sort_rank", "_star_count", "_matched_count", "_n_order", "Service Station Name"],
            ascending=[False, True, False, False, True, True],
        ).drop(columns=["_n_order"], errors="ignore").reset_index(drop=True)

    drop_cols = ["_canon_country", "_sort_rank", "_is_one_stop", "_star_count", "_matched_count"]
    primary_clean = primary_matched.drop(columns=drop_cols, errors="ignore")
    neighbor_clean = neighbor_matched.drop(columns=drop_cols, errors="ignore")

    preferred_front = ["Approval Status", "Maker Coverage", "Matched Makers", "Country", "Service Station Name", maker_col]
    if not primary_clean.empty:
        f_cols = [c for c in preferred_front if c in primary_clean.columns]
        primary_clean = primary_clean[f_cols + [c for c in primary_clean.columns if c not in f_cols]]
    if not neighbor_clean.empty:
        nf_cols = [c for c in preferred_front if c in neighbor_clean.columns]
        neighbor_clean = neighbor_clean[nf_cols + [c for c in neighbor_clean.columns if c not in nf_cols]]

    return primary_clean, neighbor_clean, neighbors, tier_counts


def extract_outlook_emails(df_stations):
    if df_stations is None or df_stations.empty:
        return [], []
    email_pattern = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    unique_emails, station_records = [], []

    for _, row in df_stations.iterrows():
        st_name = str(row.get("Service Station Name", "Station")).strip()
        st_country = str(row.get("Country", "")).strip()
        st_status = str(row.get("Approval Status", "")).strip()
        st_cov = str(row.get("Maker Coverage", "")).strip()
        row_blob = " | ".join(str(v) for v in row.values if pd.notna(v))
        found_in_row = []
        for match in email_pattern.findall(row_blob):
            clean_em = match.strip(" .,;:<>()[]\"'").lower()
            if clean_em and not clean_em.endswith((".png", ".jpg", ".pdf")):
                if clean_em not in found_in_row:
                    found_in_row.append(clean_em)
                if clean_em not in unique_emails:
                    unique_emails.append(clean_em)

        station_records.append({
            "Service Station": st_name,
            "Country": st_country,
            "Approval Status": st_status,
            "Maker Coverage": st_cov,
            "Extracted Emails": "; ".join(found_in_row) if found_in_row else "No email in directory row",
        })
    return unique_emails, station_records


def generate_bracketed_rfq_template(parsed_data, matched_df=None):
    d = parsed_data or RESULT_DEFAULTS
    vessel = d.get("vessel_name") or "Not specified"
    port = d.get("port") or "Not specified"
    country = d.get("country") or "Not specified"
    eta = d.get("eta") or "Not specified"
    makers_list = d.get("makers") or []
    makers_str = ", ".join(makers_list) if makers_list else "OEM Equipment / TBA"
    scope = d.get("scope") or "Standard technical attendance inquiry."
    spares = d.get("spares_requested") or "Inquired per inquiry"

    station_names = []
    if matched_df is not None and not matched_df.empty and "Service Station Name" in matched_df.columns:
        station_names = [str(x).strip() for x in matched_df["Service Station Name"].head(5).tolist() if str(x).strip()]
    station_greeting = " / ".join(station_names) if station_names else "Authorized Service Coordinator"

    return f"""Subject: RFQ: Technical Attendance - M/V [{vessel}] @ [{port}, {country}] - ETA: [{eta}] - [{makers_str}]

Dear [{station_greeting}],

Good day.

Kindly provide your best quotation, technician availability, and applicable rates for the following service attendance:

====================================================================
  VESSEL & ATTENDANCE PARTICULARS
====================================================================
- Vessel Name        : M/V [{vessel}]
- IMO Number         : [IMO Number / TBA]
- Service Port       : [{port}], [{country}]
- ETA / Schedule     : [{eta}]
- Equipment / Makers : [{makers_str}]
- Scope of Work      : [{scope}]
- Spares / Parts Req.: [{spares}]
- Class Society      : [Class Society / If Applicable]
- Local Port Agent   : [Full Style Local Agent Details / TBA]
====================================================================

Kindly include the following details in your offer:
1. Service Engineer normal, overtime, and weekend/holiday hourly & daily rates.
2. Estimated travel, launch boat, port gate pass, and accommodation charges.
3. Spare parts unit pricing, ex-stock availability, and delivery lead time (if applicable).
4. Copy of valid OEM Maker Approval Certificate [*] for [{makers_str}].

Please confirm technician availability upon receipt of this inquiry.

Best regards,
[Coordinator Name / Signature]
Onetech Global Technical Service Desk"""


def generate_copilot_reply(user_query, parsed_data, primary_df, neighbor_df, raw_inquiry_text, selected_engine):
    d = parsed_data or RESULT_DEFAULTS
    prim_records = primary_df.head(12).to_dict(orient="records") if primary_df is not None and not primary_df.empty else []
    neigh_records = neighbor_df.head(8).to_dict(orient="records") if neighbor_df is not None and not neighbor_df.empty else []

    sys_context = f"""You are the Onetech Maritime AI Technical Copilot embedded inside the Onetech Service Router dashboard.
Assist maritime coordinators with RFQ analysis, station routing, One-Stop-Shop multi-maker coverage, OEM maker-approval verification ('*' = strict Maker Approval), and vendor emails.

CURRENT PARSED BRIEF:
- Vessel: {d.get('vessel_name')} | Port: {d.get('port')}, {d.get('country')} | ETA: {d.get('eta')}
- Makers: {', '.join(d.get('makers') or []) or 'None'} | Scope: {d.get('scope')} | Spares: {d.get('spares_requested')}
- Discrepancies: {'; '.join(d.get('discrepancies') or []) or 'None'}
- Missing Data: {'; '.join(d.get('missing_critical_data') or []) or 'None'}
- Matched Primary Stations: {json.dumps(prim_records, ensure_ascii=False)}
- Regional Backup Stations: {json.dumps(neigh_records, ensure_ascii=False)}
- Raw Inquiry Excerpt: {(raw_inquiry_text or '')[:3000]}"""

    if selected_engine.startswith("Gemini ::") and gemini_api_key:
        pref = selected_engine.split("::", 1)[1].strip()
        for m in ([pref] + [x for x in GEMINI_MODELS if x != pref]):
            if HAS_GOOGLE_GENAI:
                try:
                    client = genai.Client(api_key=gemini_api_key)
                    resp = client.models.generate_content(model=m, contents=f"{sys_context}\n\nUSER QUESTION:\n{user_query}")
                    if getattr(resp, "text", ""):
                        return resp.text
                except Exception:
                    pass
            if HAS_LEGACY_GENAI:
                try:
                    legacy_genai.configure(api_key=gemini_api_key)
                    resp = legacy_genai.GenerativeModel(m).generate_content(f"{sys_context}\n\nUSER QUESTION:\n{user_query}")
                    if getattr(resp, "text", ""):
                        return resp.text
                except Exception:
                    pass

    if client_groq:
        active_groq = get_active_groq_models()
        pref = selected_engine.split("::", 1)[1].strip() if selected_engine.startswith("Groq ::") else active_groq[0]
        for m in ([pref] + [x for x in active_groq if x != pref]):
            try:
                resp = client_groq.chat.completions.create(
                    model=m,
                    messages=[{"role": "system", "content": sys_context}, {"role": "user", "content": user_query}],
                    temperature=0.2,
                    max_tokens=1024,
                )
                return resp.choices[0].message.content
            except Exception:
                continue

    if gemini_api_key and HAS_GOOGLE_GENAI:
        for m in GEMINI_MODELS:
            try:
                client = genai.Client(api_key=gemini_api_key)
                resp = client.models.generate_content(model=m, contents=f"{sys_context}\n\nUSER QUESTION:\n{user_query}")
                if getattr(resp, "text", ""):
                    return resp.text
            except Exception:
                pass

    prim_names = [r.get("Service Station Name", "") for r in prim_records[:5]]
    return (
        f"**Copilot Summary (Local Intelligence Mode):**\n\n"
        f"- **Vessel & Port:** M/V `{d.get('vessel_name')}` @ **{d.get('port')}, {d.get('country')}** (ETA: `{d.get('eta')}`)\n"
        f"- **Target Makers:** `{', '.join(d.get('makers') or []) or 'Not specified'}`\n"
        f"- **Matched Stations ({len(prim_records)}):** {', '.join(prim_names) if prim_names else 'None matched with current filter.'}"
    )


# ---------------------------------------------------------------------------
# SESSION STATE & CLEAN TWO-WAY SYNC CALLBACKS
# ---------------------------------------------------------------------------
def _apply_parsed_data(parsed_dict):
    d = dict(RESULT_DEFAULTS)
    if isinstance(parsed_dict, dict):
        d.update(parsed_dict)
    st.session_state.parsed_data = d
    st.session_state.eb_vessel = d.get("vessel_name") or "Not specified"
    st.session_state.eb_port = d.get("port") or "Not specified"
    st.session_state.eb_country = d.get("country") or "Not specified"
    st.session_state.eb_eta = d.get("eta") or "Not specified"
    st.session_state.eb_makers = ", ".join(d.get("makers") or [])
    st.session_state.eb_scope = d.get("scope") or "Standard technical attendance inquiry."
    st.session_state.eb_spares = d.get("spares_requested") or "Inquired per inquiry"


def _sync_brief_from_widgets():
    v_val = str(st.session_state.get("eb_vessel", "")).strip() or "Not specified"
    p_val = str(st.session_state.get("eb_port", "")).strip() or "Not specified"
    c_raw = str(st.session_state.get("eb_country", "")).strip()
    c_val = (find_country(c_raw) or c_raw.upper()) if c_raw and c_raw.lower() != "not specified" else "Not specified"
    e_val = str(st.session_state.get("eb_eta", "")).strip() or "Not specified"
    m_raw = str(st.session_state.get("eb_makers", ""))
    m_list = [m.strip().upper() for m in re.split(r"[,;/|]", m_raw) if m.strip()]
    sc_val = str(st.session_state.get("eb_scope", "")).strip() or "Standard technical attendance inquiry."
    sp_val = str(st.session_state.get("eb_spares", "")).strip() or "Inquired per inquiry"

    st.session_state.parsed_data.update({
        "vessel_name": v_val,
        "port": p_val,
        "country": c_val,
        "eta": e_val,
        "makers": m_list,
        "scope": sc_val,
        "spares_requested": sp_val,
    })


def _on_port_widget_change():
    p_val = str(st.session_state.get("eb_port", "")).strip()
    if p_val and p_val.lower() != "not specified":
        matched_p = ports_in_text(p_val)
        if matched_p:
            st.session_state.eb_port = matched_p[0][2].title()
            st.session_state.eb_country = matched_p[0][3]
    _sync_brief_from_widgets()


if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0
if "parsed_data" not in st.session_state:
    _apply_parsed_data(RESULT_DEFAULTS)
if "eb_vessel" not in st.session_state:
    _apply_parsed_data(st.session_state.parsed_data)
if "raw_inquiry_text" not in st.session_state:
    st.session_state.raw_inquiry_text = ""
if "extraction_notes" not in st.session_state:
    st.session_state.extraction_notes = []
if "vision_preview_images" not in st.session_state:
    st.session_state.vision_preview_images = []
if "last_used_engine" not in st.session_state:
    st.session_state.last_used_engine = "Ready"

# Tier 1 toggle: Maker Listed without * (capable, not OEM approved)
if "include_maker_unstarred" not in st.session_state:
    st.session_state.include_maker_unstarred = False
for _k in ("chk_unstarred_sidebar", "chk_unstarred_step1", "chk_unstarred_main"):
    if _k not in st.session_state:
        st.session_state[_k] = st.session_state.include_maker_unstarred

# Tier 2 toggle: Other Stations in country (different makers)
if "include_other_stations" not in st.session_state:
    st.session_state.include_other_stations = False
for _k in ("chk_other_sidebar", "chk_other_step1", "chk_other_main"):
    if _k not in st.session_state:
        st.session_state[_k] = st.session_state.include_other_stations

# Multi-maker One-Stop-Shop filter
if "one_stop_only" not in st.session_state:
    st.session_state.one_stop_only = False

if "show_copilot" not in st.session_state:
    st.session_state.show_copilot = True
if "copilot_messages" not in st.session_state:
    st.session_state.copilot_messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to **Onetech AI Copilot** ⚓\n\n"
                "Upload an RFQ email, PDF, Excel, Word, ZIP, or photo on the left. "
                "I can audit discrepancies, verify `*` Maker Approvals, or draft vendor follow-ups."
            ),
        }
    ]


def _sync_unstarred(source_key):
    val = bool(st.session_state[source_key])
    st.session_state.include_maker_unstarred = val
    st.session_state.chk_unstarred_sidebar = val
    st.session_state.chk_unstarred_step1 = val
    st.session_state.chk_unstarred_main = val


def _sync_other(source_key):
    val = bool(st.session_state[source_key])
    st.session_state.include_other_stations = val
    st.session_state.chk_other_sidebar = val
    st.session_state.chk_other_step1 = val
    st.session_state.chk_other_main = val


def _toggle_copilot():
    st.session_state.show_copilot = not st.session_state.show_copilot


def _close_copilot():
    st.session_state.show_copilot = False


def _reset_all_fields():
    st.session_state.reset_count += 1
    _apply_parsed_data(RESULT_DEFAULTS)
    st.session_state.raw_inquiry_text = ""
    st.session_state.extraction_notes = []
    st.session_state.vision_preview_images = []
    st.session_state.last_used_engine = "Ready"
    st.session_state.include_maker_unstarred = False
    st.session_state.chk_unstarred_sidebar = False
    st.session_state.chk_unstarred_step1 = False
    st.session_state.chk_unstarred_main = False
    st.session_state.include_other_stations = False
    st.session_state.chk_other_sidebar = False
    st.session_state.chk_other_step1 = False
    st.session_state.chk_other_main = False
    st.session_state.one_stop_only = False


rc = st.session_state.reset_count

df_directory, directory_source = load_directory()
total_stations_count = len(df_directory) if df_directory is not None else 0
unique_countries_count = df_directory["Country"].nunique() if df_directory is not None and "Country" in df_directory.columns else 0


# ---------------------------------------------------------------------------
# SIDEBAR: CONTROL CENTER
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.65rem;margin-bottom:0.4rem;">
        <div style="width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,#0284c7,#2563eb);display:flex;align-items:center;justify-content:center;color:white;font-size:1.15rem;font-weight:700;">⚓</div>
        <div>
            <div style="font-weight:800;font-size:1rem;color:#0f172a;line-height:1.15;">ONETECH ROUTER</div>
            <div style="font-size:0.72rem;color:#64748b;font-weight:500;">Enterprise Maritime Dispatch</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown("##### 🤖 AI Intelligence Engine")
    active_groq_list = get_active_groq_models()
    engine_options = (
        ["Auto (Best Available)"]
        + [f"Gemini :: {m}" for m in GEMINI_MODELS]
        + [f"Groq :: {m}" for m in active_groq_list]
        + ["Local Deterministic Only"]
    )
    selected_engine = st.selectbox("Active Parser & Copilot Model", options=engine_options, index=0)
    st.caption(f"{'🟢 Gemini API' if gemini_api_key else '⚪ Gemini Key Missing'}  •  {'🟢 Groq API' if groq_api_key else '⚪ Groq Key Missing'}")
    st.divider()

    st.markdown("##### 📡 Global Station Directory")
    st.markdown(f"""
    <div class="ot-sidebar-card">
        <div style="font-weight:700;color:#0f172a;margin-bottom:0.2rem;">🟢 {html.escape(directory_source)}</div>
        <div style="color:#475569;"><strong>{total_stations_count}</strong> Verified Stations across <strong>{unique_countries_count}</strong> Countries</div>
    </div>
    """, unsafe_allow_html=True)

    st.checkbox(
        "🟡 Include Maker Listed (No *)",
        key="chk_unstarred_sidebar",
        on_change=_sync_unstarred,
        args=("chk_unstarred_sidebar",),
        help="Show stations that list the target maker without an asterisk (*) / red OEM approval.",
    )
    st.checkbox(
        "🔧 Include Other Non-Approved Stations",
        key="chk_other_sidebar",
        on_change=_sync_other,
        args=("chk_other_sidebar",),
        help="Show all remaining stations in the target country even if they don't list the target maker.",
    )

    sb_c1, sb_c2 = st.columns(2)
    with sb_c1:
        if st.button("🔄 Sync Sheet", use_container_width=True):
            load_directory.clear()
            st.rerun()
    with sb_c2:
        st.button("🗑️ Reset All", on_click=_reset_all_fields, use_container_width=True)

    with st.expander("🔎 Browse Full Station Directory", expanded=False):
        q_search = st.text_input("Search Country / Station / Maker", placeholder="e.g. Furuno, Dubai, China...")
        if df_directory is not None and not df_directory.empty:
            view_dir = df_directory
            if q_search.strip():
                mask = view_dir.astype(str).apply(lambda col: col.str.contains(q_search.strip(), case=False, na=False)).any(axis=1)
                view_dir = view_dir[mask]
            st.dataframe(view_dir, use_container_width=True, hide_index=True, height=240)


# ---------------------------------------------------------------------------
# FLOATING COPILOT TOGGLE BUTTON & HERO HEADER
# ---------------------------------------------------------------------------
st.button(
    "✖ Hide AI Copilot" if st.session_state.show_copilot else "💬 Open AI Copilot",
    key="floating_copilot_btn",
    on_click=_toggle_copilot,
)

st.markdown(f"""
<div class="ot-hero-bar">
    <div class="ot-hero-left">
        <div class="ot-brand-logo">⚓</div>
        <div>
            <h1 class="ot-hero-title">Onetech Service Router &amp; AI Technical Copilot</h1>
            <p class="ot-hero-subtitle">Automated RFQ Telemetry Extraction • Multi-Maker One-Stop-Shop Ranking • Global Port Dispatch</p>
        </div>
    </div>
    <div class="ot-hero-badges">
        <span class="ot-pill ot-pill-live"><span class="ot-dot-live"></span> {html.escape(directory_source)}</span>
        <span class="ot-pill">🏢 {total_stations_count} Stations</span>
        <span class="ot-pill">⚡ Engine: {html.escape(st.session_state.last_used_engine)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.show_copilot:
    col_main, col_copilot = st.columns([2.25, 1.0], gap="large")
else:
    col_main = st.container()
    col_copilot = None


# ---------------------------------------------------------------------------
# MAIN WORKSPACE
# ---------------------------------------------------------------------------
with col_main:
    # STEP 01: INQUIRY INGESTION & OVERRIDE
    with st.container(border=True):
        st.markdown("""
        <div class="ot-section-header">
            <div class="ot-section-title-wrap">
                <span class="ot-step-badge">STEP 01</span>
                <h3 class="clean-header">Inquiry Ingestion &amp; Ground-Truth Override</h3>
            </div>
            <span class="ot-section-caption">Reads ALL Attachments: MSG/EML, PDF (Text &amp; Scanned), Excel, Word, ZIP &amp; Images</span>
        </div>
        """, unsafe_allow_html=True)

        ing_col1, ing_col2 = st.columns([1.15, 1.0], gap="medium")
        with ing_col1:
            uploaded_files = st.file_uploader(
                "Upload Client RFQ Emails, PDFs, Excel/Word/ZIP Files, or Equipment Images",
                type=[
                    "pdf", "eml", "msg", "txt", "xlsx", "xls", "csv",
                    "docx", "zip", "html", "htm", "png", "jpg", "jpeg", "webp", "tif", "tiff"
                ],
                accept_multiple_files=True,
                key=f"rfq_file_uploader_{rc}",
            )
            pasted_inquiry = st.text_area(
                "Or Paste Raw Email Thread / Inquiry Text",
                height=110,
                placeholder="Paste raw email thread here (top-most message is treated as latest chronological instruction)...",
                key=f"pasted_inquiry_box_{rc}",
            )
        with ing_col2:
            manual_override_input = st.text_area(
                "Manual Ground-Truth Override (Highest Priority)",
                height=192,
                placeholder="Optional: Force specific values (overrides AI & email text):\nVessel: MV Seaduty\nPort: Taicang\nCountry: China\nETA: 22-24 Nov 2026\nMaker: Furuno, JRC",
                key=f"manual_override_box_{rc}",
            )

        chk_s1_a, chk_s1_b = st.columns(2)
        with chk_s1_a:
            st.checkbox(
                "🟡 Include Maker Listed without * (Capable, Non-Approved)",
                key="chk_unstarred_step1",
                on_change=_sync_unstarred,
                args=("chk_unstarred_step1",),
                help="Show stations that list the target maker without an asterisk (*) / red OEM approval.",
            )
        with chk_s1_b:
            st.checkbox(
                "🔧 Include Other Non-Approved Stations (Different Makers)",
                key="chk_other_step1",
                on_change=_sync_other,
                args=("chk_other_step1",),
                help="Show all remaining stations in the target country even if they don't list the target maker.",
            )

        act_col1, act_col2, act_col3 = st.columns([2.6, 1.0, 0.8])
        with act_col1:
            run_analysis_btn = st.button("⚡ Analyze Inquiry & Route Approved Service Stations", type="primary", use_container_width=True)
        with act_col2:
            load_sample_btn = st.button("🧪 Load Sample RFQ", use_container_width=True)
        with act_col3:
            st.button("🗑️ Reset", on_click=_reset_all_fields, use_container_width=True, help="Clear all text boxes, attachments, and results")

        if load_sample_btn:
            sample_thread = (
                "From: Operations Executive <ops@shipping-corp.com>\n"
                "Subject: RE: MV SEADUTY - VDR & GMDSS ANNUAL SURVEY + RADAR SPARES\n\n"
                "Good day Onetech team,\n"
                "Please note vessel schedule updated: final port will be Taicang China instead of Qingdao China.\n"
                "ETA Taicang: 18-20 Nov 2026.\n"
                "Please arrange Maker Approved engineer for JRC VDR JCY-1900 Annual Survey and Furuno Radar FAR-2137 magnetron 03P9335-66 replacement.\n\n"
                "-----Original Message-----\n"
                "Subject: MV SEADUTY - VDR & GMDSS ANNUAL SURVEY @ QINGDAO\n"
                "Please quote VDR annual attendance at Qingdao, China.\n"
                "Vasilikon 51, Piraeus 18545 Greece"
            )
            st.session_state.raw_inquiry_text = sample_thread
            st.session_state.extraction_notes = []
            st.session_state.vision_preview_images = []
            with st.spinner("Analyzing sample maritime RFQ thread..."):
                parsed, eng = analyze_inquiry("", sample_thread, [], selected_engine)
                _apply_parsed_data(parsed)
                st.session_state.last_used_engine = eng
            st.rerun()

        if run_analysis_btn:
            combined_text_parts, labeled_images, all_notes = [], [], []
            if pasted_inquiry and pasted_inquiry.strip():
                combined_text_parts.append(clean_signatures(pasted_inquiry.strip()))
            if uploaded_files:
                for uf in uploaded_files:
                    txt, imgs, notes = extract_content_from_file(uf)
                    if txt:
                        combined_text_parts.append(f"--- FILE: {uf.name} ---\n{txt}")
                    if imgs:
                        labeled_images.extend(imgs)
                    if notes:
                        all_notes.extend(notes)

            labeled_images = labeled_images[:8]
            pil_images = [img for _, img in labeled_images]
            full_cleaned_text = "\n\n".join(combined_text_parts).strip()
            st.session_state.raw_inquiry_text = full_cleaned_text
            st.session_state.extraction_notes = all_notes
            st.session_state.vision_preview_images = labeled_images

            if not full_cleaned_text and not (manual_override_input and manual_override_input.strip()) and not pil_images:
                st.warning("Please upload an inquiry file, paste email text, or provide a Manual Ground-Truth Override.")
            else:
                with st.spinner("AI is reading email, all attachments & images, and routing stations..."):
                    parsed, eng = analyze_inquiry(manual_override_input, full_cleaned_text, pil_images, selected_engine)
                    _apply_parsed_data(parsed)
                    st.session_state.last_used_engine = eng
                st.rerun()

        if st.session_state.extraction_notes:
            st.caption("📎 " + " • ".join(st.session_state.extraction_notes))

        if st.session_state.vision_preview_images:
            with st.expander(f"🖼️ View {len(st.session_state.vision_preview_images)} Extracted Image(s) / Scanned Pages Sent to AI Vision", expanded=False):
                img_cols = st.columns(min(3, len(st.session_state.vision_preview_images)))
                for idx, (lbl, pil_im) in enumerate(st.session_state.vision_preview_images):
                    with img_cols[idx % len(img_cols)]:
                        st.image(pil_im, caption=lbl, use_container_width=True)

        if st.session_state.raw_inquiry_text:
            with st.expander("📄 View Cleaned Inquiry & Attachments Text (Signatures Stripped)", expanded=False):
                st.code(st.session_state.raw_inquiry_text[:10000], language="text")

    # STEP 02: EDITABLE EXECUTIVE BRIEF & KPI TELEMETRY
    cur = st.session_state.parsed_data
    v_disp = cur.get("vessel_name") or "Not specified"
    p_disp = cur.get("port") or "Not specified"
    c_disp = cur.get("country") or "Not specified"
    e_disp = cur.get("eta") or "Not specified"
    m_list = cur.get("makers") or []
    m_disp = ", ".join(m_list) if m_list else "Not specified"

    with st.container(border=True):
        st.markdown("""
        <div class="ot-section-header">
            <div class="ot-section-title-wrap">
                <span class="ot-step-badge">STEP 02</span>
                <h3 class="clean-header">Editable Executive Brief &amp; Telemetry</h3>
            </div>
            <span class="ot-section-caption">Live Two-Way Sync with Station Routing &amp; RFQ Template</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="ot-kpi-grid">
            <div class="ot-kpi-card">
                <div class="ot-kpi-label">🚢 Vessel Name</div>
                <div class="ot-kpi-value" title="{html.escape(v_disp)}">M/V {html.escape(v_disp)}</div>
                <div class="ot-kpi-sub">Cleaned Hull Identifier</div>
            </div>
            <div class="ot-kpi-card" style="border-left-color:#2563eb;">
                <div class="ot-kpi-label">📍 Destination Port</div>
                <div class="ot-kpi-value" title="{html.escape(p_disp)}, {html.escape(c_disp)}">{html.escape(p_disp)}</div>
                <div class="ot-kpi-sub">Country: <strong>{html.escape(c_disp)}</strong></div>
            </div>
            <div class="ot-kpi-card" style="border-left-color:#0d9488;">
                <div class="ot-kpi-label">🗓️ ETA / Schedule</div>
                <div class="ot-kpi-value" title="{html.escape(e_disp)}">{html.escape(e_disp)}</div>
                <div class="ot-kpi-sub">Attendance Window</div>
            </div>
            <div class="ot-kpi-card" style="border-left-color:#7c3aed;">
                <div class="ot-kpi-label">🛠️ Target OEM Makers</div>
                <div class="ot-kpi-value" title="{html.escape(m_disp)}">{html.escape(m_disp)}</div>
                <div class="ot-kpi-sub">{len(m_list)} Brand(s) Detected</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for d_list, cls, title in (
            (cur.get("discrepancies") or [], "ot-alert-warn", "⚠️ Chronology / Thread Discrepancies Detected:"),
            (cur.get("missing_critical_data") or [], "ot-alert-danger", "🚨 Missing Critical Telemetry:"),
        ):
            if d_list:
                items_html = "<br>".join(f"• {html.escape(str(x))}" for x in d_list)
                st.markdown(f'<div class="ot-alert-box {cls}"><strong>{title}</strong><br>{items_html}</div>', unsafe_allow_html=True)

        eb_c1, eb_c2, eb_c3, eb_c4 = st.columns([1.1, 1.0, 1.0, 1.1], gap="small")
        with eb_c1:
            st.text_input("Vessel Name", key="eb_vessel", on_change=_sync_brief_from_widgets)
        with eb_c2:
            st.text_input("Service Port", key="eb_port", on_change=_on_port_widget_change)
        with eb_c3:
            st.text_input("Service Country", key="eb_country", on_change=_sync_brief_from_widgets)
        with eb_c4:
            st.text_input("ETA / Schedule", key="eb_eta", on_change=_sync_brief_from_widgets)

        eb_c5, eb_c6, eb_c7 = st.columns([1.1, 1.2, 1.1], gap="small")
        with eb_c5:
            st.text_input("Target Makers (comma-separated)", key="eb_makers", on_change=_sync_brief_from_widgets)
        with eb_c6:
            st.text_input("Scope of Work", key="eb_scope", on_change=_sync_brief_from_widgets)
        with eb_c7:
            st.text_input("Spares / Parts Requested", key="eb_spares", on_change=_sync_brief_from_widgets)

    # STEP 03: SERVICE STATION ROUTING, 3-TIER FILTER & ONE-STOP-SHOP RANKING
    active_country = st.session_state.parsed_data.get("country", "Not specified")
    active_makers = st.session_state.parsed_data.get("makers", [])
    is_multi_maker = len(active_makers) > 1
    include_unstarred = bool(st.session_state.include_maker_unstarred)
    include_other = bool(st.session_state.include_other_stations)
    one_stop_only = bool(st.session_state.one_stop_only) if is_multi_maker else False

    primary_df, neighbor_df, neighbor_country_list, tier_counts = route_service_stations(
        df_directory,
        active_country,
        active_makers,
        include_maker_unstarred=include_unstarred,
        include_other_stations=include_other,
        one_stop_only=one_stop_only,
    )

    selected_primary_df = pd.DataFrame()
    selected_neighbor_df = neighbor_df.copy()

    filter_sig = f"{rc}_{canonical_country(active_country)}_{'_'.join(active_makers)}_{include_unstarred}_{include_other}_{one_stop_only}"

    with st.container(border=True):
        st.markdown("""
        <div class="ot-section-header">
            <div class="ot-section-title-wrap">
                <span class="ot-step-badge">STEP 03</span>
                <h3 class="clean-header">Service Station Routing &amp; Strict (*) Maker Verification</h3>
            </div>
            <span class="ot-section-caption">🏆 One-Stop-Shop • ✅ Maker Approved (*) • 🟡 Maker Listed (No *) • 🔧 Other Stations</span>
        </div>
        """, unsafe_allow_html=True)

        onestop_badge_html = (
            f'<span class="ot-stat-badge ot-stat-onestop">🏆 {tier_counts["one_stop"]} One-Stop-Shop ({len(active_makers)}/{len(active_makers)} Makers)</span>'
            if is_multi_maker
            else ""
        )

        st.markdown(f"""
        <div class="ot-badge-row">
            {onestop_badge_html}
            <span class="ot-stat-badge ot-stat-approved">✅ {tier_counts['approved']} Maker Approved (*)</span>
            <span class="ot-stat-badge ot-stat-unstarred">🟡 {tier_counts['unstarred']} Maker Listed (No *)</span>
            <span class="ot-stat-badge ot-stat-other">🔧 {tier_counts['other']} Other Stations in Country</span>
            <span class="ot-stat-badge ot-stat-neutral">🌐 {len(neighbor_df)} Regional Backup Stations</span>
        </div>
        """, unsafe_allow_html=True)

        if is_multi_maker:
            rt_c1, rt_c2, rt_c3 = st.columns(3)
        else:
            rt_c1, rt_c2 = st.columns(2)
            rt_c3 = None

        with rt_c1:
            st.checkbox(
                f"🟡 Include Maker Listed without * ({tier_counts['unstarred']} available)",
                key="chk_unstarred_main",
                on_change=_sync_unstarred,
                args=("chk_unstarred_main",),
            )
        with rt_c2:
            st.checkbox(
                f"🔧 Include Other Non-Approved Stations ({tier_counts['other']} available)",
                key="chk_other_main",
                on_change=_sync_other,
                args=("chk_other_main",),
            )
        if rt_c3 is not None:
            with rt_c3:
                st.checkbox(
                    f"🏆 One-Stop-Shop Only ({tier_counts['one_stop']} cover all {len(active_makers)} makers)",
                    key="one_stop_only",
                    help="Show only stations that cover EVERY requested maker in this multi-maker RFQ.",
                )

        if not canonical_country(active_country):
            st.info("Specify a valid **Service Country** or **Service Port** in STEP 01 / STEP 02 to display matching service stations.")
        elif not primary_df.empty:
            primary_for_editor = primary_df.copy()
            primary_for_editor.insert(0, "Select", True)
            disabled_primary_cols = [c for c in primary_for_editor.columns if c != "Select"]

            edited_primary_df = st.data_editor(
                primary_for_editor,
                use_container_width=True,
                hide_index=True,
                disabled=disabled_primary_cols,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Check or uncheck stations to include in Outlook email extraction and RFQ dispatch.",
                        default=True,
                    )
                },
                key=f"primary_stations_editor_{filter_sig}",
            )
            selected_primary_df = edited_primary_df[edited_primary_df["Select"] == True].drop(
                columns=["Select"], errors="ignore"
            ).reset_index(drop=True)
        else:
            st.info(
                f"No direct stations currently displayed for **{active_country}** with makers **{', '.join(active_makers) if active_makers else 'All'}**. "
                f"Try enabling **🟡 Include Maker Listed without *** ({tier_counts['unstarred']}), **🔧 Include Other Non-Approved Stations** ({tier_counts['other']}), "
                f"disabling **One-Stop-Shop Only**, or checking the **Regional / Neighboring Hub Stations** below."
            )

        if not neighbor_df.empty:
            neighbor_label = f"🌍 Regional / Neighboring Hub Stations ({len(neighbor_df)} available in {', '.join(c.upper() for c in neighbor_country_list[:5])})"
            with st.expander(neighbor_label, expanded=primary_df.empty):
                neighbor_for_editor = neighbor_df.copy()
                neighbor_for_editor.insert(0, "Select", True)
                disabled_neighbor_cols = [c for c in neighbor_for_editor.columns if c != "Select"]
                edited_neighbor_df = st.data_editor(
                    neighbor_for_editor,
                    use_container_width=True,
                    hide_index=True,
                    disabled=disabled_neighbor_cols,
                    column_config={
                        "Select": st.column_config.CheckboxColumn(
                            "Select",
                            help="Check or uncheck regional stations to include when extracting regional emails.",
                            default=True,
                        )
                    },
                    key=f"neighbor_stations_editor_{filter_sig}",
                )
                selected_neighbor_df = edited_neighbor_df[edited_neighbor_df["Select"] == True].drop(
                    columns=["Select"], errors="ignore"
                ).reset_index(drop=True)

    # STEP 04: DISPATCH TOOLKIT (OUTLOOK EMAIL EXTRACTOR & BRACKETED RFQ)
    with st.container(border=True):
        st.markdown("""
        <div class="ot-section-header">
            <div class="ot-section-title-wrap">
                <span class="ot-step-badge">STEP 04</span>
                <h3 class="clean-header">Dispatch Toolkit: Outlook Email Extractor &amp; Bracketed [...] RFQ</h3>
            </div>
            <span class="ot-section-caption">Ready-to-Send Vendor Dispatch</span>
        </div>
        """, unsafe_allow_html=True)

        tab_rfq, tab_outlook = st.tabs([
            "📝 Bracketed [...] Outbound RFQ Template",
            "📧 Outlook Email Extractor (To / Bcc)",
        ])

        with tab_rfq:
            rfq_target_df = selected_primary_df if not selected_primary_df.empty else selected_neighbor_df
            rfq_default_text = generate_bracketed_rfq_template(
                st.session_state.parsed_data,
                rfq_target_df,
            )
            rfq_c1, rfq_c2 = st.columns([1.25, 1.0], gap="medium")
            with rfq_c1:
                edited_rfq = st.text_area(
                    "Editable Outbound RFQ Template (Bracketed [...] Placeholders)",
                    value=rfq_default_text,
                    height=330,
                    key=f"rfq_template_box_{filter_sig}_{len(rfq_target_df)}",
                )
            with rfq_c2:
                st.markdown("**📋 One-Click Copy RFQ Block**")
                st.code(edited_rfq, language="text")
                st.download_button(
                    "⬇️ Download RFQ Template (.txt)",
                    data=edited_rfq.encode("utf-8"),
                    file_name=f"RFQ_{re.sub(r'[^A-Za-z0-9]+', '_', v_disp)}_{re.sub(r'[^A-Za-z0-9]+', '_', p_disp)}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

        with tab_outlook:
            default_scope_idx = 1 if (selected_primary_df.empty and not selected_neighbor_df.empty) else 0
            scope_choice = st.radio(
                "Select Station Pool for Email Extraction (Filtered by Checked 'Select' Rows in STEP 03):",
                options=[
                    "Selected Primary Country Stations Only",
                    "Selected Primary + Selected Regional Neighboring Stations",
                ],
                index=default_scope_idx,
                horizontal=True,
            )
            pool_df = (
                selected_primary_df
                if scope_choice == "Selected Primary Country Stations Only"
                else pd.concat([selected_primary_df, selected_neighbor_df], ignore_index=True)
            )
            extracted_emails, station_email_rows = extract_outlook_emails(pool_df)

            st.caption(f"Extracting emails from **{len(pool_df)}** selected station(s) (`Select == True`).")

            if extracted_emails:
                st.markdown("**📋 Outlook `To / Bcc` Semicolon-Separated Address Block**")
                st.code("; ".join(extracted_emails), language="text")
            else:
                st.info("No `@` email addresses were found in the currently selected station rows. Below is the selected station roster:")

            if station_email_rows:
                st.dataframe(pd.DataFrame(station_email_rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# STICKY RIGHT-SIDE AI COPILOT PANEL
# ---------------------------------------------------------------------------
if st.session_state.show_copilot and col_copilot is not None:
    with col_copilot:
        st.markdown('<div class="copilot-panel-marker"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            top_c1, top_c2 = st.columns([3.2, 1.2])
            with top_c1:
                st.markdown("""
                <div class="ot-copilot-header" style="margin-bottom:0.4rem;">
                    <div class="ot-copilot-title">🧭 Onetech AI Copilot</div>
                    <div class="ot-copilot-sub">RFQ &amp; Maker-Approval Assistant</div>
                </div>
                """, unsafe_allow_html=True)
            with top_c2:
                st.button(
                    "✖ Close",
                    on_click=_close_copilot,
                    key="close_copilot_header_btn",
                    help="Close panel without losing chat history",
                    use_container_width=True,
                )

            qp_c1, qp_c2 = st.columns(2)
            quick_prompt = None
            with qp_c1:
                if st.button("🔍 Audit RFQ & Risks", use_container_width=True):
                    quick_prompt = "Audit this RFQ for missing technical particulars, port discrepancies, and survey risks."
                if st.button("⭐ Verify * Approvals", use_container_width=True):
                    quick_prompt = "Which matched stations hold strict '*' Maker Approval or One-Stop-Shop coverage for the requested equipment?"
            with qp_c2:
                if st.button("✉️ Urgent Chaser", use_container_width=True):
                    quick_prompt = "Draft a short, urgent follow-up chaser email with bracketed [...] placeholders to the matched stations."
                if st.button("🧹 Clear Chat", use_container_width=True):
                    st.session_state.copilot_messages = [
                        {"role": "assistant", "content": "Chat history cleared. How can I help you route or audit this attendance?"}
                    ]
                    st.rerun()

            chat_box = st.container(height=390)
            with chat_box:
                for msg in st.session_state.copilot_messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            user_chat_input = st.chat_input("Ask Copilot about stations, makers, or RFQ...")
            active_prompt = quick_prompt or user_chat_input

            if active_prompt:
                st.session_state.copilot_messages.append({"role": "user", "content": active_prompt})
                with chat_box:
                    with st.chat_message("user"):
                        st.markdown(active_prompt)
                    with st.chat_message("assistant"):
                        with st.spinner("Copilot thinking..."):
                            reply_text = generate_copilot_reply(
                                active_prompt,
                                st.session_state.parsed_data,
                                selected_primary_df if not selected_primary_df.empty else primary_df,
                                selected_neighbor_df if not selected_neighbor_df.empty else neighbor_df,
                                st.session_state.raw_inquiry_text,
                                selected_engine,
                            )
                            st.markdown(reply_text)
                st.session_state.copilot_messages.append({"role": "assistant", "content": reply_text})
                st.rerun()
