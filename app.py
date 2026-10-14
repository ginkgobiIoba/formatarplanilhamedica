import streamlit as st
import pandas as pd
from google import genai
import json
import tempfile
import os
import re
import time
from io import BytesIO

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Normalizador de Repasses Médicos",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Normalizador e Analisador de Repasses Médicos")

st.markdown(
    """
    Faça upload do relatório PDF e o sistema irá:
    - Extrair procedimentos
    - Extrair itens de repasse
    - Separar em abas
    - Permitir filtros
    - Exportar para Excel
    """
)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.header("⚙️ Configurações")

raw_api_key = st.sidebar.text_input(
    "Gemini API Key",
    type="password"
)

api_key = raw_api_key.strip() if raw_api_key else ""

if not api_key:
    st.info("👈 Informe sua API Key do Gemini.")
    st.stop()

# --------------------------------------------------
# FUNÇÕES
# --------------------------------------------------

def gerar_com_retry(client, contents):
    """
    Retry automático para erros 503.
    """

    ultimo_erro = None

    for tentativa in range(5):

        try:
            return client.models.generate_content(
                model="gemini-3.8-flash",
                contents=contents
            )

        except Exception as e:

            ultimo_erro = e

            erro_str = str(e)

            if "503" in erro_str or "UNAVAILABLE" in erro_str:

                espera = (tentativa + 1) * 5

                st.warning(
                    f"Tentativa {tentativa+1}/5. "
                    f"Gemini indisponível. "
                    f"Aguardando {espera}s..."
                )

                time.sleep(espera)

            else:
                raise e

    raise ultimo_erro


def extrair_json(texto):
    """
    Extrai JSON mesmo quando o Gemini
    devolve markdown ou texto extra.
    """

    texto = texto.strip()

    texto = texto.replace("```json", "")
    texto = texto.replace("```", "")

    match = re.search(r"\{.*\}", texto, re.DOTALL)

    if match:
        return json.loads(match.group())

    raise Exception("Não foi possível localizar um JSON válido na resposta.")


def gerar_excel(df_proc, df_itens):
    """
    Gera Excel com duas abas.
    """

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df_proc.to_excel(
            writer,
            sheet_name="Procedimentos",
            index=False
        )

        df_itens.to_excel(
            writer,
            sheet_name="Itens",
            index=False
        )

    output.seek(0)

    return output


# --------------------------------------------------
# UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Suba o PDF do relatório",
    type=["pdf"]
)

# --------------------------------------------------
# PROCESSAMENTO
# --------------------------------------------------

if uploaded_file is not None:

    if st.button(
        "🚀 Processar Documento",
        type="primary"
    ):

        temp_path = None

        try:

            with st.spinner("Processando relatório..."):

                client = genai.Client(
                    api_key=api_key
                )

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".pdf"
                ) as tmp_file:

                    tmp_file.write(
                        uploaded_file.getvalue()
                    )

                    temp_path = tmp_file.name

                uploaded_pdf = client.files.upload(
                    file=temp_path
                )

                prompt = """
Você é especialista em auditoria e repasse médico.

Analise o PDF.

Retorne APENAS um JSON válido.

Formato obrigatório:

{
  "procedimentos": [
    {
      "Atendimento":"",
      "Paciente":"",
      "Procedimento":"",
      "Especialidade":"",
      "MedicoRepasse":"",
      "Convenio":"",
      "Plano":"",
      "Data":"",
      "Quantidade":"",
      "Valor":""
    }
  ],

  "itens": [
    {
      "Atendimento":"",
      "Paciente":"",
      "Item":"",
 
