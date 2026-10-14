import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# ==================================================
# CONFIGURAÇÃO
# ==================================================

st.set_page_config(
    page_title="Repasses Médicos",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Normalizador de Repasses Médicos")

st.markdown("""
Faça upload do PDF para:

- Extrair procedimentos
- Extrair itens de repasse
- Filtrar registros
- Visualizar totais
- Exportar para Excel
""")

# ==================================================
# FUNÇÕES
# ==================================================

def extrair_texto_pdf(arquivo):

    texto = ""

    with pdfplumber.open(arquivo) as pdf:

        for pagina in pdf.pages:

            conteudo = pagina.extract_text()

            if conteudo:
                texto += conteudo + "\n"

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

    registros = []

    for linha in linhas:

        atendimento = ""

        m = re.search(
            r"^\d{6,}",
            linha
        )

        if m:
            atendimento = m.group()

        data = ""

        m = re.search(
            r"\d{2}/\d{2}/\d{4}",
            linha
        )

        if m:
            data = m.group()

        valor = ""

        m = re.search(
            r"(\d[\d\.]*,\d{2})$",
            linha
        )

        if m:
            valor = m.group(1)

        registros.append({
            "Atendimento": atendimento,
            "Data": data,
            "Valor": valor,
            "Conteúdo": linha
        })

    return pd.DataFrame(registros)


def converter_valores(df):

    if "Valor" not in df.columns:
        return df

    df = df.copy()

    df["Valor"] = (
        df["Valor"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    df["Valor"] = pd.to_numeric(
        df["Valor"],
        errors="coerce"
    )

    return df


def gerar_excel(df_proc, df_itens):

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:

        df_proc.to_excel(
            writer,
            index=False,
            sheet_name="Procedimentos"
        )

        df_itens.to_excel(
            writer,
            index=False,
            sheet_name="Itens"
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

    with st.spinner("Processando PDF..."):

        texto_completo = extrair_texto_pdf(
            arquivo
        )

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

        df_proc = converter_valores(
            df_proc
        )

        df_itens = converter_valores(
            df_itens
        )

    st.success("✅ PDF processado com sucesso")

    # ==================================================
    # RESUMO
    # ==================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Procedimentos",
            len(df_proc)
        )

    with col2:
        st.metric(
            "Itens",
            len(df_itens)
        )

    with col3:
        st.metric(
            "Total Procedimentos",
            f"R$ {df_proc['Valor'].sum():,.2f}"
        )

    with col4:
        st.metric(
            "Total Itens",
            f"R$ {df_itens['Valor'].sum():,.2f}"
        )

    # ==================================================
    # ABAS
    # ==================================================

    tab1, tab2 = st.tabs([
        "📋 Procedimentos",
        "📦 Itens de Repasse"
    ])

    # ==================================================
    # PROCEDIMENTOS
    # ==================================================

    with tab1:

        filtro_atendimento = st.text_input(
            "Filtrar Atendimento",
            key="proc_atendimento"
        )

        filtro_texto = st.text_input(
            "Pesquisar texto",
            key="proc_texto"
        )

        df_proc_filtrado = df_proc.copy()

        if filtro_atendimento:

            df_proc_filtrado = df_proc_filtrado[
                df_proc_filtrado["Atendimento"]
                .astype(str)
                .str.contains(
                    filtro_atendimento,
                    case=False,
                    na=False
                )
            ]

        if filtro_texto:

            df_proc_filtrado = df_proc_filtrado[
                df_proc_filtrado["Conteúdo"]
                .astype(str)
                .str.contains(
                    filtro_texto,
                    case=False,
                    na=False
                )
            ]

        st.dataframe(
            df_proc_filtrado,
            use_container_width=True,
            height=600
        )

    # ==================================================
    # ITENS
    # ==================================================

    with tab2:

        filtro_atendimento_item = st.text_input(
            "Filtrar Atendimento",
            key="item_atendimento"
        )

        filtro_texto_item = st.text_input(
            "Pesquisar texto",
            key="item_texto"
        )

        df_itens_filtrado = df_itens.copy()

        if filtro_atendimento_item:

            df_itens_filtrado = df_itens_filtrado[
                df_itens_filtrado["Atendimento"]
                .astype(str)
                .str.contains(
                    filtro_atendimento_item,
                    case=False,
                    na=False
                )
            ]

        if filtro_texto_item:

            df_itens_filtrado = df_itens_filtrado[
                df_itens_filtrado["Conteúdo"]
                .astype(str)
                .str.contains(
                    filtro_texto_item,
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
    # DOWNLOAD
    # ==================================================

    st.divider()

    excel = gerar_excel(
        df_proc,
        df_itens
    )

    st.download_button(
        label="📥 Baixar Excel",
        data=excel,
        file_name="repasses_medicos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ==================================================
    # DEBUG
    # ==================================================

    with st.expander("Visualizar texto extraído do PDF"):

        st.text_area(
            "Texto Completo",
            texto_completo,
            height=500
        )
