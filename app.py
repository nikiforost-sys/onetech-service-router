import base64
import email
from email import policy
import hashlib
import html
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
import pandas as pd
from PIL import Image, ImageOps
import streamlit as st

try:
    import extract_msg
    HAS_EXTRACT_MSG = True
except ImportError:
    extract_msg = None
    HAS_EXTRACT_MSG = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    pypdf = None
    HAS_PYPDF = False

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    Groq = None
    HAS_GROQ = False

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

st.set_page_config(
    page_title="Onetech Service Router & Copilot",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------------------------
# CLEAN, CALM, THEME-SAFE UI STYLESHEET
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
    --ot-primary: #0284c7;
    --ot-accent: #2563eb;
    --ot-border: rgba(148, 163, 184, 0.26);
    --ot-text-main: var(--text-color, #0f172a);
    --ot-text-muted: #64748b;
    --ot-card-bg: var(--secondary-background-color, #f8fafc);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.block-container {
    padding-top: 1.15rem !important;
    padding-bottom: 5rem !important;
    max-width: 1380px !important;
}

.ot-topbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.75rem 1.15rem;
    margin-bottom: 0.9rem;
    border-radius: 12px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 65%, #0c4a6e 100%);
    color: #ffffff;
    box-shadow: 0 6px 18px -6px rgba(15, 23, 42, 0.22);
}
.ot-topbar-left { display: flex; align-items: center; gap: 0.75rem; }
.ot-brand-logo {
    width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
    background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
}
.ot-hero-title { font-size: 1.12rem; font-weight: 700; letter-spacing: -0.015em; margin: 0; color: #ffffff; line-height: 1.2; }
.ot-hero-subtitle { font-size: 0.78rem; color: #cbd5e1; margin: 0.1rem 0 0 0; }
.ot-topbar-right { display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem; }
.ot-pill {
    display: inline-flex; align-items: center; gap: 0.35rem;
    padding: 0.26rem 0.65rem; border-radius: 999px; font-size: 0.73rem; font-weight: 600;
    background: rgba(255, 255, 255, 0.1); color: #f8fafc; border: 1px solid rgba(255, 255, 255, 0.16);
}
.ot-pill-live { background: rgba(16, 185, 129, 0.18); color: #6ee7b7; border-color: rgba(16, 185, 129, 0.35); }
.ot-dot-live { width: 7px; height: 7px; border-radius: 50%; background: #10b981; display: inline-block; }

.ot-welcome-title {
    font-size: 1.25rem; font-weight: 700; color: var(--ot-text-main);
    margin: 0 0 0.25rem 0; letter-spacing: -0.02em;
}
.ot-welcome-sub {
    font-size: 0.85rem; color: var(--ot-text-muted); margin: 0 0 0.9rem 0;
}

.ot-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.65rem; margin-bottom: 0.7rem; }
@media (max-width: 1024px) { .ot-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 576px) { .ot-kpi-grid { grid-template-columns: 1fr; } }

.ot-kpi-card {
    background: var(--ot-card-bg);
    border: 1px solid var(--ot-border); border-left: 3px solid var(--ot-primary);
    border-radius: 10px; padding: 0.65rem 0.85rem;
}
.ot-kpi-label { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ot-text-muted); margin-bottom: 0.18rem; }
.ot-kpi-value { font-size: 0.95rem; font-weight: 700; color: var(--ot-text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ot-kpi-value-muted { font-size: 0.88rem; font-weight: 500; font-style: italic; color: var(--ot-text-muted); }
.ot-kpi-sub { font-size: 0.72rem; color: var(--ot-text-muted); margin-top: 0.1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.ot-scope-strip {
    display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; margin-bottom: 0.65rem;
}
@media (max-width: 768px) { .ot-scope-strip { grid-template-columns: 1fr; } }
.ot-scope-item {
    background: var(--ot-card-bg); border: 1px solid var(--ot-border);
    border-radius: 8px; padding: 0.5rem 0.75rem; font-size: 0.8rem; color: var(--ot-text-main);
    line-height: 1.4;
}
.ot-scope-lbl {
    font-size: 0.67rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--ot-text-muted); display: block; margin-bottom: 0.12rem;
}

.ot-alert-box { border-radius: 9px; padding: 0.6rem 0.85rem; margin-bottom: 0.65rem; font-size: 0.81rem; line-height: 1.45; }
.ot-alert-warn { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.35); border-left: 3px solid #f59e0b; color: var(--ot-text-main); }
.ot-alert-danger { background: rgba(239, 68, 68, 0.09); border: 1px solid rgba(239, 68, 68, 0.35); border-left: 3px solid #ef4444; color: var(--ot-text-main); }

.ot-selection-bar {
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.5rem;
    padding: 0.45rem 0.8rem; border-radius: 8px; margin-top: 0.35rem; margin-bottom: 0.45rem;
    background: var(--ot-card-bg); border: 1px solid var(--ot-border);
    font-size: 0.79rem; color: var(--ot-text-main);
}

.ot-maker-chip {
    display: inline-flex; align-items: center; padding: 0.16rem 0.55rem; border-radius: 999px;
    font-size: 0.72rem; font-weight: 600; margin-right: 0.3rem; margin-bottom: 0.2rem;
    background: rgba(124, 58, 237, 0.12); color: #7c3aed; border: 1px solid rgba(124, 58, 237, 0.25);
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    border-color: var(--ot-border) !important;
}

button[kind="primary"] {
    background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
    border: none !important; font-weight: 600 !important; border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2) !important;
}

div.st-key-floating_copilot_btn {
    position: fixed !important;
    bottom: 22px !important;
    right: 22px !important;
    z-index: 999999 !important;
    width: auto !important;
}
div.st-key-floating_copilot_btn button {
    border-radius: 999px !important;
    padding: 0.6rem 1.25rem !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.32) !important;
    border: 1px solid rgba(56, 189, 248, 0.45) !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2):has(.copilot-panel-marker),
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2):has(.copilot-panel-marker) {
    position: sticky !important;
    top: 3.1rem !important;
    align-self: flex-start !important;
    max-height: calc(100vh - 4rem) !important;
    overflow-y: auto !important;
}

.ot-copilot-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    color: #ffffff; padding: 0.7rem 0.9rem; border-radius: 10px; margin-bottom: 0.55rem;
}
.ot-copilot-title { font-size: 0.92rem; font-weight: 700; margin: 0; }
.ot-copilot-sub { font-size: 0.72rem; color: #93c5fd; margin-top: 0.08rem; }
.ot-sidebar-card {
    background: var(--ot-card-bg); border: 1px solid var(--ot-border);
    border-radius: 10px; padding: 0.65rem 0.8rem; margin-bottom: 0.65rem;
    font-size: 0.8rem; color: var(--ot-text-main);
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SECRETS & FAST, BOUNDED ACTIVE MODELS (GEMINI + GROQ)
# ---------------------------------------------------------------------------
def _has_secret(key_name):
    try:
        return key_name in st.secrets
    except Exception:
        return False


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

client_groq = Groq(api_key=groq_api_key, timeout=25.0, max_retries=0) if (groq_api_key and HAS_GROQ) else None

GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-4-argon",
]

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

GROQ_VISION_MODELS = {
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
}


@st.cache_data(ttl=600)
def get_active_gemini_models():
    """Auto-discover the top 5 active Gemini models for this API key."""
    discovered = []
    fallback_2x = []
    non_text_skip = (
        "embedding", "aqa", "tts", "imagen", "veo", "lyria",
        "robotics", "computer-use", "live", "audio", "transcribe", "exp", "001"
    )
    if gemini_api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("models") or []:
                methods = m.get("supportedGenerationMethods") or []
                if "generateContent" not in methods:
                    continue
                name = str(m.get("name", "")).replace("models/", "").strip()
                nl = name.lower()
                if not name or "gemini" not in nl:
                    continue
                if any(skip in nl for skip in non_text_skip):
                    continue
                if any(old in nl for old in ("1.5", "1.0")):
                    continue
                if any(v2 in nl for v2 in ("2.5", "2.0")):
                    fallback_2x.append(name)
                    continue
                discovered.append(name)
        except Exception:
            pass

    pool = discovered if discovered else fallback_2x
    if pool:
        ordered = []
        for pref in GEMINI_MODELS:
            if pref in pool and pref not in ordered:
                ordered.append(pref)
        for m in sorted(pool, reverse=True):
            if "flash" in m.lower() and m not in ordered:
                ordered.append(m)
        for m in sorted(pool, reverse=True):
            if "pro" in m.lower() and m not in ordered:
                ordered.append(m)
        for m in sorted(pool, reverse=True):
            if m not in ordered:
                ordered.append(m)
        if ordered:
            return ordered[:5]

    return list(GEMINI_MODELS)


@st.cache_data(ttl=600)
def get_active_groq_models():
    if client_groq:
        try:
            resp = client_groq.models.list()
            live_ids = []
            for m in getattr(resp, "data", []):
                mid = getattr(m, "id", "")
                if mid and not any(x in mid.lower() for x in ("whisper", "tts", "guard", "allam")):
                    live_ids.append(mid)
            if live_ids:
                live_set = set(live_ids)
                ordered = [m for m in GROQ_MODELS if m in live_set]
                for mid in live_ids:
                    if mid not in ordered:
                        ordered.append(mid)
                if ordered:
                    return ordered[:8]
        except Exception:
            pass
    return list(GROQ_MODELS)[:8]


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
        df = df.dropna(subset=["Country", "Service Station Name"]).copy()
        df["Country"] = df["Country"].astype(str).str.strip()
        df["Service Station Name"] = df["Service Station Name"].astype(str).str.strip()
        df = df[
            (df["Country"] != "")
            & (df["Service Station Name"] != "")
            & (df["Country"].str.lower() != "country")
        ]
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
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_text = resp.read().decode("utf-8-sig", errors="replace")
            if raw_text and "<html" not in raw_text[:300].lower() and "<!doctype" not in raw_text[:300].lower():
                df = _clean_df(pd.read_csv(io.StringIO(raw_text), on_bad_lines="skip"))
                if df is not None and not df.empty:
                    return df, "Google Sheets (Live)"
        except Exception:
            continue

    if HAS_GOOGLE_AUTH and _has_secret("gcp_service_account"):
        try:
            sa_info = dict(st.secrets["gcp_service_account"])
            pk = sa_info.get("private_key", "")
            if "\\n" in pk and "\n" not in pk:
                pk = pk.replace("\\n", "\n")
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
# PORTS, COUNTRIES & CANONICAL MAKERS (DEDUPLICATES SPERRY / SPERRY MARINE)
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

MAKER_CANONICAL_MAP = {
    "sperry": "SPERRY MARINE",
    "sperry marine": "SPERRY MARINE",
    "northrop grumman sperry marine": "SPERRY MARINE",
    "northrop grumman": "SPERRY MARINE",
    "ydk": "YOKOGAWA (YDK)",
    "yokogawa": "YOKOGAWA (YDK)",
    "yokogawa (ydk)": "YOKOGAWA (YDK)",
    "yokogawa denshikiki": "YOKOGAWA (YDK)",
    "anschutz": "ANSCHUTZ",
    "anschuetz": "ANSCHUTZ",
    "raytheon": "ANSCHUTZ",
    "raytheon anschutz": "ANSCHUTZ",
    "raytheon anschuetz": "ANSCHUTZ",
    "sailor": "COBHAM SAILOR",
    "cobham": "COBHAM SAILOR",
    "cobham sailor": "COBHAM SAILOR",
    "thrane & thrane": "COBHAM SAILOR",
    "jrc": "JRC",
    "alphatron": "JRC",
    "jrc / alphatron": "JRC",
    "jrc / alphatron marine": "JRC",
    "jrc alphatron": "JRC",
    "japan radio": "JRC",
    "wartsila": "WARTSILA",
    "sam electronics": "WARTSILA",
    "transas": "WARTSILA",
    "kelvin hughes": "KELVIN HUGHES",
    "hensoldt": "KELVIN HUGHES",
    "mcmurdo": "MCMURDO",
    "kannad": "MCMURDO",
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
    (r"(?i)\b(?:cmz\d{3}|pt\d{3}|uz\d{3}|eml\d{3}|mkm\d{3})\b", "YOKOGAWA (YDK)"),
    (r"(?i)\b(?:tg-\d{4}|pr-\d{4}|es-\d{4}|br-\d{4}|ec-\d{4})\b", "TOKYO KEIKI"),
    (r"(?i)\b(?:tr-8000|tron\s*\d{2}|tron\s*sart|tron\s*ais|fb-\d{2})\b", "JOTRON"),
    (r"(?i)\b(?:sailor\s*\d{4}|tt-\d{4}|fleetbroadband\s*\d{3}|sp35\d{2})\b", "COBHAM SAILOR"),
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


def _as_clean_str(val, default=""):
    """Safely convert any LLM output (str, list, dict, None) into a clean string for Streamlit widgets."""
    if val is None:
        return default
    if isinstance(val, str):
        s = val.strip()
        return s if s else default
    if isinstance(val, list):
        parts = []
        for item in val:
            if isinstance(item, dict):
                sub = " ".join(f"{v}" for v in item.values() if v is not None and str(v).strip())
                if sub:
                    parts.append(sub)
            elif item is not None and str(item).strip():
                parts.append(str(item).strip())
        return ", ".join(parts) if parts else default
    if isinstance(val, dict):
        parts = [f"{k}: {v}" for k, v in val.items() if v is not None and str(v).strip()]
        return ", ".join(parts) if parts else default
    s = str(val).strip()
    return s if s else default


def _norm_maker_str(s):
    s = str(s or "").lower()
    return s.replace("ü", "u").replace("ä", "a").replace("ö", "o")


def canonicalize_makers(maker_list):
    """Normalize aliases & deduplicate makers (e.g. 'Sperry' + 'Sperry Marine' -> ['SPERRY MARINE'])."""
    if isinstance(maker_list, str):
        raw_items = [m.strip() for m in re.split(r"[,;/|]", maker_list) if m.strip()]
    elif isinstance(maker_list, list):
        raw_items = [str(m).strip() for m in maker_list if str(m).strip()]
    else:
        return []

    mapped = []
    for item in raw_items:
        clean = item.replace("*", "").strip()
        if not clean or clean.lower() in {"not specified", "n/a", "none", "null", "unknown"}:
            continue
        norm_key = re.sub(r"\s+", " ", _norm_maker_str(clean)).strip()
        canon = MAKER_CANONICAL_MAP.get(norm_key, clean.upper())
        if canon not in mapped:
            mapped.append(canon)

    # Drop shorter substring duplicates (e.g. 'SPERRY' if 'SPERRY MARINE' exists)
    final = []
    for m in sorted(mapped, key=len, reverse=True):
        m_low = m.lower()
        if not any(m_low != o.lower() and re.search(rf"(?<![a-z0-9]){re.escape(m_low)}(?![a-z0-9])", o.lower()) for o in final):
            final.append(m)
    return final


CANONICAL_TO_ALIASES = {}
for _alias_k, _canon_v in MAKER_CANONICAL_MAP.items():
    CANONICAL_TO_ALIASES.setdefault(_canon_v.lower(), set()).add(_alias_k.lower())
    CANONICAL_TO_ALIASES[_canon_v.lower()].add(_canon_v.lower())


def canonical_country(raw_value):
    s = _as_clean_str(raw_value).lower()
    if not s or s in {"not specified", "n/a", "none", "null"}:
        return ""
    if s in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[s].lower()
    s_clean = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
    if s_clean in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[s_clean].lower()
    inferred = find_country(s_clean)
    if inferred:
        return inferred.lower()
    return s


def _maker_matches_token(maker_raw, token_clean):
    m_norm = re.sub(r"\s+", " ", _norm_maker_str(maker_raw).replace("*", "")).strip()
    if not m_norm:
        return False
    m_first = m_norm.split()[0] if m_norm.split() else m_norm
    if re.search(rf"(?<![a-z0-9]){re.escape(m_norm)}(?![a-z0-9])", token_clean):
        return True
    if len(m_first) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(m_first)}(?![a-z0-9])", token_clean):
        return True

    # Also match canonical brand aliases (e.g. 'COBHAM SAILOR' <-> 'Sailor*', 'YOKOGAWA (YDK)' <-> 'YDK*')
    canon_key = MAKER_CANONICAL_MAP.get(m_norm, m_norm.upper()).lower()
    for alias in CANONICAL_TO_ALIASES.get(canon_key, ()):
        if len(alias) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", token_clean):
            return True
    return False


def evaluate_station_coverage(approved_str, target_makers):
    """Evaluate 3-tier approval status + One-Stop-Shop multi-maker coverage."""
    tokens = [t.strip() for t in re.split(r"[,;]", str(approved_str or "")) if t.strip()]
    clean_targets = canonicalize_makers(target_makers)

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


def compute_missing_critical_data(data_dict):
    d = data_dict or {}
    missing = []
    if _as_clean_str(d.get("vessel_name"), "Not specified") in ("Not specified", ""):
        missing.append("Vessel Name is not specified")
    if (
        _as_clean_str(d.get("port"), "Not specified") in ("Not specified", "")
        and _as_clean_str(d.get("country"), "Not specified") in ("Not specified", "")
    ):
        missing.append("Destination Port / Country is missing")
    if _as_clean_str(d.get("eta"), "Not specified") in ("Not specified", ""):
        missing.append("Vessel ETA / Schedule is not specified")
    if not (d.get("makers") or []):
        missing.append("Equipment Maker / OEM Brand is not specified")
    return missing


PORT_KEYS_BY_LENGTH = sorted(PORT_TO_COUNTRY.keys(), key=len, reverse=True)
COUNTRY_KEYS_BY_LENGTH = sorted(COUNTRY_ALIASES.keys(), key=len, reverse=True)


# ---------------------------------------------------------------------------
# UNIVERSAL ATTACHMENT EXTRACTOR (MSG, EML, PDF, EXCEL, DOCX, ZIP, IMAGES)
# ---------------------------------------------------------------------------
def clean_signatures(text):
    if not text:
        return ""
    cleaned = re.sub(r"(?i)\b(?:mobile|mob|cell|tel|telephone|phone|fax)\b\s*[:\.\-]?\s*[\+\d \t\(\)\/\-]{5,}", " ", text)
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


def _prepare_pil_image(img, max_dim=1400):
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    return img


def _pil_to_jpeg_base64(img, max_dim=1200, quality=75):
    buf = io.BytesIO()
    _prepare_pil_image(img, max_dim=max_dim).save(buf, format="JPEG", quality=quality)
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
    text_utf8 = raw_bytes.decode("utf-8", errors="ignore")
    if "<table" in text_utf8.lower() or "<row" in text_utf8.lower() or "<cell" in text_utf8.lower():
        stripped = re.sub(r"<[^>]+>", " ", text_utf8)
        return re.sub(r"\s+", " ", stripped).strip()
    utf16_chunks = re.findall(r"(?:[ -~]\x00){4,}", raw_bytes.decode("latin-1"))
    decoded_u16 = [c.encode("latin-1").decode("utf-16le", errors="ignore").strip() for c in utf16_chunks]
    ascii_chunks = re.findall(r"[A-Za-z0-9_\-\./:,;()@#&+ ]{5,}", raw_bytes.decode("latin-1", errors="ignore"))
    combined = [x for x in (decoded_u16 + ascii_chunks) if x and not x.startswith("Root Entry")]
    return "\n".join(combined)


def _extract_pdf_content(raw_bytes, source_name="document.pdf", max_pages=25, max_vision_pages=6):
    extracted_text_parts = []
    extracted_images = []
    notes = []

    if not HAS_PYPDF:
        notes.append(f"⚠️ pypdf not installed — cannot parse '{source_name}'")
        return "", [], notes

    reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            notes.append(f"⚠️ Encrypted PDF '{source_name}' could not be decrypted")
            return "", [], notes

    pdf_doc = None
    try:
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
                        if pdf_doc is None:
                            import pypdfium2 as pdfium
                            pdf_doc = pdfium.PdfDocument(raw_bytes)
                        pil_page = pdf_doc[page_idx].render(scale=2.0).to_pil()
                        extracted_images.append((f"{source_name} (p.{page_idx + 1})", _prepare_pil_image(pil_page)))
                    except Exception:
                        pass
    finally:
        if pdf_doc is not None:
            try:
                pdf_doc.close()
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


def _extract_msg_obj_content(msg_obj, source_label, _depth=0):
    """Extract subject, body/htmlBody, and attachments from an extract_msg Message object."""
    text_out = ""
    imgs_out = []
    notes_out = []

    body_txt = getattr(msg_obj, "body", None) or ""
    if not body_txt.strip() and getattr(msg_obj, "htmlBody", None):
        raw_html = msg_obj.htmlBody
        if isinstance(raw_html, bytes):
            raw_html = raw_html.decode("utf-8", errors="ignore")
        body_txt = _strip_html_to_text(raw_html)
    subj_txt = getattr(msg_obj, "subject", None) or ""
    text_out += f"\nSubject: {subj_txt}\nBody:\n{body_txt}\n"

    if _depth >= 4:
        return text_out, imgs_out, notes_out

    for idx, att in enumerate(getattr(msg_obj, "attachments", []) or [], 1):
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
            nested_label = att_name or getattr(att_data, "subject", "") or f"nested_email_{idx}"
            n_txt, n_imgs, n_notes = _extract_msg_obj_content(att_data, nested_label, _depth + 1)
            text_out += f"\n--- EMBEDDED EMAIL: {nested_label} ---\n{n_txt}\n"
            imgs_out.extend(n_imgs)
            notes_out.extend(n_notes)
            notes_out.append(f"Nested email '{nested_label}' parsed")
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
                text_out += f"\n--- EMBEDDED ATTACHMENT: {att_name} ---\n{att_txt}\n"
            imgs_out.extend(att_imgs)
            notes_out.extend(att_notes)
            if not att_notes and (att_txt or att_imgs):
                notes_out.append(f"Attachment '{att_name}' parsed from MSG")

    return text_out, imgs_out, notes_out


def extract_content_from_bytes(raw_bytes, file_name, _depth=0):
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
            if not HAS_EXTRACT_MSG:
                notes.append(f"⚠️ extract-msg not installed — cannot parse '{orig_name}'")
            else:
                msg = extract_msg.Message(io.BytesIO(raw_bytes))
                try:
                    m_txt, m_imgs, m_notes = _extract_msg_obj_content(msg, orig_name, _depth=_depth)
                    extracted_text += m_txt
                    extracted_images.extend(m_imgs)
                    notes.extend(m_notes)
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
    if _depth == 0 and not cleaned.strip() and not extracted_images and not notes:
        notes.append(f"⚠️ No readable text or images found in '{orig_name}'")
    return cleaned, extracted_images[:6], notes


def extract_content_from_file(uploaded_file):
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    return extract_content_from_bytes(raw_bytes, uploaded_file.name, _depth=0)


def extract_text_from_file(uploaded_file):
    txt, _, _ = extract_content_from_file(uploaded_file)
    return txt


def clean_vessel_name(raw_name):
    raw_str = _as_clean_str(raw_name)
    if not raw_str or raw_str.lower() in {"not specified", "n/a", "none", "unknown", "null"}:
        return "Not specified"
    text = raw_str.strip('"').strip("'")
    text = re.sub(r"(?i)^(?:m/v|m/t|mv|mt|vessel|ship)\s*[:\-]?\s*", "", text)
    text = re.sub(r"(?i)\s*[\-–—]\s*(?:vdr|gmdss|annual|survey|radio|navtex|inspection|repair|radar|attendance|service|class|coc|imo|\/\/|@).*$", "", text)
    text = re.sub(r"(?i)\b(?:vdr|gmdss|annual|survey|radio|navtex|inspection|repair|attendance|service|coc|imo)\b.*$", "", text)
    text = re.sub(r"(?i)(?<!^)\b(?:will|eta|calling|arriving|sailing|during|while|due\s+to|at\s+port|in\s+port)\b.*$", "", text)
    text = re.sub(r"(?i)(?<!^)\s+(?:at|in|on|for|to|is)\s+(?:port|eta|call|calling|arr|arriving|taicang|qingdao|shanghai|dubai|singapore|malta|piraeus|rotterdam)\b.*$", "", text)
    text = re.sub(r"//.*$", "", text)
    text = re.sub(r"[@\(\)\<\>\[\]].*$", "", text)
    text = re.sub(r"(?i)\btbn\b", " / ", text)
    text = re.sub(r"\s+", " ", text).strip(" /-–—")

    parts = [p.strip(" /-–—") for p in text.split("/") if p.strip(" /-–—")][:2]
    cleaned_parts = []
    for p in parts:
        p_clean = re.sub(r"(?i)^(?:m/v|m/t|mv|mt)\s+", "", p).strip()
        words = p_clean.split()[:4]
        if words:
            cleaned_parts.append(" ".join(words))
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


def _find_thread_split_pos(text):
    """Find where an older quoted reply begins, ignoring leading From:/Sent: headers at top of email."""
    if not text:
        return 0
    explicit_sep = re.search(r"(?im)(?:^|\n)\s*(?:-----+\s*original message\s*-----+|_{5,}|on\s+[^\n]{5,120}\s+wrote\s*:)", text)
    if explicit_sep and explicit_sep.start() > 10:
        return explicit_sep.start()

    # Skip top email header block before looking for quoted From:/Sent:
    body_start = 0
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if not s or re.match(r"(?i)^(?:from|to|cc|bcc|sent|date|subject)\s*:", s):
            body_start += len(line)
        else:
            break
    search_offset = max(body_start + 20, 80)
    if search_offset < len(text):
        reply_hdr = re.search(r"(?im)(?:^|\n)\s*(?:from\s*:|sent\s*:)", text[search_offset:])
        if reply_hdr:
            return search_offset + reply_hdr.start()
    return len(text)


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

    first_reply_pos = _find_thread_split_pos(text)

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


def find_part_number_makers(text_lower):
    found = []
    raw = text_lower or ""
    for pattern, inferred_maker in PART_NUMBER_TO_MAKER:
        if re.search(pattern, raw):
            found.append(inferred_maker)
    return canonicalize_makers(found)


def find_makers(text_lower, vessel_name=""):
    found = []
    vessel_lower = (vessel_name or "").lower()
    raw = text_lower or ""
    for maker in KNOWN_MAKERS:
        if re.search(rf"(?<![a-z0-9]){re.escape(maker)}(?![a-z0-9])", raw) and maker not in vessel_lower:
            found.append(maker.upper())

    found.extend(find_part_number_makers(raw))
    return canonicalize_makers(found)


def parse_manual_inputs(manual_text):
    overrides, explicit = {}, set()
    if not manual_text or not str(manual_text).strip():
        return overrides, explicit
    text = str(manual_text)

    maker_match = re.search(r"(?im)(?:^|\n)\s*(?:makers?|equipment|brand)\s*[:=\s]\s*([^\n]+)", text)
    if maker_match:
        overrides["makers"] = canonicalize_makers(maker_match.group(1))
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

    result["eta"] = _as_clean_str(result.get("eta"), "Not specified")
    result["scope"] = _as_clean_str(result.get("scope"), "Standard technical attendance inquiry.")
    result["spares_requested"] = _as_clean_str(result.get("spares_requested"), "Inquired per inquiry")
    result["makers"] = canonicalize_makers(result.get("makers"))

    result["vessel_name"] = clean_vessel_name(result.get("vessel_name"))
    raw_country = _as_clean_str(result.get("country"))
    if raw_country and raw_country.lower() not in {"not specified", "n/a", "none", "null", "unknown"}:
        c = find_country(raw_country)
        result["country"] = c if c else raw_country.upper()
    else:
        result["country"] = "Not specified"

    port_str = _as_clean_str(result.get("port"))
    if port_str and port_str.lower() not in {"not specified", "n/a", "none", "null", "unknown"}:
        matched_ports = ports_in_text(port_str)
        if matched_ports:
            result["port"] = matched_ports[0][2].title()
            if result.get("country") in ("Not specified", ""):
                result["country"] = matched_ports[0][3]
        else:
            result["port"] = port_str
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
# HYBRID FAST VISION OCR (GEMINI REST / GROQ VISION) + FAST JSON PARSER
# ---------------------------------------------------------------------------
def _gemini_rest_generate(model_name, prompt, pil_images=None, timeout=35):
    """Direct Gemini REST API call (no deprecated temperature param for Gemini 3.5+/4)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_api_key}"
    parts = [{"text": prompt}]
    for img in (pil_images or [])[:4]:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": _pil_to_jpeg_base64(img, max_dim=1300, quality=78),
            }
        })
    payload = {
        "contents": [{"parts": parts}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Empty Gemini candidates: {str(data)[:160]}")
    res_parts = (candidates[0].get("content") or {}).get("parts") or []
    text_out = "\n".join(p.get("text", "") for p in res_parts if p.get("text"))
    if not text_out.strip():
        raise RuntimeError("Empty Gemini text output")
    return text_out.strip()


def _gemini_raw_text(prompt, pil_images=None, preferred_model=None, error_log=None):
    """Try up to 4 active Gemini 3.5+/4 models via direct REST API (fast & reliable)."""
    if not gemini_api_key:
        if error_log is not None:
            error_log.append("Gemini: GEMINI_API_KEY missing")
        return None, None

    active_gem = get_active_gemini_models()
    candidates = ([preferred_model] if preferred_model and preferred_model in active_gem else []) + [
        m for m in active_gem if m != preferred_model
    ]

    for model_name in candidates[:4]:
        try:
            txt = _gemini_rest_generate(model_name, prompt, pil_images=pil_images, timeout=35)
            if txt:
                return txt, f"Gemini ({model_name})"
        except urllib.error.HTTPError as he:
            err_body = ""
            try:
                err_body = he.read().decode("utf-8", errors="ignore")[:180]
            except Exception:
                pass
            if error_log is not None:
                error_log.append(f"Gemini {model_name}: HTTP {he.code} {err_body}")
            if he.code in (401, 403):
                break
        except Exception as exc:
            if error_log is not None:
                error_log.append(f"Gemini {model_name}: {str(exc)[:140]}")

    return None, None


def _groq_vision_ocr(prompt, pil_images, preferred_model=None, error_log=None):
    """Fallback Vision OCR via Groq Llama-4 Vision (max 2 models)."""
    if not client_groq or not pil_images:
        return None, None

    active = get_active_groq_models()
    vision_models = [m for m in active if m in GROQ_VISION_MODELS or "llama-4" in m.lower() or "vision" in m.lower()]
    if preferred_model and preferred_model in vision_models:
        vision_models = [preferred_model] + [m for m in vision_models if m != preferred_model]

    for model_name in vision_models[:2]:
        try:
            user_content = [{"type": "text", "text": prompt}]
            for img in list(pil_images)[:4]:
                b64_img = _pil_to_jpeg_base64(img, max_dim=1100, quality=72)
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                })
            resp = client_groq.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": user_content}],
                temperature=0.1,
                max_tokens=1400,
            )
            txt = (resp.choices[0].message.content or "").strip()
            if txt:
                return txt, f"Groq Vision ({model_name})"
        except Exception as exc:
            if error_log is not None:
                error_log.append(f"Groq Vision {model_name}: {str(exc)[:140]}")
            continue
    return None, None


def run_fast_vision_ocr(pil_images, selected_engine):
    """
    Focused, fast Vision OCR pass (1 call -> ~5-10s):
    Reads equipment maker, model, serial numbers, and spare part numbers from
    scanned PDFs / JPEGs so BOTH the fast JSON parser AND local regex see them.
    """
    if not pil_images:
        return "", None, []

    ocr_prompt = """Read the attached maritime technical document / photo(s) and list ONLY these facts in short bullet points:
- Vessel Name & IMO
- Equipment Type, OEM Maker, and Exact Model (IMPORTANT: On Service Reports, IGNORE the service station's letterhead / 'Authorised Dealership' brand list — report ONLY the vessel's actual 'Equipment type and model'!)
- Findings / Follow-up Needed
- Recommended or Requested Spare Parts with exact OEM Part Numbers and Quantities."""

    errors = []
    if selected_engine.startswith("Groq ::"):
        pref = selected_engine.split("::", 1)[1].strip()
        txt, eng = _groq_vision_ocr(ocr_prompt, pil_images, preferred_model=pref, error_log=errors)
        if txt:
            return txt, eng, errors
        txt, eng = _gemini_raw_text(ocr_prompt, pil_images=pil_images, error_log=errors)
        return (txt or ""), eng, errors

    pref_gem = selected_engine.split("::", 1)[1].strip() if selected_engine.startswith("Gemini ::") else None
    txt, eng = _gemini_raw_text(ocr_prompt, pil_images=pil_images, preferred_model=pref_gem, error_log=errors)
    if txt:
        return txt, eng, errors

    txt, eng = _groq_vision_ocr(ocr_prompt, pil_images, error_log=errors)
    return (txt or ""), eng, errors


def smart_local_parser(manual_override_text, files_text):
    blob = files_text or ""
    port, country, _ = choose_primary_port(blob)

    if country == "Not specified":
        split_pos = _find_thread_split_pos(blob)
        first_msg = blob[:split_pos] if split_pos > 0 else blob
        found_c = find_country(first_msg)
        if found_c and found_c != "GREECE":
            country = found_c

    vessel_name = "Not specified"
    vessel_patterns = (
        r"(?i)\b(?:m/v|m/t|mv|mt)\b(?:\s*[:\-]\s*|\s+)([A-Za-z0-9][^\n]{1,80})",
        r"(?i)\b(?:vessel(?:\s+name)?|ship(?:\s+name)?|πλο[ιί]ο)\b\s*[:\-]\s*([A-Za-z0-9][^\n]{1,80})",
    )
    for vp in vessel_patterns:
        vm = re.search(vp, blob)
        if vm:
            cand = clean_vessel_name(vm.group(1))
            if cand != "Not specified":
                vessel_name = cand
                break

    eta = "Not specified"
    eta_match = re.search(
        r"(?i)\b(?:eta|etd|arrival|on\s+about|about)\b(?:\s+[A-Za-z]{2,25})?\s*[:=]?\s*"
        r"([0-9]{1,2}(?:[-/][0-9]{1,2})?(?:[-/.][0-9]{1,2}[-/.][0-9]{2,4}|\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*(?:\s+\d{2,4})?)[^\n,\.;]*)",
        blob,
    )
    if eta_match:
        eta = eta_match.group(1).strip(" .")
    else:
        eta_loose = re.search(r"(?i)\b(?:eta|etd|arrival)\b\s*[:=]?\s*([^\n]{3,60})", blob)
        if eta_loose:
            eta = eta_loose.group(1).strip(" .")

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
    rev_match = re.search(
        r"(?i)\b([A-Za-z][A-Za-z ,]{2,35}?)\s+instead\s+of\s+([A-Za-z][A-Za-z ,]{2,35}?)(?:[\.\n;]|$)",
        blob,
    )
    if rev_match:
        new_loc_raw = rev_match.group(1).strip(" ,")
        old_loc_raw = rev_match.group(2).strip(" ,")
        new_ports = ports_in_text(new_loc_raw)
        old_ports = ports_in_text(old_loc_raw)
        if new_ports and old_ports:
            np_lbl = f"{new_ports[-1][2].title()}, {new_ports[-1][3]}"
            op_lbl = f"{old_ports[0][2].title()}, {old_ports[0][3]}"
            discrepancies.append(f"Port revised: Final destination changed to {np_lbl} instead of {op_lbl}.")
        elif old_ports:
            op_lbl = f"{old_ports[0][2].title()}, {old_ports[0][3]}"
            new_lbl = f"{port}, {country}" if port != "Not specified" else new_loc_raw.title()
            discrepancies.append(f"Port revised: Final destination changed to {new_lbl} instead of {op_lbl}.")

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


def build_prompt(manual_override_text, cleaned_files):
    inquiry = (cleaned_files or "")[:24000]
    return f"""You are an expert maritime technical coordinator. Parse the commercial RFQ, ALL extracted attachments, and any AI VISION OCR section into structured JSON.

CRITICAL INSTRUCTIONS:
1. MANUAL OVERRIDE IS ABSOLUTE GROUND TRUTH.
2. EMAIL THREAD CHRONOLOGY: The email at the VERY TOP is the active instruction. If it updates the port (e.g. 'Taicang China instead of Qingdao China' or 'Malta instead of Genova'), use the NEW port and list the old port in discrepancies. A prior Service Report attached to the email may show an older port (e.g. Weihai, China); always use the NEW requested attendance port from the email body.
3. VESSEL NAME: Strip 'MV', 'M/V', 'MT', 'M/T', and scope words. For 'MV SEADUTY - VDR & GMDSS ANNUAL SURVEY', vessel_name is strictly 'Seaduty'.
4. ALL MAKERS (NO DUPLICATE ALIASES): Identify EVERY marine electronics maker involved across the email, Excel/CSV tables, Word/PDF attachments, and Vision OCR section. Use ONE canonical name per brand (e.g. 'SPERRY MARINE' — NEVER output both 'SPERRY' and 'SPERRY MARINE'; use 'YOKOGAWA (YDK)', 'COBHAM SAILOR', 'ANSCHUTZ', 'JRC', 'FURUNO', 'DANELEC', 'TOKYO KEIKI', 'JOTRON', 'NETWAVE', etc.). Ignore service company letterhead / 'Authorised Dealership' brand lists.
5. SPARES REQUESTED: Extract a single concise STRING listing ALL requested or recommended spare parts (including description, OEM part number, and quantity if shown) across ALL makers and attachments.
6. DO NOT extract 'Piraeus' or 'Greece' from office signatures.

MANUAL OVERRIDE:
\"\"\"{manual_override_text or ""}\"\"\"

INQUIRY, ATTACHMENTS & VISION OCR TEXT:
\"\"\"{inquiry}\"\"\"

Return ONLY valid JSON:
{{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA or 'Not specified'",
  "port": "Service port or 'Not specified'",
  "country": "Service country or 'Not specified'",
  "makers": ["Canonical OEM maker names requiring service or spares"],
  "scope": "Concise technical scope summary including equipment model",
  "spares_requested": "Single string listing spares & part numbers, or 'None / Attendance only'",
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


def call_groq_text_json(prompt, preferred_model=None):
    """Fast ~1-2s text-only JSON extraction on Groq."""
    if not client_groq:
        return None, None
    active_models = get_active_groq_models()
    candidates = ([preferred_model] if preferred_model in active_models else []) + [
        m for m in active_models if m != preferred_model
    ]
    for model_name in candidates[:3]:
        try:
            resp = client_groq.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a precise maritime RFQ extraction engine. Output strictly valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            parsed = parse_model_json(resp.choices[0].message.content)
            if parsed:
                return parsed, f"Groq ({model_name})"
        except Exception:
            continue
    return None, None


def call_gemini_text_json(prompt, preferred_model=None):
    raw_txt, eng = _gemini_raw_text(prompt, pil_images=None, preferred_model=preferred_model)
    if raw_txt:
        parsed = parse_model_json(raw_txt)
        if parsed:
            return parsed, eng
    return None, None


def reconcile_results(ai_result, local_result, manual_override_text, source_text=""):
    base = dict(local_result or RESULT_DEFAULTS)
    if ai_result:
        for k in ("vessel_name", "eta", "port", "country", "scope", "spares_requested"):
            ai_val = _as_clean_str(ai_result.get(k))
            if ai_val and ai_val.lower() not in {"not specified", "n/a", "none", "null", "unknown"}:
                base[k] = ai_val

        # Trust AI's maker extraction (+ high-confidence OEM part-number matches) to avoid
        # re-injecting service station letterhead dealership lists picked up by naive regex.
        ai_makers = canonicalize_makers(ai_result.get("makers") or [])
        if ai_makers:
            pn_makers = find_part_number_makers((source_text or "").lower()) if source_text else []
            base["makers"] = canonicalize_makers(ai_makers + pn_makers)
        else:
            base["makers"] = canonicalize_makers(local_result.get("makers") or [])

        for list_k in ("discrepancies", "missing_critical_data"):
            merged = []
            for item in (ai_result.get(list_k) or []) + (local_result.get(list_k) or []):
                s = str(item).strip()
                if s and s not in merged:
                    merged.append(s)
            base[list_k] = merged

    if _as_clean_str(base.get("port")).lower() == "piraeus" and _as_clean_str(local_result.get("port")).lower() not in ("piraeus", "not specified"):
        base["port"] = local_result["port"]
        base["country"] = local_result["country"]

    overrides, explicit = parse_manual_inputs(manual_override_text)
    for k, v in overrides.items():
        if k in explicit and v:
            base[k] = v

    normalized = normalize_result(base)
    normalized["missing_critical_data"] = compute_missing_critical_data(normalized)
    return normalized


def analyze_inquiry(manual_override_text, cleaned_files, pil_images, selected_engine):
    """
    Fast Hybrid Pipeline (~5-10s total):
      1. If scanned PDF / images exist -> Fast Vision OCR (1 call to Gemini REST or Groq Vision)
      2. Fast JSON extraction on combined text (Groq ~1s, or Gemini if selected)
      3. Reconcile + Canonicalize makers (zero alias duplicates!)
    """
    enriched_text = cleaned_files or ""
    vision_status = ""
    vision_errors = []

    if pil_images and selected_engine != "Local Deterministic Only":
        ocr_text, ocr_engine, vision_errors = run_fast_vision_ocr(pil_images, selected_engine)
        if ocr_text:
            enriched_text = (
                f"{enriched_text}\n\n"
                f"--- AI VISION OCR FROM ATTACHED IMAGES / SCANNED PDF ({ocr_engine}) ---\n"
                f"{ocr_text}"
            ).strip()
            vision_status = f"👁️ AI Vision read {len(pil_images)} image(s) via {ocr_engine}"
        else:
            vision_status = "⚠️ AI Vision could not read attached images"

    local_res = smart_local_parser(manual_override_text, enriched_text)
    prompt = build_prompt(manual_override_text, enriched_text)
    ai_res, used_engine = None, "Smart Local Parser"

    if selected_engine == "Local Deterministic Only":
        return reconcile_results(None, local_res, manual_override_text, source_text=enriched_text), "Smart Local Parser", enriched_text, vision_status, vision_errors

    if selected_engine.startswith("Gemini ::"):
        pref = selected_engine.split("::", 1)[1].strip()
        ai_res, used_engine = call_gemini_text_json(prompt, preferred_model=pref)
        if not ai_res:
            ai_res, used_engine = call_groq_text_json(prompt)
    elif selected_engine.startswith("Groq ::"):
        pref = selected_engine.split("::", 1)[1].strip()
        ai_res, used_engine = call_groq_text_json(prompt, preferred_model=pref)
        if not ai_res and gemini_api_key:
            ai_res, used_engine = call_gemini_text_json(prompt)
    else:
        # Auto mode: Groq parses the combined text (+ Vision OCR) in ~1 second!
        if client_groq:
            ai_res, used_engine = call_groq_text_json(prompt)
        if not ai_res and gemini_api_key:
            ai_res, used_engine = call_gemini_text_json(prompt)

    if not used_engine:
        used_engine = "Smart Local Parser"
    return reconcile_results(ai_res, local_res, manual_override_text, source_text=enriched_text), used_engine, enriched_text, vision_status, vision_errors


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
    empty_counts = {"approved": 0, "unstarred": 0, "other": 0, "one_stop": 0, "one_stop_approved": 0}
    if df_dir is None or df_dir.empty:
        return pd.DataFrame(), pd.DataFrame(), [], empty_counts

    target_canon = canonical_country(target_country)
    if not target_canon:
        return pd.DataFrame(), pd.DataFrame(), [], empty_counts

    clean_targets = canonicalize_makers(target_makers)
    is_multi = len(clean_targets) > 1

    maker_col = get_approved_makers_col(df_dir)
    work_df = df_dir.copy()
    work_df["_canon_country"] = work_df["Country"].apply(canonical_country)

    evals = work_df[maker_col].apply(lambda s: evaluate_station_coverage(s, clean_targets))
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
        "one_stop_approved": int(((primary_pool["_is_one_stop"] == 1) & (primary_pool["_sort_rank"] == 0)).sum()),
    }

    allowed_primary_ranks = {0}
    if include_maker_unstarred or include_other_stations:
        allowed_primary_ranks.add(1)
    if include_other_stations:
        allowed_primary_ranks.add(2)

    primary_matched = primary_pool[primary_pool["_sort_rank"].isin(allowed_primary_ranks)].copy()
    if one_stop_only and is_multi:
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
        if include_maker_unstarred or include_other_stations:
            allowed_neighbor_ranks.add(1)
        neighbor_matched = neighbor_pool[neighbor_pool["_sort_rank"].isin(allowed_neighbor_ranks)].copy()
        if one_stop_only and is_multi:
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
            if clean_em and not clean_em.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf")):
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


def _split_rfq_subject_body(rfq_text):
    text = (rfq_text or "").strip()
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subj = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).lstrip("\n")
        return subj, body
    return "RFQ: Technical Attendance", text


def build_mailto_href(emails, rfq_text):
    """Build a safe mailto: URI (capped to avoid Outlook/browser URL length limits)."""
    subj, body = _split_rfq_subject_body(rfq_text)
    bcc_str = ",".join(emails or [])
    params = {}
    if bcc_str:
        params["bcc"] = bcc_str
    if subj:
        params["subject"] = subj
    base_url = "mailto:?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    full_params = dict(params)
    full_params["body"] = body
    full_url = "mailto:?" + urllib.parse.urlencode(full_params, quote_via=urllib.parse.quote)
    if len(full_url) <= 1850:
        return full_url, True
    return base_url, False


def generate_bracketed_rfq_template(parsed_data, matched_df=None):
    d = parsed_data or RESULT_DEFAULTS
    vessel = _as_clean_str(d.get("vessel_name"), "Not specified")
    port = _as_clean_str(d.get("port"), "Not specified")
    country = _as_clean_str(d.get("country"), "Not specified")
    eta = _as_clean_str(d.get("eta"), "Not specified")
    makers_list = d.get("makers") or []
    makers_str = ", ".join(makers_list) if makers_list else "OEM Equipment / TBA"
    scope = _as_clean_str(d.get("scope"), "Standard technical attendance inquiry.")
    spares = _as_clean_str(d.get("spares_requested"), "Inquired per inquiry")

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


def generate_copilot_reply(user_query, parsed_data, primary_df, neighbor_df, raw_inquiry_text, selected_engine, chat_history=None):
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
- Raw Inquiry Excerpt: {(raw_inquiry_text or '')[:3500]}"""

    recent_history = []
    if chat_history:
        for m in list(chat_history)[-6:]:
            role = m.get("role")
            content = str(m.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                recent_history.append({"role": role, "content": content[:1200]})

    history_block = ""
    if recent_history:
        lines = [f"{m['role'].upper()}: {m['content']}" for m in recent_history]
        history_block = "\n\nRECENT CONVERSATION:\n" + "\n".join(lines)

    gemini_full_prompt = f"{sys_context}{history_block}\n\nUSER QUESTION:\n{user_query}"
    groq_messages = [{"role": "system", "content": sys_context}] + recent_history + [{"role": "user", "content": user_query}]

    if selected_engine.startswith("Gemini ::") and gemini_api_key:
        pref = selected_engine.split("::", 1)[1].strip()
        txt, _ = _gemini_raw_text(gemini_full_prompt, preferred_model=pref)
        if txt:
            return txt

    if client_groq:
        active_groq = get_active_groq_models()
        pref = selected_engine.split("::", 1)[1].strip() if selected_engine.startswith("Groq ::") else active_groq[0]
        for m in ([pref] + [x for x in active_groq if x != pref])[:3]:
            try:
                resp = client_groq.chat.completions.create(
                    model=m,
                    messages=groq_messages,
                    temperature=0.2,
                    max_tokens=1024,
                )
                txt = (resp.choices[0].message.content or "").strip()
                if txt:
                    return txt
            except Exception:
                continue

    if gemini_api_key:
        txt, _ = _gemini_raw_text(gemini_full_prompt)
        if txt:
            return txt

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
def _apply_parsed_data(parsed_dict, mark_active=False):
    d = dict(RESULT_DEFAULTS)
    if isinstance(parsed_dict, dict):
        d.update(parsed_dict)
    d["makers"] = canonicalize_makers(d.get("makers"))
    if mark_active:
        d["missing_critical_data"] = compute_missing_critical_data(d)
    st.session_state.parsed_data = d
    st.session_state.eb_vessel = _as_clean_str(d.get("vessel_name"), "Not specified")
    st.session_state.eb_port = _as_clean_str(d.get("port"), "Not specified")
    st.session_state.eb_country = _as_clean_str(d.get("country"), "Not specified")
    st.session_state.eb_eta = _as_clean_str(d.get("eta"), "Not specified")
    st.session_state.eb_makers = ", ".join(d.get("makers") or [])
    st.session_state.eb_scope = _as_clean_str(d.get("scope"), "Standard technical attendance inquiry.")
    st.session_state.eb_spares = _as_clean_str(d.get("spares_requested"), "Inquired per inquiry")
    if mark_active:
        st.session_state.has_active_inquiry = True


def _sync_brief_from_widgets():
    v_val = _as_clean_str(st.session_state.get("eb_vessel"), "Not specified")
    p_val = _as_clean_str(st.session_state.get("eb_port"), "Not specified")
    c_raw = _as_clean_str(st.session_state.get("eb_country"))
    c_val = (find_country(c_raw) or c_raw.upper()) if c_raw and c_raw.lower() != "not specified" else "Not specified"
    e_val = _as_clean_str(st.session_state.get("eb_eta"), "Not specified")
    m_list = canonicalize_makers(_as_clean_str(st.session_state.get("eb_makers")))
    sc_val = _as_clean_str(st.session_state.get("eb_scope"), "Standard technical attendance inquiry.")
    sp_val = _as_clean_str(st.session_state.get("eb_spares"), "Inquired per inquiry")

    st.session_state.parsed_data.update({
        "vessel_name": v_val,
        "port": p_val,
        "country": c_val,
        "eta": e_val,
        "makers": m_list,
        "scope": sc_val,
        "spares_requested": sp_val,
    })
    st.session_state.has_active_inquiry = True
    st.session_state.parsed_data["missing_critical_data"] = compute_missing_critical_data(st.session_state.parsed_data)


def _on_port_widget_change():
    p_val = _as_clean_str(st.session_state.get("eb_port"))
    if p_val and p_val.lower() != "not specified":
        matched_p = ports_in_text(p_val)
        if matched_p:
            st.session_state.eb_port = matched_p[0][2].title()
            st.session_state.eb_country = matched_p[0][3]
    _sync_brief_from_widgets()


if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0
if "has_active_inquiry" not in st.session_state:
    st.session_state.has_active_inquiry = False
if "manual_entry_mode" not in st.session_state:
    st.session_state.manual_entry_mode = False
if "parsed_data" not in st.session_state:
    _apply_parsed_data(RESULT_DEFAULTS, mark_active=False)
if "eb_vessel" not in st.session_state:
    _apply_parsed_data(st.session_state.parsed_data, mark_active=st.session_state.has_active_inquiry)
for _wk, _wdef in (
    ("eb_vessel", "Not specified"),
    ("eb_port", "Not specified"),
    ("eb_country", "Not specified"),
    ("eb_eta", "Not specified"),
    ("eb_makers", ""),
    ("eb_scope", "Standard technical attendance inquiry."),
    ("eb_spares", "Inquired per inquiry"),
):
    if not isinstance(st.session_state.get(_wk), str):
        st.session_state[_wk] = _as_clean_str(st.session_state.get(_wk), _wdef)

if "raw_inquiry_text" not in st.session_state:
    st.session_state.raw_inquiry_text = ""
if "extraction_notes" not in st.session_state:
    st.session_state.extraction_notes = []
if "vision_status" not in st.session_state:
    st.session_state.vision_status = ""
if "vision_errors" not in st.session_state:
    st.session_state.vision_errors = []
if "vision_preview_images" not in st.session_state:
    st.session_state.vision_preview_images = []
if "last_used_engine" not in st.session_state:
    st.session_state.last_used_engine = "Ready"
if "last_analysis_sec" not in st.session_state:
    st.session_state.last_analysis_sec = None
if "_pending_toast" not in st.session_state:
    st.session_state._pending_toast = ""
if "_last_filter_sig" not in st.session_state:
    st.session_state._last_filter_sig = ""
if "primary_sel_mode" not in st.session_state:
    st.session_state.primary_sel_mode = "all"
if "primary_sel_ver" not in st.session_state:
    st.session_state.primary_sel_ver = 0
if "neighbor_sel_mode" not in st.session_state:
    st.session_state.neighbor_sel_mode = "all"
if "neighbor_sel_ver" not in st.session_state:
    st.session_state.neighbor_sel_ver = 0
if "_last_rfq_default_hash" not in st.session_state:
    st.session_state._last_rfq_default_hash = ""
if "rfq_saved_text" not in st.session_state:
    st.session_state.rfq_saved_text = ""

if "include_maker_unstarred" not in st.session_state:
    st.session_state.include_maker_unstarred = False
for _k in ("chk_unstarred_sidebar", "chk_unstarred_main"):
    if _k not in st.session_state:
        st.session_state[_k] = st.session_state.include_maker_unstarred

if "include_other_stations" not in st.session_state:
    st.session_state.include_other_stations = False
for _k in ("chk_other_sidebar", "chk_other_main"):
    if _k not in st.session_state:
        st.session_state[_k] = st.session_state.include_other_stations

if "one_stop_only" not in st.session_state:
    st.session_state.one_stop_only = False

if "show_copilot" not in st.session_state:
    st.session_state.show_copilot = False
if "copilot_messages" not in st.session_state:
    st.session_state.copilot_messages = [
        {
            "role": "assistant",
            "content": (
                "Hi! I'm **Onetech AI Copilot** ⚓\n\n"
                "Ask me to audit discrepancies, verify `*` Maker Approvals, compare matched stations, or draft vendor follow-ups."
            ),
        }
    ]


def _set_unstarred_state(val):
    v = bool(val)
    st.session_state.include_maker_unstarred = v
    st.session_state.chk_unstarred_sidebar = v
    st.session_state.chk_unstarred_main = v


def _set_other_state(val):
    v = bool(val)
    st.session_state.include_other_stations = v
    st.session_state.chk_other_sidebar = v
    st.session_state.chk_other_main = v


def _sync_unstarred(source_key):
    val = bool(st.session_state[source_key])
    _set_unstarred_state(val)
    if not val and st.session_state.include_other_stations:
        _set_other_state(False)


def _sync_other(source_key):
    val = bool(st.session_state[source_key])
    _set_other_state(val)
    if val and not st.session_state.include_maker_unstarred:
        _set_unstarred_state(True)


def _enable_unstarred_only():
    _set_unstarred_state(True)


def _enable_other_stations():
    _set_unstarred_state(True)
    _set_other_state(True)


def _disable_one_stop_only():
    st.session_state.one_stop_only = False


def _set_primary_sel_mode(mode):
    st.session_state.primary_sel_mode = mode
    st.session_state.primary_sel_ver += 1


def _set_neighbor_sel_mode(mode):
    st.session_state.neighbor_sel_mode = mode
    st.session_state.neighbor_sel_ver += 1


def _save_rfq_widget_edit():
    st.session_state.rfq_saved_text = st.session_state.get("rfq_editor_widget", "")


def _reset_rfq_editor(default_text, default_hash):
    st.session_state.rfq_saved_text = default_text
    st.session_state.rfq_editor_widget = default_text
    st.session_state._last_rfq_default_hash = default_hash


def _start_manual_entry():
    st.session_state.has_active_inquiry = True
    st.session_state.manual_entry_mode = True
    st.session_state.parsed_data["missing_critical_data"] = compute_missing_critical_data(st.session_state.parsed_data)


def _toggle_copilot():
    st.session_state.show_copilot = not st.session_state.show_copilot


def _close_copilot():
    st.session_state.show_copilot = False


def _reset_all_fields():
    st.session_state.reset_count += 1
    st.session_state.has_active_inquiry = False
    st.session_state.manual_entry_mode = False
    _apply_parsed_data(RESULT_DEFAULTS, mark_active=False)
    st.session_state.raw_inquiry_text = ""
    st.session_state.extraction_notes = []
    st.session_state.vision_status = ""
    st.session_state.vision_errors = []
    st.session_state.vision_preview_images = []
    st.session_state.last_used_engine = "Ready"
    st.session_state.last_analysis_sec = None
    _set_unstarred_state(False)
    _set_other_state(False)
    st.session_state.one_stop_only = False
    st.session_state.primary_sel_mode = "all"
    st.session_state.primary_sel_ver += 1
    st.session_state.neighbor_sel_mode = "all"
    st.session_state.neighbor_sel_ver += 1
    st.session_state._last_rfq_default_hash = ""
    st.session_state.rfq_saved_text = ""
    st.session_state._pending_toast = "Ready for a new inquiry."


def _run_sample_rfq(selected_engine):
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
    st.session_state.extraction_notes = ["Sample RFQ loaded (M/V Seaduty — JRC & Furuno @ Taicang, China)"]
    st.session_state.vision_preview_images = []
    st.session_state.vision_status = ""
    st.session_state.vision_errors = []
    st.session_state.manual_entry_mode = False
    t0 = time.perf_counter()
    with st.status("Analyzing sample RFQ...", expanded=False) as status_box:
        parsed, eng, enriched_txt, v_stat, v_errs = analyze_inquiry("", sample_thread, [], selected_engine)
        _apply_parsed_data(parsed, mark_active=True)
        st.session_state.raw_inquiry_text = enriched_txt
        st.session_state.last_used_engine = eng
        st.session_state.last_analysis_sec = time.perf_counter() - t0
        status_box.update(label=f"Sample analyzed via {eng}", state="complete")
    st.session_state._pending_toast = f"Sample routed: M/V {parsed.get('vessel_name')} @ {parsed.get('port')}, {parsed.get('country')}"
    st.rerun()


def _render_intake_form(selected_engine, rc, is_compact=False):
    """Shared clean RFQ uploader / paste / optional manual override form."""
    uploaded_files = st.file_uploader(
        "Drop client emails, PDFs, Excel/Word/ZIP files, or photos",
        type=[
            "pdf", "eml", "msg", "txt", "xlsx", "xls", "csv",
            "docx", "zip", "html", "htm", "png", "jpg", "jpeg", "webp", "tif", "tiff"
        ],
        accept_multiple_files=True,
        key=f"rfq_file_uploader_{rc}",
        help="Supports MSG/EML emails (with attachments), text & scanned PDFs, Excel, CSV, Word, ZIP archives, and equipment photos.",
    )
    pasted_inquiry = st.text_area(
        "Or paste email thread / inquiry text",
        height=95 if is_compact else 115,
        placeholder="Paste the client email thread here (the top message is treated as the latest update)...",
        key=f"pasted_inquiry_box_{rc}",
    )

    with st.expander("🎯 Manual Override (Optional — force Vessel, Port, Country, ETA, or Makers)", expanded=False):
        manual_override_input = st.text_area(
            "Manual Ground-Truth Override",
            height=115,
            label_visibility="collapsed",
            placeholder="Optional — values entered here override AI & email text:\nVessel: MV Seaduty\nPort: Taicang\nCountry: China\nETA: 22-24 Nov 2026\nMaker: Furuno, JRC",
            key=f"manual_override_box_{rc}",
        )

    if is_compact:
        run_btn = st.button("⚡ Re-analyze & Update Stations", type="primary", use_container_width=True, key=f"btn_reanalyze_{rc}")
        sample_btn = False
    else:
        b1, b2, b3 = st.columns([2.2, 1.0, 1.0], gap="small")
        with b1:
            run_btn = st.button("⚡ Analyze & Find Stations", type="primary", use_container_width=True, key=f"btn_analyze_{rc}")
        with b2:
            sample_btn = st.button("🧪 Try Sample", use_container_width=True, key=f"btn_sample_{rc}", help="Test with a realistic multi-maker RFQ")
        with b3:
            st.button("✏️ Enter Manually", on_click=_start_manual_entry, use_container_width=True, key=f"btn_manual_{rc}", help="Skip upload and search stations by port & maker directly")

    if sample_btn:
        _run_sample_rfq(selected_engine)

    if run_btn:
        t0 = time.perf_counter()
        combined_text_parts, labeled_images, all_notes = [], [], []
        with st.status("Analyzing inquiry...", expanded=True) as status_box:
            if pasted_inquiry and pasted_inquiry.strip():
                combined_text_parts.append(clean_signatures(pasted_inquiry.strip()))
            if uploaded_files:
                st.write(f"Reading **{len(uploaded_files)}** uploaded file(s)...")
                for uf in uploaded_files:
                    txt, imgs, notes = extract_content_from_file(uf)
                    if txt:
                        combined_text_parts.append(f"--- FILE: {uf.name} ---\n{txt}")
                    if imgs:
                        labeled_images.extend(imgs)
                    if notes:
                        all_notes.extend(notes)

            labeled_images = labeled_images[:6]
            pil_images = [img for _, img in labeled_images]
            full_cleaned_text = "\n\n".join(combined_text_parts).strip()
            st.session_state.extraction_notes = all_notes
            st.session_state.vision_preview_images = labeled_images

            if not full_cleaned_text and not (manual_override_input and manual_override_input.strip()) and not pil_images:
                status_box.update(label="Please add a file, paste text, or fill Manual Override", state="error", expanded=False)
                st.warning("Upload a file, paste an email, or enter a Manual Override first.")
            else:
                if pil_images and selected_engine != "Local Deterministic Only":
                    st.write(f"Running AI Vision OCR on **{len(pil_images)}** image(s)...")
                st.write("Extracting vessel details, makers, spares & matching stations...")
                parsed, eng, enriched_txt, v_stat, v_errs = analyze_inquiry(
                    manual_override_input, full_cleaned_text, pil_images, selected_engine
                )
                _apply_parsed_data(parsed, mark_active=True)
                st.session_state.manual_entry_mode = False
                st.session_state.raw_inquiry_text = enriched_txt
                st.session_state.last_used_engine = eng
                st.session_state.vision_status = v_stat
                st.session_state.vision_errors = v_errs
                elapsed = time.perf_counter() - t0
                st.session_state.last_analysis_sec = elapsed
                status_box.update(label=f"Done via {eng} ({elapsed:.1f}s)", state="complete", expanded=False)
                st.session_state._pending_toast = f"Routed via {eng} ({elapsed:.1f}s)"
                st.rerun()


if st.session_state._pending_toast:
    st.toast(st.session_state._pending_toast, icon="⚓")
    st.session_state._pending_toast = ""

rc = st.session_state.reset_count

df_directory, directory_source = load_directory()
total_stations_count = len(df_directory) if df_directory is not None else 0
unique_countries_count = df_directory["Country"].nunique() if df_directory is not None and "Country" in df_directory.columns else 0


# ---------------------------------------------------------------------------
# SIDEBAR: SETTINGS & FULL DIRECTORY (CLEAN & COLLAPSED BY DEFAULT)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.35rem;">
        <div style="width:34px;height:34px;border-radius:8px;background:linear-gradient(135deg,#0284c7,#2563eb);display:flex;align-items:center;justify-content:center;color:white;font-size:1.1rem;flex-shrink:0;">⚓</div>
        <div>
            <div style="font-weight:800;font-size:0.95rem;color:var(--text-color, #0f172a);line-height:1.15;">ONETECH SETTINGS</div>
            <div style="font-size:0.72rem;color:#64748b;">Directory &amp; Engine Controls</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown(f"""
    <div class="ot-sidebar-card">
        <div style="font-weight:700;margin-bottom:0.15rem;">🟢 {html.escape(directory_source)}</div>
        <div style="color:#64748b;"><strong>{total_stations_count}</strong> Stations • <strong>{unique_countries_count}</strong> Countries</div>
    </div>
    """, unsafe_allow_html=True)

    sb_c1, sb_c2 = st.columns(2)
    with sb_c1:
        if st.button("🔄 Sync Sheet", use_container_width=True, help="Reload latest stations from Google Sheets"):
            load_directory.clear()
            st.session_state._pending_toast = "Directory synced from live source."
            st.rerun()
    with sb_c2:
        st.button("🗑️ Reset", on_click=_reset_all_fields, use_container_width=True, help="Clear current inquiry")

    st.markdown("###### Routing Defaults")
    st.checkbox(
        "🟡 Include Unstarred (No *)",
        key="chk_unstarred_sidebar",
        on_change=_sync_unstarred,
        args=("chk_unstarred_sidebar",),
        help="Include stations that list the target maker without a strict (*) approval.",
    )
    st.checkbox(
        "🔧 Include All Country Stations",
        key="chk_other_sidebar",
        on_change=_sync_other,
        args=("chk_other_sidebar",),
        help="Include unstarred and all remaining stations in the target country.",
    )

    st.divider()

    with st.expander("🤖 AI Engine Settings", expanded=False):
        active_gemini_list = get_active_gemini_models()
        active_groq_list = get_active_groq_models()
        engine_options = (
            ["Auto (Best Available)"]
            + [f"Gemini :: {m}" for m in active_gemini_list]
            + [f"Groq :: {m}" for m in active_groq_list]
            + ["Local Deterministic Only"]
        )
        selected_engine = st.selectbox(
            "Parser & Copilot Model",
            options=engine_options,
            index=0,
            help="Auto uses Gemini/Groq Vision OCR for scanned PDFs/images and fast Groq/Gemini extraction for emails.",
        )
        st.caption(
            f"{'🟢 Gemini API' if gemini_api_key else '⚪ Gemini Key Missing'}  •  "
            f"{'🟢 Groq API' if (groq_api_key and HAS_GROQ) else '⚪ Groq Unavailable'}"
        )

    with st.expander("🔎 Browse Full Directory", expanded=False):
        if df_directory is not None and not df_directory.empty:
            dir_countries = ["All Countries"] + sorted(df_directory["Country"].dropna().astype(str).unique().tolist())
            sel_dir_country = st.selectbox("Country", options=dir_countries, index=0, key="sb_dir_country")
            q_search = st.text_input("Search Station / Maker", placeholder="e.g. Furuno, Dubai...")
            view_dir = df_directory
            if sel_dir_country != "All Countries":
                view_dir = view_dir[view_dir["Country"].astype(str) == sel_dir_country]
            if q_search.strip():
                mask = view_dir.astype(str).apply(lambda col: col.str.contains(q_search.strip(), case=False, na=False)).any(axis=1)
                view_dir = view_dir[mask]
            st.caption(f"Showing **{len(view_dir)}** of {len(df_directory)} stations")
            st.dataframe(view_dir, use_container_width=True, hide_index=True, height=230)
            st.download_button(
                "⬇️ Export CSV",
                data=view_dir.to_csv(index=False).encode("utf-8-sig"),
                file_name="onetech_station_directory.csv",
                mime="text/csv",
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# COMPACT TOP BAR & FLOATING COPILOT TRIGGER
# ---------------------------------------------------------------------------
if not st.session_state.show_copilot:
    st.button(
        "💬 AI Copilot",
        key="floating_copilot_btn",
        on_click=_toggle_copilot,
    )

timing_pill = (
    f'<span class="ot-pill">⚡ {html.escape(st.session_state.last_used_engine)} ({st.session_state.last_analysis_sec:.1f}s)</span>'
    if st.session_state.last_analysis_sec is not None
    else ""
)

st.markdown(f"""
<div class="ot-topbar">
    <div class="ot-topbar-left">
        <div class="ot-brand-logo">⚓</div>
        <div>
            <h1 class="ot-hero-title">Onetech Service Router</h1>
            <p class="ot-hero-subtitle">Upload RFQ → Match Approved (*) Stations → Dispatch</p>
        </div>
    </div>
    <div class="ot-topbar-right">
        <span class="ot-pill ot-pill-live"><span class="ot-dot-live"></span> {html.escape(directory_source)} • {total_stations_count} Stations</span>
        {timing_pill}
    </div>
</div>
""", unsafe_allow_html=True)

# Pre-compute routing state so both Main Workspace and Copilot always stay in sync
active_country = _as_clean_str(st.session_state.parsed_data.get("country"), "Not specified")
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
if st.session_state._last_filter_sig != filter_sig:
    st.session_state._last_filter_sig = filter_sig
    st.session_state.primary_sel_mode = "all"
    st.session_state.neighbor_sel_mode = "all"

if st.session_state.show_copilot:
    col_main, col_copilot = st.columns([2.35, 1.0], gap="large")
else:
    col_main = st.container()
    col_copilot = None


# ---------------------------------------------------------------------------
# MAIN WORKSPACE: PROGRESSIVE DISCLOSURE (CLEAN START -> FOCUSED RESULTS)
# ---------------------------------------------------------------------------
with col_main:
    if not st.session_state.has_active_inquiry:
        # CLEAN, CALM START SCREEN
        with st.container(border=True):
            st.markdown("""
            <div class="ot-welcome-title">Start a Service Routing Inquiry</div>
            <div class="ot-welcome-sub">Drop client emails, PDFs, spreadsheets, ZIPs, or photos — or paste text below. Open the sidebar (top-left) anytime for AI model settings or the full station directory.</div>
            """, unsafe_allow_html=True)
            _render_intake_form(selected_engine, rc, is_compact=False)
    else:
        # QUICK ACTION BAR FOR ACTIVE INQUIRY
        qa_left, qa_btn1, qa_btn2 = st.columns([3.2, 1.0, 1.0], gap="small")
        with qa_left:
            if st.session_state.vision_status:
                if st.session_state.vision_status.startswith("⚠️"):
                    st.warning(st.session_state.vision_status + (f" — {' | '.join(st.session_state.vision_errors[:2])}" if st.session_state.vision_errors else ""))
                else:
                    st.caption(st.session_state.vision_status)
            elif st.session_state.extraction_notes:
                st.caption("📎 " + " • ".join(st.session_state.extraction_notes[:3]))
            else:
                st.caption("Review the summary below, select stations, then copy emails & RFQ from **Dispatch & Emails**.")
        with qa_btn1:
            st.button(
                "✖ Hide Copilot" if st.session_state.show_copilot else "💬 AI Copilot",
                key="topbar_copilot_btn",
                on_click=_toggle_copilot,
                use_container_width=True,
            )
        with qa_btn2:
            st.button("➕ New Inquiry", key="topbar_new_inquiry_btn", on_click=_reset_all_fields, use_container_width=True)

        # COMPACT SUMMARY CARD
        cur = st.session_state.parsed_data
        v_disp = _as_clean_str(cur.get("vessel_name"), "Not specified")
        p_disp = _as_clean_str(cur.get("port"), "Not specified")
        c_disp = _as_clean_str(cur.get("country"), "Not specified")
        e_disp = _as_clean_str(cur.get("eta"), "Not specified")
        sc_disp = _as_clean_str(cur.get("scope"), "Standard technical attendance inquiry.")
        sp_disp = _as_clean_str(cur.get("spares_requested"), "Inquired per inquiry")
        m_list = cur.get("makers") or []
        m_disp = ", ".join(m_list) if m_list else "Not specified"

        v_is_set = v_disp.lower() != "not specified"
        p_is_set = p_disp.lower() != "not specified"
        e_is_set = e_disp.lower() != "not specified"
        v_kpi_label = (
            v_disp if re.match(r"(?i)^m/[vt]\s+", v_disp) else f"M/V {v_disp}"
        ) if v_is_set else "Not specified"

        with st.container(border=True):
            st.markdown(f"""
            <div class="ot-kpi-grid">
                <div class="ot-kpi-card">
                    <div class="ot-kpi-label">🚢 Vessel</div>
                    <div class="{'ot-kpi-value' if v_is_set else 'ot-kpi-value-muted'}" title="{html.escape(v_kpi_label)}">{html.escape(v_kpi_label)}</div>
                </div>
                <div class="ot-kpi-card" style="border-left-color:#2563eb;">
                    <div class="ot-kpi-label">📍 Port &amp; Country</div>
                    <div class="{'ot-kpi-value' if p_is_set else 'ot-kpi-value-muted'}" title="{html.escape(p_disp)}, {html.escape(c_disp)}">{html.escape(p_disp)}</div>
                    <div class="ot-kpi-sub">{html.escape(c_disp)}</div>
                </div>
                <div class="ot-kpi-card" style="border-left-color:#0d9488;">
                    <div class="ot-kpi-label">🗓️ ETA</div>
                    <div class="{'ot-kpi-value' if e_is_set else 'ot-kpi-value-muted'}" title="{html.escape(e_disp)}">{html.escape(e_disp)}</div>
                </div>
                <div class="ot-kpi-card" style="border-left-color:#7c3aed;">
                    <div class="ot-kpi-label">🛠️ Makers ({len(m_list)})</div>
                    <div class="{'ot-kpi-value' if m_list else 'ot-kpi-value-muted'}" title="{html.escape(m_disp)}">{html.escape(m_disp)}</div>
                </div>
            </div>
            <div class="ot-scope-strip">
                <div class="ot-scope-item"><span class="ot-scope-lbl">Scope of Work</span>{html.escape(sc_disp)}</div>
                <div class="ot-scope-item"><span class="ot-scope-lbl">Spares / Parts Requested</span>{html.escape(sp_disp)}</div>
            </div>
            """, unsafe_allow_html=True)

            discrep_list = cur.get("discrepancies") or []
            missing_list = cur.get("missing_critical_data") or []
            if discrep_list:
                items_html = "<br>".join(f"• {html.escape(str(x))}" for x in discrep_list)
                st.markdown(f'<div class="ot-alert-box ot-alert-warn"><strong>⚠️ Thread / Port Discrepancy:</strong><br>{items_html}</div>', unsafe_allow_html=True)
            if missing_list:
                items_html = "<br>".join(f"• {html.escape(str(x))}" for x in missing_list)
                st.markdown(f'<div class="ot-alert-box ot-alert-danger"><strong>🚨 Missing Details (edit below):</strong><br>{items_html}</div>', unsafe_allow_html=True)

            auto_expand_edit = bool(st.session_state.manual_entry_mode or missing_list)
            with st.expander("✏️ Edit Inquiry Details (live-updates Stations & RFQ)", expanded=auto_expand_edit):
                if st.session_state.show_copilot:
                    e1, e2 = st.columns(2, gap="small")
                    with e1:
                        st.text_input("Vessel Name", key="eb_vessel", on_change=_sync_brief_from_widgets)
                    with e2:
                        st.text_input("ETA / Schedule", key="eb_eta", on_change=_sync_brief_from_widgets)
                    e3, e4 = st.columns(2, gap="small")
                    with e3:
                        st.text_input("Service Port", key="eb_port", on_change=_on_port_widget_change, help="Known ports auto-fill Service Country.")
                    with e4:
                        st.text_input("Service Country", key="eb_country", on_change=_sync_brief_from_widgets)
                else:
                    e1, e2, e3, e4 = st.columns([1.1, 1.0, 1.0, 1.1], gap="small")
                    with e1:
                        st.text_input("Vessel Name", key="eb_vessel", on_change=_sync_brief_from_widgets)
                    with e2:
                        st.text_input("Service Port", key="eb_port", on_change=_on_port_widget_change, help="Known ports auto-fill Service Country.")
                    with e3:
                        st.text_input("Service Country", key="eb_country", on_change=_sync_brief_from_widgets)
                    with e4:
                        st.text_input("ETA / Schedule", key="eb_eta", on_change=_sync_brief_from_widgets)

                st.text_input(
                    "Target Makers (comma-separated)",
                    key="eb_makers",
                    on_change=_sync_brief_from_widgets,
                    placeholder="e.g. Furuno, JRC, Sperry Marine",
                    help="Aliases like Sperry / YDK / Sailor / Alphatron are automatically matched.",
                )
                if m_list:
                    chips_html = "".join(f'<span class="ot-maker-chip">🛠️ {html.escape(mk)}</span>' for mk in m_list)
                    st.markdown(f'<div style="margin:-0.25rem 0 0.5rem 0;">{chips_html}</div>', unsafe_allow_html=True)

                sc_c1, sc_c2 = st.columns(2, gap="small")
                with sc_c1:
                    st.text_area("Scope of Work", key="eb_scope", height=78, on_change=_sync_brief_from_widgets)
                with sc_c2:
                    st.text_area("Spares / Parts Requested", key="eb_spares", height=78, on_change=_sync_brief_from_widgets)

            source_badges = []
            if st.session_state.vision_preview_images:
                source_badges.append(f"{len(st.session_state.vision_preview_images)} image(s)")
            if st.session_state.extraction_notes:
                source_badges.append(f"{len(st.session_state.extraction_notes)} note(s)")
            src_suffix = f" ({' • '.join(source_badges)})" if source_badges else ""

            with st.expander(f"📥 Source Files, Manual Override & OCR Text{src_suffix}", expanded=False):
                _render_intake_form(selected_engine, rc, is_compact=True)
                if st.session_state.vision_preview_images:
                    st.markdown("**🖼️ Pages / Photos Sent to AI Vision**")
                    img_cols = st.columns(min(3, len(st.session_state.vision_preview_images)))
                    for idx, (lbl, pil_im) in enumerate(st.session_state.vision_preview_images):
                        with img_cols[idx % len(img_cols)]:
                            st.image(pil_im, caption=lbl, use_container_width=True)
                if st.session_state.raw_inquiry_text:
                    st.markdown("**📄 Extracted Inquiry & OCR Text**")
                    st.code(st.session_state.raw_inquiry_text[:12000], language="text")

        # FOCUSED 2-TAB WORKSPACE: STATIONS & DISPATCH
        tab_stations, tab_dispatch = st.tabs([
            f"🏢 Service Stations ({len(primary_df)} matched)",
            "📤 Dispatch & Emails",
        ])

        with tab_stations:
            if is_multi_maker:
                f_c1, f_c2, f_c3 = st.columns(3)
            else:
                f_c1, f_c2 = st.columns(2)
                f_c3 = None

            with f_c1:
                st.checkbox(
                    f"🟡 Include Unstarred / No * ({tier_counts['unstarred']})",
                    key="chk_unstarred_main",
                    on_change=_sync_unstarred,
                    args=("chk_unstarred_main",),
                    help="Show stations that list the maker without an OEM approval asterisk (*).",
                )
            with f_c2:
                st.checkbox(
                    f"🔧 Include All Country Stations ({tier_counts['other']})",
                    key="chk_other_main",
                    on_change=_sync_other,
                    args=("chk_other_main",),
                    help="Show unstarred stations plus all other stations in the target country.",
                )
            if f_c3 is not None:
                with f_c3:
                    st.checkbox(
                        f"🏆 One-Stop-Shop Only ({tier_counts['one_stop']})",
                        key="one_stop_only",
                        help=f"Show only stations covering all {len(active_makers)} requested makers.",
                    )

            if not canonical_country(active_country):
                st.info("Enter a **Service Port** or **Service Country** in **✏️ Edit Inquiry Details** above to see matching stations.")
            elif not primary_df.empty:
                s_col, b_all, b_none, b_smart = st.columns([2.3, 0.75, 0.8, 1.05], gap="small")
                with s_col:
                    primary_search_q = st.text_input(
                        "Filter stations",
                        placeholder="🔎 Filter by port, city, or station name...",
                        label_visibility="collapsed",
                        key=f"st_search_primary_{rc}",
                    )
                with b_all:
                    st.button("☑️ All", key="btn_prim_sel_all", on_click=_set_primary_sel_mode, args=("all",), use_container_width=True)
                with b_none:
                    st.button("☐ None", key="btn_prim_sel_none", on_click=_set_primary_sel_mode, args=("none",), use_container_width=True)
                with b_smart:
                    if is_multi_maker and tier_counts["one_stop"] > 0:
                        st.button("🏆 One-Stop", key="btn_prim_sel_os", on_click=_set_primary_sel_mode, args=("onestop",), use_container_width=True)
                    else:
                        st.button("⭐ Approved", key="btn_prim_sel_app", on_click=_set_primary_sel_mode, args=("approved",), use_container_width=True)

                primary_view = primary_df.copy()
                q_clean = (primary_search_q or "").strip()
                if q_clean:
                    p_mask = primary_view.astype(str).apply(lambda col: col.str.contains(q_clean, case=False, na=False)).any(axis=1)
                    primary_view = primary_view[p_mask].reset_index(drop=True)

                if primary_view.empty:
                    st.info(f"No matched stations contain **'{q_clean}'**. Clear the search box to see all {len(primary_df)} matched station(s).")
                else:
                    sel_mode = st.session_state.primary_sel_mode
                    if sel_mode == "none":
                        default_sel = [False] * len(primary_view)
                    elif sel_mode == "approved":
                        default_sel = (primary_view["Approval Status"] == "✅ Maker Approved (*)").tolist()
                    elif sel_mode == "onestop":
                        default_sel = primary_view["Maker Coverage"].astype(str).str.startswith("🏆").tolist()
                    else:
                        default_sel = [True] * len(primary_view)

                    primary_for_editor = primary_view.copy()
                    primary_for_editor.insert(0, "Select", default_sel)
                    disabled_primary_cols = [c for c in primary_for_editor.columns if c != "Select"]
                    q_hash = hashlib.md5(q_clean.lower().encode("utf-8")).hexdigest()[:6]

                    edited_primary_df = st.data_editor(
                        primary_for_editor,
                        use_container_width=True,
                        hide_index=True,
                        disabled=disabled_primary_cols,
                        column_config={
                            "Select": st.column_config.CheckboxColumn(
                                "Select",
                                help="Checked stations are included in Outlook emails and the RFQ greeting.",
                                default=True,
                            )
                        },
                        key=f"primary_stations_editor_{filter_sig}_{st.session_state.primary_sel_ver}_{q_hash}",
                    )
                    sel_mask = edited_primary_df["Select"].fillna(False).astype(bool)
                    selected_primary_df = edited_primary_df[sel_mask].drop(
                        columns=["Select"], errors="ignore"
                    ).reset_index(drop=True)

                    st.markdown(
                        f'<div class="ot-selection-bar">'
                        f'<span>✅ <strong>{len(selected_primary_df)}</strong> of <strong>{len(primary_view)}</strong> station(s) selected'
                        f' • Approved (*): <strong>{tier_counts["approved"]}</strong></span>'
                        f'<span style="color:var(--ot-text-muted);">Ready → Open <strong>📤 Dispatch &amp; Emails</strong></span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                extra_hint = ""
                if one_stop_only and tier_counts["one_stop"] > 0 and not include_unstarred and tier_counts.get("one_stop_approved", 0) == 0:
                    extra_hint = " One-Stop-Shop coverage exists under **Unstarred (No *)**."
                st.info(
                    f"No strict `(*)` approved stations shown for **{active_country}** ({', '.join(active_makers) if active_makers else 'All Makers'}).{extra_hint}"
                )
                qa_buttons = []
                if not include_unstarred and tier_counts["unstarred"] > 0:
                    qa_buttons.append(("unstarred", f"🟡 Show {tier_counts['unstarred']} Unstarred Station(s)", _enable_unstarred_only))
                if not include_other and tier_counts["other"] > 0:
                    qa_buttons.append(("other", f"🔧 Show {tier_counts['other']} Other Station(s) in {active_country}", _enable_other_stations))
                if one_stop_only:
                    qa_buttons.append(("disable_os", "🏆 Show Partial-Coverage Stations Too", _disable_one_stop_only))
                if qa_buttons:
                    qa_cols = st.columns(len(qa_buttons))
                    for col_box, (b_key, b_lbl, b_cb) in zip(qa_cols, qa_buttons):
                        with col_box:
                            st.button(b_lbl, key=f"empty_qa_{b_key}", on_click=b_cb, use_container_width=True)

            if not neighbor_df.empty:
                neighbor_label = f"🌍 Regional Backup Hubs ({len(neighbor_df)} in {', '.join(c.upper() for c in neighbor_country_list[:5])})"
                with st.expander(neighbor_label, expanded=primary_df.empty):
                    nb_c1, nb_c2, nb_c3 = st.columns([2.8, 0.85, 0.9], gap="small")
                    with nb_c1:
                        st.caption("Backup stations in neighboring countries.")
                    with nb_c2:
                        st.button("☑️ All", key="btn_nb_sel_all", on_click=_set_neighbor_sel_mode, args=("all",), use_container_width=True)
                    with nb_c3:
                        st.button("☐ None", key="btn_nb_sel_none", on_click=_set_neighbor_sel_mode, args=("none",), use_container_width=True)

                    nb_default = [False] * len(neighbor_df) if st.session_state.neighbor_sel_mode == "none" else [True] * len(neighbor_df)
                    neighbor_for_editor = neighbor_df.copy()
                    neighbor_for_editor.insert(0, "Select", nb_default)
                    disabled_neighbor_cols = [c for c in neighbor_for_editor.columns if c != "Select"]
                    edited_neighbor_df = st.data_editor(
                        neighbor_for_editor,
                        use_container_width=True,
                        hide_index=True,
                        disabled=disabled_neighbor_cols,
                        column_config={
                            "Select": st.column_config.CheckboxColumn(
                                "Select",
                                help="Checked regional stations are included when Regional Backup is enabled in Dispatch.",
                                default=True,
                            )
                        },
                        key=f"neighbor_stations_editor_{filter_sig}_{st.session_state.neighbor_sel_ver}",
                    )
                    nb_mask = edited_neighbor_df["Select"].fillna(False).astype(bool)
                    selected_neighbor_df = edited_neighbor_df[nb_mask].drop(
                        columns=["Select"], errors="ignore"
                    ).reset_index(drop=True)
                    st.caption(f"Selected **{len(selected_neighbor_df)}** of **{len(neighbor_df)}** regional hub(s).")

        # LIVE RFQ GENERATION & SYNC (SURVIVES COPY/EDIT MODE SWITCHES)
        rfq_target_df = selected_primary_df if not selected_primary_df.empty else selected_neighbor_df
        rfq_default_text = generate_bracketed_rfq_template(st.session_state.parsed_data, rfq_target_df)
        rfq_default_hash = hashlib.md5(rfq_default_text.encode("utf-8")).hexdigest()[:12]
        if not st.session_state.rfq_saved_text or st.session_state._last_rfq_default_hash != rfq_default_hash:
            st.session_state.rfq_saved_text = rfq_default_text
            st.session_state._last_rfq_default_hash = rfq_default_hash
            if "rfq_editor_widget" in st.session_state:
                st.session_state.rfq_editor_widget = rfq_default_text

        with tab_dispatch:
            # 1) OUTLOOK RECIPIENTS BLOCK
            st.markdown("##### 📧 1. Outlook Recipients (`To / Bcc`)")
            if not neighbor_df.empty:
                default_scope_idx = 1 if (selected_primary_df.empty and not selected_neighbor_df.empty) else 0
                scope_choice = st.radio(
                    "Stations to include",
                    options=[
                        "Selected Primary Country Stations Only",
                        "Selected Primary + Selected Regional Backup Stations",
                    ],
                    index=default_scope_idx,
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"outlook_scope_radio_{rc}",
                )
                pool_df = (
                    selected_primary_df
                    if scope_choice == "Selected Primary Country Stations Only"
                    else pd.concat([selected_primary_df, selected_neighbor_df], ignore_index=True)
                )
            else:
                pool_df = selected_primary_df

            extracted_emails, station_email_rows = extract_outlook_emails(pool_df)
            missing_email_count = sum(1 for r in station_email_rows if r.get("Extracted Emails") == "No email in directory row")

            st.caption(
                f"**{len(pool_df)}** selected station(s) • **{len(extracted_emails)}** unique email(s) ready"
                + (f" • ⚠️ **{missing_email_count}** missing email in sheet" if missing_email_count > 0 else "")
            )

            if extracted_emails:
                st.code("; ".join(extracted_emails), language="text")
            else:
                st.info("No `@` email addresses found in the currently selected rows.")

            if station_email_rows:
                with st.expander(f"📋 Station Email Roster & Gmail Format ({len(station_email_rows)} stations)", expanded=missing_email_count > 0 and not extracted_emails):
                    if extracted_emails:
                        st.caption("Comma-separated (Gmail / Webmail):")
                        st.code(", ".join(extracted_emails), language="text")
                    roster_df = pd.DataFrame(station_email_rows)
                    st.dataframe(roster_df, use_container_width=True, hide_index=True)
                    clean_v_fn = re.sub(r"[^A-Za-z0-9]+", "_", v_disp).strip("_") or "Vessel"
                    st.download_button(
                        "⬇️ Download Roster (.csv)",
                        data=roster_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"Stations_{clean_v_fn}.csv",
                        mime="text/csv",
                    )

            st.divider()

            # 2) OUTBOUND RFQ TEMPLATE (CLEAN COPY vs EDIT TOGGLE — NO DUPLICATE BOXES)
            hdr_l, hdr_r = st.columns([1.8, 1.2])
            with hdr_l:
                st.markdown("##### 📝 2. Outbound RFQ Message")
            with hdr_r:
                rfq_view_mode = st.radio(
                    "RFQ mode",
                    options=["📋 Copy Ready", "✏️ Edit Message"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"rfq_view_mode_{rc}",
                )

            if rfq_view_mode == "✏️ Edit Message":
                if "rfq_editor_widget" not in st.session_state:
                    st.session_state.rfq_editor_widget = st.session_state.rfq_saved_text
                st.text_area(
                    "Edit RFQ message",
                    height=330,
                    label_visibility="collapsed",
                    key="rfq_editor_widget",
                    on_change=_save_rfq_widget_edit,
                )
                active_rfq_text = st.session_state.rfq_saved_text
            else:
                active_rfq_text = st.session_state.rfq_saved_text
                rfq_subj, _ = _split_rfq_subject_body(active_rfq_text)
                st.caption("Subject line (click copy icon on right):")
                st.code(rfq_subj, language="text")
                st.caption("Full RFQ message (click copy icon on right):")
                st.code(active_rfq_text, language="text")

            mailto_url, mailto_has_body = build_mailto_href(extracted_emails, active_rfq_text)
            clean_v_fn = re.sub(r"[^A-Za-z0-9]+", "_", v_disp).strip("_") or "Vessel"
            clean_p_fn = re.sub(r"[^A-Za-z0-9]+", "_", p_disp).strip("_") or "Port"
            is_customized = active_rfq_text != rfq_default_text

            act_a, act_b, act_c = st.columns([1.2, 1.1, 1.0], gap="small")
            with act_a:
                st.link_button(
                    "📬 Open in Email App",
                    url=mailto_url,
                    use_container_width=True,
                    help="Opens Outlook / default email app with Bcc & Subject" + (" + Body" if mailto_has_body else " (paste body from above)"),
                )
            with act_b:
                st.download_button(
                    "⬇️ Download (.txt)",
                    data=active_rfq_text.encode("utf-8"),
                    file_name=f"RFQ_{clean_v_fn}_{clean_p_fn}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            with act_c:
                st.button(
                    "↺ Reset Template",
                    key="btn_reset_rfq_tpl",
                    on_click=_reset_rfq_editor,
                    args=(rfq_default_text, rfq_default_hash),
                    disabled=not is_customized,
                    use_container_width=True,
                )


# ---------------------------------------------------------------------------
# STICKY RIGHT-SIDE AI COPILOT PANEL
# ---------------------------------------------------------------------------
if st.session_state.show_copilot and col_copilot is not None:
    with col_copilot:
        st.markdown('<div class="copilot-panel-marker"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            top_c1, top_c2 = st.columns([3.0, 1.2])
            with top_c1:
                st.markdown("""
                <div class="ot-copilot-header" style="margin-bottom:0.35rem;">
                    <div class="ot-copilot-title">🧭 Onetech AI Copilot</div>
                    <div class="ot-copilot-sub">RFQ &amp; Maker-Approval Assistant</div>
                </div>
                """, unsafe_allow_html=True)
            with top_c2:
                st.button(
                    "✖ Close",
                    on_click=_close_copilot,
                    key="close_copilot_header_btn",
                    help="Hide panel (chat history is kept)",
                    use_container_width=True,
                )

            qp_c1, qp_c2 = st.columns(2)
            quick_prompt = None
            with qp_c1:
                if st.button("🔍 Audit RFQ", use_container_width=True, help="Audit missing details, port discrepancies, and survey risks"):
                    quick_prompt = "Audit this RFQ for missing technical particulars, port discrepancies, and survey risks."
                if st.button("⭐ Verify * Makers", use_container_width=True, help="Verify strict '*' Maker Approval and One-Stop-Shop coverage"):
                    quick_prompt = "Which matched stations hold strict '*' Maker Approval or One-Stop-Shop coverage for the requested equipment?"
            with qp_c2:
                if st.button("✉️ Urgent Chaser", use_container_width=True, help="Draft a short follow-up chaser email"):
                    quick_prompt = "Draft a short, urgent follow-up chaser email with bracketed [...] placeholders to the matched stations."
                if st.button("🧹 Clear Chat", use_container_width=True):
                    st.session_state.copilot_messages = [
                        {"role": "assistant", "content": "Chat history cleared. How can I help with this attendance?"}
                    ]
                    st.rerun()

            chat_box = st.container(height=390)
            with chat_box:
                for msg in st.session_state.copilot_messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            user_chat_input = st.chat_input("Ask about stations, makers, or RFQ...")
            active_prompt = quick_prompt or user_chat_input

            if active_prompt:
                prior_history = list(st.session_state.copilot_messages)
                st.session_state.copilot_messages.append({"role": "user", "content": active_prompt})
                with chat_box:
                    with st.chat_message("user"):
                        st.markdown(active_prompt)
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            reply_text = generate_copilot_reply(
                                active_prompt,
                                st.session_state.parsed_data,
                                selected_primary_df if not selected_primary_df.empty else primary_df,
                                selected_neighbor_df if not selected_neighbor_df.empty else neighbor_df,
                                st.session_state.raw_inquiry_text,
                                selected_engine,
                                chat_history=prior_history,
                            )
                            st.markdown(reply_text)
                st.session_state.copilot_messages.append({"role": "assistant", "content": reply_text})
                st.rerun()
