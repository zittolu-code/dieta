import streamlit as st
import pandas as pd

# Inizializzazione del DataFrame in session_state se non esiste
if "dispensa_df" not in st.session_state:
    # Struttura dati con le nuove colonne: costo, quantita, link_prodotto
    st.session_state.dispensa_df = pd.DataFrame([
        {
            "_id": 1,  # Chiave interna (nascosta all'utente)
            "Nome": "Fiocchi d'avena piccoli bio",
            "Categoria": "COLAZIONE",
            "Costo (€)": 4.50,
            "Quantità": "1 kg",
            "kJ": 1562,
            "kcal": 372,
            "Grassi (g)": 7.0,
            "Saturi (g)": 1.3,
            "Carboidrati (g)": 59.0,
            "Zuccheri (g)": 0.7,
            "Fibre (g)": 10.0,
            "Proteine (g)": 14.0,
            "Sale (g)": 0.02,
            "link_prodotto": "https://www.koro-shop.it/fiocchi-di-avena-piccoli-bio-2-5-kg"
        }
    ])

# Helper per cancellare un elemento
def elimina_alimento(idx):
    st.session_state.dispensa_df = st.session_state.dispensa_df.drop(index=idx).reset_index(drop=True)
    st.rerun()

# -----------------------------------------------------------------------------
# Sezione UI: Tabella Dispensa Interattiva
# -----------------------------------------------------------------------------

st.subheader("I Tuoi Alimenti in Dispensa")

# Filtro Categoria
col_filtro, _ = st.columns([3, 1])
with col_filtro:
    categoria_sel = st.radio(
        "Filtra Dispensa:",
        options=["TUTTE", "COLAZIONE", "PRANZO", "SPUNTINO", "CENA"],
        horizontal=True
    )

df_view = st.session_state.dispensa_df.copy()
if categoria_sel != "TUTTE":
    df_view = df_view[df_view["Categoria"] == categoria_sel]

if df_view.empty:
    st.info("Nessun alimento presente in questa categoria.")
else:
    # Header personalizzato per la tabella a schede/righe
    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([3, 1.5, 1, 1, 1.5, 2])
    with h_col1: st.caption("**Nome**")
    with h_col2: st.caption("**Categoria**")
    with h_col3: st.caption("**Q.tà**")
    with h_col4: st.caption("**Costo**")
    with h_col5: st.caption("**kcal / 100g**")
    with h_col6: st.caption("**Azioni**")
    st.divider()

    # Rendering dinamico riga per riga
    for index, row in df_view.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([3, 1.5, 1, 1, 1.5, 2], vertical_alignment="center")
        
        with c1:
            st.write(f"**{row['Nome']}**")
        with c2:
            st.write(f"`{row['Categoria']}`")
        with c3:
            st.write(f"{row['Quantità']}")
        with c4:
            st.write(f"€ {row['Costo (€)']:.2f}")
        with c5:
            st.write(f"{row['kcal']} kcal")
            
        with c6:
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            
            # 1. Pulsante Link Prodotto
            with btn_col1:
                link = row.get("link_prodotto", "")
                if link and str(link).startswith("http"):
                    st.link_button("🔗", url=link, help="Apri scheda prodotto")
                else:
                    st.button("🔗", disabled=True, key=f"nolink_{index}", help="Nessun link disponibile")

            # 2. Modifica Singola Voce (tramite popover)
            with btn_col2:
                with st.popover("✏️", help="Modifica Alimento"):
                    st.write(f"**Modifica {row['Nome']}**")
                    new_nome = st.text_input("Nome", value=row["Nome"], key=f"edit_nome_{index}")
                    new_cat = st.selectbox("Categoria", ["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"], 
                                           index=["COLAZIONE", "PRANZO", "SPUNTINO", "CENA"].index(row["Categoria"]),
                                           key=f"edit_cat_{index}")
                    new_qta = st.text_input("Quantità (es. 500g, 1pz)", value=row["Quantità"], key=f"edit_qta_{index}")
                    new_costo = st.number_input("Costo (€)", value=float(row["Costo (€)"]), step=0.10, key=f"edit_costo_{index}")
                    new_kcal = st.number_input("kcal", value=int(row["kcal"]), key=f"edit_kcal_{index}")
                    new_link = st.text_input("Link Scheda Prodotto", value=row.get("link_prodotto", ""), key=f"edit_link_{index}")
                    
                    if st.button("Salva Modifiche", key=f"save_edit_{index}", type="primary"):
                        st.session_state.dispensa_df.at[index, "Nome"] = new_nome
                        st.session_state.dispensa_df.at[index, "Categoria"] = new_cat
                        st.session_state.dispensa_df.at[index, "Quantità"] = new_qta
                        st.session_state.dispensa_df.at[index, "Costo (€)"] = new_costo
                        st.session_state.dispensa_df.at[index, "kcal"] = new_kcal
                        st.session_state.dispensa_df.at[index, "link_prodotto"] = new_link
                        st.success("Aggiornato!")
                        st.rerun()

            # 3. Elimina Singola Voce
            with btn_col3:
                if st.button("🗑️", key=f"del_{index}", help="Elimina alimento"):
                    elimina_alimento(index)
                    
        st.divider()
