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

# Tabella Dispensa
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS dispensa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT,
    nome TEXT,
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

# Tabella Voci Piano Settimanale
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS piano_pasti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    giorno TEXT,
    pasto TEXT,
    alimento_id INTEGER,
    grammi REAL,
    FOREIGN KEY(alimento_id) REFERENCES dispensa(id)
)
"""
)

# Tabella Obiettivi
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS obiettivi (
    id INTEGER PRIMARY KEY,
    titolo TEXT,
    sottotitolo TEXT,
    target_kcal REAL,
    target_kj REAL,
    target_grassi REAL,
    target_carbo REAL,
    target_pro REAL
)
"""
)
cursor.execute("SELECT COUNT(*) FROM obiettivi")
if cursor.fetchone()[0] == 0:
  cursor.execute(
      """
    INSERT INTO obiettivi (id, titolo, sottotitolo, target_kcal, target_kj, target_grassi, target_carbo, target_pro)
    VALUES (1, 'Piano nutrizionale settimanale', 'Perdita di massa grassa · mantenimento della massa magra', 2106.0, 8811.0, 59.0, 230.0, 165.0)
    """
  )
conn.commit()

# --- Configurazione Pagina e Stile ---
st.set_page_config(
    page_title="Piano Nutrizionale Settimanale", layout="wide"
)

st.markdown(
    """
<style>
    .reportview-container, .main .block-container {
        padding-top: 2rem;
        max-width: 1250px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e5ede4;
        padding: 6px;
        border-radius: 12px;
        width: fit-content;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
        color: #243828;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1b3523 !important;
        color: #ffffff !important;
    }
    .card-box {
        background: #ffffff;
        border: 1px solid #e1ebe2;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .nutri-box {
        background: #ffffff;
        border: 2px solid #1b3523;
        border-radius: 12px;
        padding: 20px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Costanti
GIORNI = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
GIORNI_MAP = {
    "LUN": "Lunedì",
    "MAR": "Martedì",
    "MER": "Mercoledì",
    "GIO": "Giovedì",
    "VEN": "Venerdì",
    "SAB": "Sabato",
    "DOM": "Domenica",
}
PASTI = ["Colazione", "Pranzo", "Cena", "Spuntini"]
PASTI_CAT_MAP = {
    "Colazione": "COLAZIONE",
    "Pranzo": "PRANZO",
    "Cena": "CENA",
    "Spuntini": "SPUNTINO",
}

# Inizializzazione session state
default_buffer = {
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
  st.session_state["food_buffer"] = default_buffer.copy()

if "selected_day" not in st.session_state:
  st.session_state["selected_day"] = "LUN"

# Caricamento Obiettivi
cursor.execute("SELECT * FROM obiettivi WHERE id=1")
obj_row = cursor.fetchone()
info_titolo = obj_row[1]
info_sottotitolo = obj_row[2]
t_kcal = obj_row[3]
t_kj = obj_row[4]
t_grassi = obj_row[5]
t_carbo = obj_row[6]
t_pro = obj_row[7]

# Header Principale
st.markdown(f"# {info_titolo}")
st.markdown(
    f"<p style='color: #4b6350; margin-top: -10px;'>{info_sottotitolo}</p>",
    unsafe_allow_html=True,
)

# Calcolo Dati Settimanali
query_piano = """
SELECT p.id, p.giorno, p.pasto, p.grammi, d.id as alimento_id, d.nome, d.categoria, d.kj, d.kcal, d.grassi, d.saturi, d.carboidrati, d.zuccheri, d.fibre, d.proteine, d.sale
FROM piano_pasti p
JOIN dispensa d ON p.alimento_id = d.id
"""
df_piano = pd.read_sql_query(query_piano, conn)

day_stats = {}
for g in GIORNI:
  sub = df_piano[df_piano["giorno"] == g]
  tot_kcal = (sub["kcal"] * sub["grammi"] / 100.0).sum()
  tot_kj = (sub["kj"] * sub["grammi"] / 100.0).sum()
  tot_pro = (sub["proteine"] * sub["grammi"] / 100.0).sum()
  tot_carbo = (sub["carboidrati"] * sub["grammi"] / 100.0).sum()
  tot_grassi = (sub["grassi"] * sub["grammi"] / 100.0).sum()
  tot_saturi = (sub["saturi"] * sub["grammi"] / 100.0).sum()
  tot_zuccheri = (sub["zuccheri"] * sub["grammi"] / 100.0).sum()
  tot_fibre = (sub["fibre"] * sub["grammi"] / 100.0).sum()
  tot_sale = (sub["sale"] * sub["grammi"] / 100.0).sum()
  day_stats[g] = {
      "kcal": tot_kcal,
      "kj": tot_kj,
      "pro": tot_pro,
      "carbo": tot_carbo,
      "grassi": tot_grassi,
      "saturi": tot_saturi,
      "zuccheri": tot_zuccheri,
      "fibre": tot_fibre,
      "sale": tot_sale,
  }

# Tab Principali
tab_giorno, tab_settimana, tab_dispensa, tab_obiettivi = st.tabs([
    "📅 Piano giornaliero",
    "⊞ Tabella settimanale",
    "📦 Dispensa",
    "⚙️ Obiettivi",
])

# ==============================================================================
# TAB 1: PIANO GIORNALIERO (FOTO 2)
# ==============================================================================
with tab_giorno:
  # Selettore Giorni a Card
  cols_giorni = st.columns(7)
  for idx, g in enumerate(GIORNI):
    with cols_giorni[idx]:
      kcal_val = int(round(day_stats[g]["kcal"]))
      is_active = st.session_state["selected_day"] == g
      bg_col = "#1b3523" if is_active else "#ffffff"
      text_col = "#ffffff" if is_active else "#1b3523"
      border_col = "#1b3523" if is_active else "#e1ebe2"

      st.markdown(
          f"""
            <div style="background-color: {bg_col}; color: {text_col}; border: 1px solid {border_col}; border-radius: 12px; padding: 10px; text-align: center;">
                <div style="font-size: 12px; font-weight: 700;">{g}</div>
                <div style="font-size: 18px; font-weight: 800; margin: 4px 0;">{kcal_val}</div>
                <div style="height: 4px; background: {'#527c5e' if is_active else '#dbe5dc'}; border-radius: 2px;"></div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(f"Seleziona {g}", key=f"btn_giorno_{g}"):
        st.session_state["selected_day"] = g
        st.rerun()

  # Media Giornaliera Settimanale
  avg_kcal = sum(s["kcal"] for s in day_stats.values()) / 7.0
  avg_pro = sum(s["pro"] for s in day_stats.values()) / 7.0
  avg_carbo = sum(s["carbo"] for s in day_stats.values()) / 7.0
  avg_grassi = sum(s["grassi"] for s in day_stats.values()) / 7.0

  st.markdown(
      f"<p style='margin: 15px 0; font-size: 13px; color: #3e5644;'>"
      f"Media giornaliera settimana: <b>{avg_kcal:.0f} kcal</b> · P"
      f" <b>{avg_pro:.1f}g</b> · C <b>{avg_carbo:.1f}g</b> · G"
      f" <b>{avg_grassi:.1f}g</b></p>",
      unsafe_allow_html=True,
  )

  # Layout Principale: Pasti a Sinistra, Card Valori Nutrizionali a Destra
  sel_g = st.session_state["selected_day"]
  cur_stats = day_stats[sel_g]

  col_pasti, col_nutri = st.columns([1.6, 1.1])

  with col_pasti:
    df_disp_all = pd.read_sql_query("SELECT * FROM dispensa", conn)

    for pasto in PASTI:
      cat_corrispondente = PASTI_CAT_MAP[pasto]
      df_pasto = df_piano[
          (df_piano["giorno"] == sel_g) & (df_piano["pasto"] == pasto)
      ]
      pasto_kcal = (df_pasto["kcal"] * df_pasto["grammi"] / 100.0).sum()

      with st.container():
        st.markdown(
            f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                    <span style="font-size: 16px; font-weight: 700; color: #1b3523;">{pasto}</span>
                    <span style="font-size: 14px; font-weight: 600; color: #4b6350;">{pasto_kcal:.0f} kcal</span>
                </div>
                """,
            unsafe_allow_html=True,
        )

        # Mostra cibi già inseriti nel pasto
        for _, item in df_pasto.iterrows():
          c_item1, c_item2, c_item3 = st.columns([3, 1.2, 0.5])
          with c_item1:
            st.markdown(f"• **{item['nome']}**")
          with c_item2:
            new_g = st.number_input(
                "g",
                value=float(item["grammi"]),
                step=10.0,
                key=f"g_{item['id']}",
                label_visibility="collapsed",
            )
            if new_g != item["grammi"]:
              cursor.execute(
                  "UPDATE piano_pasti SET grammi=? WHERE id=?",
                  (new_g, item["id"]),
              )
              conn.commit()
              st.rerun()
          with c_item3:
            if st.button("✕", key=f"del_item_{item['id']}"):
              cursor.execute(
                  "DELETE FROM piano_pasti WHERE id=?", (item["id"],)
              )
              conn.commit()
              st.rerun()

        # Inserimento nuovo alimento nel pasto
        disp_cat = df_disp_all[df_disp_all["categoria"] == cat_corrispondente]
        food_options = {
            row["nome"]: row["id"] for _, row in disp_cat.iterrows()
        }

        c_sel, c_qty, c_btn = st.columns([2.5, 1.2, 1.3])
        with c_sel:
          scelta_food = st.selectbox(
              f"Seleziona {pasto}",
              options=[""] + list(food_options.keys()),
              key=f"sel_{sel_g}_{pasto}",
              label_visibility="collapsed",
          )
        with c_qty:
          qty_to_add = st.number_input(
              "Grammi",
              value=100.0,
              step=10.0,
              key=f"qty_{sel_g}_{pasto}",
              label_visibility="collapsed",
          )
        with c_btn:
          if st.button(
              "＋ Aggiungi", key=f"btn_add_{sel_g}_{pasto}", type="primary"
          ):
            if scelta_food:
              food_id = food_options[scelta_food]
              cursor.execute(
                  """
                            INSERT INTO piano_pasti (giorno, pasto, alimento_id, grammi)
                            VALUES (?, ?, ?, ?)
                            """,
                  (sel_g, pasto, food_id, qty_to_add),
              )
              conn.commit()
              st.rerun()

        st.markdown(
            "<hr style='margin: 8px 0 16px 0; border: none; border-top: 1px"
            " solid #e1ebe2;'>",
            unsafe_allow_html=True,
        )

  with col_nutri:
    st.markdown(
        f"""
        <div class="nutri-box">
            <h4 style="margin: 0; color: #1b3523; font-weight: 800; font-size: 15px; letter-spacing: 0.5px;">VALORI NUTRIZIONALI</h4>
            <div style="font-size: 12px; color: #5a7560; margin-bottom: 15px;">Porzione: {GIORNI_MAP[sel_g]}</div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 2px solid #1b3523; padding-bottom: 10px;">
                <div>
                    <div style="font-weight: 700; font-size: 14px; color: #1b3523;">Valore energetico</div>
                    <div style="font-size: 11px; color: #5a7560;">Obiettivo {t_kcal:.0f} kcal · {t_kj:.0f} kJ</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 26px; font-weight: 800; color: #1b3523;">{cur_stats['kcal']:.0f}</div>
                    <div style="font-size: 10px; color: #5a7560;">{int((cur_stats['kcal']/t_kcal)*100) if t_kcal else 0}%</div>
                </div>
            </div>
            <div style="margin-top: 12px; font-size: 13px; color: #1b3523;">
                <div style="display: flex; justify-content: space-between; font-weight: 700; padding: 4px 0;">
                    <span>Grassi</span>
                    <span>{cur_stats['grassi']:.1f} g / {t_grassi:.0f} g</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 2px 0 2px 14px; color: #4b6350; font-size: 12px;">
                    <span>di cui acidi grassi saturi</span>
                    <span>{cur_stats['saturi']:.1f} g</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-weight: 700; padding: 4px 0; border-top: 1px solid #e1ebe2;">
                    <span>Carboidrati</span>
                    <span>{cur_stats['carbo']:.1f} g / {t_carbo:.0f} g</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 2px 0 2px 14px; color: #4b6350; font-size: 12px;">
                    <span>di cui zuccheri</span>
                    <span>{cur_stats['zuccheri']:.1f} g</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-weight: 700; padding: 4px 0; border-top: 1px solid #e1ebe2;">
                    <span>Fibra alimentare</span>
                    <span>{cur_stats['fibre']:.1f} g</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-weight: 700; padding: 4px 0; border-top: 1px solid #e1ebe2;">
                    <span>Proteine</span>
                    <span>{cur_stats['pro']:.1f} g / {t_pro:.0f} g</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-weight: 700; padding: 6px 0 2px 0; border-top: 1px solid #1b3523; margin-top: 6px;">
                    <span>Sale</span>
                    <span>{cur_stats['sale']:.2f} g</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# TAB 2: TABELLA SETTIMANALE (FOTO 1)
# ==============================================================================
with tab_settimana:
  st.markdown(
      "<div style='overflow-x: auto; background: white; border-radius: 12px;"
      " border: 1px solid #e1ebe2; padding: 15px;'>",
      unsafe_allow_html=True,
  )

  # Header Tabella con Pulsanti Giorni
  header_cols = st.columns([1.5, 2, 2, 2, 2, 2, 2, 2])
  with header_cols[0]:
    st.markdown(
        "<div style='font-size: 11px; font-weight: 800; color:"
        " #4b6350;'>PASTO</div>",
        unsafe_allow_html=True,
    )

  for i, g in enumerate(GIORNI):
    with header_cols[i + 1]:
      kcal_val = int(round(day_stats[g]["kcal"]))
      if st.button(
          f"{g}\n{kcal_val} kcal",
          key=f"tab_nav_{g}",
          use_container_width=True,
      ):
        st.session_state["selected_day"] = g
        st.rerun()

  st.markdown(
      "<hr style='margin: 8px 0; border: none; border-top: 1px solid #e1ebe2;'>",
      unsafe_allow_html=True,
  )

  # Righe Pasti
  for pasto in PASTI:
    row_cols = st.columns([1.5, 2, 2, 2, 2, 2, 2, 2])
    with row_cols[0]:
      st.markdown(f"**{pasto}**")

    for i, g in enumerate(GIORNI):
      with row_cols[i + 1]:
        sub = df_piano[(df_piano["giorno"] == g) & (df_piano["pasto"] == pasto)]
        if sub.empty:
          st.markdown(
              "<span style='color: #8fa693;'>—</span>", unsafe_allow_html=True
          )
        else:
          cibi_txt = "<br>".join(
              [f"{r['nome']}<br><b>{r['grammi']:.0f}g</b>" for _, r in sub.iterrows()]
          )
          st.markdown(
              f"<div style='font-size: 12px; color: #1b3523;'>{cibi_txt}</div>",
              unsafe_allow_html=True,
          )

    st.markdown(
        "<hr style='margin: 8px 0; border: none; border-top: 1px solid"
        " #f0f5f1;'>",
        unsafe_allow_html=True,
    )

  # Righe Totali Nutrizionali
  metriche = [
      ("Kcal", "kcal", ".0f"),
      ("Proteine (g)", "pro", ".1f"),
      ("Carboidrati (g)", "carbo", ".1f"),
      ("Grassi (g)", "grassi", ".1f"),
  ]

  for label, key_val, fmt in metriche:
    r_cols = st.columns([1.5, 2, 2, 2, 2, 2, 2, 2])
    with r_cols[0]:
      st.markdown(f"**{label}**")
    for i, g in enumerate(GIORNI):
      with r_cols[i + 1]:
        val = day_stats[g][key_val]
        st.markdown(f"**{val:{fmt}}**")

  st.markdown("</div>", unsafe_allow_html=True)
  st.caption(
      "Clicca su un giorno in testata per aprirlo nel piano giornaliero e"
      " modificarlo."
  )

# ==============================================================================
# TAB 3: DISPENSA & SMART INGEST
# ==============================================================================
with tab_dispensa:
  is_editing = st.session_state["food_buffer"]["edit_id"] is not None
  st.subheader(
      "✏️ Modifica Alimento" if is_editing else "Aggiungi Alimento alla Dispensa"
  )

  col_upload, col_manual = st.columns([1, 1])

  with col_upload:
    st.markdown("**Caricamento Automatico con gemini-3.7-flash**")
    api_key_secret = st.secrets.get("GEMINI_API_KEY", "")
    api_key = (
        api_key_secret
        if api_key_secret
        else st.text_input("Gemini API Key", type="password")
    )
    uploaded_img = st.file_uploader(
        "Carica foto etichetta / confezione", type=["png", "jpg", "jpeg"]
    )
    url_input = st.text_input("Oppure incolla il link della scheda prodotto")

    if st.button("Estrai Valori") and api_key and (uploaded_img or url_input):
      with st.spinner("Lettura ed estrazione in corso con gemini-3.7-flash..."):
        try:
          genai.configure(api_key=api_key)
          model = genai.GenerativeModel("gemini-3.7-flash")

          prompt = """
                    Estrai con precisione:
                    1. Nome del prodotto.
                    2. Quantita/peso netto della confezione in grammi (se in kg moltiplica x1000, es: 2.5 kg = 2500; se assente metti 100).
                    3. Costo/prezzo del prodotto in Euro (numero decimale con punto, es: 4.99; se assente metti 0.0).
                    4. Valori nutrizionali medi per 100g.
                    
                    Rispondi SOLO ed ESCLUSIVAMENTE con un JSON valido con questa struttura esatta:
                    {
                      "nome": "string",
                      "quantita": 0.0,
                      "costo": 0.0,
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

          response = model.generate_content(content)
          raw = response.text.strip()
          start_idx = raw.find("{")
          end_idx = raw.rfind("}")
          json_text = (
              raw[start_idx : end_idx + 1]
              if (start_idx != -1 and end_idx != -1)
              else raw
          )
          extracted = json.loads(json_text)

          st.session_state["food_buffer"] = {
              "edit_id": st.session_state["food_buffer"].get("edit_id", None),
              "nome": str(extracted.get("nome", "")),
              "categoria": st.session_state["food_buffer"].get(
                  "categoria", "COLAZIONE"
              ),
              "quantita": float(extracted.get("quantita", 100.0)),
              "costo": float(extracted.get("costo", 0.0)),
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
          st.success("Dati estratti con successo!")
          st.rerun()
        except Exception as e:
          st.error(f"Errore durante l'estrazione: {e}")

  with col_manual:
    st.markdown("**Dati Prodotto e Valori Nutrizionali (per 100 g)**")
    buff = st.session_state["food_buffer"]

    r1_col1, r1_col2, r1_col3 = st.columns([2, 1, 1])
    with r1_col1:
      nome = st.text_input("Nome Alimento", value=buff["nome"])
    with r1_col2:
      quantita = st.number_input(
          "📦 Confezione (g/pz)", value=float(buff["quantita"]), step=10.0
      )
    with r1_col3:
      costo = st.number_input(
          "💶 Prezzo (€)", value=float(buff["costo"]), step=0.1
      )

    cat_options = ["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"]
    cat_index = (
        cat_options.index(buff["categoria"])
        if buff["categoria"] in cat_options
        else 0
    )
    categoria = st.selectbox(
        "Categoria Dispensa", cat_options, index=cat_index
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
                            UPDATE dispensa SET categoria=?, nome=?, quantita=?, costo=?, kj=?, kcal=?, grassi=?, saturi=?, carboidrati=?, zuccheri=?, fibre=?, proteine=?, sale=?
                            WHERE id=?
                            """,
                (
                    categoria,
                    nome,
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
                            INSERT INTO dispensa (categoria, nome, quantita, costo, kj, kcal, grassi, saturi, carboidrati, zuccheri, fibre, proteine, sale)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                (
                    categoria,
                    nome,
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
          st.session_state["food_buffer"] = default_buffer.copy()
          st.success("Alimento salvato!")
          st.rerun()
        else:
          st.warning("Inserisci il nome dell'alimento.")

    with btn_col2:
      if st.button("🧹 Annulla / Svuota", use_container_width=True):
        st.session_state["food_buffer"] = default_buffer.copy()
        st.rerun()

  st.divider()

  # Tabella Cibi in Dispensa
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
  df_disp = pd.read_sql_query(query, conn)

  if df_disp.empty:
    st.info("Nessun alimento presente nella dispensa.")
  else:
    header_cols = st.columns([1.2, 2.5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.2])
    headers = [
        "Cat.",
        "Nome",
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

    for _, row in df_disp.iterrows():
      cols = st.columns([1.2, 2.5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.2])
      cols[0].write(f"**{row['categoria']}**")
      cols[1].write(row["nome"])
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
        cursor.execute(
            "DELETE FROM piano_pasti WHERE alimento_id = ?",
            (int(row["id"]),),
        )
        conn.commit()
        if st.session_state["food_buffer"].get("edit_id") == row["id"]:
          st.session_state["food_buffer"] = default_buffer.copy()
        st.rerun()

# ==============================================================================
# TAB 4: OBIETTIVI NUTRIZIONALI
# ==============================================================================
with tab_obiettivi:
  st.subheader("Personalizza Obiettivi e Intestazione")
  with st.form("form_obiettivi"):
    n_titolo = st.text_input("Titolo Scheda", value=info_titolo)
    n_sottotitolo = st.text_input("Sottotitolo", value=info_sottotitolo)

    c_o1, c_o2 = st.columns(2)
    n_kcal = c_o1.number_input("Obiettivo Kcal", value=float(t_kcal), step=50.0)
    n_kj = c_o2.number_input("Obiettivo kJ", value=float(t_kj), step=100.0)

    c_o3, c_o4, c_o5 = st.columns(3)
    n_grassi = c_o3.number_input(
        "Obiettivo Grassi (g)", value=float(t_grassi), step=1.0
    )
    n_carbo = c_o4.number_input(
        "Obiettivo Carboidrati (g)", value=float(t_carbo), step=5.0
    )
    n_pro = c_o5.number_input(
        "Obiettivo Proteine (g)", value=float(t_pro), step=5.0
    )

    if st.form_submit_button("Aggiorna Obiettivi", type="primary"):
      cursor.execute(
          """
            UPDATE obiettivi SET titolo=?, sottotitolo=?, target_kcal=?, target_kj=?, target_grassi=?, target_carbo=?, target_pro=?
            WHERE id=1
            """,
          (
              n_titolo,
              n_sottotitolo,
              n_kcal,
              n_kj,
              n_grassi,
              n_carbo,
              n_pro,
          ),
      )
      conn.commit()
      st.success("Obiettivi aggiornati con successo!")
      st.rerun()
