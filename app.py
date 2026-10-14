import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="Repasses Médicos",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Normalizador de Repasses Médicos")

st.markdown("""
Faça upload do PDF e visualize:

- Procedimentos
- Itens de Repasse
- Exportação para Excel
""")

# ==================================================
# FUNÇÕES
# ==================================================

def extrair_texto_pdf(arquivo):

    texto = ""

    with pdfplumber.open(arquivo) as pdf:

        for pagina in pdf.pages:

            pagina_texto = pagina.extract_text()

            if pagina_texto:
                texto += pagina_texto + "\n"

    return texto


def separar_secoes(texto):

    procedimentos = ""
    itens = ""

    proc_match = re.search(
        r"Repasse - Procedimentos(.*?)Repasse - Itens de Repasse",
        texto,
        re.DOTALL
    )

    if proc_match:
        procedimentos = proc_match.group(1)

    itens_match = re.search(
        r"Repasse - Itens de Repasse(.*)",
        texto,
        re.DOTALL
    )

    if itens_match:
        itens = itens_match.group(1)

    return procedimentos, itens


def limpar_linhas(texto):

    linhas = []

    for linha in texto.split("\n"):

        linha = linha.strip()

        if not linha:
            continue

        linhas.append(linha)

    return linhas


def criar_dataframe(linhas):

    return pd.DataFrame({
        "Conteúdo": linhas
    })


def gerar_excel(df_proc, df_itens):

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:

        df_proc.to_excel(
            writer,
            sheet_name="Procedimentos",
            index=False
        )

        df_itens.to_excel(
            writer,
            sheet_name="Itens de Repasse",
            index=False
        )

    buffer.seek(0)

    return buffer


# ==================================================
# UPLOAD
# ==================================================

arquivo = st.file_uploader(
    "Selecione o PDF",
    type=["pdf"]
)

# ==================================================
# PROCESSAMENTO
# ==================================================

if arquivo:

    with st.spinner("Lendo PDF..."):

        texto_completo = extrair_texto_pdf(arquivo)

        texto_proc, texto_itens = separar_secoes(
            texto_completo
        )

        linhas_proc = limpar_linhas(
            texto_proc
        )

        linhas_itens = limpar_linhas(
            texto_itens
        )

        df_proc = criar_dataframe(
            linhas_proc
        )

        df_itens = criar_dataframe(
            linhas_itens
        )

    st.success("✅ PDF processado com sucesso")

    st.metric(
        "Linhas de Procedimentos",
        len(df_proc)
    )

    st.metric(
        "Linhas de Itens",
        len(df_itens)
    )

    # ==================================================
    # ABAS
    # ==================================================

    aba1, aba2 = st.tabs([
        "📋 Procedimentos",
        "📦 Itens de Repasse"
    ])

    # --------------------------------------------------
    # PROCEDIMENTOS
    # --------------------------------------------------

    with aba1:

        busca_proc = st.text_input(
            "Pesquisar em Procedimentos"
        )

        df_proc_filtrado = df_proc.copy()

        if busca_proc:

            df_proc_filtrado = df_proc_filtrado[
                df_proc_filtrado["Conteúdo"].str.contains(
                    busca_proc,
                    case=False,
                    na=False
                )
            ]

        st.dataframe(
            df_proc_filtrado,
            use_container_width=True,
            height=600
        )

    # --------------------------------------------------
    # ITENS
    # --------------------------------------------------

    with aba2:

        busca_itens = st.text_input(
            "Pesquisar em Itens"
        )

        df_itens_filtrado = df_itens.copy()

        if busca_itens:

            df_itens_filtrado = df_itens_filtrado[
                df_itens_filtrado["Conteúdo"].str.contains(
                    busca_itens,
                    case=False,
                    na=False
                )
            ]

        st.dataframe(
            df_itens_filtrado,
            use_container_width=True,
            height=600
        )

    # ==================================================
    # DOWNLOAD EXCEL
    # ==================================================

    excel_file = gerar_excel(
        df_proc,
        df_itens
    )

    st.download_button(
        label="📥 Baixar Excel",
        data=excel_file,
        file_name="repasses_medicos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ==================================================
    # DEBUG OPCIONAL
    # ==================================================

    with st.expander("Visualizar texto extraído do PDF"):

        st.text_area(
            "Texto Completo",
            texto_completo,
            height=400
        )
