import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import ast
import plotly.express as px
import calendar

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
        st.header("Visualització de factures i ubicacions")
        df = self.data_manager.get_data().copy()
        if df.empty:
            st.info("No hi ha dades per mostrar.")
            return
        # --- Filtre de mesos ---
        # Detecta la columna de data
        data_col = None
        for possible in ['Data', 'Fecha', 'Date', 'data', 'fecha', 'date']:
            if possible in df.columns:
                data_col = possible
                break
        mesos_disponibles = []
        mesos_map = {}
        selected_mesos = []
        if data_col:
            # Guarda els valors originals per a parseig fila a fila
            original_dates = df[data_col].copy()
            # Intenta parsejar primer amb dayfirst=True, després amb dayfirst=False per cobrir DD/MM/AAAA i MM/DD/AAAA
            df[data_col] = pd.to_datetime(df[data_col], errors='coerce', dayfirst=True)
            # Torna a intentar amb dayfirst=True si hi ha NaT (per evitar warning de pandas)
            if df[data_col].isna().any():
                df.loc[df[data_col].isna(), data_col] = pd.to_datetime(original_dates[df[data_col].isna()], errors='coerce', dayfirst=True)
            # Si encara hi ha NaT, intenta parsejar fila a fila amb formats habituals amb guions, usant el valor original
            if df[data_col].isna().any():
                mask_nat = df[data_col].isna()
                for idx in df[mask_nat].index:
                    raw_val = str(original_dates.at[idx])
                    parsed = pd.NaT
                    for fmt in ("%d-%m-%Y", "%m-%d-%Y", "%Y-%m-%d"):
                        try:
                            parsed = pd.to_datetime(raw_val, format=fmt, errors='raise')
                            break
                        except Exception:
                            continue
                    df.at[idx, data_col] = parsed
            df = df.dropna(subset=[data_col])
            mesos = df[data_col].dt.to_period('M').dropna().unique()
            mesos = sorted(mesos)
            if mesos:
                min_mes = mesos[0].to_timestamp().to_pydatetime()
                max_mes = mesos[-1].to_timestamp().to_pydatetime()
                # Slider amb rang de mesos
                if(min_mes < max_mes):
                    slider_value = st.slider(
                        "Selecciona rang de mesos",
                        min_value=min_mes,
                        max_value=max_mes,
                        value=(min_mes, max_mes),
                        format="%B %Y"
                    )
                    # Filtra el dataframe segons el rang seleccionat
                    start, end = pd.to_datetime(slider_value[0]), pd.to_datetime(slider_value[1])
                    mask = (df[data_col] >= start) & (df[data_col] <= end + pd.offsets.MonthEnd(0))
                    df = df[mask]
        # Comprovació robusta de columnes essencials
        for col in ['Imports', 'Productes']:
            if col not in df.columns:
                st.error(f"El fitxer de dades no conté la columna obligatòria: '{col}'. Carrega un CSV amb aquesta columna.")
                return
        # --- Filtres seleccionadors ---
        # --- Emissors ---
        emissors = df['Emisor'].unique().tolist() if 'Emisor' in df.columns else []
        emissors_labels = ['Tots'] + emissors
        key_emissors = 'selected_emissors'
        prev_emissors = st.session_state.get(key_emissors, ['Tots'])
        # Lògica UX: si totes seleccionades o 'Tots' + altres, només 'Tots'
        if set(prev_emissors) == set(emissors) or ('Tots' in prev_emissors and len(prev_emissors) > 1):
            prev_emissors = ['Tots']
            st.session_state[key_emissors] = ['Tots']
        selected_emissors = st.multiselect("Selecciona emissors a mostrar", emissors_labels, default=['Tots'], key=key_emissors)
        # Si l'usuari selecciona totes manualment, converteix-ho a ['Tots'] i força rerun
        if set(selected_emissors) == set(emissors):
            st.session_state[key_emissors] = ['Tots']
            st.experimental_rerun()
        # Si selecciona 'Tots' + altres, només 'Tots' i rerun
        if 'Tots' in selected_emissors and len(selected_emissors) > 1:
            st.session_state[key_emissors] = ['Tots']
            st.experimental_rerun()
        # Si 'Tots' està seleccionat o res seleccionat, selecciona tots els emissors
        if 'Tots' in selected_emissors or not selected_emissors:
            selected_emissors = emissors
        else:
            selected_emissors = [e for e in selected_emissors if e != 'Tots']
        # --- Productes ---
        productes = set()
        if 'Productes' in df.columns:
            for prods in df['Productes'].dropna():
                if isinstance(prods, str) and prods.strip().startswith('['):
                    try:
                        l = ast.literal_eval(prods)
                        for p in l:
                            productes.add(str(p).strip())
                    except:
                        continue
                else:
                    for p in str(prods).split(','):
                        productes.add(p.strip())
        productes = sorted([p for p in productes if p])
        productes_labels = ['Tots'] + productes
        key_productes = 'selected_productes'
        prev_productes = st.session_state.get(key_productes, ['Tots'])
        if set(prev_productes) == set(productes) or ('Tots' in prev_productes and len(prev_productes) > 1):
            prev_productes = ['Tots']
            st.session_state[key_productes] = ['Tots']
        selected_productes = st.multiselect("Selecciona productes a mostrar", productes_labels, default=['Tots'], key=key_productes)
        if set(selected_productes) == set(productes):
            st.session_state[key_productes] = ['Tots']
            st.experimental_rerun()
        if 'Tots' in selected_productes and len(selected_productes) > 1:
            st.session_state[key_productes] = ['Tots']
            st.experimental_rerun()
        if 'Tots' in selected_productes or not selected_productes:
            selected_productes = productes
        else:
            selected_productes = [p for p in selected_productes if p != 'Tots']
        df_filt = df[df['Emisor'].isin(selected_emissors)]
        if 'Productes' in df_filt.columns:
            def prod_match(row):
                if isinstance(row, str) and row.strip().startswith('['):
                    try:
                        l = ast.literal_eval(row)
                        return any(p in l for p in selected_productes)
                    except:
                        return False
                else:
                    return any(p in row for p in selected_productes)
            df_filt = df_filt[df_filt['Productes'].apply(prod_match)]
        # --- Pregunta mode gràfic ---
        mode = st.radio("Com vols mostrar els gràfics?", ["Per emissor", "Per producte venut"])
        # --- Layout: mapa petit + gràfic de percentatges al costat ---
        st.subheader("Mapa d'ubicacions de pagadors i emissors i gràfic de percentatges")
        col1, col2 = st.columns([1,2], gap="medium")
        with col1:
            m = folium.Map(location=[41.4, 2.16], zoom_start=6, tiles='CartoDB positron', width=350, height=250)
            for idx, row in df_filt.iterrows():
                for tipus, col in [("Pagador", "AdrecaPagador"), ("Emisor", "AdrecaEmisor")]:
                    adreca = row.get(col, None)
                    if pd.notnull(adreca) and adreca:
                        lat, lon = self.geocode_postal_code(adreca.split()[-1])
                        if lat and lon:
                            folium.Marker(
                                location=[lat, lon],
                                popup=f"{tipus}: {row.get(tipus, '')}<br>Adreça: {adreca}",
                                icon=folium.Icon(color='blue' if tipus=="Pagador" else 'green')
                            ).add_to(m)
            st_folium(m, width=350, height=250, returned_objects=[])
        with col2:
            # --- Gràfic de percentatges ---
            if mode == "Per emissor":
                df_filt['ImportTotal'] = df_filt['Imports'].apply(lambda x: sum([float(i.replace('€','').replace('$','').replace(',','.')) for i in ast.literal_eval(x)] if isinstance(x, str) and x.strip().startswith('[') else [float(i.replace('€','').replace('$','').replace(',','.')) for i in str(x).split(',') if i.strip()]))
                total = df_filt['ImportTotal'].sum()
                df_filt['Percentatge'] = df_filt['ImportTotal'] / total * 100 if total else 0
                fig2 = px.pie(df_filt, names='Emisor', values='Percentatge', title='Percentatge de cada emissor respecte el total')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                producte_imports = {}
                for idx, row in df_filt.iterrows():
                    prods = ast.literal_eval(row['Productes']) if isinstance(row['Productes'], str) and row['Productes'].strip().startswith('[') else [p.strip() for p in str(row['Productes']).split(',')]
                    imps = ast.literal_eval(row['Imports']) if isinstance(row['Imports'], str) and row['Imports'].strip().startswith('[') else [i.strip() for i in str(row['Imports']).split(',')]
                    for p, imp in zip(prods, imps):
                        imp_num = float(imp.replace('€','').replace('$','').replace(',','.'))
                        producte_imports[p] = producte_imports.get(p, 0) + imp_num
                df_prod = pd.DataFrame(list(producte_imports.items()), columns=['Producte','ImportTotal'])
                total = df_prod['ImportTotal'].sum()
                df_prod['Percentatge'] = df_prod['ImportTotal'] / total * 100 if total else 0
                fig2 = px.pie(df_prod, names='Producte', values='Percentatge', title='Percentatge de cada producte respecte el total')
                st.plotly_chart(fig2, use_container_width=True)
        # --- Gràfic de barres sota el layout ---
        # Elimina marges i padding verticals entre el mapa/percentatge i el gràfic de barres
        st.markdown("""
            <style>
            .block-container {padding-top: 1rem !important;}
            .stSubheader {margin-bottom: 0.2rem !important;}
            .stPlotlyChart {margin-top: 0rem !important; margin-bottom: 0.2rem !important;}
            .stDataFrame {margin-top: 0.2rem !important;}
            .element-container:has(.folium-map) {margin-bottom: 0px !important; padding-bottom: 0px !important;}
            .folium-map {margin-bottom: 0px !important;}
            /* Elimina espai vertical entre columnes (mapa/grafic) i el següent element */
            div[data-testid="column"] {margin-bottom: 0rem !important;}
            /* Elimina padding i margin de la fila de columnes */
            div[data-testid="stHorizontalBlock"] {margin-bottom: 0rem !important; padding-bottom: 0rem !important;}
            </style>
        """, unsafe_allow_html=True)
        # Mostra el gràfic d'import just després del layout, sense subheader ni espai extra
        if mode == "Per emissor":
            # Agrupa per Emisor i suma imports per garantir que es mostren tots els emissors
            df_filt['Emisor'] = df_filt['Emisor'].astype(str)
            df_grouped = df_filt.groupby('Emisor', as_index=False)['ImportTotal'].sum()
            df_grouped = pd.DataFrame({'Emisor': selected_emissors}) \
                .merge(df_grouped, on='Emisor', how='left').fillna({'ImportTotal': 0})
            emissors_zero = df_grouped[df_grouped['ImportTotal'] == 0]['Emisor'].tolist()
            if emissors_zero:
                st.warning(f"Els següents emissors seleccionats tenen import total 0 i es mostren al gràfic: {', '.join(emissors_zero)}")
            fig = px.bar(df_grouped, x='Emisor', y='ImportTotal', title='Import per emissor', color_discrete_sequence=['#b6e388', '#f7e6a6', '#f7c873', '#e6f7b6', '#f7e6a6'])
            fig.update_xaxes(type='category')
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_grouped, use_container_width=True)
        else:
            df_prod = pd.DataFrame(list(producte_imports.items()), columns=['Producte','ImportTotal'])
            fig = px.bar(df_prod, x='Producte', y='ImportTotal', title='Import per producte venut', color_discrete_sequence=['#b6e388', '#f7e6a6', '#f7c873', '#e6f7b6', '#f7e6a6'])
            st.plotly_chart(fig, use_container_width=True)

        # --- Estil Streamlit: fons blanc, components i textos verd/groc foscos, i eliminació barra blanca sota el mapa ---
        st.markdown('''
            <style>
            .block-container {padding-top: 1rem !important;}
            .stSubheader {margin-bottom: 0.2rem !important;}
            .stPlotlyChart {margin-top: 0.2rem !important; margin-bottom: 0.2rem !important;}
            .stDataFrame {margin-top: 0.2rem !important;}
            /* Elimina marges i padding extra sota el mapa */
            .element-container:has(.folium-map) {margin-bottom: 0px !important; padding-bottom: 0px !important;}
            .folium-map {margin-bottom: 0px !important;}
            </style>
        ''', unsafe_allow_html=True)
