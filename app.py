import streamlit as st
import pandas as pd
import sqlite3
import json
from PIL import Image
import google.generativeai as genai

# --- Configurazione Database Locale ---
conn = sqlite3.connect("nutrition_planner.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS dispensa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    categoria TEXT,
    kj REAL,
    kcal REAL,
    grassi REAL,
    saturi REAL,
    carboidrati REAL,
    zuccheri REAL,
    fibre REAL,
    proteine REAL,
    sale REAL
)
''')
conn.commit()

# --- Configurazione Pagina ---
st.set_page_config(page_title="Diet Planner", layout="wide")
st.title("🥗 Piano Nutrizionale & Dispensa Smart")

# Recupero chiave da Secrets o da input
api_key_secret = st.secrets.get("GEMINI_API_KEY", "")

tab_dispensa, tab_piano, tab_obiettivi = st.tabs(["📦 Dispensa", "📅 Piano Settimanale", "🎯 Obiettivi"])

# ----------------------------------------------------
# TAB 1: DISPENSA & INSERIMENTO SMART
# ----------------------------------------------------
with tab_dispensa:
    st.subheader("Aggiungi Alimento alla Dispensa")
    col_upload, col_manual = st.columns([1, 1])
    
    with col_upload:
        st.markdown("**Caricamento Automatico (Immagine o Link)**")
        api_key = api_key_secret if api_key_secret else st.text_input("Gemini API Key", type="password")
        uploaded_img = st.file_uploader("Carica foto etichetta", type=["png", "jpg", "jpeg"])
        url_input = st.text_input("Oppure incolla il link della scheda prodotto")
        
        extracted_data = {}
        if st.button("Estrai Valori") and api_key and (uploaded_img or url_input):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                prompt = """
                Estrai i valori nutrizionali per 100g dall'immagine/testo fornito.
                Rispondi ESCLUSIVAMENTE con un JSON valido con questa struttura (usa numeri decimali con il punto):
                {
                  "nome": "Nome Alimento",
                  "kj": 0.0,
                  "kcal": 0.0,
                  "grassi": 0.0,
                  "saturi": 0.0,
                  "carboidrati": 0.0,
                  "zuccheri": 0.0,
                  "fibre": 0.0,
                  "proteine": 0.0,
                  "sale": 0.0
                }
                """
                if uploaded_img:
                    img = Image.open(uploaded_img)
                    response = model.generate_content([prompt, img])
                else:
                    response = model.generate_content([prompt, f"Link: {url_input}"])
                
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                extracted_data = json.loads(clean_text)
                st.success("Dati estratti con successo!")
            except Exception as e:
                st.error(f"Errore durante l'estrazione: {e}")

    with col_manual:
        st.markdown("**Verifica e Salva (Valori per 100 g)**")
        with st.form("form_alimento"):
            nome = st.text_input("Nome Alimento", value=extracted_data.get("nome", ""))
            categoria = st.selectbox("Categoria Dispensa", ["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"])
            
            c1, c2 = st.columns(2)
            kj = c1.number_input("Energia (kJ)", value=float(extracted_data.get("kj", 0.0)))
            kcal = c2.number_input("Energia (kcal)", value=float(extracted_data.get("kcal", 0.0)))
            
            c3, c4 = st.columns(2)
            grassi = c3.number_input("Grassi (g)", value=float(extracted_data.get("grassi", 0.0)))
            saturi = c4.number_input("di cui acidi grassi saturi (g)", value=float(extracted_data.get("saturi", 0.0)))
            
            c5, c6 = st.columns(2)
            carboidrati = c5.number_input("Carboidrati (g)", value=float(extracted_data.get("carboidrati", 0.0)))
            zuccheri = c6.number_input("di cui zuccheri (g)", value=float(extracted_data.get("zuccheri", 0.0)))
            
            c7, c8, c9 = st.columns(3)
            fibre = c7.number_input("Fibra alimentare (g)", value=float(extracted_data.get("fibre", 0.0)))
            proteine = c8.number_input("Proteine (g)", value=float(extracted_data.get("proteine", 0.0)))
            sale = c9.number_input("Sale (g)", value=float(extracted_data.get("sale", 0.0)))
            
            submit = st.form_submit_button("Salva in Dispensa")
            if submit and nome:
                cursor.execute('''
                INSERT INTO dispensa (nome, categoria, kj, kcal, grassi, saturi, carboidrati, zuccheri, fibre, proteine, sale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nome, categoria, kj, kcal, grassi, saturi, carboidrati, zuccheri, fibre, proteine, sale))
                conn.commit()
                st.success(f"{nome} aggiunto alla categoria {categoria}!")

    st.divider()
    cat_filter = st.radio("Filtra Dispensa:", ["TUTTE", "COLAZIONE", "PRANZO", "SPUNTINO", "CENA"], horizontal=True)
    query = "SELECT * FROM dispensa" if cat_filter == "TUTTE" else f"SELECT * FROM dispensa WHERE categoria = '{cat_filter}'"
    df_dispensa = pd.read_sql_query(query, conn)
    st.dataframe(df_dispensa, use_container_width=True)

# ----------------------------------------------------
# TAB 2: PIANO SETTIMANALE
# ----------------------------------------------------
with tab_piano:
    st.subheader("Griglia Settimanale Pasti")
    giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    pasti = ["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"]
    
    selected_day = st.selectbox("Seleziona Giorno", giorni)
    st.markdown(f"### Pasti di {selected_day}")
    
    cols = st.columns(4)
    for idx, pasto in enumerate(pasti):
        with cols[idx]:
            st.markdown(f"**{pasto}**")
            items = df_dispensa[df_dispensa['categoria'] == pasto]['nome'].tolist()
            st.multiselect(f"Aggiungi a {pasto}", items, key=f"{selected_day}_{pasto}")

# ----------------------------------------------------
# TAB 3: OBIETTIVI NUTRIZIONALI
# ----------------------------------------------------
with tab_obiettivi:
    st.subheader("Target Giornalieri")
    c_t1, c_t2, c_t3, c_t4 = st.columns(4)
    target_kcal = c_t1.number_input("Target Calorie (kcal)", value=2000)
    target_pro = c_t2.number_input("Target Proteine (g)", value=140)
    target_carb = c_t3.number_input("Target Carboidrati (g)", value=220)
    target_fat = c_t4.number_input("Target Grassi (g)", value=65)
