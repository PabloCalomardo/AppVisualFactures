# INSTRUCCIONS PER EXECUTAR L'APP DESKTOP A MACOS

1. **Clona el projecte al teu Mac real (no dins d'un workspace Linux, Docker o Codespaces).**

2. **Assegura't que tens Python 3.9+ instal·lat.**

3. **Instal·la les dependències bàsiques:**
   ```bash
   python3 -m pip install --upgrade pip setuptools wheel
   python3 -m pip install -r requirements.txt
   ```

4. **Instal·la pyobjc només a macOS:**
   ```bash
   python3 -m pip install pyobjc
   ```
   Si dóna error, assegura't que tens Xcode Command Line Tools:
   ```bash
   xcode-select --install
   ```
   i torna-ho a provar.

5. **Executa l'app desktop:**
   ```bash
   python3 src/run_desktop.py
   ```

6. **Si tens problemes amb pywebview o pyobjc:**
   - Comprova que la versió de Python sigui la de macOS (no la d'un entorn virtual Linux).
   - Comprova que pyobjc està instal·lat correctament:
     ```bash
     python3 -m pip show pyobjc
     ```
   - Si cal, actualitza pywebview:
     ```bash
     python3 -m pip install --upgrade pywebview
     ```

7. **Recorda:**
   - No pots executar la versió desktop nativa dins de Linux, Docker, Codespaces o WSL.
   - Només la part web (Streamlit) funciona a qualsevol sistema.

---

Si segueixes tenint problemes a macOS real, copia aquí el missatge d'error complet i t'ajudaré a resoldre'l.
