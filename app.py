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
# Migrazione dinamica colonne se la tabella esiste già
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

# Buffer dati form / modifica
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
              "gemini-2.0-flash",
              "gemini-3.7-flash",
              "gemini-1.5-pro",
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
              response.text.replace("```json", "").replace("```", "").strip()
          )
          extracted = json.loads(raw_text)

          st.session_state["food_buffer"] = {
              "edit_id": st.session_state["food_buffer"].get("edit_id", None),
              "nome": str(extracted.get("nome", "")),
              "categoria": st.session_state["food_buffer"].get(
                  "categoria", "COLAZIONE"
              ),
              "quantita": float(
                  st.session_state["food_buffer"].get("quantita", 100.0)
              ),
              "costo": float(st.session_state["food_buffer"].get("costo", 0.0)),
              "kj": float(extracted.get("kj", 0.0)),
              "kcal": float(extracted.get("kcal", 0.0)),
              "grassi": float(extracted.get("grassi", 0.0)),
              "saturi": float(extracted.get("saturi", 0.0)),
              "carboidrati": float(extracted.get("carboidrati", 0.0)),
              "zuccheri": float(extracted.get("zuccheri", 0.0)),
              "fibre": float(extracted.get("fibre", 0.0)),
              "proteine": float(extracted.get("proteine", 0.0)),
              "sale": float(extracted.get("sale", 0.0)),
          }
          st.success("Dati estratti! Verifica i campi a destra e salva.")
          st.rerun()
        except Exception as e:
          st.error(f"Errore durante l'estrazione: {e}")

  with col_manual:
    st.markdown("**Dati Prodotto e Valori Nutrizionali (per 100 g)**")
    buff = st.session_state["food_buffer"]

    nome = st.text_input("Nome Alimento", value=buff["nome"])

    c_cat, c_qty, c_cost = st.columns([2, 1, 1])
    cat_options = ["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"]
    cat_index = (
        cat_options.index(buff["categoria"])
        if buff["categoria"] in cat_options
        else 0
    )
    categoria = c_cat.selectbox(
        "Categoria Dispensa", cat_options, index=cat_index
    )
    quantita = c_qty.number_input(
        "Quantità (g / pz)", value=float(buff["quantita"]), step=10.0
    )
    costo = c_cost.number_input(
        "Costo (€)", value=float(buff["costo"]), step=0.1
    )

    c1, c2 = st.columns(2)
    kj = c1.number_input("Energia (kJ)", value=float(buff["kj"]), step=0.1)
    kcal = c2.number_input("Energia (kcal)", value=float(buff["kcal"]), step=0.1)

    c3, c4 = st.columns(2)
    grassi = c3.number_input(
        "Grassi (g)", value=float(buff["grassi"]), step=0.1
    )
    saturi = c4.number_input(
        "di cui acidi grassi saturi (g)",
        value=float(buff["saturi"]),
        step=0.1,
    )

    c5, c6 = st.columns(2)
    carboidrati = c5.number_input(
        "Carboidrati (g)", value=float(buff["carboidrati"]), step=0.1
    )
    zuccheri = c6.number_input(
        "di cui zuccheri (g)", value=float(buff["zuccheri"]), step=0.1
    )

    c7, c8, c9 = st.columns(3)
    fibre = c7.number_input(
        "Fibra alimentare (g)", value=float(buff["fibre"]), step=0.1
    )
    proteine = c8.number_input(
        "Proteine (g)", value=float(buff["proteine"]), step=0.1
    )
    sale = c9.number_input("Sale (g)", value=float(buff["sale"]), step=0.01)

    btn_col1, btn_col2 = st.columns([1, 1])

    with btn_col1:
      btn_label = "Aggiorna Alimento" if is_editing else "💾 Salva in Dispensa"
      if st.button(btn_label, type="primary", use_container_width=True):
        if nome.strip():
          if is_editing:
            cursor.execute(
                """
                            UPDATE dispensa SET nome=?, categoria=?, quantita=?, costo=?, kj=?, kcal=?, grassi=?, saturi=?, carboidrati=?, zuccheri=?, fibre=?, proteine=?, sale=?
                            WHERE id=?
                            """,
                (
                    nome,
                    categoria,
                    quantita,
                    costo,
                    kj,
                    kcal,
                    grassi,
                    saturi,
                    carboidrati,
                    zuccheri,
                    fibre,
                    proteine,
                    sale,
                    buff["edit_id"],
                ),
            )
          else:
            cursor.execute(
                """
                            INSERT INTO dispensa (nome, categoria, quantita, costo, kj, kcal, grassi, saturi, carboidrati, zuccheri, fibre, proteine, sale)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                (
                    nome,
                    categoria,
                    quantita,
                    costo,
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
          st.session_state["food_buffer"] = default_values.copy()
          st.success("Operazione completata con successo!")
          st.rerun()
        else:
          st.warning("Inserisci il nome dell'alimento prima di salvare.")

    with btn_col2:
      if st.button("🧹 Svuota Campi / Annulla", use_container_width=True):
        st.session_state["food_buffer"] = default_values.copy()
        st.rerun()

  st.divider()

  # Visualizzazione Tabella Dispensa
  cat_filter = st.radio(
      "Filtra Dispensa:",
      ["TUTTE", "COLAZIONE", "PRANZO", "SPUNTINO", "CENA"],
      horizontal=True,
  )

  query = (
      "SELECT * FROM dispensa"
      if cat_filter == "TUTTE"
      else f"SELECT * FROM dispensa WHERE categoria = '{cat_filter}'"
  )
  df_dispensa = pd.read_sql_query(query, conn)

  if df_dispensa.empty:
    st.info("Nessun alimento presente nella dispensa.")
  else:
    header_cols = st.columns([2.5, 1.2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.2])
    headers = [
        "Nome",
        "Cat.",
        "Q.tà",
        "Costo",
        "Kcal",
        "Grassi",
        "Saturi",
        "Carbo",
        "Zucch",
        "Fibre",
        "Prot",
        "Sale",
        "Azioni",
    ]
    for col, h in zip(header_cols, headers):
      col.markdown(f"**{h}**")

    for _, row in df_dispensa.iterrows():
      cols = st.columns([2.5, 1.2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.2])
      cols[0].write(row["nome"])
      cols[1].write(row["categoria"])
      cols[2].write(f"{row['quantita']:.0f}g")
      cols[3].write(f"€{row['costo']:.2f}")
      cols[4].write(f"{row['kcal']:.0f}")
      cols[5].write(f"{row['grassi']:.1f}")
      cols[6].write(f"{row['saturi']:.1f}")
      cols[7].write(f"{row['carboidrati']:.1f}")
      cols[8].write(f"{row['zuccheri']:.1f}")
      cols[9].write(f"{row['fibre']:.1f}")
      cols[10].write(f"{row['proteine']:.1f}")
      cols[11].write(f"{row['sale']:.2f}")

      action_c1, action_c2 = cols[12].columns(2)
      if action_c1.button("✏️", key=f"edit_{row['id']}"):
        st.session_state["food_buffer"] = {
            "edit_id": row["id"],
            "nome": row["nome"],
            "categoria": row["categoria"],
            "quantita": float(row["quantita"]),
            "costo": float(row["costo"]),
            "kj": float(row["kj"]),
            "kcal": float(row["kcal"]),
            "grassi": float(row["grassi"]),
            "saturi": float(row["saturi"]),
            "carboidrati": float(row["carboidrati"]),
            "zuccheri": float(row["zuccheri"]),
            "fibre": float(row["fibre"]),
            "proteine": float(row["proteine"]),
            "sale": float(row["sale"]),
        }
        st.rerun()

      if action_c2.button("🗑️", key=f"del_{row['id']}"):
        cursor.execute(
            "DELETE FROM dispensa WHERE id = ?", (int(row["id"]),)
        )
        conn.commit()
        if st.session_state["food_buffer"].get("edit_id") == row["id"]:
          st.session_state["food_buffer"] = default_values.copy()
        st.rerun()

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
