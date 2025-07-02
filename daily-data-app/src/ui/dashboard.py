import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

class Dashboard:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def geocode_postal_code(self, postal_code):
        # Utilitza l'API de Nominatim (OpenStreetMap)
        url = f"https://nominatim.openstreetmap.org/search?postalcode={postal_code}&country=Spain&format=json&limit=1"
        try:
            response = requests.get(url, headers={"User-Agent": "streamlit-app"})
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        except Exception:
            pass
        return None, None

    def show(self):
        st.header("Gràfic interactiu per Pagador i mapa per ubicació d'Emisor")
        df = self.data_manager.get_data()
        if df.empty:
            st.info("No hi ha dades per mostrar.")
            return
        # Selector de pagador
        pagadors = df['Pagador'].dropna().unique().tolist()
        pagador = st.selectbox("Selecciona un pagador", pagadors)
        df_pagador = df[df['Pagador'] == pagador]
        st.write(f"Factures del pagador: {pagador}")
        st.dataframe(df_pagador)
        # Mapa bonic amb Folium
        if 'DadesEmisor' in df_pagador.columns:
            df_pagador = df_pagador.copy()
            df_pagador['CodiPostalEmisor'] = df_pagador['DadesEmisor'].str.extract(r'(\d{5})')
            st.subheader("Ubicacions de les entitats emissores (codi postal)")
            st.dataframe(df_pagador[['Emisor','DadesEmisor','CodiPostalEmisor']])
            # Geocodificació real amb Nominatim
            coords = []
            # Evita duplicats per codi postal i emisor
            unique_emisors = df_pagador.drop_duplicates(subset=['Emisor','CodiPostalEmisor'])
            for _, row in unique_emisors.iterrows():
                cp = row['CodiPostalEmisor']
                if pd.notnull(cp):
                    lat, lon = self.geocode_postal_code(cp)
                    coords.append({'lat': lat, 'lon': lon, 'Emisor': row['Emisor']} if lat and lon else None)
                else:
                    coords.append(None)
            unique_emisors['lat'] = [c['lat'] if c else None for c in coords]
            unique_emisors['lon'] = [c['lon'] if c else None for c in coords]
            df_map = unique_emisors.dropna(subset=['lat','lon'])
            if not df_map.empty:
                m = folium.Map(location=[41.820, 1.5], zoom_start=8)
                for _, row in df_map.iterrows():
                    folium.Marker(
                        location=[row['lat'], row['lon']],
                        popup=row['Emisor'],
                        tooltip=row['Emisor'],
                        icon=folium.Icon(color='red', icon='info-sign')
                    ).add_to(m)
                st_folium(m, width=700, height=500)
        # Gràfic interactiu: imports per factura d'aquest pagador
        if 'Imports' in df_pagador.columns:
            def suma_imports(x):
                try:
                    return sum(float(i.replace(',', '.')) for i in str(x).split(',') if i.strip())
                except:
                    return 0
            df_pagador['TotalFactura'] = df_pagador['Imports'].apply(suma_imports)
            fig, ax = plt.subplots()
            df_pagador.plot.bar(x='NumeroFactura', y='TotalFactura', ax=ax)
            ax.set_xlabel('Numero de Factura')
            ax.set_ylabel('Total (€)')
            ax.set_title(f'Total per Factura per a {pagador}')
            st.pyplot(fig)
