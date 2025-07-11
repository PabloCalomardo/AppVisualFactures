import streamlit as st
from data.data_manager import DataManager
from ui.dashboard import Dashboard
import numpy as np
import pandas as pd
import os


st.set_page_config(page_title="APP DE MANAGEMENT DE FACTURES I GASTOS", layout="wide")

data_manager = DataManager()
dashboard = Dashboard(data_manager)

st.title("APP DE MANAGEMENT DE FACTURES I GASTOS")

uploaded_file = st.file_uploader("Carrega un fitxer .txt, .pdf o imatge", type=["txt", "pdf", "png", "jpg", "jpeg"])
file_type = None
if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1].lower()
    if st.button("Processa fitxer"):
        try:
            data_manager.load_data_from_any(uploaded_file, file_type)
            st.success(f"Fitxer {file_type.upper()} carregat i processat!")
            # Després de processar, esborra el fitxer de la memòria per evitar reprocessament
            uploaded_file = None
        except RuntimeError as e:
            st.error(str(e))

st.header("GESTIÓ I EDICIÓ DE DADES")
data_manager.edit_data()

dashboard.show()