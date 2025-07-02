import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

class DataManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = pd.read_csv(file_path, dtype=str)

    def get_data(self):
        return self.data

    def edit_data(self):
        # Permet editar i esborrar files directament amb Streamlit Data Editor
        edited_data = st.data_editor(self.data, num_rows="dynamic", use_container_width=True, key="data_editor")
        # Detecta files esborrades
        if len(edited_data) < len(self.data):
            self.data = edited_data.reset_index(drop=True)
            self.data.to_csv(self.file_path, index=False)
            st.success("Files esborrades correctament!")
        elif not edited_data.equals(self.data):
            self.data = edited_data
            self.data.to_csv(self.file_path, index=False)
            st.success("Dades actualitzades correctament!")

    def save_csv(self):
        self.data.to_csv(self.file_path, index=False)

class Dashboard:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def show(self):
        st.header("Dashboard de dades")
        df = self.data_manager.get_data()
        if df.empty:
            st.info("No hi ha dades per mostrar.")
            return
        st.subheader("Visualitza i edita les dades:")
        # Selecció de files per esborrar
        selected = st.multiselect(
            "Selecciona files a esborrar (per NumeroFactura)",
            options=df['NumeroFactura'].astype(str).tolist(),
            help="Selecciona una o més factures per eliminar-les del registre."
        )
        if selected and st.button("Esborra seleccionats"):
            df = df[~df['NumeroFactura'].astype(str).isin(selected)]
            self.data_manager.data = df.reset_index(drop=True)
            self.data_manager.save_csv()
            st.success("Files esborrades correctament!")
        self.data_manager.edit_data()
        st.subheader("Gràfics")
        # Gràfic per TipusFactura
        if 'TipusFactura' in df.columns:
            tipus_counts = df['TipusFactura'].value_counts()
            fig, ax = plt.subplots()
            tipus_counts.plot(kind='bar', ax=ax)
            ax.set_xlabel('Tipus de Factura')
            ax.set_ylabel('Nombre de registres')
            ax.set_title('Registres per Tipus de Factura')
            st.pyplot(fig)
        # Gràfic per Import total per factura
        if 'Imports' in df.columns:
            def suma_imports(x):
                try:
                    return sum(float(i.replace(',', '.')) for i in str(x).split(',') if i.strip())
                except:
                    return 0
            df['TotalFactura'] = df['Imports'].apply(suma_imports)
            fig2, ax2 = plt.subplots()
            if 'NumeroFactura' in df.columns:
                df.plot.bar(x='NumeroFactura', y='TotalFactura', ax=ax2)
                ax2.set_xlabel('Numero de Factura')
                ax2.set_ylabel('Total (€)')
                ax2.set_title('Total per Factura')
                st.pyplot(fig2)
        st.dataframe(df)

def main():
    st.set_page_config(page_title="Dashboard diari", layout="wide")
    file_path = 'src/registro_total.csv'
    data_manager = DataManager(file_path)
    dashboard = Dashboard(data_manager)
    dashboard.show()

if __name__ == "__main__":
    main()