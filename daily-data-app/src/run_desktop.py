import subprocess
import time
from streamlit_desktop_app import start_desktop_app
import webview
import sys
import os

# Llança el servidor Streamlit en segon pla
streamlit_proc = subprocess.Popen([
    sys.executable, '-m', 'streamlit', 'run', os.path.join(os.path.dirname(__file__), 'main.py')
])

# Espera uns segons perquè el servidor arrenqui
# (pots ajustar el temps si cal)
time.sleep(3)

# Crea la finestra webview apuntant a la URL local de Streamlit
webview.create_window(
    'APP DE MANAGEMENT DE FACTURES I GASTOS',
    'http://localhost:8501',
    width=1200,
    height=800
)

# Inicia pywebview sense forçar backend (Cocoa s'usarà automàticament si pyobjc està instal·lat)
webview.start()

# Quan tanquem la finestra, matem el procés Streamlit
streamlit_proc.terminate()
