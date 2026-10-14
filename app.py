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
Faça upload do PDF para:

- Extrair procedimentos
- Extrair itens de repasse
- Visualizar os dados
- Exportar para Excel
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


def reconstruir_registros(texto):

    registros = []

    atual = ""

    for linha in texto.split("\n"):

        linha = linha.strip()

        if not linha:
            continue

        if re.match(r"^\d+\s+(INT|AMB)\s+", linha):

            if atual:
                registros.append(atual)

            atual = linha

        else:

            if atual:
                atual += " " + linha

    if atual:
        registros.append(atual)

    return registros


def criar_dataframe(registros):

    dados = []

    for linha in registros:

        atendimento = ""
        tipo = ""
        tuss = ""
        data = ""
        valor = ""

        match = re.search(
            r"^(\d+)\s+(INT|AMB)\s+(\d+)",
            linha
        )

        if match:
            atendimento = match.group(1)
            tipo = match.group(2)
            tuss = match.group(3)

        match_data = re.search(
            r"(\d{2}/\d{2}/\d{4})",
            linha
        )

        if match_data:
            data = match_data.group(1)

        match_valor = re.search(
            r"(\d[\d\.]*,\d{2})$",
            linha
        )

        if match_valor:
            valor = match_valor.group(1)

        dados.append({
            "Atendimento": atendimento,
            "Tipo": tipo,
            "TUSS": tuss,
            "Data": data,
            "Valor": valor,
            "Conteúdo": linha
        })

    return pd.DataFrame(dados)


def criar_dataframe_itens(texto):

    registros = []

    for linha in texto.split("\n"):

        linha = linha.strip()

        if not linha:
            continue

        if "Total Itens Repasse" in linha:
            continue

        match = re.search(
            r"^(\d+).*?(\d{2}/\d{2}/\d{4}).*?(\d[\d\.]*,\d{2})$",
            linha
        )

        atendimento = ""
        data = ""
        valor = ""

        if match:

            atendimento = match.group(1)
            data = match.group(2)
            valor = match.group(3)

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
            sheet_name="Procedimentos",
            index=False
        )

        df_itens.to_excel(
            writer,
            sheet_name="Itens",
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

    with st.spinner("Processando PDF..."):

        texto_completo = extrair_texto_pdf(
            arquivo
        )

        texto_proc, texto_itens = separar_secoes(
            texto_completo
        )

        registros_proc = reconstruir_registros(
            texto_proc
        )

        df_proc = criar_dataframe(
            registros_proc
        )

        df_itens = criar_dataframe_itens(
            texto_itens
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

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Qtd Procedimentos",
            len(df_proc)
        )

    with c2:
        st.metric(
            "Qtd Itens",
            len(df_itens)
        )

    with c3:
        st.metric(
            "Total Procedimentos",
            f"R$ {df_proc['Valor'].sum():,.2f}"
        )

    with c4:
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

    with tab1:

        filtro = st.text_input(
            "Pesquisar Procedimentos"
        )

        df_filtrado = df_proc.copy()

        if filtro:

            df_filtrado = df_filtrado[
                df_filtrado["Conteúdo"]
                .str.contains(
                    filtro,
                    case=False,
                    na=False
                )
            ]

        st.dataframe(
            df_filtrado,
            use_container_width=True,
            height=600
        )

    with tab2:

        filtro_itens = st.text_input(
            "Pesquisar Itens"
        )

        df_itens_filtrado = df_itens.copy()

        if filtro_itens:

            df_itens_filtrado = df_itens_filtrado[
                df_itens_filtrado["Conteúdo"]
                .str.contains(
                    filtro_itens,
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
    # DEBUG
    # ==================================================

    with st.expander("Ver registros reconstruídos"):

        st.write("### Procedimentos")

        for registro in registros_proc[:20]:
            st.text(registro)

        st.write("### Itens")

        st.text_area(
            "Texto dos Itens",
            texto_itens,
            height=300
        )
