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
        # DEBUG: Mostra la darrera resposta crua de l'LLM local si existeix
        if hasattr(self.data_manager, 'last_llm_response') and self.data_manager.last_llm_response:
            with st.expander("Resposta crua del model local (debug)"):
                st.code(self.data_manager.last_llm_response, language='json')
        if df.empty:
            st.info("No hi ha dades per mostrar.")
            return
        # Selector de pagador
        pagadors = df['Pagador'].dropna().unique().tolist()
        pagador = st.selectbox("Selecciona un pagador", pagadors)
        df_pagador = df[df['Pagador'] == pagador]
        st.write(f"Factures del pagador: {pagador}")
        st.dataframe(df_pagador)
        # Mapa modern amb Folium i punts personalitzats
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
                    coords.append({'lat': lat, 'lon': lon, 'Emisor': row['Emisor'], 'DadesEmisor': row['DadesEmisor']} if lat and lon else None)
                else:
                    coords.append(None)
            unique_emisors['lat'] = [c['lat'] if c else None for c in coords]
            unique_emisors['lon'] = [c['lon'] if c else None for c in coords]
            unique_emisors['popup'] = [f"<b>{c['Emisor']}</b><br>{c['DadesEmisor']}" if c else '' for c in coords]
            df_map = unique_emisors.dropna(subset=['lat','lon'])
            if not df_map.empty:
                # Centra el mapa a la mitjana de les coordenades dels punts
                center_lat = df_map['lat'].mean()
                center_lon = df_map['lon'].mean()
                # Utilitza columnes Streamlit per centrar el mapa
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles='CartoDB positron')
                    for _, row in df_map.iterrows():
                        folium.Marker(
                            location=[row['lat'], row['lon']],
                            popup=folium.Popup(row['popup'], max_width=300),
                            tooltip=row['Emisor'],
                            icon=folium.Icon(color='blue', icon='building', prefix='fa')
                        ).add_to(m)
                    st_folium(m, width=800, height=400)  # Redueix l'alçada del mapa
                # --- Gràfic interactiu modern dins del mateix contenidor ---
                st.markdown("<h4 style='text-align:center; margin-bottom:0.5rem;'>Gràfic interactiu de factures</h4>", unsafe_allow_html=True)
                st.markdown("<div style='margin-top:-1.5rem;'></div>", unsafe_allow_html=True)  # Redueix espai entre mapa i gràfic
                # Prepara dades per a gràfic interactiu
                df_graf = df_map.copy()
                # Conversió de Data a datetime
                if 'Data' in df_graf.columns:
                    df_graf['Data'] = pd.to_datetime(df_graf['Data'], errors='coerce', dayfirst=True)
                # Conversió d'import total
                if 'Imports' in df_graf.columns:
                    def suma_imports(x):
                        try:
                            return sum(float(i.replace(',', '.')) for i in str(x).split(',') if i.strip())
                        except:
                            return 0
                    df_graf['TotalFactura'] = df_graf['Imports'].apply(suma_imports)
                # Filtres interactius
                # Comprova que hi hagi dates vàlides abans de crear el slider
                if 'Data' in df_graf.columns and df_graf['Data'].notnull().any():
                    min_date = df_graf['Data'].min()
                    max_date = df_graf['Data'].max()
                    if pd.isnull(min_date) or pd.isnull(max_date):
                        st.warning("No hi ha dates vàlides per filtrar.")
                        return
                    min_date = min_date.date()
                    max_date = max_date.date()
                    df_graf['Data_date'] = df_graf['Data'].dt.date
                    date_range = st.slider(
                        "Filtra per data de factura",
                        min_value=min_date,
                        max_value=max_date,
                        value=(min_date, max_date),
                        format="DD/MM/YYYY"
                    )
                    df_graf = df_graf[(df_graf['Data_date'] >= date_range[0]) & (df_graf['Data_date'] <= date_range[1])]
                # Filtres addicionals
                # Filtra per Categoria (TipusFactura)
                categories = df_graf['TipusFactura'].dropna().unique().tolist() if 'TipusFactura' in df_graf.columns else []
                if categories:
                    categories_selected = st.multiselect("Filtra per categoria (Tipus de Factura)", categories, default=categories)
                    df_graf = df_graf[df_graf['TipusFactura'].isin(categories_selected)]
                # Filtra per Emisor
                emissors = df_graf['Emisor'].dropna().unique().tolist()
                if len(emissors) > 1:
                    emissors_selected = st.multiselect("Filtra per emisor", emissors, default=emissors)
                    df_graf = df_graf[df_graf['Emisor'].isin(emissors_selected)]
                # Filtra per Producte
                productes = set()
                if 'Productes' in df_graf.columns:
                    for prods in df_graf['Productes'].dropna():
                        for p in [x.strip() for x in prods.split(',')]:
                            if p:
                                productes.add(p)
                productes = sorted(productes)
                if productes:
                    productes_selected = st.multiselect("Filtra per producte pagat", productes, default=productes)
                    mask = df_graf['Productes'].apply(lambda x: any(p in x for p in productes_selected) if pd.notnull(x) else False)
                    df_graf = df_graf[mask]
                # Conversió d'import total
                if 'TotalFactura' in df_graf.columns and df_graf['TotalFactura'].notnull().any():
                    min_import = float(df_graf['TotalFactura'].min())
                    max_import = float(df_graf['TotalFactura'].max())
                    if min_import < max_import:
                        import_range = st.slider("Filtra per import total", min_value=min_import, max_value=max_import, value=(min_import, max_import))
                        df_graf = df_graf[(df_graf['TotalFactura'] >= import_range[0]) & (df_graf['TotalFactura'] <= import_range[1])]
                    else:
                        st.info(f"Totes les factures tenen el mateix import: {min_import} €")
                # Gràfic modern amb Plotly
                import plotly.express as px
                if not df_graf.empty:
                    # Opció per separar per producte
                    separar_per_producte = st.checkbox("Separa el gràfic per producte pagat", value=False)
                    if separar_per_producte and 'Productes' in df_graf.columns:
                        # Explode per producte i calcula import individual
                        df_exploded = df_graf.copy()
                        df_exploded = df_exploded.assign(Producte=df_exploded['Productes'].str.split(','), ImportProducte=df_exploded['Imports'].str.split(','))
                        df_exploded = df_exploded.explode(['Producte', 'ImportProducte'])
                        df_exploded['Producte'] = df_exploded['Producte'].str.strip()
                        df_exploded['ImportProducte'] = df_exploded['ImportProducte'].str.replace(',','.')
                        df_exploded['ImportProducte'] = pd.to_numeric(df_exploded['ImportProducte'], errors='coerce')
                        # Filtra només productes seleccionats
                        df_exploded = df_exploded[df_exploded['Producte'].isin(productes_selected)]
                        fig = px.bar(
                            df_exploded,
                            x='Data',
                            y='ImportProducte',
                            color='Producte',
                            hover_data=['NumeroFactura', 'Producte', 'ImportProducte'],
                            title='Import de cada producte per data',
                            labels={'ImportProducte': 'Import (€)', 'Data': 'Data factura'}
                        )
                        fig.update_layout(barmode='group', xaxis_title='Data', yaxis_title='Import (€)', legend_title='Producte')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        fig = px.bar(
                            df_graf,
                            x='Data',
                            y='TotalFactura',
                            color='Emisor',
                            hover_data=['NumeroFactura', 'Productes', 'TotalFactura'],
                            title='Total de factures per data i emisor',
                            labels={'TotalFactura': 'Import (€)', 'Data': 'Data factura'}
                        )
                        fig.update_layout(barmode='group', xaxis_title='Data', yaxis_title='Total (€)', legend_title='Emisor')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hi ha dades per mostrar amb aquests filtres.")
            return
