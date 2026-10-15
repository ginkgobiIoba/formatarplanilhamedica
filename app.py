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
<style>
div[data-baseweb="select"] {
    background-color: #eef1f5;
}

input {
    background-color: #eef1f5 !important;
}

.stTextInput input {
    background-color: #eef1f5 !important;
}

.stMultiSelect {
    background-color: #ffffff !important;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

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

    dados = []

    medicos = [
        "FABRICIO CHAVES NOVAES",
        "RODRIGO SOUSA MADEIRA CAMPOS"
    ]

    funcoes = [
        "Primeiro Auxiliar",
        "Segundo Auxiliar",
        "Clínico",
        "Cirurgião",
        "Anestesista"
    ]

    especialidades = [
        "Urologia",
        "Cardiologia",
        "Ortopedia",
        "Cirurgia Geral"
    ]

    for linha in registros:

        atendimento = ""
        tipo = ""
        tuss = ""
        paciente = ""
        procedimento = ""
        especialidade = ""
        funcao = ""
        medico = ""
        convenio_plano = ""
        data = ""
        percentual = ""
        valor = ""

        # -------------------
        # Dados básicos
        # -------------------

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
            r"(\d+)\s*%",
            linha
        )

        if m:
            percentual = m.group(1)

        m = re.search(
            r"(\d[\d\.]*,\d{2})",
            linha
        )

        if m:
            valor = m.group(1)


                # -------------------
        # Especialidade
        # -------------------

        for esp in especialidades:
            if esp in linha:
                especialidade = esp
                break

        # -------------------
        # Função
        # -------------------

        for f in funcoes:
            if f in linha:
                funcao = f
                break

        # -------------------
        # Médico
        # -------------------

        medico = ""

        if funcao:

            pos_funcao = linha.find(funcao)

            if pos_funcao != -1:

                trecho_medico = linha[
                    pos_funcao + len(funcao):
                ]

                data_match = re.search(
                    r"\d{2}/\d{2}/\d{4}",
                    trecho_medico
                )

                if data_match:
                    trecho_medico = trecho_medico[
                        :data_match.start()
                    ]

                palavras = trecho_medico.split()

                ignorar = {
                    "CABESP",
                    "ASSOCIADOS",
                    "PORTO",
                    "OURO",
                    "DIAMANTE",
                    "EXECUTIVO",
                    "PREMIUM",
                    "MAX",
                    "Q"
                }

                palavras_medico = []

                for palavra in palavras:

                    if palavra.upper() in ignorar:
                        break

                    palavras_medico.append(
                        palavra
                    )

                medico = " ".join(
                    palavras_medico[:3]
                )

                # -------------------
        # Convênio e Plano
        # -------------------

        data_match = re.search(
            r"\d{2}/\d{2}/\d{4}",
            linha
        )

        if medico and data_match:

            pos_medico = linha.find(medico)

            if pos_medico != -1:

                trecho = linha[
                    pos_medico + len(medico):
                    data_match.start()
                ]

                trecho = re.sub(
                    r"\b\d+\b",
                    "",
                    trecho
                )

                trecho = trecho.replace("%", "")

                trecho = trecho.strip()

                convenio_plano = trecho
                    
        # -------------------
        # Paciente
        # -------------------

        if especialidade:

            inicio_paciente = re.search(
                r"^\d+\s+(INT|AMB)\s+\d+\s+",
                linha
            )

            if inicio_paciente:

                texto_tmp = linha[
                    inicio_paciente.end():
                ]

                fim = texto_tmp.find(
                    especialidade
                )

                if fim > 0:

                    trecho = texto_tmp[:fim]

                    palavras = trecho.split()

                    paciente_palavras = []

                    for palavra in palavras:

                        if (
                            palavra.isupper()
                            and any(c.isalpha() for c in palavra)
                        ):
                            paciente_palavras.append(
                                palavra
                            )

                        else:
                            break

                    paciente = " ".join(
                        paciente_palavras
                    )

                # -------------------
        # Procedimento
        # -------------------

        if especialidade:

            inicio_paciente = re.search(
                r"^\d+\s+(INT|AMB)\s+\d+\s+",
                linha
            )

            if inicio_paciente:

                texto_tmp = linha[
                    inicio_paciente.end():
                ]

                fim = texto_tmp.find(
                    especialidade
                )

                if fim > 0:

                    trecho = texto_tmp[:fim]

                    palavras = trecho.split()

                    ponto_corte = 0

                    for i, palavra in enumerate(palavras):

                        if (
                            palavra.isupper()
                            and any(c.isalpha() for c in palavra)
                        ):
                            ponto_corte = i + 1
                        else:
                            break

                    procedimento = " ".join(
                        palavras[ponto_corte:]
                    )
                    procedimento = " ".join(
                        palavras[ponto_corte:]
                    )

        # Remover coluna Via (U, M, D, B)

                    if procedimento:

                        palavras_proc = procedimento.split()

                        if (
                            len(palavras_proc) > 0
                            and palavras_proc[-1] in ["U", "M", "D", "B"]
                        ):

                            procedimento = " ".join(
                                palavras_proc[:-1]
                            )


        # -------------------
        # Complemento Procedimento
        # -------------------

        complemento_procedimento = ""
        if data:
            pos_data = linha.find(data)
            if pos_data != -1:
                texto_final = linha[pos_data:]
                match_valor = re.search(
                    r"\d[\d\.]*,\d{2}",
                    texto_final
                )

                if match_valor:
                    sobra = texto_final[
                        match_valor.end():
                    ].strip()
                    complemento_procedimento = sobra
                    
                complemento_procedimento = (
                    complemento_procedimento
                    .replace(" Principal", "")
                    .replace(" Primeiro Auxiliar", "")
                    .replace(" Segundo Auxiliar", "")
                    .replace(" Clínico", "")
                    .replace(" APARTAMENTO", "")
                )

                complemento_procedimento = re.sub(
                    r"CORPORATIVA.*",
                    "",
                    complemento_procedimento
                ).strip()

                # Junta complemento ao procedimento

                if complemento_procedimento:

                    procedimento = (
                        procedimento + " " +
                        complemento_procedimento
                    ).strip()

        dados.append({
            "Atendimento": atendimento,
            "Tipo": tipo,
            "TUSS": tuss,
            "Paciente": paciente,
            "Procedimento": procedimento,
            "ComplementoProcedimento": complemento_procedimento,
            "Especialidade": especialidade,
            "Função": funcao,
            "Médico": medico,
            "Convênio/Plano": convenio_plano,
            "Data": data,
            "Repasse": percentual,
            "Valor": valor,
            "ConteudoCompleto": linha
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

        # Atendimento
        m = re.search(
            r"^(\d+)",
            linha
        )

        if m:
            atendimento = m.group(1)

        # Data
        m = re.search(
            r"(\d{2}/\d{2}/\d{4})",
            linha
        )

        if m:
            data = m.group(1)

        m = re.search(
            r"(\d+)\s*%",
            linha
        )

        if m:
            percentual = m.group(1)

        # Último valor monetário da linha
        valores = re.findall(
            r"\d[\d\.]*,\d{2}",
            linha
        )

        if valores:
            valor = valores[-1]
        else:
            valor = ""

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

    st.info(
        f"{len(df_proc)} procedimentos e {len(df_itens)} itens encontrados."
    )

    # ==========================================
    # ABAS
    # ==========================================

    aba1, aba2 = st.tabs(
        ["📋 Procedimentos", "📦 Itens"]
    )

    with aba1:

        df_exibir = df_proc.copy()

        busca_convenio = st.text_input(
            "Pesquisar Convênio/Plano (Ex: Porto, Sul América)"
        )

        if busca_convenio:

            termos = [
                t.strip()
                for t in busca_convenio.replace(";", ",").split(",")
                if t.strip()
            ]

            mascara = pd.Series(
                False,
                index=df_exibir.index
            )

            for termo in termos:

                mascara = mascara | (
                    df_exibir["Convênio/Plano"]
                    .astype(str)
                    .str.contains(
                        termo,
                        case=False,
                        na=False
                    )
                )

            df_exibir = df_exibir[mascara]
        
        
        medicos_disponiveis = sorted(
            [m for m in df_proc["Médico"].dropna().unique() if m]
        )

        medicos_selecionados = st.multiselect(
            "Filtrar Médico",
            medicos_disponiveis,
            default=medicos_disponiveis
        )

    if medicos_selecionados:

        df_exibir = df_exibir[
            df_exibir["Médico"].isin(
                medicos_selecionados
            )
        ]

    filtro = st.text_input(
        "Pesquisar Procedimentos"
    )

    if filtro:

        df_exibir = df_exibir[
            df_exibir["Conteúdo"]
            .str.contains(
                filtro,
                case=False,
                na=False
            )
        ]

    colunas_exibir = [
        "Paciente",
        "Procedimento",
        "Especialidade",
        "Função",
        "Médico",
        "Convênio/Plano",
        "Repasse",
        "Data",
        "Valor"
    ]

    st.dataframe(
        df_exibir[colunas_exibir],
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
