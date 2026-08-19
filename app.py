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

          # Lista modelli con Gemini Flash in ordine di preferenza
          candidate_models = [
              "gemini-2.0-flash",
              "gemini-2.0-flash-exp",
              "gemini-1.5-flash",
              "gemini-3.7-flash",
              "gemini-1.5-flash-8b",
              "gemini-1.5-pro",
          ]

          prompt = """
                    Estrai i valori nutrizionali medi per 100g dall'input fornito.
                    Rispondi SOLO ed ESCLUSIVAMENTE con un JSON valido con questa struttura esatta (usa numeri decimali con il punto, 0 se assenti):
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
              response.text.replace("```json", "").replace("```", "").strip()
          )
          extracted = json.loads(raw_text)

          # Aggiorna lo stato con i valori estratti
          st.session_state["nome"] = str(extracted.get("nome", ""))
          st.session_state["kj"] = float(extracted.get("kj", 0.0))
          st.session_state["kcal"] = float(extracted.get("kcal", 0.0))
          st.session_state["grassi"] = float(extracted.get("grassi", 0.0))
          st.session_state["saturi"] = float(extracted.get("saturi", 0.0))
          st.session_state["carboidrati"] = float(
              extracted.get("carboidrati", 0.0)
          )
          st.session_state["zuccheri"] = float(extracted.get("zuccheri", 0.0))
          st.session_state["fibre"] = float(extracted.get("fibre", 0.0))
          st.session_state["proteine"] = float(extracted.get("proteine", 0.0))
          st.session_state["sale"] = float(extracted.get("sale", 0.0))

          st.success("Dati estratti! Verifica i campi a destra e salva.")
          st.rerun()
        except Exception as e:
          st.error(f"Errore durante l'estrazione: {e}")

  with col_manual:
    st.markdown("**Verifica e Salva (Valori per 100 g)**")

    nome = st.text_input("Nome Alimento", key="nome")
    categoria = st.selectbox(
        "Categoria Dispensa",
        ["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"],
        key="categoria",
    )

    c1, c2 = st.columns(2)
    kj = c1.number_input("Energia (kJ)", key="kj", step=0.1)
    kcal = c2.number_input("Energia (kcal)", key="kcal", step=0.1)

    c3, c4 = st.columns(2)
    grassi = c3.number_input("Grassi (g)", key="grassi", step=0.1)
    saturi = c4.number_input(
        "di cui acidi grassi saturi (g)", key="saturi", step=0.1
    )

    c5, c6 = st.columns(2)
    carboidrati = c5.number_input(
        "Carboidrati (g)", key="carboidrati", step=0.1
    )
    zuccheri = c6.number_input("di cui zuccheri (g)", key="zuccheri", step=0.1)

    c7, c8, c9 = st.columns(3)
    fibre = c7.number_input("Fibra alimentare (g)", key="fibre", step=0.1)
    proteine = c8.number_input("Proteine (g)", key="proteine", step=0.1)
    sale = c9.number_input("Sale (g)", key="sale", step=0.01)

    btn_col1, btn_col2 = st.columns([1, 1])

    with btn_col1:
      if st.button(
          "💾 Salva in Dispensa", type="primary", use_container_width=True
      ):
        if nome:
          cursor.execute(
              """
                        INSERT INTO dispensa (nome, categoria, kj, kcal, grassi, saturi, carboidrati, zuccheri, fibre, proteine, sale)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
              (
                  nome,
                  categoria,
                  kj,
                  kcal,
                  grassi,
                  saturi,
                  carboidrati,
                  zuccheri,
                  fibre,
                  proteine,
                  sale,
              ),
          )
          conn.commit()
          st.success(f"{nome} salvato con successo!")
          for k, v in default_nutri_values.items():
            st.session_state[k] = v
          st.rerun()
        else:
          st.warning("Inserisci il nome dell'alimento prima di salvare.")

    with btn_col2:
      if st.button("🧹 Svuota Campi", use_container_width=True):
        for k, v in default_nutri_values.items():
          st.session_state[k] = v
        st.rerun()

  st.divider()

  row_top = st.columns([3, 1])
  with row_top[0]:
    cat_filter = st.radio(
        "Filtra Dispensa:",
        ["TUTTE", "COLAZIONE", "PRANZO", "SPUNTINO", "CENA"],
        horizontal=True,
    )
  with row_top[1]:
    st.write("")
    with st.popover("🗑️ Elimina Tutti i Cibi"):
      st.error(
          "Sei sicuro di voler cancellare l'intera dispensa? Questa azione non"
          " si può annullare."
      )
      if st.button("Conferma Eliminazione Totale", type="primary"):
        cursor.execute("DELETE FROM dispensa")
        conn.commit()
        st.success("Tutti i dati della dispensa sono stati eliminati.")
        st.rerun()

  query = (
      "SELECT * FROM dispensa"
      if cat_filter == "TUTTE"
      else f"SELECT * FROM dispensa WHERE categoria = '{cat_filter}'"
  )
  df_dispensa = pd.read_sql_query(query, conn)
  st.dataframe(df_dispensa, use_container_width=True)

# ----------------------------------------------------
# TAB 2: PIANO SETTIMANALE
# ----------------------------------------------------
with tab_piano:
  st.subheader("Griglia Settimanale Pasti")
  giorni = [
      "Lunedì",
      "Martedì",
      "Mercoledì",
      "Giovedì",
      "Venerdì",
      "Sabato",
      "Domenica",
  ]
  pasti = ["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"]

  selected_day = st.selectbox("Seleziona Giorno", giorni)
  st.markdown(f"### Pasti di {selected_day}")

  cols = st.columns(4)
  for idx, pasto in enumerate(pasti):
    with cols[idx]:
      st.markdown(f"**{pasto}**")
      items = df_dispensa[df_dispensa["categoria"] == pasto]["nome"].tolist()
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
