import streamlit as st
import pandas as pd
from PIL import Image
from google import genai

st.set_page_config(
    page_title="Validador Multi-Máquinas OP", page_icon="🏭", layout="wide"
)

st.title("🏭 Validação de Codificação e Lotes por Máquina")
st.caption(
    "Validação visual rápida (Lata + Etiqueta / Pacote + Caixa / Etiquetas Jungle)"
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

# MODIFICAÇÃO: Utiliza o seletor nativo do sistema que ativa a câmera traseira nos telemóveis/celulares
img_file_buffer = st.file_uploader(
    "Tirar foto da embalagem/etiqueta (Câmera Traseira)", 
    type=["jpg", "jpeg", "png", "webp"]
)

if img_file_buffer is not None:
    image = Image.open(img_file_buffer)
    st.image(image, caption="Imagem Capturada", use_container_width=True)
    
    with st.spinner("⚡ Analisando imagem..."):
        # Ajustado para 2048px para preservar detalhes de impressão inkjet sem desfocar
        image_otimizada = image.copy()
        image_otimizada.thumbnail((2048, 2048))
        
        contexto_op = ""
        if dados_op is not None:
            contexto_op += f"\n\n--- TABELA DE ORDEM DE PRODUÇÃO (OP) ATIVA ---\n{dados_op.to_string(index=False)}"
        
        if dados_dun is not None:
            contexto_op += f"\n\n--- TABELA DE REFERÊNCIA CADASTRO SKU x DUN-14 ---\n{dados_dun.to_string(index=False)}"
        
        prompt = f"""
        Você é um auditor de qualidade de linha de produção.
        Analise a imagem capturada e execute as verificações estruturadas abaixo:

        1. EXTRAÇÃO DE DADOS DA IMAGEM:
           - Identifique se pertence à linha JUNGLE (Sim/Não)
           - Descrição do Produto lida
           - Código SKU lido
           - Código de Barras DUN / EAN lido
           - Número do Lote (se presente)
           - Data de Validade / Fabricação (se presente)

        2. REGRAS OBRIGATÓRIAS DE VALIDAÇÃO:
           - **EXCEÇÃO ETIQUETAS JUNGLE**:
             * As etiquetas exclusivamente da linha JUNGLE possuem APENAS Descrição do Produto, Código DUN e SKU.
             * **É ESPERADO E NORMAL QUE ETIQUETAS JUNGLE NÃO POSSUAM LOTE NEM DATA DE VALIDADE.**
             * NUNCA aponte a falta de Lote ou Validade como erro para a linha JUNGLE.
           
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
             - ✅ **DADOS CONFORMES**: Se a etiqueta for Jungle (Descrição, DUN-14 e SKU corretos) ou outro produto com todos os dados corretos.
             - ❌ **DIVERGÊNCIA ENCONTRADA**: Detalhe estritamente a divergência.
        """
        
        MODELO = "gemini-2.5-flash"
        
        resposta = None
        ultimo_erro = None
        
        for key in api_keys:
            try:
                client = genai.Client(api_key=key)
                resposta = client.models.generate_content(
                    model=MODELO,
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
