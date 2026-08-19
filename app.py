import json
import sqlite3
import google.generativeai as genai
import pandas as pd
from PIL import Image
import streamlit as st

# --- Inizializzazione Session State per i Campi del Form ---
default_nutri_values = {
    "nome": "",
    "categoria": "COLAZIONE",
    "kj": 0.0,
    "kcal": 0.0,
    "grassi": 0.0,
    "saturi": 0.0,
    "carboidrati": 0.0,
    "zuccheri": 0.0,
    "fibre": 0.0,
    "proteine": 0.0,
    "sale": 0.0,
}

for key, val in default_nutri_values.items():
  if key not in st.session_state:
    st.session_state[key] = val

# --- Configurazione Database Locale ---
conn = sqlite3.connect("nutrition_planner.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
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
"""
)
conn.commit()

# --- Configurazione Pagina ---
st.set_page_config(page_title="Diet Planner", layout="wide")
st.title("🥗 Piano Nutrizionale & Dispensa Smart")

api_key_secret = st.secrets.get("GEMINI_API_KEY", "")

tab_dispensa, tab_piano, tab_obiettivi = st.tabs(
    ["📦 Dispensa", "📅 Piano Settimanale", "🎯 Obiettivi"]
)

# ----------------------------------------------------
# TAB 1: DISPENSA & INSERIMENTO SMART
# ----------------------------------------------------
with tab_dispensa:
  st.subheader("Aggiungi Alimento alla Dispensa")
  col_upload, col_manual = st.columns([1, 1])

  with col_upload:
    st.markdown("**Caricamento Automatico (Immagine o Link)**")
    api_key = (
        api_key_secret
        if api_key_secret
        else st.text_input("Gemini API Key", type="password")
    )
    uploaded_img = st.file_uploader(
        "Carica foto etichetta", type=["png", "jpg", "jpeg"]
    )
    url_input = st.text_input("Oppure incolla il link della scheda prodotto")

    if st.button("Estrai Valori") and api_key and (uploaded_img or url_input):
      with st.spinner("Estrazione dati nutrizionali in corso..."):
        try:
          genai.configure(api_key=api_key)
          candidate_models = [
              "gemini-1.5-flash",
              "gemini-2.0-flash",
              "gemini-1.5-pro",
              "gemini-pro",
          ]

          prompt = """
                    Estrai i valori nutrizionali medi per 100g dall'input fornito.
                    Rispondi SOLO ed ESCLUSIVAMENTE con un JSON valido con questa struttura (numeri decimali con punto, zero se assenti):
                    {
                      "nome": "string",
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

          content = (
              [prompt, Image.open(uploaded_img)]
              if uploaded_img
              else [prompt, f"Link o testo prodotto: {url_input}"]
          )
          response = None
          last_err = None

          for model_name in candidate_models:
            try:
              model = genai.GenerativeModel(model_name)
              response = model.generate_content(content)
              if response and response.text:
                break
            except Exception as e:
              last_err = e
              continue

          if not response:
            raise last_err

          raw_text = (
              response.text.replace("```json", "").replace("
