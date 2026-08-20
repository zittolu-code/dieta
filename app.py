import streamlit as st
import pandas as pd

# Inizializzazione del DataFrame in session_state
if "dispensa_df" not in st.session_state:
    st.session_state.dispensa_df = pd.DataFrame([
        {
            "nome": "Fiocchi d'avena piccoli bio",
            "categoria": "COLAZIONE",
            "quantità": "2.5 kg",
            "prezzo (€)": 8.99,
            "link": "https://www.koro-shop.it/fiocchi-di-avena-piccoli-bio-2-5-kg?search=avena",
            "kj": 1562,
            "kcal": 372,
            "grassi": 7.0,
            "saturi": 1.3,
            "carboidrati": 59.0,
            "zuccheri": 0.7,
            "fibre": 10.0,
            "proteine": 14.0,
            "sale": 0.02
        }
    ])

# -----------------------------------------------------------------------------
# Filtro Dispensa
# -----------------------------------------------------------------------------
col_filtro, col_svuota = st.columns([4, 1])

with col_filtro:
    categoria_sel = st.radio(
        "Filtra Dispensa:",
        options=["TUTTE", "COLAZIONE", "PRANZO", "SPUNTINO", "CENA"],
        horizontal=True
    )

with col_svuota:
    if st.button("🗑️ Elimina tutti i cibi", type="secondary"):
        st.session_state.dispensa_df = st.session_state.dispensa_df.iloc[0:0]
        st.rerun()

# Filtraggio dati
df_filtrato = st.session_state.dispensa_df.copy()
if categoria_sel != "TUTTE":
    df_filtrato = df_filtrato[df_filtrato["categoria"] == categoria_sel]

# -----------------------------------------------------------------------------
# Tabella Originale Modificabile (Data Editor)
# -----------------------------------------------------------------------------
# Mostra la tabella completa con tutte le colonne originali + quantità e prezzo,
# nascondendo l'indice/ID e consentendo modifica/cancellazione riga direttamente.
edited_df = st.data_editor(
    df_filtrato,
    use_container_width=True,
    hide_index=True,        # Rimuove la colonna ID / indice numerico a sinistra
    num_rows="dynamic",     # Permette di selezionare ed eliminare le singole righe o aggiungerne di nuove
    column_config={
        "nome": st.column_config.TextColumn("nome", required=True),
        "categoria": st.column_config.SelectboxColumn(
            "categoria",
            options=["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"],
            required=True
        ),
        "quantità": st.column_config.TextColumn("quantità", help="Es. 500g, 1kg, 2pz"),
        "prezzo (€)": st.column_config.NumberColumn("prezzo (€)", format="€ %.2f", min_value=0.0),
        "link": st.column_config.LinkColumn("link", display_text="Apri Link 🔗"),
        "kj": st.column_config.NumberColumn("kj", format="%d"),
        "kcal": st.column_config.NumberColumn("kcal", format="%d"),
        "grassi": st.column_config.NumberColumn("grassi", format="%.1f"),
        "saturi": st.column_config.NumberColumn("saturi", format="%.1f"),
        "carboidrati": st.column_config.NumberColumn("carboidrati", format="%.1f"),
        "zuccheri": st.column_config.NumberColumn("zuccheri", format="%.1f"),
        "fibre": st.column_config.NumberColumn("fibre", format="%.1f"),
        "proteine": st.column_config.NumberColumn("proteine", format="%.1f"),
        "sale": st.column_config.NumberColumn("sale", format="%.2f")
    },
    key="dispensa_editor"
)

# Salva eventuali modifiche dirette effettuate sulla tabella
if not edited_df.equals(df_filtrato):
    st.session_state.dispensa_df = edited_df
