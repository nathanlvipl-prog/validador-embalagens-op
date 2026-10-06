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
    "Validação visual (Lata + Etiqueta / Pacote + Caixa / Etiquetas Jungle) com cruzamento de OP e Tabela de SKUs/DUNs"
)

# Barra Lateral: Configurações e Integração Google Sheets
st.sidebar.header("⚙ Configurações")

# Procura a chave nos Secrets do Streamlit Cloud ou pede na barra lateral
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Chave API do Gemini:", type="password")

# IDs das Planilhas do Google Sheets
SHEET_OP_ID = "1YScgtOowZjmTWMKnlcwya1nPQKt0u34luPSb4U82_-E"
SHEET_DUN_ID = "1TDROYy4E6u41k6n05lWyGfh3o7SjYz4JoofK1saNC-M"

GSHEET_OP_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_OP_ID}/export?format=csv"
GSHEET_DUN_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_DUN_ID}/export?format=csv"

# Função para carregar os dados em tempo real (cache de 60 segundos)
@st.cache_data(ttl=60)
def carregar_dados_gsheet(url):
    return pd.read_csv(url)

# Botão para forçar a sincronização imediata
if st.sidebar.button("🔄 Sincronizar Planilhas (OP e SKUs)"):
    st.cache_data.clear()

dados_op = None
dados_dun = None

# Carregamento Automático da Planilha de OPs
try:
    dados_op = carregar_dados_gsheet(GSHEET_OP_URL)
    st.sidebar.success("✅ Planilha de OPs conectada!")
except Exception:
    st.sidebar.warning("⚠️ Não foi possível carregar a planilha de OPs.")

# Carregamento Automático da Planilha de DUNs/SKUs
try:
    dados_dun = carregar_dados_gsheet(GSHEET_DUN_URL)
    st.sidebar.success("✅ Planilha de SKUs / DUNs conectada!")
except Exception:
    st.sidebar.warning("⚠️ Não foi possível carregar a planilha de SKUs/DUNs.")

# Visualização das Tabelas Carregadas
if dados_op is not None or dados_dun is not None:
    with st.expander("📋 Ver Tabelas de Referência (OPs e SKUs)"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ordem de Produção (OP)")
            st.dataframe(dados_op)
        with col2:
            st.subheader("Cadastro SKU x DUN")
            st.dataframe(dados_dun)

if not api_key:
    st.warning("Insira a sua Chave de API na barra lateral para continuar.")
    st.stop()

# Inicializa o cliente do Gemini
client = genai.Client(api_key=api_key)

st.subheader("📷 Captura de Imagem")
img_file_buffer = st.camera_input("Tirar fotografia da embalagem/etiqueta")

if img_file_buffer is not None:
    image = Image.open(img_file_buffer)
    st.image(image, caption="Imagem Capturada", use_container_width=True)
    
    with st.spinner("Analisando liberação de produto final..."):
        contexto_op = ""
        if dados_op is not None:
            contexto_op += f"\n\n--- TABELA DE ORDEM DE PRODUÇÃO (OP) ATIVA ---\n{dados_op.to_string(index=False)}"
        
        if dados_dun is not None:
            contexto_op += f"\n\n--- TABELA DE REFERÊNCIA CADASTRO SKU x DUN-14 ---\n{dados_dun.to_string(index=False)}"
        
        prompt = f"""
        Você é um auditor de qualidade de linha de produção.
        Analise a imagem capturada e execute as verificações estruturadas abaixo.

        1. EXTRAÇÃO DE DADOS DA IMAGEM:
           - Identifique se o produto/etiqueta pertence à linha **JUNGLE**.
           - Descrição do Produto lida
           - Código SKU lido
           - Código de Barras DUN / EAN lido na etiqueta/caixa
           - Número do Lote (se presente)
           - Data de Validade / Fabricação (se presente)

        2. REGRAS OBRIGATÓRIAS DE VALIDAÇÃO:
           - **EXCEÇÃO ETIQUETAS JUNGLE**:
             * As etiquetas exclusivamente da linha **JUNGLE** possuem APENAS Descrição do Produto, Código DUN e SKU.
             * **É ESPERADO E NORMAL QUE ETIQUETAS JUNGLE NÃO POSSUAM LOTE NEM DATA DE VALIDADE.**
             * NUNCA aponte a falta de Lote ou Validade como erro ou ausência de dados para etiquetas da linha **JUNGLE**.
           
           - **Validação do DUN-14**:
             * O código DUN deve ter EXATAMENTE 14 dígitos numéricos.
             * Contabilize os dígitos do DUN lido na imagem. Se tiver mais ou menos de 14 dígitos, marque como erro.
           
           - **Cruzamento SKU x DUN x OP**:
             * O DUN lido e o SKU devem corresponder exatamente ao item cadastrado na Tabela de Referência SKU x DUN.
             * Verifique se o SKU/DUN corresponde a uma OP ativa na Tabela de Ordem de Produção (OP).

        {contexto_op}

        3. FORMATO DO RESULTADO:
           - Apresente os dados extraídos da imagem.
           - Informe a contagem de dígitos do DUN (ex: "DUN Lido: 17896045111081 - Total: 14 dígitos").
           - Exiba o parecer final claro:
             - ✅ **DADOS CONFORMES**: Se a etiqueta for Jungle (Descrição, DUN-14 e SKU corretos conforme a tabela) ou se for outro produto com todos os dados (incluindo Lote/Validade) corretos.
             - ❌ **DIVERGÊNCIA ENCONTRADA**: Detalhe estritamente a divergência encontrada (ex: divergência no código SKU/DUN, contagem incorreta de dígitos no DUN-14, ou SKU não bate com a OP).
        """
        
        # Lógica de Retry automático para erros de alta procura (503)
        max_tentativas = 3
        resposta = None
        
        for tentativa in range(max_tentativas):
            try:
                resposta = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[image, prompt]
                )
                break
            except Exception as e:
                if ("503" in str(e) or "UNAVAILABLE" in str(e)) and tentativa < max_tentativas - 1:
                    time.sleep(2)
                else:
                    st.error(f"Erro ao processar imagem com o Gemini: {e}")
                    st.stop()
        
        if resposta and resposta.text:
            st.markdown("### 🔍 Resultado da Validação")
            st.write(resposta.text)
