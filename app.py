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
uploaded_file = st.sidebar.file_uploader("Ou carregue manualmente (Excel / CSV):", type=["xlsx", "csv"])
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            dados_op = pd.read_csv(uploaded_file)
        else:
            dados_op = pd.read_excel(uploaded_file)
        st.sidebar.success("✅ Ficheiro de OP carregado manualmente!")
    except Exception as e:
        st.sidebar.error(f"Erro ao ler ficheiro: {e}")

# Visualização da Tabela de OPs ativas
if dados_op is not None:
    with st.expander("📋 Ver Tabela de OPs Carregada"):
        st.dataframe(dados_op)

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
        contexto_op = ""
        if dados_op is not None:
            contexto_op = f"\n\nDados da Tabela de OP Atual:\n{dados_op.to_string(index=False)}"
        
        prompt = f"""
        Analise a imagem da embalagem e extraia as seguintes informações em formato estruturado:
        - Código de Barras / EAN
        - Número do Lote
        - Data de Validade / Fabricação
        - Linha / Máquina (se visível)
        
        Compare os dados lidos na imagem com a Tabela de OPs fornecida abaixo e valide se a produção está correta.{contexto_op}
        
        Forneça um parecer final claro:
        - ✅ DADOS CONFORMES (se o lote e a validade corresponderem à OP)
        - ❌ DIVERGÊNCIA ENCONTRADA (se houver alguma inconformidade)
        """
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[image, prompt]
            )
            
            st.markdown("### 🔍 Resultado da Validação")
            st.write(response.text)
            
        except Exception as e:
            st.error(f"Erro ao processar imagem com o Gemini: {e}")
