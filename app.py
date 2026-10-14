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
Faça upload do PDF para visualizar e exportar os dados.
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


def criar_dataframe_procedimentos(registros):

    medicos_conhecidos = [
        "FABRICIO CHAVES NOVAES",
        "RODRIGO SOUSA MADEIRA CAMPOS"
    ]

    especialidades = [
        "Urologia",
        "Cardiologia",
        "Ortopedia",
        "Cirurgia Geral"
    ]

    funcoes = [
        "Primeiro Auxiliar",
        "Segundo Auxiliar",
        "Clínico",
        "Cirurgião",
        "Anestesista"
    ]

    dados = []

    for linha in registros:

        atendimento = ""
        tipo = ""
        tuss = ""
        data = ""
        valor = ""
        medico = ""
        especialidade = ""
        funcao = ""

        m = re.search(
            r"^(\d+)\s+(INT|AMB)\s+(\d+)",
            linha
        )

        if m:
            atendimento = m.group(1)
            tipo = m.group(2)
            tuss = m.group(3)

        m = re.search(
            r"(\d{2}/\d{2}/\d{4})",
            linha
        )

        if m:
            data = m.group(1)

        m = re.search(
            r"(\d[\d\.]*,\d{2})",
            linha
        )

        if m:
            valor = m.group(1)

        for med in medicos_conhecidos:

            if med in linha:
                medico = med
                break

        for esp in especialidades:

            if esp in linha:
                especialidade = esp
                break

        for func in funcoes:

            if func in linha:
                funcao = func
                break

        dados.append({
            "Atendimento": atendimento,
            "Tipo": tipo,
            "TUSS": tuss,
            "Especialidade": especialidade,
            "Função": funcao,
            "Médico": medico,
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

        atendimento = ""
        data = ""
        valor = ""

        m = re.search(
            r"^(\d+)",
            linha
        )

        if m:
            atendimento = m.group(1)

        m = re.search(
            r"(\d{2}/\d{2}/\d{4})",
            linha
        )

        if m:
            data = m.group(1)

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

if arquivo is not None:

    with st.spinner("Processando PDF..."):

        texto = extrair_texto_pdf(arquivo)

        texto_proc, texto_itens = separar_secoes(
            texto
        )

        registros_proc = reconstruir_registros(
            texto_proc
        )

        df_proc = criar_dataframe_procedimentos(
            registros_proc
        )

        df_itens = criar_dataframe_itens(
            texto_itens
        )

        df_proc = converter_valores(df_proc)
        df_itens = converter_valores(df_itens)

    st.success("✅ PDF processado com sucesso")

    # ==========================================
    # MÉTRICAS
    # ==========================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Procedimentos",
        len(df_proc)
    )

    c2.metric(
        "Itens",
        len(df_itens)
    )

    c3.metric(
        "Total Procedimentos",
        f"R$ {df_proc['Valor'].sum():,.2f}"
    )

    c4.metric(
        "Total Itens",
        f"R$ {df_itens['Valor'].sum():,.2f}"
    )

    # ==========================================
    # ABAS
    # ==========================================

    aba1, aba2 = st.tabs(
        ["📋 Procedimentos", "📦 Itens"]
    )

    with aba1:

        filtro = st.text_input(
            "Pesquisar Procedimentos"
        )

        df_exibir = df_proc.copy()

        if filtro:

            df_exibir = df_exibir[
                df_exibir["Conteúdo"]
                .str.contains(
                    filtro,
                    case=False,
                    na=False
                )
            ]

        st.dataframe(
            df_exibir,
            use_container_width=True,
            height=600
        )

    with aba2:

        filtro_itens = st.text_input(
            "Pesquisar Itens"
        )

        df_itens_exibir = df_itens.copy()

        if filtro_itens:

            df_itens_exibir = df_itens_exibir[
                df_itens_exibir["Conteúdo"]
                .str.contains(
                    filtro_itens,
                    case=False,
                    na=False
                )
            ]

        st.dataframe(
            df_itens_exibir,
            use_container_width=True,
            height=600
        )

    # ==========================================
    # DOWNLOAD
    # ==========================================

    excel = gerar_excel(
        df_proc,
        df_itens
    )

    st.download_button(
        "📥 Baixar Excel",
        data=excel,
        file_name="repasses_medicos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
