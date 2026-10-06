import streamlit as st
import pandas as pd
from PIL import Image
from google import genai
import time

st.set_page_config(
    page_title="Validador Multi-Máquinas OP", page_icon="🏭", layout="wide"
)

st.title("🏭 Validação de Codificação e Lotes por Máquina")
st.caption(
    "Validação visual rápida e gratuita (Lata + Etiqueta / Pacote + Caixa / Etiquetas Jungle)"
)

# Barra Lateral: Configurações
st.sidebar.header("⚙ Configurações")

# Suporte a uma ou várias chaves separadas por vírgula
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    raw_api_keys = st.secrets["GEMINI_API_KEY"]
else:
    raw_api_keys = st.sidebar.text_input("Chave(s) API do Gemini (separadas por vírgula):", type="password")

api_keys = [k.strip() for k in raw_api_keys.split(",") if k.strip()] if raw_api_keys else []

SHEET_OP_ID = "1YScgtOowZjmTWMKnlcwya1nPQKt0u34luPSb4U82_-E"
SHEET_DUN_ID = "1TDROYy4E6u41k6n05lWyGfh3o7SjYz4JoofK1saNC-M"

GSHEET_OP_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_OP_ID}/export?format=csv"
GSHEET_DUN_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_DUN_ID}/export?format=csv"

@st.cache_data(ttl=60)
def carregar_dados_gsheet(url):
    return pd.read_csv(url)

if st.sidebar.button("🔄 Sincronizar Planilhas (OP e SKUs)"):
    st.cache_data.clear()

dados_op = None
dados_dun = None

try:
    dados_op = carregar_dados_gsheet(GSHEET_OP_URL)
    st.sidebar.success("✅ Planilha de OPs conectada!")
except Exception:
    st.sidebar.warning("⚠️ Não foi possível carregar a planilha de OPs.")

try:
    dados_dun = carregar_dados_gsheet(GSHEET_DUN_URL)
    st.sidebar.success("✅ Planilha de SKUs / DUNs conectada!")
except Exception:
    st.sidebar.warning("⚠️ Não foi possível carregar a planilha de SKUs/DUNs.")

if dados_op is not None or dados_dun is not None:
    with st.expander("📋 Ver Tabelas de Referência (OPs e SKUs)"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ordem de Produção (OP)")
            st.dataframe(dados_op)
        with col2:
            st.subheader("Cadastro SKU x DUN")
            st.dataframe(dados_dun)

if not api_keys:
    st.warning("Insira pelo menos uma Chave de API na barra lateral para continuar.")
    st.stop()

st.subheader("📷 Captura de Imagem")
img_file_buffer = st.camera_input("Tirar fotografia da embalagem/etiqueta")

if img_file_buffer is not None:
    image = Image.open(img_file_buffer)
    st.image(image, caption="Imagem Capturada", use_container_width=True)
    
    with st.spinner("⚡ Analisando imagem..."):
        image_otimizada = image.copy()
        image_otimizada.thumbnail((1024, 1024))
        
        contexto_op = ""
        if dados_op is not None:
            contexto_op += f"\n\n--- TABELA DE ORDEM DE PRODUÇÃO (OP) ATIVA ---\n{dados_op.to_string(index=False)}"
        
        if dados_dun is not None:
            contexto_op += f"\n\n--- TABELA DE REFERÊNCIA CADASTRO SKU x DUN-14 ---\n{dados_dun.to_string(index=False)}"
        
        prompt = f"""
        Você é um auditor de qualidade de linha de produção.
        Analise a imagem e valide internamente segundo estas regras:

        1. LINHA JUNGLE: Se for etiqueta Jungle, contém apenas Descrição, DUN e SKU. É NORMAL NÃO TER LOTE OU VALIDADE.
        2. DUN-14: O código DUN de caixas deve possuir EXATAMENTE 14 dígitos numéricos.
        3. CRUZAMENTO DE DADOS: O DUN, SKU e Lote lidos na imagem devem coincidir exatamente com os cadastros nas tabelas de referência fornecidas.

        {contexto_op}

        --- INSTRUÇÕES RIGOROSAS DE SAÍDA ---
        NÃO liste os dados extraídos. NÃO crie tópicos numerados ou explicações intermediárias.
        Retorne APENAS um dos dois formatos abaixo:

        Se estiver TUDO CONFORME:
        ✅ **VALIDAÇÃO DE P.A CONFORME**
        *Todos os dados da embalagem conferem com a Ordem de Produção e cadastro.*

        Se houver QUALQUER DIVERGÊNCIA:
        ❌ **VALIDAÇÃO DE P.A NÃO CONFORME**
        **Onde está a não conformidade:**
        - [Descreva aqui exatamente o ponto de divergência.]
        """
        
        MODELO_LITE = "gemini-3.5-flash-lite"
        
        resposta = None
        ultimo_erro = None
        
        for key in api_keys:
            try:
                client = genai.Client(api_key=key)
                resposta = client.models.generate_content(
                    model=MODELO_LITE,
                    contents=[image_otimizada, prompt]
                )
                if resposta and resposta.text:
                    break
            except Exception as e:
                ultimo_erro = e
                continue
        
        if resposta and resposta.text:
            st.markdown("### 🔍 Resultado da Validação")
            st.write(resposta.text)
        else:
            if "429" in str(ultimo_erro) or "RESOURCE_EXHAUSTED" in str(ultimo_erro):
                st.error("⚠️ Quota diária atingida nesta chave. Adicione outra chave API separada por vírgula para continuar.")
            else:
                st.error(f"Erro no processamento: {ultimo_erro}. Por favor, tente novamente.")
