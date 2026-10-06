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
st.sidebar.header("⚙️ Configurações")

# Procura a chave nos Secrets do Streamlit Cloud ou pede na barra lateral
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Chave API do Gemini:", type="password")

# Link direto para a sua folha de cálculo do Google Sheets em formato CSV
SHEET_ID = "1G62clUnNEPBJVWS4VNrOTRq4YhZ2lQqCYsEjZxNsZOE"
GID = "220654294"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# Função para carregar os dados em tempo real (atualiza automaticamente a cada 60s)
@st.cache_data(ttl=60)
def carregar_dados_gsheet(url):
    return pd.read_csv(url)

# Botão para forçar a atualização imediata da folha se necessário
if st.sidebar.button("🔄 Sincronizar Folha de OP"):
    st.cache_data.clear()

# Carregamento da tabela de OPs
dados_op = None
try:
    dados_op = carregar_dados_gsheet(GSHEET_URL)
    st.sidebar.success("✅ Folha de OPs ligada ao Google Sheets!")
except Exception as e:
    st.sidebar.error(f"Erro ao carregar Google Sheets: {e}")
    st.sidebar.info("Certifique-se de que a folha está configurada como 'Qualquer pessoa com o link'.")

if not api_key:
    st.warning("Insira a sua Chave de API na barra lateral para continuar.")
    st.stop()

# Inicializa o cliente do Gemini
client = genai.Client(api_key=api_key)

st.subheader("📷 Captura de Imagem")
img_file_buffer = st.camera_input("Tirar fotografia da embalagem (Lata+Etiqueta ou Pacote+Caixa)")

if img_file_buffer is not None:
    image = Image.open(img_file_buffer)
    st.image(image, caption="Imagem Capturada", use_container_width=True)
    
    with st.spinner("A analisar imagem com o Gemini..."):
        prompt = """
        Analise a imagem da embalagem e extraia as seguintes informações em formato estruturado:
        - Código de Barras / EAN
        - Número do Lote
        - Data de Validade / Fabricação
        - Linha / Máquina (se visível)
        
        Forneça uma resposta clara e objetiva com os dados identificados.
        """
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image, prompt]
            )
            
            st.markdown("### 🔍 Resultado da Análise OCR")
            st.write(response.text)
            
        except Exception as e:
            st.error(f"Erro ao processar imagem com o Gemini: {e}")
