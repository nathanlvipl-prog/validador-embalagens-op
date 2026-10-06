import streamlit as st
import pandas as pd
from PIL import Image
from google import genai

st.set_page_config(
    page_title="Validador Multi-Máquinas OP", page_icon="🏭", layout="wide"
)

st.title("🏭 Validação de Codificação e Lotes por Máquina")
st.caption("Validação de conformidade de embalagem primária vs secundária e OP")

# Barra Lateral: Configurações
st.sidebar.header("⚙ Configurações")

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

if not api_keys:
    st.warning("Insira pelo menos uma Chave de API na barra lateral para continuar.")
    st.stop()

st.subheader("📷 Captura de Imagem")
img_file_buffer = st.camera_input("Tirar fotografia da embalagem/etiqueta")

if img_file_buffer is not None:
    image = Image.open(img_file_buffer)
    st.image(image, caption="Imagem Capturada", use_container_width=True)
    
    with st.spinner("⚡ Analisando imagem caractere por caractere..."):
        # Manter alta resolução para não desfocar matriz de pontos inkjet
        image_otimizada = image.copy()
        image_otimizada.thumbnail((2048, 2048))
        
        contexto_op = ""
        if dados_op is not None:
            contexto_op += f"\n\n--- ORDEM DE PRODUÇÃO (OP) ATIVA ---\n{dados_op.to_string(index=False)}"
        
        if dados_dun is not None:
            contexto_op += f"\n\n--- CADASTRO SKU x DUN-14 ---\n{dados_dun.to_string(index=False)}"
        
        prompt = f"""
        Você é um auditor de controle de qualidade industrial de alta precisão.
        Sua tarefa é fazer o OCR caractere por caractere e validar os dados da imagem.

        Siga rigorosamente estas 4 etapas:

        ETAPA 1: OCR E TRANSCRIÇÃO DIRETA DA IMAGEM
        - Transcreva com extrema atenção aos números da matriz de pontos (inkjet):
          • **Embalagem Primária (Refil/Pacote/Sachê em cima)**: Lote = [escreva aqui], Validade = [escreva aqui]
          • **Embalagem Secundária (Caixa de Papelão/Etiqueta em baixo)**: Lote = [escreva aqui], Validade = [escreva aqui], EAN/DUN = [escreva aqui]

        ETAPA 2: COMPARAÇÃO DIRETA (PRIMÁRIA VS SECUNDÁRIA)
        - Compare o Lote da Embalagem Primária com o Lote da Embalagem Secundária.
        - Se houver divergência de 1 único dígito ou caractere entre o pacote e a caixa, reporte IMEDIATAMENTE como NÃO CONFORME.

        ETAPA 3: CONFRONTO COM TABELAS DE REFERÊNCIA
        - Verifique se os dados lidos conferem com a OP e Cadastro abaixo.
        {contexto_op}

        ETAPA 4: VEREDITO FINAL
        Exiba o resultado neste formato:

        ### 🔍 Dados Identificados
        - **Refil/Pacote**: Lote: `[lote_refil]` | Validade: `[validade_refil]`
        - **Caixa**: Lote: `[lote_caixa]` | Validade: `[validade_caixa]`

        ---
        ### 📋 Resultado da Validação

        Se TUDO for exatamente igual e bater com a OP:
        ✅ **VALIDAÇÃO DE P.A CONFORME**
        *Todos os dados da embalagem conferem entre si e com a Ordem de Produção.*

        Se houver QUALQUER DIVERGÊNCIA (Lote do refil diferente do lote da caixa ou dados divergentes da OP):
        ❌ **VALIDAÇÃO DE P.A NÃO CONFORME**
        **Motivo da Não Conformidade:** [Explique claramente onde está a divergência, por exemplo: "O Lote impresso no Refil (L1090543) é diferente do Lote impresso na Caixa (L1097543)".]
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
            st.markdown(resposta.text)
        else:
            if "429" in str(ultimo_erro) or "RESOURCE_EXHAUSTED" in str(ultimo_erro):
                st.error("⚠️ Quota excedida na chave API. Adicione outra chave na barra lateral.")
            else:
                st.error(f"Erro no processamento: {ultimo_erro}")
