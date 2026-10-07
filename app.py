import streamlit as st
import pandas as pd
from PIL import Image
from google import genai

# 1. Configuração da Página
st.set_page_config(
    page_title="Qualit3c - Liberação de Produto Final", 
    page_icon="📦", 
    layout="wide"
)

# 2. DICIONÁRIO DE MATRÍCULAS E COLABORADORES
CADASTRO_COLABORADORES = {
    "32164": "SILVIO NATHANAEL MEDEIROS DA SILVA",
    "32177": "EMANUEL LUCAS SEVERIANO DE SOUSA"
}

# 3. GERENCIAMENTO DE SESSÃO / TELA ATIVA
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario_nome" not in st.session_state:
    st.session_state.usuario_nome = ""
if "usuario_funcao" not in st.session_state:
    st.session_state.usuario_funcao = ""
if "usuario_matricula" not in st.session_state:
    st.session_state.usuario_matricula = ""

# 4. ESTILIZAÇÃO CSS (QUALIT3C EXACT STYLE)
st.markdown("""
<style>
    /* Ocultar cabeçalho padrão do Streamlit */
    header[data-testid="stHeader"] {
        background-color: transparent;
    }

    /* ESTILO DA TELA DE LOGIN (TELA 1) */
    .login-container {
        background: #ffffff;
        border-radius: 12px;
        padding: 35px 25px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        border-top: 6px solid #e67e22;
        margin-top: 20px;
    }
    .qualit3c-logo {
        font-size: 2.3rem;
        font-weight: 800;
        color: #333333;
        text-align: center;
        margin-bottom: 5px;
    }
    .qualit3c-logo span {
        color: #e67e22;
    }
    .qualit3c-subtitle {
        text-align: center;
        color: #7f8c8d;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-bottom: 25px;
    }

    /* ESTILO DA TELA DE VALIDAÇÃO (TELA 2) */
    .stApp {
        background-color: #f2f4f7;
        color: #2c3e50;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Banner Superior estilo Qualit3c / SAP tablet */
    .qualit3c-topbar {
        background: linear-gradient(90deg, #d35400 0%, #e67e22 100%);
        color: #ffffff;
        padding: 12px 18px;
        border-radius: 6px;
        margin-bottom: 18px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .qualit3c-topbar-user {
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    .qualit3c-topbar-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
    }

    /* Cards e Containers Brancos */
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
        border-bottom: 2px solid #e67e22;
        padding-bottom: 6px;
    }

    /* Botões Padrão Laranja Qualit3c */
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

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }

    /* Area de Upload */
    section[data-testid="stFileUploadDropzone"] {
        background-color: #ffffff !important;
        border: 2px dashed #e67e22 !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# TELA 1: IDENTIFICAÇÃO DO COLABORADOR (QUALIT3C)
# ==============================================================================
if not st.session_state.logged_in:
    col_left, col_center, col_right = st.columns([1, 1.8, 1])
    
    with col_center:
        st.markdown("""
        <div class="login-container">
            <div class="qualit3c-logo">Qualit<span>3c</span></div>
            <div class="qualit3c-subtitle">SISTEMA DE CONTROLE DE QUALIDADE</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_identificacao"):
            funcao_selecionada = st.selectbox(
                "Função",
                ["Controle de Qualidade", "Operador de Produção"]
            )
            
            matricula_digitada = st.text_input(
                "Matrícula",
                placeholder="Ex: 32164"
            )
            
            btn_entrar = st.form_submit_button("ENTRAR", use_container_width=True)
            
            if btn_entrar:
                mat_clean = matricula_digitada.strip()
                if mat_clean == "":
                    st.error("O campo 'Matrícula' é obrigatório.")
                else:
                    # Converte a matrícula para o nome do colaborador
                    nome_colaborador = CADASTRO_COLABORADORES.get(
                        mat_clean, 
                        f"COLABORADOR {mat_clean}"
                    )
                    
                    st.session_state.logged_in = True
                    st.session_state.usuario_nome = nome_colaborador
                    st.session_state.usuario_funcao = funcao_selecionada
                    st.session_state.usuario_matricula = mat_clean
                    st.rerun()

    st.stop()


# ==============================================================================
# TELA 2: VALIDAÇÃO E LIBERAÇÃO DE PRODUTO FINAL
# ==============================================================================

# Cabeçalho Laranja idêntico ao Qualit3c
st.markdown(f"""
<div class="qualit3c-topbar">
    <div class="qualit3c-topbar-user">
        👤 {st.session_state.usuario_nome.upper()} | {st.session_state.usuario_funcao.upper()}
    </div>
    <div class="qualit3c-topbar-title">📦 Liberação de Produto Final</div>
</div>
""", unsafe_allow_html=True)

# Barra Lateral (Sidebar)
st.sidebar.header("👤 Colaborador Ativo")
st.sidebar.info(
    f"**Nome:** {st.session_state.usuario_nome}\n\n"
    f"**Função:** {st.session_state.usuario_funcao}\n\n"
    f"**Matrícula:** {st.session_state.usuario_matricula}"
)

if st.sidebar.button("🚪 Sair / Trocar Usuário", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.usuario_nome = ""
    st.session_state.usuario_funcao = ""
    st.session_state.usuario_matricula = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurações do Sistema")

# Chaves API Gemini
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    raw_api_keys = st.secrets["GEMINI_API_KEY"]
else:
    raw_api_keys = st.sidebar.text_input("Chave(s) API do Gemini (separadas por vírgula):", type="password")

api_keys = [k.strip() for k in raw_api_keys.split(",") if k.strip()] if raw_api_keys else []

# Carregamento de Planilhas Google
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

# Tabela de Referência
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

# Card de Upload/Câmera
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
            image_otimizada =
