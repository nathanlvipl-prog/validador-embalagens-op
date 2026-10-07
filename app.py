import streamlit as st
import pandas as pd
from PIL import Image
from google import genai

# 1. Configuração da Página
st.set_page_config(
    page_title="Liberação de Produto Final - Qualit3c", 
    page_icon="📦", 
    layout="wide"
)

# 2. INJEÇÃO DE CSS PERSONALIZADO (ESTILO QUALIT3C)
st.markdown("""
<style>
    /* Fundo geral da aplicação */
    .stApp {
        background-color: #f2f4f7;
        color: #2c3e50;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Ocultar cabeçalho padrão do Streamlit */
    header[data-testid="stHeader"] {
        background-color: transparent;
    }

    /* Header Laranja estilo Qualit3c */
    .qualit3c-topbar {
        background: linear-gradient(90deg, #e67e22 0%, #f39c12 100%);
        color: white;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.12);
    }
    .qualit3c-topbar h1 {
        color: #ffffff !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .qualit3c-topbar p {
        color: #fefefe !important;
        font-size: 0.85rem !important;
        margin: 4px 0 0 0 !important;
        opacity: 0.95;
    }

    /* Estilo dos Cards/Containers Brancos */
    .qualit3c-card {
        background-color: #ffffff;
        border: 1px solid #dcdfe6;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .qualit3c-card-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 10px;
        border-bottom: 2px solid #f39c12;
        padding-bottom: 6px;
    }

    /* Botões estilizados */
    .stButton > button {
        background-color: #e67e22 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(230, 126, 34, 0.3);
    }
    .stButton > button:hover {
        background-color: #d35400 !important;
        box-shadow: 0 4px 8px rgba(211, 84, 0, 0.4);
    }

    /* Estilização da Barra Lateral */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }

    /* Caixa de Upload */
    section[data-testid="stFileUploadDropzone"] {
        background-color: #ffffff !important;
        border: 2px dashed #e67e22 !important;
        border-radius: 8px !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        border-radius: 6px !important;
        border: 1px solid #dcdfe6 !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. CABEÇALHO DO SISTEMA
st.markdown("""
<div class="qualit3c-topbar">
    <h1>📦 Liberação de Produto Final</h1>
    <p>SISTEMA DE CONTROLE DE QUALIDADE | INSPEÇÃO E AUDITORIA DE PRODUTO FINAL</p>
</div>
""", unsafe_allow_html=True)

# 4. BARRA LATERAL (Configurações)
st.sidebar.header("⚙️ Configurações do Sistema")

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

if st.sidebar.button("🔄 Sincronizar Planilhas (OP e SKUs)", use_container_width=True):
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

# 5. TABELAS DE REFERÊNCIA
if dados_op is not None or dados_dun is not None:
    with st.expander("📋 Tabela de Referência para Liberação (OPs e SKUs)"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ordem de Produção (OP)")
            st.dataframe(dados_op, use_container_width=True)
        with col2:
            st.subheader("Cadastro SKU x DUN")
            st.dataframe(dados_dun, use_container_width=True)

if not api_keys:
    st.warning("⚠️ Insira pelo menos uma Chave de API na barra lateral para liberar a validação.")
    st.stop()

# 6. CAPTURA E LIBERAÇÃO DE PRODUTO FINAL
st.markdown("""
<div class="qualit3c-card">
    <div class="qualit3c-card-title">📷 Captura da Embalagem para Liberação</div>
</div>
""", unsafe_allow_html=True)

img_file_buffer = st.file_uploader(
    "Toque para abrir a câmera ou selecione a imagem da embalagem/etiqueta", 
    type=["jpg", "jpeg", "png"]
)

if img_file_buffer is not None:
    image = Image.open(img_file_buffer)
    
    col_img, col_res = st.columns([1, 1])
    
    with col_img:
        st.image(image, caption="Imagem do Produto Capturada", use_container_width=True)
    
    with col_res:
        with st.spinner("⚡ Inspecionando produto para liberação..."):
            image_otimizada = image.copy()
            image_otimizada.thumbnail((1024, 1024))
            
            contexto_op = ""
            if dados_op is not None:
                contexto_op += f"\n\n--- TABELA DE ORDEM DE PRODUÇÃO (OP) ATIVA ---\n{dados_op.to_string(index=False)}"
            
            if dados_dun is not None:
                contexto_op += f"\n\n--- TABELA DE REFERÊNCIA CADASTRO SKU x DUN-14 ---\n{dados_dun.to_string(index=False)}"
            
            prompt = f"""
            Você é um auditor de qualidade responsável pela LIBERAÇÃO DE PRODUTO FINAL na linha de produção.
            Analise a imagem capturada e execute a verificação estruturada abaixo:

            1. EXTRAÇÃO DE DADOS DA EMBALAGEM:
               - Pertence à linha JUNGLE? (Sim/Não)
               - Descrição do Produto lida
               - Código SKU lido
               - Código de Barras DUN / EAN lido
               - Número do Lote (se presente)
               - Data de Validade / Fabricação (se presente)

            2. REGRAS OBRIGATÓRIAS DE LIBERAÇÃO:
               - **EXCEÇÃO ETIQUETAS JUNGLE**:
                 * As etiquetas exclusivamente da linha JUNGLE possuem APENAS Descrição do Produto, Código DUN e SKU.
                 * **É ESPERADO E NORMAL QUE ETIQUETAS JUNGLE NÃO POSSUAM LOTE NEM DATA DE VALIDADE.**
                 * NUNCA reprove ou aponte a falta de Lote ou Validade como erro para a linha JUNGLE.
               
               - **Validação do DUN-14**:
                 * O código DUN deve ter EXATAMENTE 14 dígitos numéricos.
                 * Contabilize os dígitos do DUN lido na imagem. Se tiver mais ou menos de 14 dígitos, marque como erro.
               
               - **Cruzamento SKU x DUN x OP**:
                 * O DUN lido e o SKU devem corresponder exatamente ao item cadastrado na Tabela de Referência SKU x DUN.
                 * Verifique se o SKU/DUN corresponde a uma OP ativa na Tabela de Ordem de Produção (OP).

            {contexto_op}

            3. FORMATO DO PARECER DE LIBERAÇÃO:
               - Apresente os dados extraídos da embalagem.
               - Informe a contagem de dígitos do DUN (ex: "DUN Lido: 17896045111081 - Total: 14 dígitos").
               - Exiba o parecer de liberação final bem destacado:
                 - ✅ **LIBERAÇÃO APROVADA (PRODUTO CONFORME)**: Se a etiqueta for Jungle ou outro produto com todas as informações corretas e alinhadas com a OP.
                 - ❌ **LIBERAÇÃO REPROVADA (DIVERGÊNCIA ENCONTRADA)**: Detalhe estritamente o motivo da não conformidade.
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
                st.markdown("### 🔍 Parecer de Liberação do Produto")
                st.markdown(resposta.text)
            else:
                if "429" in str(ultimo_erro) or "RESOURCE_EXHAUSTED" in str(ultimo_erro):
                    st.error("⚠️ Quota diária atingida nesta chave API. Adicione outra chave separada por vírgula.")
                else:
                    st.error(f"Erro no processamento: {ultimo_erro}. Tente novamente.")
