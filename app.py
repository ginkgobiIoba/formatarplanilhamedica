import streamlit as st
import pdfplumber

st.set_page_config(
    page_title="Leitor PDF Médico",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Leitor de Relatório Médico")

arquivo = st.file_uploader(
    "Selecione o PDF",
    type=["pdf"]
)

if arquivo:

    texto_completo = ""

    with pdfplumber.open(arquivo) as pdf:

        st.success(f"PDF carregado. Total de páginas: {len(pdf.pages)}")

        for pagina in pdf.pages:

            texto = pagina.extract_text()

            if texto:
                texto_completo += texto
                texto_completo += "\n\n"

    st.subheader("Texto extraído")

    st.text_area(
        "Conteúdo",
        texto_completo,
        height=500
    )
