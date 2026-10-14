import streamlit as st
import pandas as pd
from google import genai
import json
import tempfile
import os
import re
import time
from io import BytesIO

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="Normalizador de Repasses Médicos",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Normalizador e Analisador de Repasses Médicos")

st.markdown("""
Faça upload do relatório PDF e o sistema irá:

- Extrair procedimentos
- Extrair itens de repasse
- Separar em abas
- Permitir filtros
- Exportar para Excel
""")

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.header("⚙️ Configurações")

api_key = st.sidebar.text_input(
    "Gemini API Key",
    type="password"
).strip()

if not api_key:
    st.info("👈 Informe sua API Key do Gemini.")
    st.stop()

# ==================================================
# FUNÇÕES
# ==================================================

def gerar_com_retry(client, contents):

    ultimo_erro = None

    for tentativa in range(5):

        try:
            return client.models.generate_content(
                model="gemini-3.8-flash",
                contents=contents
            )

        except Exception as e:

            ultimo_erro = e

            if "503" in str(e) or "UNAVAILABLE" in str(e):

                espera = (tentativa + 1) * 5

                st.warning(
                    f"Tentativa {tentativa + 1}/5. "
                    f"Gemini indisponível. "
                    f"Aguardando {espera}s..."
                )

                time.sleep(espera)

            else:
                raise

    raise ultimo_erro


def extrair_json(texto):

    texto = texto.strip()

    texto = texto.replace("```json", "")
    texto = texto.replace("```", "")

    match = re.search(r"\{.*\}", texto, re.DOTALL)

    if not match:
        raise Exception(
            "Não foi possível localizar um JSON válido na resposta."
        )

    return json.loads(match.group())


def gerar_excel(df_proc, df_itens):

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


# ==================================================
# UPLOAD
# ==================================================

uploaded_file = st.file_uploader(
    "Suba o PDF do relatório",
    type=["pdf"]
)

# ==================================================
# PROCESSAMENTO
# ==================================================

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

Analise o PDF enviado.

Retorne APENAS um JSON válido.

Formato OBRIGATÓRIO:

{
  "procedimentos": [
    {
      "Atendimento": "",
      "Paciente": "",
      "Procedimento": "",
      "Especialidade": "",
      "MedicoRepasse": "",
      "Convenio": "",
      "Plano": "",
      "Data": "",
      "Quantidade": "",
      "Valor": ""
    }
  ],

  "itens": [
    {
      "Atendimento": "",
      "Paciente": "",
      "Item": "",
      "MedicoRepasse": "",
      "Data": "",
      "Quantidade": "",
      "Valor": ""
    }
  ]
}

REGRAS:

- Não use markdown
- Não use ```json
- Não escreva explicações
- Retorne somente JSON
- Separe procedimentos em "procedimentos"
- Separe itens de repasse em "itens"
"""

                response = gerar_com_retry(
                    client,
                    [uploaded_pdf, prompt]
                )

                resultado = extrair_json(
                    response.text
                )

                procedimentos = resultado.get(
                    "procedimentos",
                    []
                )

                itens = resultado.get(
                    "itens",
                    []
                )

                df_proc = pd.DataFrame(
                    procedimentos
                )

                df_itens = pd.DataFrame(
                    itens
                )

                st.session_state["df_proc"] = df_proc
                st.session_state["df_itens"] = df_itens

                st.success(
                    f"✅ Processado com sucesso! "
                    f"{len(df_proc)} procedimentos e "
                    f"{len(df_itens)} itens encontrados."
                )

        except Exception as e:

            st.error(
                f"Erro ao processar o documento: {e}"
            )

        finally:

            if (
                temp_path
                and os.path.exists(temp_path)
            ):
         
