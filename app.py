import streamlit as st
import pandas as pd
from PIL import Image
from google import genai

st.set_page_config(
    page_title="Validador Multi-Máquinas OP", page_icon="🏭", layout="wide"
)

st.title("🏭 Validação de Codificação e Lotes por Máquina")
st.caption(
    "Validação visual (Lata + Etiqueta / Pacote + Caixa) com cruzamento de OP"
)

# Barra Lateral: Configurações e Integração Google Sheets
st.sidebar.header("⚙ Configurações")

# Procura a chave nos Secrets do Streamlit Cloud ou pede na barra lateral
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Chave API do Gemini:", type="password")

# ID da folha de cálculo do Google Sheets
SHEET_ID = "1YScgtOowZjmTWMKnlcwya1nPQKt0u34luPSb4U82_-E"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# Função para carregar os dados em tempo real (atualiza automaticamente a cada 60s)
@st.cache_data(ttl=60)
def carregar_dados_gsheet(url):
    return pd.read_csv(url)

# Botão para forçar a sincronização imediata
if st.sidebar.button("🔄 Sincronizar Folha de OP"):
    st.cache_data.clear()

dados_op = None

# Tenta carregar automaticamente do Google Sheets
try:
    dados_op = carregar_dados_gsheet(GSHEET_URL)
    st.sidebar.success("✅ Folha de OPs ligada ao Google Sheets!")
except Exception:
    st.sidebar.warning("⚠️ Não foi possível aceder ao Google Sheets automaticamente.")

# Opção de Carregamento Manual como alternativa
uploaded_file = st.sidebar.file_uploader("Ou carregue manualmente
