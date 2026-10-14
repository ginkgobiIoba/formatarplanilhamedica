import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import tempfile
import os

# Configuração da página
st.set_page_config(
    page_title="Normalizador de Repasses Médicos",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Normalizador e Analisador de Repasses Médicos")
st.markdown("Suba o relatório em PDF do mês para normalizar os dados via Gemini API e aplicar filtros por procedimento.")

# Sidebar - Configurações
st.sidebar.header("⚙️ Configurações")
api_key = st.sidebar.text_input("Insira sua API Key Gratuita do Gemini:", type="password")

if not api_key:
    st.info("👈 Insira sua API Key do Gemini (gerada no Google AI Studio) no menu lateral para começar.")
    st.stop()

# Configura a chave
genai.configure(api_key=api_key)

# Upload do PDF
uploaded_file = st.file_uploader("Suba o relatório PDF do mês:", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 Processar e Normalizar Documento", type="primary"):
        with st.spinner("Analisando o relatório e extraindo procedimentos..."):
            temp_path = None
            try:
                # 1. Salva o arquivo temporariamente no disco para passar ao Gemini
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_path = tmp_file.name

                model = genai.GenerativeModel('gemini-1.5-pro')
                
                prompt = """
                Você é um especialista em extração de dados médicos.
                Extraia TODOS os procedimentos e itens de repasse deste relatório PDF.
                
                Retorne ESTRITAMENTE um array JSON de objetos com as seguintes chaves:
                - "Nº Atendimento"
                - "Paciente"
                - "Tipo Atendimento"
                - "Cód. TUSS / Item"
                - "Procedimento"
                - "Via de Acesso"
                - "Especialidade"
                - "Função do Médico"
                - "Médico do Repasse"
                - "Médico Responsável"
                - "Convênio"
                - "Plano"
                - "Quantidade"
                - "Data"
                - "% Repasse"
                - "Valor Total (R$)"
                - "Tipo de Registro" (use 'Procedimento' ou 'Item de Repasse')
                
                Não inclua nenhuma introdução ou texto além do JSON.
                """
                
                # 2. Faz o upload informando o caminho temporário no disco
                pdf_file = genai.upload_file(temp_path, mime_type="application/pdf")
                response = model.generate_content([pdf_file, prompt])
                
                # Tratamento do JSON
                raw_json = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(raw_json)
                
                st.session_state['df'] = pd.DataFrame(data)
                st.success("✅ Relatório processado com sucesso!")

            except Exception as e:
                st.error(f"Erro ao processar o documento: {e}")

            finally:
                # 3. Remove o arquivo temporário após o envio
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

# Filtros e visualização
if 'df' in st.session_state:
    df = st.session_state['df']
    
    st.divider()
    st.subheader("🔍 Filtros Dinâmicos")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        medicos = list(df["Médico do Repasse"].unique()) if "Médico do Repasse" in df.columns else []
        medico_sel = st.multiselect("Filtrar por Médico:", options=medicos, default=medicos)
        
    with c2:
        procedimentos = list(df["Procedimento"].unique()) if "Procedimento" in df.columns else []
        procedimento_sel = st.multiselect("Filtrar por Procedimento:", options=procedimentos, default=procedimentos)
        
    with c3:
        tipos = list(df["Tipo de Registro"].unique()) if "Tipo de Registro" in df.columns else []
        tipo_sel = st.multiselect("Tipo de Registro:", options=tipos, default=tipos)
        
    # Filtragem dos dados
    df_filtered = df.copy()
    if medico_sel and "Médico do Repasse" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Médico do Repasse"].isin(medico_sel)]
    if procedimento_sel and "Procedimento" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Procedimento"].isin(procedimento_sel)]
    if tipo_sel and "Tipo de Registro" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Tipo de Registro"].isin(tipo_sel)]
        
    st.subheader(f"📊 Registros Filtrados ({len(df_filtered)} de {len(df)})")
    st.dataframe(df_filtered, use_container_width=True)
    
    # Download
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Tabela Filtrada (CSV)",
        data=csv,
        file_name="repasse_normalizado.csv",
        mime="text/csv",
        type="primary"
    )
