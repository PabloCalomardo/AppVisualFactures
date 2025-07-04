# INSTRUCCIONS OBLIGATÒRIES PER UTILITZAR L'APP AMB EXTRACCIÓ INTEL·LIGENT DE FACTURES (HuggingFace)

Aquesta app NOMÉS funciona amb el model gratuït 'bigscience/bloomz-560m' de HuggingFace per extreure camps de factures (PDF, imatge, TXT).

## Passos OBLIGATORIS:

1. **Crea un compte gratuït a HuggingFace:**
   https://huggingface.co/join

2. **Obté el teu token d'accés personal:**
   - Ves a https://huggingface.co/settings/tokens
   - Clica "New token" (amb permís "Read")
   - Copia el token (comença per `hf_...`)

3. **Exporta la variable d'entorn HF_TOKEN abans d'executar l'app:**
   ```bash
   export HF_TOKEN=hf_... # (enganxa aquí el teu token)
   streamlit run src/main.py
   ```

4. **Si NO defineixes la variable d'entorn HF_TOKEN, l'app NO funcionarà.**

---

- L'app NO utilitza OpenAI ni cap altre LLM de pagament.
- Pots canviar de model HuggingFace a `data_manager.py` si vols provar-ne d'altres.
- Si tens dubtes, demana ajuda!
