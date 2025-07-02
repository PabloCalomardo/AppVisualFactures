import streamlit as st
from data.data_manager import DataManager
from ui.dashboard import Dashboard

st.set_page_config(page_title="Daily Data Management App", layout="wide")

data_manager = DataManager()
dashboard = Dashboard(data_manager)

st.title("Daily Data Management App")

uploaded_file = st.file_uploader("Carrega un fitxer .txt", type="txt")
if uploaded_file is not None:
    data_manager.load_data_from_txt(uploaded_file)
    st.success("Fitxer carregat correctament!")

if st.button("Mostrar Dashboard"):
    dashboard.show()