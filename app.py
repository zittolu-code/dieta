st.data_editor(
    st.session_state.dispensa_df,
    column_config={
        "_id": None,  # Nasconde completamente la colonna ID
        "link_prodotto": st.column_config.LinkColumn(
            "Scheda Prodotto",
            help="Clicca per aprire lo store",
            display_text="Apri Link 🔗"
        ),
        "Costo (€)": st.column_config.NumberColumn(
            "Costo (€)",
            format="€ %.2f",
            min_value=0.0
        ),
        "Quantità": st.column_config.TextColumn(
            "Quantità",
            placeholder="es. 500g"
        ),
    },
    num_rows="dynamic", # Permette di eliminare/aggiungere righe direttamente dalla tabella
    use_container_width=True,
    hide_index=True # Nasconde l'indice numerico di default a sinistra (0, 1, 2...)
)

