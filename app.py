import json
import sqlite3
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
from PIL import Image
import requests
import streamlit as st

# --- Configurazione Database Locale ---
conn = sqlite3.connect("nutrition_planner.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS dispensa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    categoria TEXT,
    quantita REAL DEFAULT 100.0,
    costo REAL DEFAULT 0.0,
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
# Migrazione dinamica colonne nel caso la tabella esista già
cursor.execute("PRAGMA table_info(dispensa)")
columns = [row[1] for row in cursor.fetchall()]
if "quantita" not in columns:
  cursor.execute("ALTER TABLE dispensa ADD COLUMN quantita REAL DEFAULT 100.0")
if "costo" not in columns:
  cursor.execute("ALTER TABLE dispensa ADD COLUMN costo REAL DEFAULT 0.0")
conn.commit()

# --- Configurazione Pagina ---
st.set_page_config(page_title="Diet Planner", layout="wide")
st.title("🥗 Piano Nutrizionale & Dispensa Smart")

# Buffer per inserimento / modifica alimento
default_values = {
    "edit_id": None,
    "nome": "",
    "categoria": "COLAZIONE",
    "quantita": 100.0,
    "costo": 0.0,
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

if "food_buffer" not in st.session_state:
  st.session_state["food_buffer"] = default_values.copy()

api_key_secret = st.secrets.get("GEMINI_API_KEY", "")

tab_dispensa, tab_piano, tab_obiettivi = st.tabs(
    ["📦 Dispensa", "📅 Piano Settimanale", "🎯 Obiettivi"]
)

# ----------------------------------------------------
# TAB 1: DISPENSA & INSERIMENTO SMART
# ----------------------------------------------------
with tab_dispensa:
  is_editing = st.session_state["food_buffer"]["edit_id"] is not None
  st.subheader(
      "✏️ Modifica Alimento" if is_editing else "Aggiungi Alimento alla Dispensa"
  )

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
      with st.spinner("Lettura dati ed estrazione con Gemini..."):
        try:
          genai.configure(api_key=api_key)
          candidate_models = [
              "gemini-3.7-flash",
              "gemini-2.0-flash",
              "gemini-1.5-flash",
          ]

          prompt = """
                    Estrai con precisione i valori nutrizionali medi per 100g dal contenuto fornito.
                    Rispondi SOLO ed ESCLUSIVAMENTE con un JSON valido con questa struttura (numeri decimali con punto, 0 se assenti):
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

          if uploaded_img:
            content = [prompt, Image.open(uploaded_img)]
          else:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
            }
            res = requests.get(url_input, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            for s in soup(["script", "style", "nav", "footer"]):
              s.decompose()
            page_text = " ".join(soup.stripped_strings)[:12000]
            content = [
                prompt,
                f"Testo estratto dalla pagina del prodotto:\n{page_text}",
            ]

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
