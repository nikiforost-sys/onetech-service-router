import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Onetech Service Station Router", layout="wide")

st.title("Onetech Marine Service Assistant & Station Router")
st.markdown("Εισαγωγή RFQ πελάτη για έλεγχο πληρότητας και εντοπισμό εγκεκριμένου τεχνικού σταθμού.")

# 1. Σύνδεση με το Google Sheet μέσω ID
@st.cache_data(ttl=300)
def load_directory():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Χρήση του ID του Google Sheet για απόλυτη ακρίβεια
    sheet_id = "1h5fKvAE_dYfcitrSfSSl-qPptTA3OYlVqynunObK3Iw"
    sheet = client.open_by_key(sheet_id).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

try:
    df = load_directory()
    st.sidebar.success(f"Επιτυχής σύνδεση! Φορτώθηκαν {len(df)} εγγραφές σταθμών.")
except Exception as e:
    st.sidebar.error(f"Σφάλμα σύνδεσης: {e}")
    df = pd.DataFrame()

# 2. Πλαίσιο εισαγωγής RFQ
rfq_text = st.text_area("Επικολλήστε το RFQ του πελάτη παρακάτω:", height=200, placeholder="Customer inquiry text, vessel name, port, equipment details...")

if st.button("Ανάλυση RFQ & Εύρεση Σταθμού"):
    if not rfq_text.strip():
        st.warning("Παρακαλώ εισάγετε κείμενο RFQ για έλεγχο.")
    else:
        text_lower = rfq_text.lower()
        
        # Έλεγχος πληρότητας στοιχείων
        missing_items = []
        if not any(k in text_lower for k in ["eta", "etd", "arrival", "departure", "date"]):
            missing_items.append("Ημερομηνία άφιξης / αναχώρησης (ETA / ETD)")
        if not any(k in text_lower for k in ["agent", "agency", "husbandry", "contact"]):
            missing_items.append("Στοιχεία τοπικού πράκτορα (Agent details)")
        if not any(k in text_lower for k in ["maker", "model", "type", "s/n", "serial", "jrc", "furuno", "sperry", "yokogawa", "anschutz"]):
            missing_items.append("Μοντέλο, κατασκευαστής ή σειριακός αριθμός συσκευής")
        if not any(k in text_lower for k in ["fault", "alarm", "defect", "error", "issue", "apt", "annual", "survey", "problem"]):
            missing_items.append("Περιγραφή βλάβης, κωδικοί συναγερμού ή σκοπός επιθεώρησης (π.χ. APT)")

        st.markdown("### 1. Έλεγχος Στοιχείων RFQ")
        if missing_items:
            st.error("Ελλιπή στοιχεία στο αίτημα. Ενημερώστε τον πελάτη για τα εξής:")
            for item in missing_items:
                st.write(f"- **{item}**")
        else:
            st.success("Το αίτημα περιέχει όλες τις απαραίτητες τεχνικές πληροφορίες.")

        st.markdown("---")
        st.markdown("### 2. Προτεινόμενοι Σταθμοί Εξυπηρέτησης")

        if not df.empty:
            matched_indices = []
            for idx, row in df.iterrows():
                port_val = str(row.get("Port", "")).strip().lower()
                country_val = str(row.get("Country", "")).strip().lower()
                
                if (port_val and port_val in text_lower) or (country_val and country_val in text_lower):
                    matched_indices.append(idx)

            if matched_indices:
                results_df = df.loc[matched_indices]
                st.dataframe(results_df, use_container_width=True)
            else:
                st.info("Δεν εντοπίστηκε αυτόματα συγκεκριμένο λιμάνι ή χώρα στο RFQ. Δείτε παρακάτω ολόκληρο τον κατάλογο:")
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("Δεν υπάρχουν διαθέσιμα δεδομένα σταθμών.")
