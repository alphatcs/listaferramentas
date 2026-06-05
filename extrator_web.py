"""
Extrator de Parágrafos por Palavra-Chave — Interface Web (Streamlit)
=====================================================================
Acesso pela rede local: http://<IP-do-servidor>:8501

Instalação:
    pip install streamlit supabase

Execução:
    streamlit run extrator_web.py --server.address 0.0.0.0
"""

import streamlit as st
from datetime import datetime
import os
import io
from supabase import create_client

# =============================================================
# CONFIGURACAO GLOBAL
# Preencha para fixar a palavra-chave sem o usuário digitar.
# Deixe como "" para o campo aparecer na tela.
# =============================================================
PALAVRA_BUSCA = "T"
# =============================================================

# ---- Conexão Supabase via variáveis de ambiente ----
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def registrar_historico(arquivo, ordem_servico, maquina, palavra, modo, total):
    """Grava uma linha na tabela historico do Supabase."""
    try:
        supabase = get_supabase()
        supabase.table("historico").insert({
            "arquivo":           arquivo,
            "ordem_servico":     ordem_servico,
            "maquina":           maquina,
            "palavra_chave":     palavra,
            "modo":              modo,
            "total_encontrados": total
        }).execute()
    except Exception as e:
        st.warning(f"Histórico não registrado: {e}")


st.set_page_config(
    page_title="Extrator de Ferramentas",
    page_icon="🔍",
    layout="centered"
)

# ---- Cabeçalho ----
st.title("🔍 Extrator de Ferramentas")
st.caption("Alphatech Solutions — Ferramenta de busca em arquivos de programa CNC")
st.divider()

# ---- Abas: Extrator | Histórico ----
aba_extrator, aba_historico = st.tabs(["🔎 Extrator", "📋 Histórico"])


# ================================================================
# ABA EXTRATOR
# ================================================================
with aba_extrator:

    st.subheader("1. Selecione o arquivo")
    arquivo = st.file_uploader(
        "Arraste ou clique para selecionar o arquivo .txt",
        type=["txt"],
        help="Suporta arquivos com quebras de linha Windows (\\r\\n), Unix (\\n) e CNC (\\r)"
    )

    st.subheader("2. Dados da Ordem de Serviço")
    col1, col2 = st.columns(2)
    with col1:
        ordem_servico = st.text_input("Número da Ordem de Serviço", placeholder="Ex: OS-2024-001")
    with col2:
        maquina = st.text_input("Máquina", placeholder="Ex: CNC ROMI GL240")

    st.subheader("3. Palavra-chave")
    if PALAVRA_BUSCA:
        palavra = PALAVRA_BUSCA
        st.info(f"Palavra-chave configurada: **{PALAVRA_BUSCA}**")
    else:
        palavra = st.text_input("Digite a palavra ou trecho a buscar", placeholder="Ex: BROCA, CYCLE 83, T08")

    case_sensitive = st.checkbox("Diferenciar maiúsculas/minúsculas")

    st.divider()
    buscar = st.button("🔎 Buscar", type="primary", use_container_width=True)

    # ---- Funções ----
    def ler_arquivo(conteudo_bytes: bytes) -> str:
        texto = conteudo_bytes.decode("utf-8", errors="replace")
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        return texto

    def detectar_modo(texto: str) -> str:
        linhas = [l for l in texto.split("\n") if l.strip()]
        total = len(linhas)
        if total == 0:
            return "linhas"
        linhas_em_branco = texto.count("\n\n")
        if linhas_em_branco < total * 0.1:
            return "linhas"
        return "paragrafos"

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

    def gerar_txt(paragrafos, palavra, nome_arquivo, modo, ordem_servico, maquina) -> str:
        tipo = "linha(s)" if modo == "linhas" else "parágrafo(s)"
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        linhas = []
        linhas.append("=" * 60)
        linhas.append("  EXTRATOR DE FERRAMENTAS DO PROGRAMA CNC .TXT")
        linhas.append("=" * 60)
        if ordem_servico:
            linhas.append(f"  Ordem de Servico : {ordem_servico}")
        if maquina:
            linhas.append(f"  Maquina          : {maquina}")
        linhas.append(f"  Data/Hora        : {agora}")
        linhas.append(f"  Arquivo de origem: {nome_arquivo}")
        linhas.append(f"  Palavra-chave    : '{palavra}'")
        linhas.append(f"  Modo de leitura  : {modo}")
        linhas.append(f"  Registros encontrados: {len(paragrafos)} {tipo}")
        linhas.append("=" * 60)
        linhas.append("")
        if not paragrafos:
            linhas.append(f"Nenhum registro encontrado com a palavra-chave '{palavra}'.")
        else:
            for i, bloco in enumerate(paragrafos, start=1):
                linhas.append(f"[{i}]")
                linhas.append(bloco)
                linhas.append("")
        return "\n".join(linhas)

    # ---- Execução da busca ----
    if buscar:
        if not arquivo:
            st.warning("⚠️ Selecione um arquivo .txt antes de buscar.")
        elif not palavra.strip():
            st.warning("⚠️ Digite uma palavra-chave antes de buscar.")
        else:
            conteudo_bytes = arquivo.read()
            texto = ler_arquivo(conteudo_bytes)
            paragrafos, modo = extrair_paragrafos(texto, palavra.strip(), case_sensitive)

            st.divider()
            st.subheader("Resultado")

            col1, col2, col3 = st.columns(3)
            col1.metric("Registros encontrados", len(paragrafos))
            col2.metric("Modo de leitura", modo)
            col3.metric("Arquivo", arquivo.name)

            if not paragrafos:
                st.error(f"Nenhum registro encontrado com a palavra-chave **'{palavra}'**.")
            else:
                st.success(f"✅ {len(paragrafos)} registro(s) encontrado(s) com **'{palavra}'**")

                for i, bloco in enumerate(paragrafos, start=1):
                    with st.expander(f"[{i}]  {bloco[:80]}{'...' if len(bloco) > 80 else ''}"):
                        st.code(bloco, language=None)

                conteudo_saida = gerar_txt(
                    paragrafos, palavra.strip(), arquivo.name,
                    modo, ordem_servico, maquina
                )
                nome_base = os.path.splitext(arquivo.name)[0]
                sufixo_os = f"_OS{ordem_servico}" if ordem_servico else ""
                nome_saida = f"{nome_base}{sufixo_os}_resultado_{palavra.strip().replace(' ', '_')}.txt"

                st.divider()
                st.download_button(
                    label="⬇️ Baixar resultado em .txt",
                    data=conteudo_saida.encode("utf-8"),
                    file_name=nome_saida,
                    mime="text/plain",
                    use_container_width=True
                )

            # ---- Registra no Supabase independente do resultado ----
            registrar_historico(
                arquivo=arquivo.name,
                ordem_servico=ordem_servico,
                maquina=maquina,
                palavra=palavra.strip(),
                modo=modo,
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