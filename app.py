import streamlit as st
import pandas as pd
import pypdf
import io
import re
import json
import os
import email
from email import policy
import extract_msg
from PIL import Image
import base64
from groq import Groq

try:
    from groq import APIStatusError, APIConnectionError, RateLimitError
except ImportError:  # older groq packages
    APIStatusError = Exception
    APIConnectionError = Exception
    RateLimitError = Exception

st.set_page_config(page_title="Onetech Service Station Router & Discrepancy Audit", layout="wide")
st.title("Onetech Marine Service Assistant & Discrepancy Audit")
st.markdown("Automated RFQ Parsing, Global Port Matching & Cross-Source Discrepancy Detection.")


def read_groq_api_key():
    """Read GROQ_API_KEY from Streamlit secrets, then from the environment."""
    raw = ""
    try:
        raw = st.secrets.get("GROQ_API_KEY", "") or ""
    except Exception:
        raw = ""
    if not raw:
        raw = os.environ.get("GROQ_API_KEY", "") or ""
    return str(raw).strip().strip('"').strip("'")


groq_api_key = read_groq_api_key()
# Official Groq client. urllib / requests are not used for the API call.
client = Groq(api_key=groq_api_key, timeout=60.0, max_retries=2) if groq_api_key else None

# Requested models first. Fallbacks run only if Groq reports the model decommissioned.
TEXT_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
]

VISION_MODELS = [
    "llama-3.2-11b-vision-preview",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen/qwen3.8-27b",
]

PORT_TO_COUNTRY = {
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
    "primorsk": "RUSSIA", "murmansk": "RUSSIA", "vladivostok": "RUSSIA",
    "nakhodka": "RUSSIA",

    # --- THAILAND ---
    "kohsichang": "THAILAND", "sichang": "THAILAND", "bangkok": "THAILAND",
    "laem chabang": "THAILAND", "map ta phut": "THAILAND", "songkhla": "THAILAND",
    "sriracha": "THAILAND", "phuket": "THAILAND",

    # --- BRAZIL ---
    "sao francisco do sul": "BRAZIL", "santos": "BRAZIL", "paranagua": "BRAZIL",
    "rio grande": "BRAZIL", "itajai": "BRAZIL", "imbituba": "BRAZIL",
    "tubarao": "BRAZIL", "vitoria": "BRAZIL", "suape": "BRAZIL",
    "rio de janeiro": "BRAZIL", "salvador": "BRAZIL", "manaus": "BRAZIL",
    "paranaagua": "BRAZIL", "pecem": "BRAZIL", "fortaleza": "BRAZIL",
    "itaqui": "BRAZIL", "belem": "BRAZIL", "macapa": "BRAZIL", "acú": "BRAZIL",

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

    # --- GREECE, CYPRUS & MALTA ---
    "piraeus": "GREECE", "thessaloniki": "GREECE", "eleusis": "GREECE",
    "perama": "GREECE", "agios theodoroi": "GREECE", "corinth": "GREECE",
    "patras": "GREECE", "volos": "GREECE", "heraklion": "GREECE",
    "syros": "GREECE", "rhodes": "GREECE", "lavrio": "GREECE",
    "megara": "GREECE", "astakos": "GREECE", "kavala": "GREECE",
    "chalkis": "GREECE", "alexandroupolis": "GREECE", "kalamata": "GREECE",
    "limassol": "CYPRUS", "larnaca": "CYPRUS", "vassiliko": "CYPRUS",
    "valletta": "MALTA", "marsaxlokk": "MALTA",

    # --- NETHERLANDS, BELGIUM, GERMANY, UK & NORTHERN EUROPE ---
    "rotterdam": "NETHERLANDS", "amsterdam": "NETHERLANDS", "vlissingen": "NETHERLANDS",
    "terneuzen": "NETHERLANDS", "ijmuiden": "NETHERLANDS", "moerdijk": "NETHERLANDS",
    "delfzijl": "NETHERLANDS", "eemshaven": "NETHERLANDS",
    "antwerp": "BELGIUM", "zeebrugge": "BELGIUM", "ghent": "BELGIUM",
    "ostend": "BELGIUM", "brussels": "BELGIUM",
    "hamburg": "GERMANY", "bremen": "GERMANY", "bremerhaven": "GERMANY",
    "wilhelmshaven": "GERMANY", "rostock": "GERMANY", "kiel": "GERMANY",
    "lubeck": "GERMANY", "emden": "GERMANY", "brunsbuttel": "GERMANY",
    "felixstowe": "UK", "southampton": "UK", "london": "UK",
    "liverpool": "UK", "immingham": "UK", "teesside": "UK",
    "milford haven": "UK", "grangemouth": "UK", "belfast": "UK",
    "aberdovey": "UK", "aberdeen": "UK", "hull": "UK", "dover": "UK",
    "dublin": "IRELAND", "cork": "IRELAND", "shannon": "IRELAND",
    "gdansk": "POLAND", "gdynia": "POLAND", "szczecin": "POLAND", "swinoujscie": "POLAND",
    "copenhagen": "DENMARK", "aarhus": "DENMARK", "esbjerg": "DENMARK",
    "skagen": "DENMARK", "fredericia": "DENMARK", "odense": "DENMARK",
    "gothenburg": "SWEDEN", "stockholm": "SWEDEN", "malmo": "SWEDEN",
    "helsingborg": "SWEDEN", "trelleborg": "SWEDEN",
    "oslo": "NORWAY", "bergen": "NORWAY", "stavanger": "NORWAY",
    "narvik": "NORWAY", "tromso": "NORWAY", "kristiansand": "NORWAY",
    "helsinki": "FINLAND", "kotka": "FINLAND", "turku": "FINLAND", "rauma": "FINLAND",
    "tallinn": "ESTONIA", "muuga": "ESTONIA",
    "riga": "LATVIA", "ventspils": "LATVIA", "liepaja": "LATVIA",
    "klaipeda": "LITHUANIA",

    # --- SPAIN, GIBRALTAR & PORTUGAL ---
    "algeciras": "SPAIN", "valencia": "SPAIN", "barcelona": "SPAIN",
    "las palmas": "SPAIN", "bilbao": "SPAIN", "cartagena": "SPAIN",
    "huelva": "SPAIN", "tarragona": "SPAIN", "malaga": "SPAIN",
    "vigo": "SPAIN", "cadiz": "SPAIN", "castellon": "SPAIN",
    "tenerife": "SPAIN", "gijon": "SPAIN", "santander": "SPAIN",
    "ferrol": "SPAIN", "almeria": "SPAIN", "sagunto": "SPAIN",
    "gibraltar": "GIBRALTAR",
    "lisbon": "PORTUGAL", "sines": "PORTUGAL", "leixoes": "PORTUGAL",
    "setubal": "PORTUGAL", "aveiro": "PORTUGAL", "funchal": "PORTUGAL",

    # --- ITALY, FRANCE & ADRIATIC ---
    "genoa": "ITALY", "augusta": "ITALY", "trieste": "ITALY",
    "venice": "ITALY", "ravenna": "ITALY", "livorno": "ITALY",
    "naples": "ITALY", "cagliari": "ITALY", "gioia tauro": "ITALY",
    "taranto": "ITALY", "savona": "ITALY", "la spezia": "ITALY",
    "civitavecchia": "ITALY", "bari": "ITALY", "brindisi": "ITALY",
    "ancona": "ITALY", "palermo": "ITALY", "messina": "ITALY", "milazzo": "ITALY",
    "marseilles": "FRANCE", "marseille": "FRANCE", "fos": "FRANCE",
    "le havre": "FRANCE", "dunkirk": "FRANCE", "fayard": "FRANCE",
    "bordeaux": "FRANCE", "st nazaire": "FRANCE", "nantes": "FRANCE",
    "rouen": "FRANCE", "brest": "FRANCE", "la pallice": "FRANCE", "sete": "FRANCE",
    "koper": "SLOVENIA",
    "rijeka": "CROATIA", "split": "CROATIA", "ploce": "CROATIA", "zadar": "CROATIA",
    "bar": "MONTENEGRO", "durres": "ALBANIA",

    # --- MIDDLE EAST & UAE ---
    "dubai": "UAE", "fujairah": "UAE", "jebel ali": "UAE",
    "khor fakkan": "UAE", "abu dhabi": "UAE", "sharjah": "UAE",
    "ras al khaimah": "UAE", "hamriyah": "UAE", "ruwais": "UAE",
    "sohar": "OMAN", "salalah": "OMAN", "muscat": "OMAN", "duqm": "OMAN",
    "dammam": "SAUDI ARABIA", "jeddah": "SAUDI ARABIA", "jubail": "SAUDI ARABIA",
    "yanbu": "SAUDI ARABIA", "ras tanura": "SAUDI ARABIA", "jizan": "SAUDI ARABIA",
    "doha": "QATAR", "ras laffan": "QATAR", "umesaid": "QATAR", "mesaieed": "QATAR", "hamad": "QATAR",
    "bahrain": "BAHRAIN", "mina sulman": "BAHRAIN", "khalifa bin salman": "BAHRAIN",
    "kuwait": "KUWAIT", "shuwaikh": "KUWAIT", "shuaiba": "KUWAIT", "mina al ahmadi": "KUWAIT",
    "bandar abbas": "IRAN", "khark island": "IRAN", "assaluyeh": "IRAN", "bandar imam khomeini": "IRAN",
    "basrah": "IRAQ", "um qasr": "IRAQ", "khor al zubair": "IRAQ",
    "aqaba": "JORDAN",
    "haifa": "ISRAEL", "ashdod": "ISRAEL", "ashkelon": "ISRAEL",
    "beirut": "LEBANON",
    "latakia": "SYRIA", "tartous": "SYRIA",
    "aden": "YEMEN", "hodeidah": "YEMEN",

    # --- AFRICA (NORTH, WEST, EAST, SOUTH) ---
    "casablanca": "MOROCCO", "tangier": "MOROCCO", "tanger med": "MOROCCO",
    "agadir": "MOROCCO", "jorf lasfar": "MOROCCO", "nador": "MOROCCO",
    "mohammedia": "MOROCCO", "safi": "MOROCCO",
    "algiers": "ALGERIA", "oran": "ALGERIA", "annaba": "ALGERIA",
    "arzew": "ALGERIA", "bejaia": "ALGERIA", "skikda": "ALGERIA",
    "alexandria": "EGYPT", "port said": "EGYPT", "suez": "EGYPT",
    "damietta": "EGYPT", "cairo": "EGYPT", "safaga": "EGYPT",
    "sokhna": "EGYPT", "ain sokhna": "EGYPT", "dekheila": "EGYPT",
    "tunis": "TUNISIA", "sfax": "TUNISIA", "bizerte": "TUNISIA",
    "la goulette": "TUNISIA", "rades": "TUNISIA", "gabes": "TUNISIA",
    "tripoli": "LIBYA", "benghazi": "LIBYA", "misurata": "LIBYA", "tobruk": "LIBYA",
    "lagos": "NIGERIA", "apapa": "NIGERIA", "tin can": "NIGERIA",
    "port harcourt": "NIGERIA", "onne": "NIGERIA", "lekki": "NIGERIA",
    "dakar": "SENEGAL",
    "abidjan": "IVORY COAST", "san pedro": "IVORY COAST",
    "accra": "GHANA", "tema": "GHANA", "takoradi": "GHANA",
    "lome": "TOGO", "cotonou": "BENIN", "douala": "CAMEROON", "kribi": "CAMEROON",
    "libreville": "GABON", "port gentil": "GABON",
    "pointe noire": "CONGO", "matadi": "DR CONGO",
    "luanda": "ANGOLA", "lobito": "ANGOLA", "cabinda": "ANGOLA",
    "walvis bay": "NAMIBIA",
    "durban": "SOUTH AFRICA", "cape town": "SOUTH AFRICA", "richards bay": "SOUTH AFRICA",
    "port elizabeth": "SOUTH AFRICA", "ngqura": "SOUTH AFRICA", "saldanha": "SOUTH AFRICA",
    "maputo": "MOZAMBIQUE", "beira": "MOZAMBIQUE", "nacala": "MOZAMBIQUE",
    "dar es salaam": "TANZANIA", "mombasa": "KENYA",
    "djibouti": "DJIBOUTI", "port sudan": "SUDAN",
    "port louis": "MAURITIUS", "toamasina": "MADAGASCAR",
    "conakry": "GUINEA", "freetown": "SIERRA LEONE", "monrovia": "LIBERIA",
    "nouakchott": "MAURITANIA", "nouadhibou": "MAURITANIA",

    # --- ASIA & FAR EAST ---
    "singapore": "SINGAPORE",
    "shanghai": "CHINA", "ningbo": "CHINA", "shenzhen": "CHINA",
    "guangzhou": "CHINA", "qingdao": "CHINA", "tianjin": "CHINA",
    "hong kong": "CHINA", "dalian": "CHINA", "xiamen": "CHINA",
    "rizhao": "CHINA", "yingkou": "CHINA", "zhoushan": "CHINA",
    "nantong": "CHINA", "jiangyin": "CHINA", "caofeidian": "CHINA",
    "qinhuangdao": "CHINA", "tangshan": "CHINA", "yantai": "CHINA",
    "fangcheng": "CHINA", "zhanjiang": "CHINA", "shekou": "CHINA", "yantian": "CHINA",
    "kaohsiung": "TAIWAN", "keelung": "TAIWAN", "taichung": "TAIWAN", "taipei": "TAIWAN",
    "busan": "SOUTH KOREA", "ulsan": "SOUTH KOREA", "incheon": "SOUTH KOREA",
    "yeosu": "SOUTH KOREA", "pohang": "SOUTH KOREA", "daesan": "SOUTH KOREA",
    "pyeongtaek": "SOUTH KOREA", "gwangyang": "SOUTH KOREA", "mokpo": "SOUTH KOREA",
    "tokyo": "JAPAN", "yokohama": "JAPAN", "nagoya": "JAPAN",
    "osaka": "JAPAN", "kobe": "JAPAN", "chiba": "JAPAN", "kitakyushu": "JAPAN",
    "kawasaki": "JAPAN", "mizushima": "JAPAN", "hakata": "JAPAN", "shimizu": "JAPAN",
    "port kelang": "MALAYSIA", "port klang": "MALAYSIA", "penang": "MALAYSIA",
    "pasir gudang": "MALAYSIA", "tanjung pelepas": "MALAYSIA",
    "miri": "MALAYSIA", "bintulu": "MALAYSIA", "kemaman": "MALAYSIA",
    "kuantan": "MALAYSIA", "labuan": "MALAYSIA", "kota kinabalu": "MALAYSIA",
    "jakarta": "INDONESIA", "surabaya": "INDONESIA", "belawan": "INDONESIA",
    "batam": "INDONESIA", "balikpapan": "INDONESIA", "semarang": "INDONESIA",
    "cigading": "INDONESIA", "merak": "INDONESIA", "dumai": "INDONESIA", "makassar": "INDONESIA",
    "manila": "PHILIPPINES", "cebu": "PHILIPPINES", "subic bay": "PHILIPPINES",
    "batangas": "PHILIPPINES", "davao": "PHILIPPINES", "cagayan de oro": "PHILIPPINES",
    "ho chi minh": "VIETNAM", "haiphong": "VIETNAM", "danang": "VIETNAM",
    "cai mep": "VIETNAM", "vung tau": "VIETNAM", "quy nhon": "VIETNAM", "cam pha": "VIETNAM",
    "sihanoukville": "CAMBODIA", "yangon": "MYANMAR", "muara": "BRUNEI",
    "mumbai": "INDIA", "chennai": "INDIA", "kolkata": "INDIA",
    "cochin": "INDIA", "visakhapatnam": "INDIA", "mormugao": "INDIA",
    "kandla": "INDIA", "mundra": "INDIA", "nhava sheva": "INDIA",
    "tuticorin": "INDIA", "haldia": "INDIA", "paradip": "INDIA",
    "new mangalore": "INDIA", "pipavav": "INDIA", "hazira": "INDIA", "kakinada": "INDIA",
    "colombo": "SRI LANKA", "galle": "SRI LANKA", "trincomalee": "SRI LANKA", "hambantota": "SRI LANKA",
    "karachi": "PAKISTAN", "port qasim": "PAKISTAN", "gwadar": "PAKISTAN",
    "chittagong": "BANGLADESH", "mongla": "BANGLADESH", "payra": "BANGLADESH",

    # --- AMERICAS & CARIBBEAN ---
    "houston": "USA", "new orleans": "USA", "new york": "USA",
    "los angeles": "USA", "long beach": "USA", "savannah": "USA",
    "miami": "USA", "baltimore": "USA", "seattle": "USA",
    "philadelphia": "USA", "charleston": "USA", "port arthur": "USA",
    "galveston": "USA", "corpus christi": "USA", "baton rouge": "USA",
    "norfolk": "USA", "mobile": "USA", "tampa": "USA", "jacksonville": "USA",
    "oakland": "USA", "portland": "USA", "tacoma": "USA", "beaumont": "USA",
    "lake charles": "USA", "freeport tx": "USA", "boston": "USA",
    "vancouver": "CANADA", "montreal": "CANADA", "halifax": "CANADA",
    "quebec": "CANADA", "prince rupert": "CANADA", "toronto": "CANADA",
    "saint john": "CANADA", "sept-iles": "CANADA", "hamilton": "CANADA",
    "veracruz": "MEXICO", "altamira": "MEXICO", "lazaro cardenas": "MEXICO",
    "tampico": "MEXICO", "coatzacoalcos": "MEXICO", "progreso": "MEXICO",
    "panama": "PANAMA", "balboa": "PANAMA", "cristobal": "PANAMA",
    "colon": "PANAMA", "manzanillo": "PANAMA",
    "buenos aires": "ARGENTINA", "rosario": "ARGENTINA", "bahia blanca": "ARGENTINA",
    "la plata": "ARGENTINA", "san lorenzo": "ARGENTINA", "san nicolas": "ARGENTINA",
    "campana": "ARGENTINA", "zarate": "ARGENTINA", "necochea": "ARGENTINA",
    "montevideo": "URUGUAY", "nueva palmira": "URUGUAY",
    "valparaiso": "CHILE", "san antonio": "CHILE", "antofagasta": "CHILE",
    "concepcion": "CHILE", "iquique": "CHILE", "talcahuano": "CHILE",
    "mejillones": "CHILE", "lirquen": "CHILE", "san vicente": "CHILE",
    "callao": "PERU", "paita": "PERU", "marcona": "PERU", "matarani": "PERU", "salaverry": "PERU",
    "guayaquil": "ECUADOR", "esmeraldas": "ECUADOR", "manta": "ECUADOR",
    "barranquilla": "COLOMBIA", "santa marta": "COLOMBIA", "buenaventura": "COLOMBIA",
    "puerto cabello": "VENEZUELA", "maracaibo": "VENEZUELA", "la guaira": "VENEZUELA", "jose": "VENEZUELA",
    "georgetown": "GUYANA", "paramaribo": "SURINAME",
    "point lisas": "TRINIDAD AND TOBAGO", "port of spain": "TRINIDAD AND TOBAGO",
    "kingston": "JAMAICA", "caucedo": "DOMINICAN REPUBLIC", "santo domingo": "DOMINICAN REPUBLIC",
    "freeport": "BAHAMAS", "san juan": "PUERTO RICO", "havana": "CUBA",

    # --- AUSTRALIA & OCEANIA ---
    "sydney": "AUSTRALIA", "melbourne": "AUSTRALIA", "brisbane": "AUSTRALIA",
    "fremantle": "AUSTRALIA", "newcastle": "AUSTRALIA", "port hedland": "AUSTRALIA",
    "adelaide": "AUSTRALIA", "darwin": "AUSTRALIA", "gladstone": "AUSTRALIA",
    "dampier": "AUSTRALIA", "port kembla": "AUSTRALIA", "geelong": "AUSTRALIA",
    "townsville": "AUSTRALIA", "hay point": "AUSTRALIA", "mackay": "AUSTRALIA",
    "auckland": "NEW ZEALAND", "wellington": "NEW ZEALAND", "lyttelton": "NEW ZEALAND",
    "tauranga": "NEW ZEALAND", "napier": "NEW ZEALAND",
}

# Comprehensive maritime neighboring/regional fallback map for all countries
NEIGHBORING_COUNTRIES = {
    # --- EUROPE & BLACK SEA / MEDITERRANEAN ---
    "romania": ["bulgaria", "turkey", "greece", "ukraine", "cyprus", "italy"],
    "bulgaria": ["romania", "turkey", "greece", "cyprus", "italy"],
    "ukraine": ["romania", "bulgaria", "turkey", "greece", "poland"],
    "georgia": ["turkey", "romania", "bulgaria", "greece"],
    "russia": ["turkey", "finland", "estonia", "latvia", "lithuania", "poland", "china", "south korea"],
    "turkey": ["greece", "bulgaria", "romania", "cyprus", "italy", "egypt"],
    "greece": ["turkey", "cyprus", "italy", "malta", "bulgaria", "romania", "egypt"],
    "cyprus": ["greece", "turkey", "egypt", "israel", "lebanon", "italy", "malta"],
    "malta": ["italy", "greece", "tunisia", "spain", "france", "cyprus"],
    "italy": ["greece", "france", "spain", "malta", "croatia", "slovenia", "turkey"],
    "slovenia": ["italy", "croatia", "greece", "malta"],
    "croatia": ["italy", "slovenia", "greece", "montenegro", "malta"],
    "montenegro": ["croatia", "italy", "greece", "albania"],
    "albania": ["greece", "italy", "montenegro", "croatia", "turkey"],
    "spain": ["portugal", "france", "italy", "gibraltar", "morocco", "uk", "netherlands"],
    "portugal": ["spain", "gibraltar", "france", "morocco", "uk", "netherlands"],
    "gibraltar": ["spain", "portugal", "morocco", "uk", "france", "italy"],
    "france": ["belgium", "netherlands", "uk", "spain", "italy", "germany"],
    "netherlands": ["belgium", "germany", "uk", "france", "denmark"],
    "belgium": ["netherlands", "france", "germany", "uk"],
    "germany": ["netherlands", "belgium", "denmark", "poland", "sweden", "uk", "france"],
    "uk": ["netherlands", "belgium", "france", "ireland", "germany", "denmark", "norway", "spain"],
    "ireland": ["uk", "netherlands", "belgium", "france", "spain"],
    "denmark": ["germany", "sweden", "norway", "netherlands", "poland", "uk"],
    "norway": ["sweden", "denmark", "germany", "netherlands", "uk", "finland"],
    "sweden": ["denmark", "norway", "finland", "germany", "poland", "estonia", "latvia", "lithuania", "netherlands"],
    "finland": ["sweden", "estonia", "latvia", "lithuania", "poland", "germany", "denmark", "norway"],
    "poland": ["germany", "lithuania", "latvia", "estonia", "sweden", "denmark", "netherlands"],
    "estonia": ["finland", "latvia", "lithuania", "sweden", "poland", "germany"],
    "latvia": ["lithuania", "estonia", "finland", "sweden", "poland", "germany"],
    "lithuania": ["latvia", "poland", "estonia", "sweden", "finland", "germany"],

    # --- MIDDLE EAST ---
    "uae": ["oman", "saudi arabia", "qatar", "bahrain", "kuwait", "india", "singapore"],
    "oman": ["uae", "saudi arabia", "qatar", "bahrain", "kuwait", "india"],
    "saudi arabia": ["uae", "bahrain", "qatar", "kuwait", "oman", "egypt", "jordan"],
    "qatar": ["uae", "bahrain", "saudi arabia", "kuwait", "oman"],
    "bahrain": ["saudi arabia", "qatar", "uae", "kuwait", "oman"],
    "kuwait": ["saudi arabia", "bahrain", "qatar", "uae", "iraq", "oman"],
    "iraq": ["kuwait", "uae", "saudi arabia", "bahrain", "qatar", "oman"],
    "iran": ["uae", "oman", "qatar", "bahrain", "kuwait", "turkey"],
    "jordan": ["egypt", "saudi arabia", "israel", "cyprus", "uae", "greece"],
    "israel": ["cyprus", "greece", "egypt", "turkey", "jordan", "italy"],
    "lebanon": ["cyprus", "turkey", "greece", "egypt", "israel"],
    "syria": ["turkey", "cyprus", "lebanon", "greece", "egypt"],
    "yemen": ["oman", "uae", "saudi arabia", "djibouti", "egypt"],

    # --- AFRICA ---
    "egypt": ["greece", "cyprus", "turkey", "saudi arabia", "israel", "jordan", "italy", "malta", "uae"],
    "morocco": ["spain", "portugal", "gibraltar", "algeria", "tunisia", "france"],
    "algeria": ["morocco", "tunisia", "spain", "france", "italy", "malta"],
    "tunisia": ["italy", "malta", "algeria", "morocco", "france", "greece", "spain"],
    "libya": ["malta", "italy", "tunisia", "egypt", "greece", "turkey"],
    "sudan": ["egypt", "saudi arabia", "djibouti", "uae"],
    "djibouti": ["uae", "oman", "saudi arabia", "egypt", "kenya"],
    "senegal": ["ivory coast", "ghana", "morocco", "spain", "nigeria"],
    "guinea": ["senegal", "ivory coast", "ghana", "sierra leone", "liberia"],
    "sierra leone": ["guinea", "liberia", "senegal", "ivory coast", "ghana"],
    "liberia": ["ivory coast", "ghana", "sierra leone", "guinea", "senegal"],
    "mauritania": ["senegal", "morocco", "spain", "portugal"],
    "ivory coast": ["ghana", "senegal", "nigeria", "togo", "benin", "cameroon", "south africa"],
    "ghana": ["ivory coast", "nigeria", "togo", "benin", "senegal", "cameroon", "south africa"],
    "togo": ["ghana", "benin", "nigeria", "ivory coast", "senegal"],
    "benin": ["nigeria", "togo", "ghana", "ivory coast", "cameroon"],
    "nigeria": ["ghana", "ivory coast", "benin", "togo", "cameroon", "senegal", "south africa"],
    "cameroon": ["nigeria", "ghana", "ivory coast", "gabon", "congo", "angola", "south africa"],
    "gabon": ["cameroon", "congo", "nigeria", "angola", "ivory coast", "south africa"],
    "congo": ["angola", "gabon", "cameroon", "dr congo", "south africa", "namibia"],
    "dr congo": ["congo", "angola", "gabon", "cameroon", "south africa", "namibia"],
    "angola": ["namibia", "south africa", "congo", "gabon", "cameroon", "nigeria"],
    "namibia": ["south africa", "angola", "congo"],
    "south africa": ["namibia", "mozambique", "angola", "mauritius", "kenya", "tanzania", "uae"],
    "mozambique": ["south africa", "tanzania", "kenya", "mauritius", "madagascar", "namibia"],
    "tanzania": ["kenya", "mozambique", "south africa", "mauritius", "uae"],
    "kenya": ["tanzania", "south africa", "mozambique", "djibouti", "uae"],
    "mauritius": ["south africa", "madagascar", "mozambique", "kenya", "uae", "singapore"],
    "madagascar": ["mauritius", "south africa", "mozambique", "tanzania", "kenya"],

    # --- ASIA & FAR EAST ---
    "singapore": ["malaysia", "indonesia", "thailand", "vietnam", "philippines", "china"],
    "malaysia": ["singapore", "thailand", "indonesia", "vietnam", "philippines", "china"],
    "thailand": ["singapore", "malaysia", "vietnam", "indonesia", "china", "philippines"],
    "indonesia": ["singapore", "malaysia", "australia", "philippines", "thailand", "vietnam"],
    "philippines": ["singapore", "taiwan", "china", "malaysia", "vietnam", "indonesia", "south korea", "japan"],
    "vietnam": ["singapore", "china", "thailand", "malaysia", "taiwan", "philippines"],
    "cambodia": ["thailand", "vietnam", "singapore", "malaysia"],
    "myanmar": ["thailand", "singapore", "malaysia", "india", "bangladesh"],
    "brunei": ["malaysia", "singapore", "indonesia", "philippines"],
    "china": ["south korea", "japan", "taiwan", "singapore", "vietnam", "philippines"],
    "taiwan": ["china", "south korea", "japan", "philippines", "singapore", "vietnam"],
    "south korea": ["china", "japan", "taiwan", "singapore"],
    "japan": ["south korea", "china", "taiwan", "singapore"],
    "india": ["sri lanka", "uae", "singapore", "pakistan", "bangladesh", "oman"],
    "sri lanka": ["india", "singapore", "malaysia", "uae"],
    "pakistan": ["uae", "oman", "india", "saudi arabia", "bahrain", "qatar"],
    "bangladesh": ["india", "sri lanka", "singapore", "malaysia", "thailand"],

    # --- AMERICAS & CARIBBEAN ---
    "usa": ["canada", "mexico", "panama", "bahamas", "colombia"],
    "canada": ["usa", "uk", "netherlands"],
    "mexico": ["usa", "panama", "colombia", "brazil"],
    "panama": ["colombia", "usa", "mexico", "costa rica", "ecuador", "brazil"],
    "colombia": ["panama", "ecuador", "peru", "brazil", "venezuela", "usa"],
    "venezuela": ["colombia", "panama", "trinidad and tobago", "brazil", "usa"],
    "guyana": ["trinidad and tobago", "suriname", "brazil", "panama", "colombia", "usa"],
    "suriname": ["guyana", "trinidad and tobago", "brazil", "panama", "colombia"],
    "ecuador": ["peru", "colombia", "panama", "chile"],
    "peru": ["chile", "ecuador", "colombia", "panama", "brazil"],
    "chile": ["peru", "argentina", "uruguay", "brazil", "ecuador", "panama"],
    "brazil": ["argentina", "uruguay", "chile", "colombia", "panama", "peru"],
    "argentina": ["uruguay", "brazil", "chile"],
    "uruguay": ["argentina", "brazil", "chile"],
    "trinidad and tobago": ["panama", "colombia", "usa", "brazil", "venezuela"],
    "jamaica": ["usa", "panama", "colombia", "dominican republic", "bahamas"],
    "dominican republic": ["usa", "puerto rico", "panama", "colombia", "jamaica"],
    "bahamas": ["usa", "panama", "jamaica", "dominican republic"],
    "puerto rico": ["usa", "dominican republic", "panama", "colombia"],
    "cuba": ["mexico", "panama", "jamaica", "dominican republic", "bahamas"],

    # --- AUSTRALIA & OCEANIA ---
    "australia": ["new zealand", "singapore", "indonesia", "malaysia"],
    "new zealand": ["australia", "singapore"],
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
for _country_key in NEIGHBORING_COUNTRIES.keys():
    COUNTRY_ALIASES[_country_key.lower()] = _country_key.upper()
    for _neigh in NEIGHBORING_COUNTRIES[_country_key]:
        COUNTRY_ALIASES[_neigh.lower()] = _neigh.upper()

COUNTRY_ALIASES.update({
    "uae": "UAE",
    "u.a.e.": "UAE",
    "united arab emirates": "UAE",
    "usa": "USA",
    "u.s.a.": "USA",
    "u.s.": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "uk": "UK",
    "u.k.": "UK",
    "united kingdom": "UK",
    "great britain": "UK",
    "england": "UK",
    "korea": "SOUTH KOREA",
    "south korea": "SOUTH KOREA",
    "republic of korea": "SOUTH KOREA",
    "hellas": "GREECE",
    "ελλάδα": "GREECE",
    "ελλαδα": "GREECE",
    "ρουμανία": "ROMANIA",
    "ρουμανια": "ROMANIA",
    "βουλγαρία": "BULGARIA",
    "βουλγαρια": "BULGARIA",
    "τούρκια": "TURKEY",
    "τουρκία": "TURKEY",
    "τουρκια": "TURKEY",
    "κύπρος": "CYPRUS",
    "κυπρος": "CYPRUS",
    "brasil": "BRAZIL",
    "türkiye": "TURKEY",
    "turkiye": "TURKEY",
    "holland": "NETHERLANDS",
    "the netherlands": "NETHERLANDS",
    "ksa": "SAUDI ARABIA",
    "kingdom of saudi arabia": "SAUDI ARABIA",
    "ivory coast": "IVORY COAST",
    "côte d'ivoire": "IVORY COAST",
    "cote d'ivoire": "IVORY COAST",
    "viet nam": "VIETNAM",
    "prc": "CHINA",
    "p.r.c.": "CHINA",
    "hong kong": "CHINA",
    "russian federation": "RUSSIA",
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
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def clean_vessel_name(raw_name):
    if not raw_name or str(raw_name).strip().lower() in {"not specified", "n/a", "none", "unknown", "null"}:
        return "Not specified"
    text = str(raw_name).strip().strip('"').strip("'")
    text = re.sub(r"(?i)^(m/v|m/t|mv|mt|vessel|ship)\s*[:\-]?\s*", "", text)
    text = re.sub(
        r"(?i)\b(will|at|eta|port|call|calling|arr|arriving|due|to|for|is|and|the|in|on|sailing)\b.*$",
        "",
        text,
    )
    text = re.sub(r"(?i)\btbn\b", " / ", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text).strip(" /-")
    parts = [p.strip(" /-") for p in text.split("/") if p.strip(" /-")]
    parts = parts[:2]
    cleaned_parts = []
    for part in parts:
        words = part.split()
        if len(words) > 3:
            words = words[:3]
        if words:
            cleaned_parts.append(" ".join(words))
    if not cleaned_parts:
        return "Not specified"
    return " / ".join(cleaned_parts).title()


def is_office_address_line(line):
    """True when a line is a Piraeus office / signature address, not a port call."""
    s = (line or "").strip()
    if not s:
        return False
    has_piraeus = re.search(r"(?i)piraeus|πειραι", s) is not None
    has_postal = re.search(r"\b18[0-9]\s*\d{2}\b", s) is not None
    has_contact = re.search(
        r"(?i)\b(tel|telephone|phone|fax|mobile|email|e-mail|web|website)\b|www\.|https?://|@",
        s,
    ) is not None
    has_greece = re.search(r"(?i)\b(greece|hellas)\b|ελλ[αά]δ", s) is not None
    has_company = re.search(r"(?i)\bonetech\b|one[\s\-]*tech|mega\s+shipping", s) is not None
    has_street = re.search(
        r"(?i)vasilikon\s*51|akti\s+moutsopoulou|akti\s+miaouli|akti\s+kondyli|akti\s+poseidonos",
        s,
    ) is not None
    operational = re.search(
        r"(?i)^\s*(port|λιμ[αά]νι|λιμανι)\b|\b(eta|etd|berth|calling|call at|arrival|arriving|anchorage|destination|port of|vessel)\b",
        s,
    ) is not None
    if operational and not has_street and not has_postal:
        return False
    if has_street:
        return True
    if has_piraeus and (has_postal or has_contact):
        return True
    if has_company and (has_piraeus or has_postal or has_contact or has_greece):
        return True
    if has_piraeus and has_greece and not operational and len(s) < 90:
        return True
    if has_postal and has_greece and has_piraeus:
        return True
    return False


def clean_signatures(text):
    """Drop OneTech / shipping-company Piraeus office addresses from inquiry text."""
    if not text:
        return ""
    cleaned = re.sub(r"(?i)vasilikon\s*51[^\n]*", " ", text)
    cleaned = re.sub(r"(?i)akti\s*(?:moutsopoulou|miaouli|kondyli|poseidonos)[^\n]*", " ", cleaned)
    cleaned = re.sub(r"(?i)piraeus\s*185\d\d\s*greece", " ", cleaned)
    cleaned = re.sub(r"(?i)18[0-9]\s*\d{2}\s*,?\s*piraeus\s*,?\s*greece", " ", cleaned)
    kept = []
    skip_bare_country = False
    for line in cleaned.splitlines():
        if is_office_address_line(line):
            skip_bare_country = True
            continue
        if skip_bare_country and re.fullmatch(
            r"(?i)\s*(greece|hellas|piraeus|πειραιάς|πειραιας|ελλάδα|ελλαδα)\s*\.?\s*",
            line,
        ):
            skip_bare_country = False
            continue
        skip_bare_country = False
        kept.append(line)
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _overlaps(span, spans):
    start, end = span
    for s, e in spans:
        if start < e and end > s:
            return True
    return False


def ports_in_text(text):
    """Return (start, end, port_key, country) for every known port, longest match first."""
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


def operational_port_context(text, port_key):
    if not text or not port_key:
        return False
    port = re.escape(port_key)
    pattern = (
        rf"(?i)(?:\b(?:port|calling|call|eta|etd|arrival|arriving|berth|anchorage|"
        rf"destination|alongside|bound)\b.{{0,70}}{port}|{port}.{{0,50}}"
        rf"\b(?:port|eta|etd|berth|anchorage|calling|arrival)\b|\bat\s+{port}\b)"
    )
    return re.search(pattern, text) is not None


def find_makers(text_lower, vessel_name=""):
    found = []
    vessel_lower = (vessel_name or "").lower()
    for maker in KNOWN_MAKERS:
        if not re.search(rf"(?<![a-z0-9]){re.escape(maker)}(?![a-z0-9])", text_lower or ""):
            continue
        if maker in vessel_lower:
            continue
        found.append(maker.upper())
    # Prefer the longer brand when both "sperry" and "sperry marine" hit.
    unique = []
    for maker in sorted(set(found), key=len, reverse=True):
        if any(maker != other and maker in other for other in unique):
            continue
        unique.append(maker)
    return unique


def as_str_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append("; ".join(f"{k}: {v}" for k, v in item.items()))
            elif item is not None and str(item).strip():
                out.append(str(item).strip())
        return out
    text = str(value).strip()
    return [text] if text else []


def specified(value):
    return bool(value) and str(value).strip().lower() not in {"not specified", "n/a", "none", "unknown", "null", ""}


def same_fact(a, b):
    return str(a or "").strip().lower() == str(b or "").strip().lower()


def choose_primary_port(text):
    found = ports_in_text(text)
    if not found:
        return "Not specified", "Not specified", []
    lower = (text or "").lower()
    scored = []
    for start, end, key, country in found:
        window = lower[max(0, start - 80):min(len(lower), end + 80)]
        score = 0
        for token, weight in (
            ("port", 3), ("eta", 3), ("calling", 3), ("berth", 2),
            ("arrival", 2), ("destination", 2), ("anchorage", 2), ("λιμ", 3),
        ):
            if token in window:
                score += weight
        if key == "piraeus" and score == 0 and not operational_port_context(text, "piraeus"):
            score = -5
        scored.append((score, start, key, country))
    scored.sort(key=lambda item: (-item[0], item[1]))
    _, _, key, country = scored[0]
    return key.title(), country, found


def extract_facts(text):
    """Local facts from one source. Does not apply manual override."""
    blob = text or ""
    port, country, ports = choose_primary_port(blob)
    if not specified(country):
        found_country = find_country(blob)
        if found_country:
            country = found_country
    vessel_name = "Not specified"
    vessel_match = re.search(
        r"(?i)(?:vessel|ship|πλο[ιί]ο|\bm/v\b|\bm/t\b|\bmv\b|\bmt\b)\s*[:\-]?\s*([A-Za-z0-9][^\n]{1,80})",
        blob,
    )
    if vessel_match:
        vessel_name = clean_vessel_name(vessel_match.group(1))
    eta = "Not specified"
    eta_match = re.search(r"(?i)\b(?:eta|etd|arrival)\b\s*[:=]?\s*([^\n]{3,60})", blob)
    if eta_match:
        eta = eta_match.group(1).strip()
    return {
        "vessel_name": vessel_name,
        "eta": eta,
        "port": port if specified(port) else "Not specified",
        "country": country if specified(country) else "Not specified",
        "makers": find_makers(blob.lower(), vessel_name),
        "ports_all": [(key, country_name) for _, _, key, country_name in ports],
    }


def parse_manual_inputs(manual_text):
    """Manual Override wins. Labeled fields beat free-text mentions."""
    overrides = {}
    explicit = set()
    if not manual_text or not str(manual_text).strip():
        return overrides, explicit
    text = str(manual_text)
    country_match = re.search(
        r"(?im)(?:^|\n)\s*(?:country|χώρα|χωρα)\s*[:=]\s*([^\n]+)",
        text,
    )
    if country_match:
        captured = country_match.group(1).strip()
        known = find_country(captured)
        overrides["country"] = known or captured.strip(" .,").upper()
        explicit.add("country")

    port_match = re.search(
        r"(?im)(?:^|\n)\s*(?:port|λιμ[αά]νι|λιμανι)\s*[:=]\s*([^\n]+)",
        text,
    )
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
        if overrides.get("port") and overrides.get("port") != "Not specified":
            explicit.add("port")

    vessel_match = re.search(
        r"(?im)(?:^|\n)\s*(?:vessel|ship|πλο[ιί]ο|πλοιο|m/v|m/t)\s*[:=]\s*([^\n]+)",
        text,
    )
    if vessel_match:
        overrides["vessel_name"] = clean_vessel_name(vessel_match.group(1))
        explicit.add("vessel_name")

    eta_match = re.search(r"(?im)(?:^|\n)\s*(?:eta|etd|arrival)\s*[:=]\s*([^\n]+)", text)
    if eta_match:
        overrides["eta"] = eta_match.group(1).strip()
        explicit.add("eta")

    maker_match = re.search(
        r"(?im)(?:^|\n)\s*(?:makers?|equipment|brand)\s*[:=]\s*([^\n]+)",
        text,
    )
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
            if len({key for _, _, key, _ in known_ports}) > 1:
                names = []
                for _, _, key, country_name in known_ports:
                    label = f"{key.title()} ({country_name})"
                    if label not in names:
                        names.append(label)
                overrides["_port_conflicts"] = names

    if "country" not in explicit:
        found_country = find_country(text)
        if found_country:
            overrides["country"] = found_country
            explicit.add("country")

    if "vessel_name" not in explicit:
        loose_vessel = re.search(
            r"(?i)\b(?:vessel|ship|πλο[ιί]ο|\bm/v\b|\bm/t\b|\bmv\b|\bmt\b)\b\s*[:\-]?\s*([A-Za-z0-9][^\n]{1,80})",
            text,
        )
        if loose_vessel:
            overrides["vessel_name"] = clean_vessel_name(loose_vessel.group(1))
            explicit.add("vessel_name")

    if "vessel_name" not in explicit:
        scope_hints = ("survey", "annual", "spare", "radio", "vdr", "attend", "service", "repair", "program", "eta", "maker")
        for line in text.splitlines():
            raw_line = line.strip()
            if not raw_line or ":" in raw_line or "=" in raw_line:
                continue
            if ports_in_text(raw_line) or find_country(raw_line):
                continue
            if re.search(r"(?i)" + "|".join(scope_hints), raw_line):
                continue
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9'./\- ]{1,40}", raw_line) and 1 <= len(raw_line.split()) <= 3:
                overrides["vessel_name"] = clean_vessel_name(raw_line)
                explicit.add("vessel_name")
                break

    if "country" not in explicit and overrides.get("_port_country"):
        overrides["country"] = overrides["_port_country"]

    return overrides, explicit


def normalize_result(data):
    if not isinstance(data, dict):
        return None
    result = dict(RESULT_DEFAULTS)
    result["makers"] = []
    result["discrepancies"] = []
    result["missing_critical_data"] = []
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
    result["discrepancies"] = as_str_list(result.get("discrepancies"))
    result["missing_critical_data"] = as_str_list(result.get("missing_critical_data"))
    result["vessel_name"] = clean_vessel_name(result.get("vessel_name"))
    for field in ("eta", "port", "country", "scope", "spares_requested"):
        if not specified(result.get(field)):
            result[field] = "Not specified" if field in {"eta", "port", "country"} else RESULT_DEFAULTS[field]
        else:
            result[field] = str(result[field]).strip()
    if specified(result.get("country")):
        raw_c = str(result["country"]).strip()
        canonical_c = find_country(raw_c)
        result["country"] = canonical_c if canonical_c else raw_c.upper()
    if not specified(result.get("country")) and specified(result.get("port")):
        p_key = str(result["port"]).strip().lower()
        if p_key in PORT_TO_COUNTRY:
            result["country"] = PORT_TO_COUNTRY[p_key]
    return result


def dedupe_keep_order(items):
    seen = set()
    out = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        marker = text.lower()
        if marker in seen:
            continue
        seen.add(marker)
        out.append(text)
    return out


def smart_local_parser(manual_override_text, files_text):
    cleaned_files = clean_signatures(files_text)
    file_facts = extract_facts(cleaned_files)
    text_lower = (cleaned_files or "").lower()
    scope_text = "Standard technical attendance inquiry."
    if "annual" in text_lower:
        scope_text = "Annual Radio / VDR / Navigation Survey"
    elif "re-programming" in text_lower or "reprogramming" in text_lower:
        scope_text = "Re-programming of Radio and Navigation Equipment"
    elif "spare" in text_lower:
        scope_text = "Spare parts supply"
    result = {
        "vessel_name": file_facts["vessel_name"],
        "eta": file_facts["eta"],
        "port": file_facts["port"],
        "country": file_facts["country"],
        "makers": file_facts["makers"],
        "scope": scope_text,
        "spares_requested": "Inquired per inquiry",
        "discrepancies": [],
        "missing_critical_data": [],
    }
    if len({key for key, _ in file_facts["ports_all"]}) > 1:
        names = [f"{key.title()} ({country})" for key, country in file_facts["ports_all"]]
        result["discrepancies"].append(
            "Documents mention more than one port: " + ", ".join(dict.fromkeys(names)) + "."
        )
    return normalize_result(result)


def build_prompt(manual_override_text, cleaned_files, image_count):
    inquiry = cleaned_files or ""
    truncated = False
    if len(inquiry) > 12000:
        inquiry = inquiry[:12000]
        truncated = True
    photo_line = (
        f"{image_count} photograph(s) are attached. Read them as a third source and compare them with the manual override and the inquiry text."
        if image_count
        else "No photographs were attached."
    )
    truncation_line = "The inquiry text was truncated for length.\n" if truncated else ""
    return f"""You are an expert maritime technical coordinator. Parse the commercial RFQ and extract facts into JSON.

CRITICAL INSTRUCTIONS:
1. MANUAL OVERRIDE IS ABSOLUTE GROUND TRUTH. If a country, port, or vessel is stated there, use it unconditionally, even when documents or photographs disagree. Still record the disagreement inside "discrepancies".
2. DO NOT extract 'Piraeus' or 'Greece' when it comes from a company footer or office address (OneTech, Mega Shipping, Vasilikon 51, Akti Miaouli, Akti Moutsopoulou, postal codes 185xx, telephone/email signature blocks). Those are not the service port.
3. A real port call at Piraeus (ETA, berth, "calling at", "port:") must still be kept.
4. If an inquiry states 'MV KIRRIBILLI TBN SEA GRACE', the vessel name is 'Kirribilli / Sea Grace'.
5. Cross-check MANUAL OVERRIDE vs INQUIRY TEXT vs PHOTOGRAPHS. List every conflicting port, country, vessel, ETA, or maker in "discrepancies", naming the source of each fact.
6. Office addresses must never become the service port.
{truncation_line}{photo_line}

MANUAL OVERRIDE (ground truth):
\"\"\"{manual_override_text or ""}\"\"\"

INQUIRY TEXT (office addresses already stripped where detected):
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


def image_to_data_url(uploaded_file):
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    raw = uploaded_file.read()
    name = (uploaded_file.name or "").lower()
    mime = "image/jpeg"
    if name.endswith(".png"):
        mime = "image/png"
    elif name.endswith(".webp"):
        mime = "image/webp"
    elif name.endswith(".gif"):
        mime = "image/gif"
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        encoded = base64.b64encode(raw).decode("utf-8")
        return f"data:{mime};base64,{encoded}"


def build_messages(prompt_text, data_urls):
    system = (
        "You extract maritime RFQ facts. Manual override beats documents and photos. "
        "Never treat a Piraeus office address or email signature as the service port. "
        "Reply with JSON only."
    )
    if not data_urls:
        user_content = prompt_text
    else:
        user_content = [{"type": "text", "text": prompt_text}]
        for url in data_urls:
            user_content.append({"type": "image_url", "image_url": {"url": url}})
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def error_text(exc):
    body = getattr(exc, "body", None)
    if isinstance(body, (dict, list)):
        try:
            return json.dumps(body)
        except Exception:
            return str(body)
    if body:
        return str(body)
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            return response.text
        except Exception:
            pass
    return str(exc)


def is_model_unavailable(exc):
    text = error_text(exc).lower()
    markers = (
        "model_decommissioned",
        "decommissioned",
        "model_not_found",
        "does not exist",
        "unknown model",
        "invalid model",
        "no such model",
        "not found",
        "unsupported model",
    )
    status = getattr(exc, "status_code", None)
    if status == 404 and "model" in text:
        return True
    return any(marker in text for marker in markers)


def is_json_mode_unsupported(exc):
    text = error_text(exc).lower()
    return "response_format" in text or "json_object" in text or "json mode" in text


def is_auth_error(exc):
    status = getattr(exc, "status_code", None)
    text = error_text(exc).lower()
    return status in {401, 403} or "invalid api key" in text or "invalid_api_key" in text


def is_vision_rejected(exc):
    text = error_text(exc).lower()
    return "image" in text and any(token in text for token in ("not support", "unsupported", "invalid", "cannot"))


def create_completion(model, messages, json_mode):
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        return client.chat.completions.create(**kwargs, max_completion_tokens=2048)
    except TypeError:
        return client.chat.completions.create(**kwargs, max_tokens=2048)


def groq_parse(messages, models):
    """Try each model. Returns (result_dict_or_None, model_used_or_None, error_or_None, notes)."""
    last_error = None
    notes = []
    for model in models:
        skip_model = False
        for json_mode in (True, False):
            try:
                completion = create_completion(model, messages, json_mode)
                content = ""
                if completion and completion.choices:
                    content = completion.choices[0].message.content or ""
                parsed = normalize_result(parse_model_json(content))
                if not parsed:
                    raise ValueError("Model returned JSON that was not an object.")
                if model != models[0]:
                    notes.append(f"Requested model '{models[0]}' was unavailable. Connected with '{model}'.")
                return parsed, model, None, notes
            except (APIStatusError, APIConnectionError, RateLimitError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if is_auth_error(exc):
                    return None, None, exc, notes
                if is_model_unavailable(exc) or is_vision_rejected(exc):
                    skip_model = True
                    break
                if json_mode and (is_json_mode_unsupported(exc) or isinstance(exc, (ValueError, json.JSONDecodeError))):
                    continue
                if json_mode:
                    continue
                skip_model = True
                break
            except Exception as exc:
                last_error = exc
                if is_auth_error(exc) or is_model_unavailable(exc) or is_vision_rejected(exc):
                    if is_auth_error(exc):
                        return None, None, exc, notes
                    skip_model = True
                    break
                if json_mode:
                    continue
                skip_model = True
                break
        if skip_model:
            continue
    return None, None, last_error, notes


def reject_office_piraeus(result, cleaned_files, manual_text):
    port = str(result.get("port") or "")
    if not re.search(r"(?i)piraeus|πειραι", port):
        return
    manual_claims_piraeus = bool(re.search(r"(?i)piraeus|πειραι", manual_text or ""))
    if manual_claims_piraeus:
        return
    if operational_port_context(cleaned_files or "", "piraeus"):
        return
    if re.search(r"(?<![a-z0-9])piraeus(?![a-z0-9])", (cleaned_files or "").lower()):
        if operational_port_context(cleaned_files, "piraeus"):
            return
    result["port"] = "Not specified"
    other_greek = [
        key for key, country in PORT_TO_COUNTRY.items()
        if country == "GREECE" and key != "piraeus" and re.search(
            rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])",
            (cleaned_files or "").lower(),
        )
    ]
    if str(result.get("country") or "").upper() == "GREECE" and not other_greek:
        result["country"] = "Not specified"
    result["discrepancies"].append(
        "Ignored Piraeus/Greece because it appears only as an office address (OneTech or a shipping-company signature), not as the service port."
    )


def apply_manual_override(result, manual_text):
    overrides, explicit = parse_manual_inputs(manual_text)
    notes = []
    if overrides.get("_port_conflicts"):
        notes.append(
            "Manual override mentions multiple ports: "
            + ", ".join(overrides["_port_conflicts"])
            + ". The first one was applied."
        )
    for key in ("country", "port", "vessel_name", "eta", "makers"):
        if key not in overrides or key not in explicit:
            continue
        new_value = overrides[key]
        previous = result.get(key)
        if key == "makers":
            prev_list = [str(m).upper() for m in (previous or [])]
            if prev_list and prev_list != new_value:
                notes.append(
                    f"Manual override makers '{', '.join(new_value)}' supersede '{', '.join(prev_list)}' extracted from attachments."
                )
            result["makers"] = new_value
            continue
        if specified(previous) and not same_fact(previous, new_value):
            blob = " ".join(result.get("discrepancies") or []).lower()
            if str(previous).lower() not in blob or str(new_value).lower() not in blob:
                label = {"country": "Country", "port": "Port", "vessel_name": "Vessel", "eta": "ETA"}[key]
                notes.append(
                    f"Manual override {label} '{new_value}' supersedes '{previous}' extracted from attachments."
                )
        result[key] = new_value
    if "country" in explicit and "port" in explicit and overrides.get("_port_country"):
        if not same_fact(overrides.get("country"), overrides.get("_port_country")):
            notes.append(
                f"Manual override country '{overrides['country']}' does not match the country of manual port "
                f"'{overrides['port']}' ({overrides['_port_country']}). Both manual values were kept; country drives station routing."
            )
    elif "port" in explicit and "country" not in explicit and overrides.get("_port_country"):
        result["country"] = overrides["_port_country"]
    result["discrepancies"] = dedupe_keep_order(list(result.get("discrepancies") or []) + notes)
    return result


def add_cross_source_audit(result, manual_text, cleaned_files):
    manual_facts, manual_explicit = parse_manual_inputs(manual_text)
    file_facts = extract_facts(cleaned_files)
    notes = list(result.get("discrepancies") or [])
    pairs = (
        ("port", "Port"),
        ("country", "Country"),
        ("vessel_name", "Vessel"),
    )
    for key, label in pairs:
        manual_value = manual_facts.get(key)
        file_value = file_facts.get(key)
        model_value = result.get(key)
        if key in manual_explicit and specified(manual_value) and specified(file_value) and not same_fact(manual_value, file_value):
            notes.append(
                f"{label} conflict: manual override says '{manual_value}', documents say '{file_value}'. Manual override applied."
            )
        if specified(model_value) and specified(file_value) and not same_fact(model_value, file_value):
            if not (key in manual_explicit and same_fact(model_value, manual_facts.get(key))):
                notes.append(
                    f"{label} conflict between model reading '{model_value}' and document text '{file_value}'."
                )
    file_ports = []
    for key, country in file_facts.get("ports_all") or []:
        label = f"{key.title()} ({country})"
        if label not in file_ports:
            file_ports.append(label)
    if len(file_ports) > 1:
        notes.append("Documents mention more than one port: " + ", ".join(file_ports) + ".")
    manual_makers = set(manual_facts.get("makers") or [])
    file_makers = set(file_facts.get("makers") or [])
    if manual_makers and file_makers and manual_makers != file_makers:
        notes.append(
            "Maker conflict: manual override says '"
            + ", ".join(sorted(manual_makers))
            + "', documents say '"
            + ", ".join(sorted(file_makers))
            + "'."
        )
    result["discrepancies"] = dedupe_keep_order(notes)
    missing = list(result.get("missing_critical_data") or [])
    if not specified(result.get("port")):
        missing.append("Service port was not identified.")
    if not specified(result.get("country")):
        missing.append("Service country was not identified.")
    if not specified(result.get("vessel_name")):
        missing.append("Vessel name was not identified.")
    result["missing_critical_data"] = dedupe_keep_order(missing)
    return result


def analyze_rfq(manual_override_text, files_text, image_files):
    cleaned_files = clean_signatures(files_text)
    res_json = None
    model_used = None
    image_files = image_files or []
    data_urls = [image_to_data_url(img) for img in image_files[:4]]
    photos_analyzed = False
    if len(image_files) > 4:
        st.info("Only the first 4 photographs were sent to Groq.")
    if client:
        prompt_text = build_prompt(manual_override_text, cleaned_files, len(data_urls))
        try:
            if data_urls:
                parsed, model_used, error, notes = groq_parse(
                    build_messages(prompt_text, data_urls),
                    VISION_MODELS,
                )
                if parsed:
                    photos_analyzed = True
                    res_json = parsed
                else:
                    if error is not None and is_auth_error(error):
                        st.error(f"Groq authentication failed: {error_text(error)}")
                    else:
                        st.warning(
                            "Vision model request failed"
                            + (f": {error_text(error)}" if error else "")
                            + ". Retrying with the text model on documents only."
                        )
                    text_parsed, model_used, text_error, text_notes = groq_parse(
                        build_messages(prompt_text, []),
                        TEXT_MODELS,
                    )
                    notes = list(notes or []) + list(text_notes or [])
                    if text_parsed:
                        res_json = text_parsed
                        res_json["discrepancies"] = dedupe_keep_order(
                            list(res_json.get("discrepancies") or [])
                            + ["Photographs could not be read by the vision model, so the photo discrepancy check was skipped."]
                            + notes
                        )
                    elif text_error is not None:
                        st.error(f"Groq API request failed: {error_text(text_error)}")
            else:
                parsed, model_used, error, notes = groq_parse(
                    build_messages(prompt_text, []),
                    TEXT_MODELS,
                )
                if parsed:
                    res_json = parsed
                    if notes:
                        res_json["discrepancies"] = dedupe_keep_order(list(res_json.get("discrepancies") or []) + notes)
                elif error is not None:
                    if is_auth_error(error):
                        st.error(f"Groq authentication failed: {error_text(error)}")
                    else:
                        st.warning(f"Groq API request failed: {error_text(error)}. Executing local rule engine.")
        except Exception as exc:
            st.warning(f"Groq API request failed: {exc}. Executing local rule engine.")
    else:
        st.info("GROQ_API_KEY not detected in secrets. Running local parser.")
    if not res_json:
        res_json = smart_local_parser(manual_override_text, files_text)
    res_json = normalize_result(res_json) or smart_local_parser(manual_override_text, files_text)
    reject_office_piraeus(res_json, cleaned_files, manual_override_text)
    if image_files and not photos_analyzed:
        res_json["discrepancies"] = dedupe_keep_order(
            list(res_json.get("discrepancies") or [])
            + ["Photographs were uploaded but were not analyzed, so no photo-based discrepancy check was possible."]
        )
        res_json["missing_critical_data"] = dedupe_keep_order(
            list(res_json.get("missing_critical_data") or [])
            + ["Photo evidence was not available to the model."]
        )
    add_cross_source_audit(res_json, manual_override_text, cleaned_files)
    # Absolute last step: typed country / port / vessel always beat files and photos.
    apply_manual_override(res_json, manual_override_text)
    res_json["_groq_model"] = model_used or ""
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

if client:
    st.sidebar.success("Groq API client ready (official SDK).")
else:
    st.sidebar.warning("GROQ_API_KEY missing. Local parser only.")

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
            model_used = parsed.pop("_groq_model", "") or ""
            st.markdown("---")
            st.subheader("2. RFQ Executive Brief")
            if model_used:
                st.caption(f"Groq model: {model_used}")
            elif client:
                st.caption("Groq did not return a result. Local rule engine was used.")
            else:
                st.caption("Local rule engine (no Groq API key).")

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

            missing = parsed.get("missing_critical_data") or []
            if missing:
                st.info("Missing critical data:")
                for item in missing:
                    st.write(f"- {item}")

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
                        if m in app_lower:
                            return True
                        tokens = m.split()
                        if tokens and len(tokens[0]) >= 3 and tokens[0] in app_lower:
                            return True
                    return False

                # 1. Έλεγχος στην κύρια χώρα μόνο για σταθμούς που υποστηρίζουν τον κατασκευαστή
                if not country_match.empty:
                    if target_makers:
                        filtered = country_match[country_match["Approved Makers"].apply(maker_filter)]
                        if not filtered.empty:
                            final_df = filtered
                    else:
                        final_df = country_match

                # 2. Αν δεν βρέθηκε ο κατασκευαστής στην κύρια χώρα, ψάχνουμε στις γειτονικές χώρες
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
                        matched_location_label = (
                            f"{', '.join(matched_neighbors)} "
                            f"(Neighboring Countries to {target_country.upper()})"
                        )

                makers_formatted = ', '.join([m.upper() for m in target_makers]) if target_makers else "ALL"
                if not final_df.empty:
                    if matched_location_label != target_country.upper():
                        st.info(
                            f"No approved station in **{target_country.upper()}** supports **{makers_formatted}**. "
                            f"Showing approved stations in neighboring countries:"
                        )
                    st.success(f"Matched stations in **{matched_location_label}** for makers: {makers_formatted}")
                    st.dataframe(final_df, use_container_width=True)
                else:
                    st.warning(
                        f"No approved stations found for **{makers_formatted}** in {target_country.upper()} "
                        f"or neighboring regions. Showing full directory:"
                    )
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning("Target country is not specified or no stations matched.")

            with st.expander("Show Parsed Raw Inputs"):
                st.write("**Manual Override Text:**")
                st.text(rfq_pasted_text)
                st.write("**Files Text (after Piraeus office-address removal):**")
                st.text(clean_signatures(files_combined_text))
