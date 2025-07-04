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
if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1].lower()
    try:
        data_manager.load_data_from_any(uploaded_file, file_type)
        st.success(f"Fitxer {file_type.upper()} carregat i processat!")
    except RuntimeError as e:
        st.error(str(e))

st.header("GESTIÓ I EDICIÓ DE DADES")
data_manager.edit_data()

dashboard.show()

st.header("RESUM GENERAL DE DADES")
df = data_manager.get_data()

st.subheader("Resum general")
if not df.empty:
    # Conversió de Data i Import
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
    def suma_imports(x):
        try:
            return sum(float(i.replace(',', '.')) for i in str(x).split(',') if i.strip())
        except:
            return 0
    df['TotalFactura'] = df['Imports'].apply(suma_imports)
    # Gastos totals mensuals
    df['Mes'] = df['Data'].dt.to_period('M').astype(str)  # Converteix Period a str per evitar error de serialització
    gastos_mensuals = df.groupby('Mes')['TotalFactura'].sum().reset_index()
    st.metric("Gasto total", f"{df['TotalFactura'].sum():.2f} €")
    st.metric("Gasto mensual mitjà", f"{gastos_mensuals['TotalFactura'].mean():.2f} €")
    st.subheader("Gastos totals mensuals")
    import plotly.express as px
    fig = px.bar(gastos_mensuals, x='Mes', y='TotalFactura', labels={'Mes':'Mes','TotalFactura':'Gasto (€)'}, title='Gasto total per mes')
    st.plotly_chart(fig, use_container_width=True)
    # Percentatge per categoria
    if 'TipusFactura' in df.columns:
        per_categoria = df.groupby('TipusFactura')['TotalFactura'].sum().reset_index()
        per_categoria['Percentatge'] = 100 * per_categoria['TotalFactura'] / per_categoria['TotalFactura'].sum()
        st.subheader("Percentatge de gasto per categoria")
        fig2 = px.pie(per_categoria, names='TipusFactura', values='TotalFactura', title='Distribució per categoria', hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(per_categoria[['TipusFactura','TotalFactura','Percentatge']].round(2))
    # Percentatge per emisor
    if 'Emisor' in df.columns:
        per_emisor = df.groupby('Emisor')['TotalFactura'].sum().reset_index()
        per_emisor['Percentatge'] = 100 * per_emisor['TotalFactura'] / per_emisor['TotalFactura'].sum()
        st.subheader("Percentatge de gasto per emisor")
        st.dataframe(per_emisor[['Emisor','TotalFactura','Percentatge']].round(2))
else:
    st.info("No hi ha dades per mostrar.")