import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import ast
import plotly.express as px  # <-- Assegura import global
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
                mesos_options = [m.to_timestamp().to_pydatetime() for m in mesos]
                mesos_labels = [f"{calendar.month_name[m.month]} {m.year}" for m in mesos]
                idx_min = 0
                idx_max = len(mesos_options) - 1
                if idx_max > idx_min:
                    selected_range = st.slider(
                        "Selecciona rang de mesos",
                        min_value=idx_min,
                        max_value=idx_max,
                        value=(idx_min, idx_max),
                        format=None,
                        step=1,
                        key="slider_mesos"
                    )
                    mesos_seleccionats = mesos_options[selected_range[0]:selected_range[1]+1]
                    mesos_labels_seleccionats = mesos_labels[selected_range[0]:selected_range[1]+1]
                    start, end = mesos_seleccionats[0], mesos_seleccionats[-1]
                    mask = (df[data_col] >= start) & (df[data_col] <= end + pd.offsets.MonthEnd(0))
                    df = df[mask]
                    st.markdown(
                        '<div style="margin-bottom: 0.5rem;">' +
                        ' '.join([f'<span style="background-color:#e6f7b6; color:#333; border-radius:8px; padding:4px 10px; margin-right:4px; font-size:0.95em;">{m}</span>' for m in mesos_labels_seleccionats]) +
                        '</div>', unsafe_allow_html=True
                    )
                else:
                    # Només hi ha un mes disponible, mostra'l sense slider
                    mesos_seleccionats = mesos_options
                    mesos_labels_seleccionats = mesos_labels  # CORRECCIÓ: variable ben escrita
                    start, end = mesos_seleccionats[0], mesos_seleccionats[-1]
                    mask = (df[data_col] >= start) & (df[data_col] <= end + pd.offsets.MonthEnd(0))
                    df = df[mask]
                    st.markdown(
                        '<div style="margin-bottom: 0.5rem;">' +
                        ' '.join([f'<span style="background-color:#e6f7b6; color:#333; border-radius:8px; padding:4px 10px; margin-right:4px; font-size:0.95em;">{m}</span>' for m in mesos_labels_seleccionats]) +
                        '</div>', unsafe_allow_html=True
                    )
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

        # --- RESUM GENERAL DE DADES ---
        st.header("RESUM GENERAL DE DADES")
        st.subheader("Resum general")
        if not df.empty:
            # Conversió de Data i Import
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
            def suma_imports(x):
                try:
                    # Accepta llistes, cadenes amb comes, i elimina símbols
                    if isinstance(x, list):
                        return sum(float(str(i).replace('€','').replace('$','').replace(',','.')) for i in x if str(i).strip())
                    elif isinstance(x, str) and x.strip().startswith('['):
                        import ast
                        l = ast.literal_eval(x)
                        return sum(float(str(i).replace('€','').replace('$','').replace(',','.')) for i in l if str(i).strip())
                    else:
                        return sum(float(str(i).replace('€','').replace('$','').replace(',','.')) for i in str(x).split(',') if str(i).strip())
                except Exception:
                    return 0
            if 'Imports' in df.columns:
                df['TotalFactura'] = df['Imports'].apply(suma_imports)
            else:
                df['TotalFactura'] = 0
            # Gastos totals mensuals
            if 'Data' in df.columns:
                df['Mes'] = df['Data'].dt.to_period('M').astype(str)
            else:
                df['Mes'] = ''
            gastos_mensuals = df.groupby('Mes')['TotalFactura'].sum().reset_index()
            st.metric("Gasto total", f"{df['TotalFactura'].sum():.2f} €")
            st.metric("Gasto mensual mitjà", f"{gastos_mensuals['TotalFactura'].mean():.2f} €")
            st.subheader("Gastos totals mensuals")
            # Omple mesos sense dades amb 0
            if not gastos_mensuals.empty:
                # Troba el rang complet de mesos entre el primer i l'últim
                idx = pd.period_range(start=gastos_mensuals['Mes'].min(), end=gastos_mensuals['Mes'].max(), freq='M')
                idx_str = idx.astype(str)
                gastos_mensuals = gastos_mensuals.set_index('Mes').reindex(idx_str, fill_value=0).reset_index().rename(columns={'index': 'Mes'})
            fig = px.line(gastos_mensuals, x='Mes', y='TotalFactura', markers=True, labels={'Mes':'Mes','TotalFactura':'Gasto (€)'}, title='Gasto total per mes')
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
