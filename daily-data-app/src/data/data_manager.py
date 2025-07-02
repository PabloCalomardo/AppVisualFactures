import pandas as pd
import os
import streamlit as st
import re

class DataManager:
    def __init__(self):
        self.csv_path = os.path.join(os.path.dirname(__file__), '../registro_total.csv')
        self.data = self.load_csv()

    def load_csv(self):
        if os.path.exists(self.csv_path):
            return pd.read_csv(self.csv_path)
        else:
            return pd.DataFrame(columns=["NumeroFactura", "TipusFactura", "Pagador", "DadesPagador", "Emisor", "DadesEmisor", "Data", "Productes", "Imports"])

    def save_csv(self):
        self.data.to_csv(self.csv_path, index=False)

    def parse_custom_txt(self, uploaded_file):
        content = uploaded_file.read().decode('utf-8')
        lines = content.splitlines()
        data = {}
        productes = []
        imports = []
        for line in lines:
            if line.startswith('Numero de Factura:'):
                data['NumeroFactura'] = line.split(':',1)[1].strip()
            elif line.startswith('Tipus Factura:'):
                data['TipusFactura'] = line.split(':',1)[1].strip()
            elif line.startswith('Pagador:'):
                data['Pagador'] = line.split(':',1)[1].strip()
            elif line.startswith('Dades_Pagador:'):
                data['DadesPagador'] = line.split(':',1)[1].strip()
            elif line.startswith('Emisor:'):
                data['Emisor'] = line.split(':',1)[1].strip()
            elif line.startswith('Dades_Emisor:'):
                data['DadesEmisor'] = line.split(':',1)[1].strip()
            elif line.startswith('Data:'):
                data['Data'] = line.split(':',1)[1].strip()
            elif re.match(r'Producte \d+:', line):
                productes.append(line.split(':',1)[1].strip())
            elif re.match(r'Import \d+:', line):
                imports.append(line.split(':',1)[1].strip())
        data['Productes'] = ', '.join(productes)
        data['Imports'] = ', '.join(imports)
        return pd.DataFrame([data])

    def load_data_from_txt(self, uploaded_file):
        content = uploaded_file.read()
        uploaded_file.seek(0)
        if b'Numero de Factura:' in content:
            uploaded_file.seek(0)
            new_data = self.parse_custom_txt(uploaded_file)
        else:
            uploaded_file.seek(0)
            new_data = pd.read_csv(uploaded_file, sep=';', names=self.data.columns)
        self.data = pd.concat([self.data, new_data], ignore_index=True)
        self.save_csv()

    def edit_data(self):
        # Permet editar i esborrar files directament amb Streamlit Data Editor
        edited_df = st.data_editor(self.data, num_rows="dynamic", use_container_width=True, key="data_editor")
        if st.button("Desa canvis al CSV"):
            self.data = edited_df.reset_index(drop=True)
            self.save_csv()
            st.success("Canvis desats correctament!")

    def get_data(self):
        return self.data