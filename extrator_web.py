"""
Extrator de Parágrafos por Palavra-Chave — Interface Web (Streamlit)
Engenharia HKM — Versão com modo CNC para detecção de ferramentas
"""

import streamlit as st
from datetime import datetime
import os
import re

# =============================================================
# CONFIGURACAO GLOBAL
# Preencha para fixar a palavra-chave sem o usuário digitar.
# Deixe como "" para o campo aparecer na tela.
# =============================================================
PALAVRA_BUSCA = ""
# =============================================================

# ---- Conexão Supabase ----
@st.cache_resource
def get_supabase():
    from supabase import create_client
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def registrar_historico(arquivo, ordem_servico, maquina, palavra, modo, total):
    try:
        supabase = get_supabase()
        supabase.table("historico").insert({
            "arquivo":           arquivo,
            "ordem_servico":     ordem_servico,
            "maquina":           maquina,
            "palavra_chave":     palavra,
            "modo":              modo,
            "total_encontrados": total,
            "origem":            "web"
        }).execute()
    except Exception as e:
        st.warning(f"Histórico não registrado: {e}")


# ---- Funções de processamento ----
def ler_arquivo(conteudo_bytes: bytes) -> str:
    texto = conteudo_bytes.decode("utf-8", errors="replace")
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def detectar_modo(texto: str) -> str:
    linhas = [l for l in texto.split("\n") if l.strip()]
    total = len(linhas)
    if total == 0:
        return "linhas"
    if texto.count("\n\n") < total * 0.1:
        return "linhas"
    return "paragrafos"


def extrair_ferramentas_cnc(texto: str):
    """
    Detecta chamadas de ferramenta nos padrões:
    - FANUC  : T1( BROCA DE CENTRO )
    - Fagor  : T01D01;OPERACAO 2
    - Siemens: T0101 (4 digitos colados — 2 ferramenta + 2 corretor)
    """
    padrao = re.compile(
        r'(?<![A-Z])'             # Nao precedido de letra maiuscula
        r'T(\d{1,4})'             # T + 1-4 digitos
        r'(?:'
        r'D\d{1,4}'               # Fagor: TD colados (T01D01)
        r'|\s+D\d{1,4}'           # variante com espaco (T1 D1)
        r'|\s*\([^)]+\)'         # FANUC: T1( descricao )
        r'|(?=\s*;|\s*$|\s*\()'  # Siemens: T0101 sozinho ou antes de ;
        r')'
    )
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    resultado = []
    for linha in linhas:
        if padrao.search(linha):
            resultado.append(linha)
    return resultado


def extrair_paragrafos(texto: str, palavra: str, case_sensitive: bool = False):
    modo = detectar_modo(texto)
    if modo == "paragrafos":
        blocos = texto.split("\n\n")
        blocos = [" ".join(b.split()) for b in blocos if b.strip()]
    else:
        blocos = [l.strip() for l in texto.split("\n") if l.strip()]
    if case_sensitive:
        resultado = [b for b in blocos if palavra in b]
    else:
        resultado = [b for b in blocos if palavra.lower() in b.lower()]
    return resultado, modo


def gerar_txt(paragrafos, palavra, nome_arquivo, modo, ordem_servico, maquina, modo_busca) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    tipo = "ferramenta(s)" if modo_busca == "cnc" else ("linha(s)" if modo == "linhas" else "parágrafo(s)")
    linhas = []
    linhas.append("=" * 60)
    linhas.append("  EXTRATOR DE PARAGRAFOS POR PALAVRA-CHAVE")
    linhas.append("=" * 60)
    if ordem_servico:
        linhas.append(f"  Ordem de Servico : {ordem_servico}")
    if maquina:
        linhas.append(f"  Maquina          : {maquina}")
    linhas.append(f"  Data/Hora        : {agora}")
    linhas.append(f"  Arquivo de origem: {nome_arquivo}")
    if modo_busca == "cnc":
        linhas.append(f"  Modo             : Deteccao automatica de ferramentas CNC")
    else:
        linhas.append(f"  Palavra-chave    : '{palavra}'")
        linhas.append(f"  Modo de leitura  : {modo}")
    linhas.append(f"  Registros encontrados: {len(paragrafos)} {tipo}")
    linhas.append("=" * 60)
    linhas.append("")
    if not paragrafos:
        linhas.append("Nenhum registro encontrado.")
    else:
        for i, bloco in enumerate(paragrafos, start=1):
            linhas.append(f"[{i}]")
            linhas.append(bloco)
            linhas.append("")
    linhas.append("=" * 60)
    linhas.append("  Desenvolvido por Gilberto Artur Ferreira")
    linhas.append("  Engenheiro | Alphatech Solutions")
    linhas.append("=" * 60)
    return "\n".join(linhas)


# ---- Interface ----
st.set_page_config(page_title="Extrator de Parágrafos", page_icon="🔍", layout="centered")
st.title("🔍 Extrator de Parágrafos")
st.caption("Engenharia HKM — Ferramenta de busca em arquivos de programa CNC")
st.divider()

aba_extrator, aba_historico = st.tabs(["🔎 Extrator", "📋 Histórico"])

# ================================================================
# ABA EXTRATOR
# ================================================================
with aba_extrator:

    st.subheader("1. Selecione o arquivo")
    arquivo = st.file_uploader(
        "Arraste ou clique para selecionar o arquivo .txt",
        type=["txt"],
        help="Suporta arquivos com quebras de linha Windows, Unix e CNC"
    )

    st.subheader("2. Dados da Ordem de Serviço")
    col1, col2 = st.columns(2)
    with col1:
        ordem_servico = st.text_input("Número da Ordem de Serviço", placeholder="Ex: OS-2024-001")
    with col2:
        maquina = st.text_input("Máquina", placeholder="Ex: CNC ROMI GL240")

    st.subheader("3. Modo de busca")
    modo_busca = st.radio(
        "Como deseja buscar?",
        options=["palavra", "cnc"],
        format_func=lambda x: "🔤 Palavra-chave" if x == "palavra" else "⚙️ Ferramentas CNC (T + dígitos)",
        horizontal=True
    )

    palavra = ""
    if modo_busca == "palavra":
        if PALAVRA_BUSCA:
            palavra = PALAVRA_BUSCA
            st.info(f"Palavra-chave configurada: **{PALAVRA_BUSCA}**")
        else:
            palavra = st.text_input("Digite a palavra ou trecho a buscar", placeholder="Ex: BROCA, CYCLE 83")
        case_sensitive = st.checkbox("Diferenciar maiúsculas/minúsculas")
    else:
        st.info("🔍 Serão detectadas automaticamente todas as linhas com chamada de ferramenta no padrão **T + número + (descrição)**")
        case_sensitive = False

    st.divider()
    buscar = st.button("🔎 Buscar", type="primary", use_container_width=True)

    if buscar:
        if not arquivo:
            st.warning("⚠️ Selecione um arquivo .txt antes de buscar.")
        elif modo_busca == "palavra" and not palavra.strip():
            st.warning("⚠️ Digite uma palavra-chave antes de buscar.")
        else:
            texto = ler_arquivo(arquivo.read())

            if modo_busca == "cnc":
                paragrafos = extrair_ferramentas_cnc(texto)
                modo = "linhas"
                palavra = "T[0-9]+(descrição CNC)"
            else:
                paragrafos, modo = extrair_paragrafos(texto, palavra.strip(), case_sensitive)

            st.divider()
            st.subheader("Resultado")

            col1, col2, col3 = st.columns(3)
            col1.metric("Registros encontrados", len(paragrafos))
            col2.metric("Modo", "CNC" if modo_busca == "cnc" else modo)
            col3.metric("Arquivo", arquivo.name)

            if not paragrafos:
                st.error("Nenhum registro encontrado.")
            else:
                st.success(f"✅ {len(paragrafos)} registro(s) encontrado(s)")
                for i, bloco in enumerate(paragrafos, start=1):
                    with st.expander(f"[{i}]  {bloco[:80]}{'...' if len(bloco) > 80 else ''}"):
                        st.code(bloco, language=None)

                conteudo_saida = gerar_txt(
                    paragrafos, palavra, arquivo.name,
                    modo, ordem_servico, maquina, modo_busca
                )
                nome_base = os.path.splitext(arquivo.name)[0]
                sufixo_os = f"_OS{ordem_servico}" if ordem_servico else ""
                sufixo = "_ferramentas_CNC" if modo_busca == "cnc" else f"_resultado_{palavra.strip().replace(' ', '_')}"
                nome_saida = f"{nome_base}{sufixo_os}{sufixo}.txt"

                st.divider()
                st.download_button(
                    label="⬇️ Baixar resultado em .txt",
                    data=conteudo_saida.encode("utf-8"),
                    file_name=nome_saida,
                    mime="text/plain",
                    use_container_width=True
                )

            registrar_historico(
                arquivo=arquivo.name,
                ordem_servico=ordem_servico,
                maquina=maquina,
                palavra="[CNC ferramentas]" if modo_busca == "cnc" else palavra.strip(),
                modo="cnc" if modo_busca == "cnc" else modo,
                total=len(paragrafos)
            )

# ================================================================
# ABA HISTÓRICO
# ================================================================
with aba_historico:
    st.subheader("Histórico de extrações")

    if st.button("🔄 Atualizar", use_container_width=True):
        st.rerun()

    try:
        supabase = get_supabase()
        response = supabase.table("historico") \
            .select("*") \
            .order("data_hora", desc=True) \
            .limit(100) \
            .execute()
        dados = response.data

        if not dados:
            st.info("Nenhuma extração registrada ainda.")
        else:
            st.caption(f"{len(dados)} registro(s) encontrado(s)")
            for row in dados:
                with st.expander(
                    f"🗂️ {row.get('arquivo','—')}  |  "
                    f"OS: {row.get('ordem_servico','—')}  |  "
                    f"Palavra: {row.get('palavra_chave','—')}  |  "
                    f"{row.get('data_hora','')[:16].replace('T',' ')}"
                ):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Registros", row.get("total_encontrados", 0))
                    c2.metric("Máquina", row.get("maquina") or "—")
                    c3.metric("Modo", row.get("modo") or "—")
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")

# ---- Rodapé ----
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px;'>
        Desenvolvido por <b>Gilberto Artur Ferreira</b> — Engenheiro | Alphatech Solutions
    </div>
    """,
    unsafe_allow_html=True
)
