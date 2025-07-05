import pandas as pd
import os
import streamlit as st
import re
import pdfplumber
import pytesseract
from PIL import Image
import requests
import pdf2image
import json, re
import ollama


class DataManager:
    def __init__(self):
        self.csv_path = os.path.join(os.path.dirname(__file__), '../registro_total.csv')
        self.data = self.load_csv()

    def load_csv(self):
        if os.path.exists(self.csv_path):
            return pd.read_csv(self.csv_path)
        else:
            return pd.DataFrame(columns=[
                "NumeroFactura", "TipusFactura", "Pagador",
                "DadesPagador", "AdrecaPagador", "EmailPagador",
                "Emisor", "DadesEmisor", "AdrecaEmisor", "EmailEmisor",
                "Data", "Productes", "Imports"
            ])

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
                dades_pagador = line.split(':',1)[1].strip()
                import re as _re
                email = _re.search(r'[\w\.-]+@[\w\.-]+', dades_pagador)
                data['DadesPagador'] = dades_pagador
                data['AdrecaPagador'] = _re.sub(r'[\w\.-]+@[\w\.-]+', '', dades_pagador).strip()
                data['EmailPagador'] = email.group(0) if email else ''
            elif line.startswith('Emisor:'):
                data['Emisor'] = line.split(':',1)[1].strip()
            elif line.startswith('Dades_Emisor:'):
                dades_emisor = line.split(':',1)[1].strip()
                email = _re.search(r'[\w\.-]+@[\w\.-]+', dades_emisor)
                data['DadesEmisor'] = dades_emisor
                data['AdrecaEmisor'] = _re.sub(r'[\w\.-]+@[\w\.-]+', '', dades_emisor).strip()
                data['EmailEmisor'] = email.group(0) if email else ''
            elif line.startswith('Data:'):
                data['Data'] = line.split(':',1)[1].strip()
            elif re.match(r'Producte \d+:', line):
                productes.append(line.split(':',1)[1].strip())
            elif re.match(r'Import \d+:', line):
                imports.append(line.split(':',1)[1].strip())
        data['Productes'] = ', '.join(productes)
        data['Imports'] = ', '.join(imports)
        # Elimina antics camps plans si existeixen
        data.pop('DadesPagador', None)
        data.pop('DadesEmisor', None)
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

    def extract_fields_llm(self, text):
        # Extracció de camps amb Ollama local (llama3) i prompt enriquit
        print("extract_fields_llm (Ollama):", text)
        prompt = (
            "Ets un assistent expert en facturació. Analitza el següent text extret d'una factura (pot contenir errors d'OCR o estar desordenat). "
            "Extreu els següents camps en format JSON, amb aquestes claus exactes i seguint aquestes instruccions:\n"
            "- NumeroFactura: El número únic de la factura, tal com apareix al document.\n"
            "- TipusFactura: El tipus de factura (ex: Servei, Producte, Proforma, etc.).\n"
            "- Pagador: El nom o raó social de la persona o empresa que paga la factura.\n"
            "- DadesPagador: Altres dades rellevants del pagador (NIF, CIF, etc.), excloent adreça i email.\n"
            "- AdrecaPagador: L’adreça postal completa del pagador.\n"
            "- EmailPagador: El correu electrònic del pagador.\n"
            "- Emisor: El nom o raó social de l’empresa o persona que emet la factura.\n"
            "- DadesEmisor: Altres dades rellevants de l’emissor (NIF, CIF, etc.), excloent adreça i email.\n"
            "- AdrecaEmisor: L’adreça postal completa de l’emissor.\n"
            "- EmailEmisor: El correu electrònic de l’emissor.\n"
            "- Data: La data d’emissió de la factura.\n"
            "- Productes: Una llista plana, separada per comes, amb el nom de cada producte o servei facturat.\n"
            "- Imports: Una llista plana, separada per comes, amb l’import corresponent a cada producte o servei, en el mateix ordre que a Productes. ÉS IMPORTANT QUE ELS IMPORTS APAREGUIN AMB SÍMBOL CORRESPONENT DE MONEDA, € $ O £ devant de l'import, ja que mes endevant es fara una conversió\n"
            "El text de la factura és:\n" + text
        )
        try:
            print("[Ollama] Enviant prompt a model local llama3...")
            response = ollama.chat(
                model='llama3',
                messages=[
                    {'role': 'system', 'content': 'Ets un assistent expert en facturació.'},
                    {'role': 'user', 'content': prompt}
                ]
            )
            resposta = response['message']['content']
            self.last_llm_response = resposta
            print("[Ollama] Resposta content:", resposta)
            fields = parse_json_robust(resposta)
            if fields:
                print("[Ollama] JSON robust trobat:", fields)
            else:
                print("[Ollama] No s'ha pogut parsejar JSON robustament!")
                fields = {k: '' for k in [
                    "NumeroFactura", "TipusFactura", "Pagador", "DadesPagador", "AdrecaPagador", "EmailPagador",
                    "Emisor", "DadesEmisor", "AdrecaEmisor", "EmailEmisor", "Data", "Productes", "Imports"
                ]}
        except Exception as e:
            print("[Ollama] Error Ollama:", e)
            self.last_llm_response = str(e)
            fields = {k: '' for k in [
                "NumeroFactura", "TipusFactura", "Pagador", "DadesPagador", "AdrecaPagador", "EmailPagador",
                "Emisor", "DadesEmisor", "AdrecaEmisor", "EmailEmisor", "Data", "Productes", "Imports"
            ]}
        print("[Ollama] Camps extrets:", fields)
        return pd.DataFrame([fields])
        # --- FI: Extracció de camps amb Ollama local ---

    def parse_invoice_ai(self, uploaded_file, file_type):
        print(f"parse_invoice_ai: file_type={file_type}")
        text = ""
        if file_type == "pdf":
            images = pdf2image.convert_from_bytes(uploaded_file.read())
            print(f"parse_invoice_ai: PDF convertit a {len(images)} imatges")
            # OCR de totes les pàgines
            text = "\n".join(pytesseract.image_to_string(img, lang='cat+spa+eng') for img in images)
        elif file_type in ["png", "jpg", "jpeg"]:
            image = Image.open(uploaded_file)
            print(f"parse_invoice_ai: Imatge carregada")
            text = pytesseract.image_to_string(image, lang='cat+spa+eng')
        elif file_type == "txt":
            text = uploaded_file.read().decode('utf-8')
            print(f"parse_invoice_ai: TXT carregat, longitud text: {len(text)}")
        else:
            print(f"parse_invoice_ai: Tipus de fitxer no suportat: {file_type}")
            return pd.DataFrame([{k: '' for k in [
                "NumeroFactura", "TipusFactura", "Pagador", "DadesPagador", "AdrecaPagador", "EmailPagador",
                "Emisor", "DadesEmisor", "AdrecaEmisor", "EmailEmisor", "Data", "Productes", "Imports"
            ]}])
        print(f"parse_invoice_ai: Text OCR extret, longitud: {len(text)}")
        result = self.extract_fields_llm(text)
        print(f"parse_invoice_ai: resultat extract_fields_llm: {result}")
        return result

    def load_data_from_any(self, uploaded_file, file_type):
        print(f"load_data_from_any: file_type={file_type}")
        if file_type == "txt":
            content = uploaded_file.read()
            uploaded_file.seek(0)
            if b'Numero de Factura:' in content:
                uploaded_file.seek(0)
                new_data = self.parse_custom_txt(uploaded_file)
            else:
                uploaded_file.seek(0)
                new_data = pd.read_csv(uploaded_file, sep=';', names=self.data.columns)
            print(f"load_data_from_any: new_data={new_data}")
            self.data = pd.concat([self.data, new_data], ignore_index=True)
            self.save_csv()
            print("load_data_from_any: dades desades al CSV")
        else:
            new_data = self.parse_invoice_ai(uploaded_file, file_type)
            print(f"load_data_from_any: new_data={new_data}")
            self.data = pd.concat([self.data, new_data], ignore_index=True)
            self.save_csv()
            print("load_data_from_any: dades desades al CSV")

    def edit_data(self):
        # Permet editar i esborrar files directament amb Streamlit Data Editor
        edited_df = st.data_editor(self.data, num_rows="dynamic", use_container_width=True, key="data_editor")
        if st.button("Desa canvis al CSV"):
            self.data = edited_df.reset_index(drop=True)
            self.save_csv()
            st.success("Canvis desats correctament!")

    def get_data(self):
        return self.data

def parse_json_robust(text):
            # Busca el primer bloc JSON balancejat
            stack = []
            start = None
            for i, c in enumerate(text):
                if c == '{':
                    if start is None:
                        start = i
                    stack.append('{')
                elif c == '}':
                    if stack:
                        stack.pop()
                        if not stack:
                            try:
                                return json.loads(text[start:i+1])
                            except Exception as e:
                                # Intenta arreglar: converteix objectes interns a string
                                import re as _re
                                fixed = _re.sub(r'("[^"]+":)\s*\{[^\}]*\}', r'\1 "[OBJECTE]"', text[start:i+1])
                                try:
                                    return json.loads(fixed)
                                except:
                                    return None
            return None