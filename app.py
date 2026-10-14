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
# CONFIGURAÇÃO DA PÁGINA
# ==================================================

st.set_page_config(
    page_title="Normalizador de Repasses Médicos",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Normalizador e Analisador de Repasses Médicos")

st.markdown("""
Faça upload do relatório PDF do mês e o sistema irá:
- Extrair procedimentos
- Extrair itens de repasse
- Separar em abas interativas na tela
- Permitir filtros por médico
- Exportar o resultado formatado para Excel (.xlsx)
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
    st.info("👈 Informe sua API Key do Gemini na barra lateral para começar.")
    st.stop()

# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================

def gerar_com_retry(client, contents):
    """Tenta chamar o modelo Gemini com retry em caso de indisponibilidade (503)."""
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
                    f"Tentativa {tentativa + 1}/5. Gemini indisponível no momento. "
                    f"Aguardando {espera}s para tentar novamente..."
                )
                time.sleep(espera)
            else:
                raise
    raise ultimo_erro


def extrair_json(texto):
    """Extrai e valida o objeto JSON do texto retornado pelo modelo."""
    texto = texto.strip()
    texto = texto.replace("```json", "").replace("```", "")
    
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if not match:
        raise Exception("Não foi possível localizar um JSON válido na resposta do modelo.")
        
    return json.loads(match.group())


def gerar_excel(df_proc, df_itens):
    """Gera um arquivo Excel em memória com duas abas."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
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
# UPLOAD DE ARQUIVO
# ==================================================

uploaded_file = st.file_uploader(
    "Suba o PDF do relatório mensal:",
    type=["pdf"]
)

# ==================================================
# PROCESSAMENTO DO DOCUMENTO
# ==================================================

if uploaded_file is not None:
    if st.button("🚀 Processar Documento", type="primary"):
        temp_path = None
        try:
            with st.spinner("Processando relatório e extraindo dados com o Gemini..."):
                client = genai.Client(api_key=api_key)

                # Salva o PDF em arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_path = tmp_file.name

                # Upload do arquivo para a API do Gemini
                uploaded_pdf = client.files.upload(file=temp_path)

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

                resultado = extrair_json(response.text)

                procedimentos = resultado.get("procedimentos", [])
                itens = resultado.get("itens", [])

                df_proc = pd.DataFrame(procedimentos)
                df_itens = pd.DataFrame(itens)

                # Salva os DataFrames na sessão
                st.session_state["df_proc"] = df_proc
                st.session_state["df_itens"] = df_itens

                st.success(
                    f"✅ Processado com sucesso! "
                    f"{len(df_proc)} procedimentos e "
                    f"{len(df_itens)} itens de repasse encontrados."
                )

        except Exception as e:
            st.error(f"Erro ao processar o documento: {e}")

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

# ==================================================
# VISUALIZAÇÃO, FILTROS E EXPORTAÇÃO
# ==================================================

if "df_proc" in st.session_state and "df_itens" in st.session_state:
    df_proc = st.session_state["df_proc"]
    df_itens = st.session_state["df_itens"]

    st.divider()
    st.subheader("📊 Visualização e Filtros")

    aba_proc, aba_itens = st.tabs(["📋 Procedimentos", "📦 Itens de Repasse"])

    # --- ABA 1: PROCEDIMENTOS ---
    with aba_proc:
        if not df_proc.empty:
            medicos = list(df_proc["MedicoRepasse"].unique()) if "MedicoRepasse" in df_proc.columns else []
            medicos_sel = st.multiselect(
                "Filtrar por Médico (Procedimentos):",
                options=medicos,
                default=medicos
            )

            df_proc_filtrado = df_proc.copy()
            if medicos_sel and "MedicoRepasse" in df_proc_filtrado.columns:
                df_proc_filtrado = df_proc_filtrado[df_proc_filtrado["MedicoRepasse"].isin(medicos_sel)]

            st.dataframe(df_proc_filtrado, use_container_width=True)
        else:
            st.info("Nenhum procedimento encontrado.")

    # --- ABA 2: ITENS DE REPASSE ---
    with aba_itens:
        if not df_itens.empty:
            medicos_i = list(df_itens["MedicoRepasse"].unique()) if "MedicoRepasse" in df_itens.columns else []
            medicos_i_sel = st.multiselect(
                "Filtrar por Médico (Itens):",
                options=medicos_i,
                default=medicos_i
            )

            df_itens_filtrado = df_itens.copy()
            if medicos_i_sel and "MedicoRepasse" in df_itens_filtrado.columns:
                df_itens_filtrado = df_itens_filtrado[df_itens_filtrado["MedicoRepasse"].isin(medicos_i_sel)]

            st.dataframe(df_itens_filtrado, use_container_width=True)
        else:
            st.info("Nenhum item de repasse encontrado.")

    # --- EXPORTAÇÃO PARA EXCEL ---
    st.divider()
    excel_bytes = gerar_excel(df_proc, df_itens)

    st.download_button(
        label="📥 Baixar Relatório em Excel (.xlsx)",
        data=excel_bytes,
        file_name="relatorio_repasse_normalizado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
