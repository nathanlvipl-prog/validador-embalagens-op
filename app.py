import json
from google import genai
from google.genai import types
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="Validador Multi-Máquinas OP", page_icon="🏭", layout="wide"
)

st.title("🏭 Validação de Codificação e Lotes por Máquina")
st.caption(
    "Validação visual (Lata + Etiqueta / Pacote + Caixa) com cruzamento de OP"
)

# Barra Lateral: Configurações e Carregamento da Folha de Cálculo
st.sidebar.header("⚙️ Configurações")
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Chave API do Gemini:", type="password")
arquivo_op = st.sidebar.file_uploader(
    "Carregar Folha de Cálculo de OP (Excel / CSV)", type=["xlsx", "csv"]
)

# Tabela de OPs em memória
dados_op = None
if arquivo_op:
  try:
    if arquivo_op.name.endswith(".csv"):
      dados_op = pd.read_csv(arquivo_op)
    else:
      dados_op = pd.read_excel(arquivo_op)
    st.sidebar.success("Folha de cálculo de OP carregada com sucesso!")
  except Exception as e:
    st.sidebar.error(f"Erro ao ler folha de cálculo: {e}")

if not api_key:
  st.warning("Insira a sua Chave de API na barra lateral para continuar.")
  st.stop()

client = genai.Client(api_key=api_key)

# Captura da Imagem pelo Telemóvel/Computador
st.subheader("📸 Captura de Imagem")
foto = st.camera_input("Tirar fotografia da embalagem (Lata+Etiqueta ou Pacote+Caixa)")

if foto:
  imagem = Image.open(foto)

  # Prompt genérico e inteligente para qualquer máquina
  prompt = """
    Atue como um inspetor de controlo de qualidade fabril especialista em OCR industrial.
    Analise a imagem e identifique os DOIS elementos de codificação presentes (exemplo: Tampa da Lata e Etiqueta Adesiva, ou Pacote Alumínio e Caixa de Papelão, ou Refil e Caixa).

    INSTRUÇÕES DE EXTRAÇÃO:
    1. Identifique o tipo de pares presentes na foto (ex: "LATA_E_ETIQUETA" ou "PACOTE_E_CAIXA" ou "REFIL_E_CAIXA").
    2. Identifique a Máquina (ex: "M028", "B16", "BOSCH16", "ML01", "LEEPACK", etc.).
    3. Extraia de CADA um dos dois elementos:
       - Data de Validade (normalizada no formato DD/MM/AAAA ou DD/MM/AA)
       - Lote (ex: "1096907", "1096911", "L1096911")
       - Sigla do Estado / UF (ex: "RN", "CO")
       - Código da Máquina
    4. Compare os dados entre o Elemento 1 e o Elemento 2.

    Responda EXCLUSIVAMENTE num formato JSON estrito com esta estrutura:
    {
      "tipo_par": "LATA_E_ETIQUETA ou PACOTE_E_CAIXA ou REFIL_E_CAIXA",
      "maquina_detectada": "M028 / B16 / ML01...",
      "conformidade_par": true ou false,
      "motivo_divergencia_par": "Caso exista divergência entre os dois elementos, descreva aqui. Se iguais, deixe vazio.",
      "elemento_1": {
        "nome": "Ex: Tampa da Lata / Pacote",
        "validade": "texto extraído",
        "maquina": "texto extraído",
        "lote": "texto extraído",
        "uf": "texto extraído"
      },
      "elemento_2": {
        "nome": "Ex: Etiqueta Adesiva / Caixa",
        "validade": "texto extraído",
        "maquina": "texto extraído",
        "lote": "texto extraído",
        "uf": "texto extraído"
      }
    }
    """

  with st.spinner("A analisar a imagem com visão computacional..."):
    try:
      response = client.models.generate_content(
          model="gemini-2.5-flash",
          contents=[imagem, prompt],
          config=types.GenerateContentConfig(
              response_mime_type="application/json"
          ),
      )

      res = json.loads(response.text)

      # Apresentação do Tipo de Validação
      st.info(
          f"🔍 **Par Detetado:** {res.get('tipo_par')} | **Máquina:**"
          f" {res.get('maquina_detectada')}"
      )

      # 1. Validação entre os dois elementos
      par_ok = res.get("conformidade_par", False)

      # 2. Validação contra a Folha de Cálculo de OP (se carregada)
      lote_elemento = (
          res.get("elemento_1", {})
          .get("lote", "")
          .replace("L", "")
          .strip()
      )
      maquina_elem = res.get("maquina_detectada", "").upper()

      op_ok = True
      motivo_op = ""

      if dados_op is not None and lote_elemento:
        # Procura o lote na folha de cálculo
        lotes_validos = (
            dados_op["LOTE PA"].astype(str).str.strip().tolist()
            if "LOTE PA" in dados_op.columns
            else []
        )

        if lote_elemento in lotes_validos:
          motivo_op = f"Lote {lote_elemento} confirmado na Folha de Cálculo de OP!"
        else:
          op_ok = False
          motivo_op = (
              f"Lote {lote_elemento} NÃO foi encontrado na Folha de Cálculo de"
              " OP!"
          )

      # Painel de Resultado Final
      st.subheader("Resultado da Inspeção")

      if par_ok and op_ok:
        st.success(f"✅ **PRODUTO CONFORME!**\n\n- {res.get('motivo_divergencia_par', 'Codificações idênticas entre elementos.')}\n- {motivo_op}")
      else:
        st.error("❌ **NÃO CONFORME!**")
        if not par_ok:
          st.write(f"• **Divergência de Impressão:** {res.get('motivo_divergencia_par')}")
        if not op_ok:
          st.write(f"• **Divergência de OP:** {motivo_op}")

      # Tabela Comparativa Visual
      col1, col2 = st.columns(2)
      with col1:
        st.markdown(f"### {res['elemento_1'].get('nome', 'Elemento 1')}")
        st.json(res["elemento_1"])
      with col2:
        st.markdown(f"### {res['elemento_2'].get('nome', 'Elemento 2')}")
        st.json(res["elemento_2"])

    except Exception as e:
      st.error(f"Erro ao processar validação: {e}")
