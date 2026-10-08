import base64
from datetime import datetime, timedelta, timezone
import io
import re
from google import genai
import pandas as pd
from PIL import Image
import requests
import streamlit as st

# ==============================================================================
# CONFIGURAÇÃO DE FUSO HORÁRIO BRASIL (UTC-3) E CÁLCULO DE TURNO
# ==============================================================================
FUSO_BR = timezone(timedelta(hours=-3))


def obter_datetime_br():
  """Retorna o objeto datetime atual no fuso horário do Brasil (UTC-3)"""
  return datetime.now(FUSO_BR)


def obter_hora_atual():
  """Retorna data e hora formatadas no fuso horário do Brasil (UTC-3)"""
  return obter_datetime_br().strftime("%d/%m/%Y %H:%M:%S")


def calcular_turno(dt=None):
  """Calcula o turno com base nos intervalos de horário definidos"""
  if dt is None:
    dt = obter_datetime_br()

  minutos_totais = dt.hour * 60 + dt.minute

  # 05:40 = 340 min | 14:00 = 840 min | 22:20 = 1340 min
  if 340 <= minutos_totais < 840:
    return "Turno A"
  elif 840 <= minutos_totais < 1340:
    return "Turno B"
  else:
    return "Turno C"


def extrair_apenas_digitos(texto):
  """Remove tudo que não for dígito numérico"""
  if not texto:
    return ""
  return re.sub(r"\D", "", str(texto))


def formatar_validade(val_str):
  """Garante a formatação com pontos (ex: 08.10.2027)"""
  if not val_str:
    return "00.00.0000"
  digitos = extrair_apenas_digitos(val_str)
  if len(digitos) == 8:
    return f"{digitos[:2]}.{digitos[2:4]}.{digitos[4:]}"
  elif len(digitos) == 6:
    return f"{digitos[:2]}.{digitos[2:4]}.20{digitos[4:]}"
  val_clean = str(val_str).strip().replace("/", ".").replace("-", ".")
  return val_clean if val_clean else "00.00.0000"


def formatar_lote(lote_raw):
  """Garante o formato com espaço entre 'L' e a numeração (ex: L 1098396)"""
  digitos = extrair_apenas_digitos(lote_raw)
  if digitos:
    return f"L {digitos}"
  lote_clean = str(lote_raw).strip()
  if lote_clean.upper().startswith("L"):
    return f"L {lote_clean[1:].strip()}"
  return f"L {lote_clean}" if lote_clean else "L 0000000"


def converter_imagem_base64(img):
  """Otimiza e converte a imagem PIL para string Base64 compacta"""
  img_copia = img.copy()
  if img_copia.width > 1600 or img_copia.height > 1600:
    img_copia.thumbnail((1600, 1600))
  buffered = io.BytesIO()
  img_copia.convert("RGB").save(buffered, format="JPEG", quality=85)
  return base64.b64encode(buffered.getvalue()).decode("utf-8")


# ==============================================================================
# CONFIGURAÇÃO GERAL E LINK DO WEBHOOK GOOGLE SHEETS / DRIVE
# ==============================================================================
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxveohVoFHdb5UUcSFBq3N3Jh-V_2VEGMbwt0cCBpp92myghXb7XE90n0eQJPtLgaLybA/exec"

st.set_page_config(
    page_title="Qualit3c - Liberação do Produto Final",
    page_icon="📦",
    layout="wide",
)

# CADASTRO DE COLABORADORES
CADASTRO_COLABORADORES = {
    "32164": "SILVIO NATHANAEL MEDEIROS DA SILVA",
    "32177": "EMANUEL LUCAS SEVERIANO DE SOUSA",
}

# GERENCIAMENTO DE SESSÃO / NAVEGAÇÃO
if "pagina" not in st.session_state:
  st.session_state.pagina = 1

if "usuario_nome" not in st.session_state:
  st.session_state.usuario_nome = ""
if "usuario_funcao" not in st.session_state:
  st.session_state.usuario_funcao = ""
if "usuario_matricula" not in st.session_state:
  st.session_state.usuario_matricula = ""
if "hora_login" not in st.session_state:
  st.session_state.hora_login = ""

if "imagem_capturada" not in st.session_state:
  st.session_state.imagem_capturada = None
if "resultado_analise" not in st.session_state:
  st.session_state.resultado_analise = ""
if "hora_analise" not in st.session_state:
  st.session_state.hora_analise = ""


# FUNÇÃO PARA ENVIAR LOGS E IMAGEM PARA O GOOGLE SHEETS/DRIVE
def enviar_log_sheets(webhook_url, dados):
  """Envia os dados de registro e imagem via HTTP POST"""
  if not webhook_url or "SUA_URL" in webhook_url:
    return False
  try:
    res = requests.post(webhook_url, json=dados, timeout=25)
    if res.status_code == 200 and "Sucesso" in res.text:
      return True
    return False
  except Exception as e:
    print(f"Erro ao enviar para o webhook: {e}")
    return False


# ESTILIZAÇÃO CSS
st.markdown(
    """
<style>
    header[data-testid="stHeader"] { background-color: transparent; }

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
    .qualit3c-logo span { color: #e67e22; }
    .qualit3c-subtitle {
        text-align: center;
        color: #7f8c8d;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-bottom: 25px;
    }

    .stApp {
        background-color: #f2f4f7;
        color: #2c3e50;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

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
        margin-bottom: 4px;
    }
    .qualit3c-topbar-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
    }

    .qualit3c-card {
        background-color: #ffffff;
        border: 1px solid #dcdfe6;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }

    details {
        background-color: #f8f9fa;
        border: 1px solid #dcdfe6;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    summary {
        font-weight: 700;
        cursor: pointer;
        color: #2c3e50;
    }

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

    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# CONFIGURAÇÕES NA SIDEBAR
api_keys = []

if st.session_state.pagina > 1:
  st.sidebar.header("👤 Validador Ativo")
  st.sidebar.info(
      f"**Nome:** {st.session_state.usuario_nome}\n\n"
      f"**Função:** {st.session_state.usuario_funcao}\n\n"
      f"**Matrícula:** {st.session_state.usuario_matricula}\n\n"
      f"**Login:** {st.session_state.hora_login}"
  )

  if st.sidebar.button("🚪 Sair / Trocar Usuário", use_container_width=True):
    st.session_state.pagina = 1
    st.session_state.usuario_nome = ""
    st.session_state.usuario_funcao = ""
    st.session_state.usuario_matricula = ""
    st.session_state.imagem_capturada = None
    st.session_state.resultado_analise = ""
    st.rerun()

  st.sidebar.markdown("---")
  st.sidebar.header("⚙️ Configurações do Sistema")

  if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    raw_api_keys = st.secrets["GEMINI_API_KEY"]
  else:
    raw_api_keys = st.sidebar.text_input(
        "Chave(s) API do Gemini (separadas por vírgula):", type="password"
    )

  api_keys = (
      [k.strip() for k in raw_api_keys.split(",") if k.strip()]
      if raw_api_keys
      else []
  )

# ==============================================================================
# PÁGINA 1: IDENTIFICAÇÃO DO VALIDADOR
# ==============================================================================
if st.session_state.pagina == 1:
  col_left, col_center, col_right = st.columns([1, 1.8, 1])

  with col_center:
    st.markdown(
        """
        <div class="login-container">
            <div class="qualit3c-logo">Qualit<span>3c</span></div>
            <div class="qualit3c-subtitle">SISTEMA DE CONTROLE DE QUALIDADE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("form_login"):
      funcao_selecionada = st.selectbox(
          "Função", ["Controle de Qualidade", "Operador de Produção"]
      )

      matricula_digitada = st.text_input("Matrícula", placeholder="Ex: 32164")

      btn_entrar = st.form_submit_button("ENTRAR", use_container_width=True)

      if btn_entrar:
        mat_clean = matricula_digitada.strip()
        if mat_clean == "":
          st.error("O campo 'Matrícula' é obrigatório.")
        else:
          nome_colaborador = CADASTRO_COLABORADORES.get(
              mat_clean, f"COLABORADOR {mat_clean}"
          )

          hora_agora = obter_hora_atual()

          st.session_state.usuario_nome = nome_colaborador
          st.session_state.usuario_funcao = funcao_selecionada
          st.session_state.usuario_matricula = mat_clean
          st.session_state.hora_login = hora_agora
          st.session_state.pagina = 2

          log_login = {
              "data_hora": hora_agora,
              "tipo_evento": "LOGIN",
              "matricula": mat_clean,
              "nome": nome_colaborador,
              "funcao": funcao_selecionada,
              "status": "LOGIN REALIZADO",
              "detalhes": f"Acesso ao sistema às {hora_agora}",
          }
          enviar_log_sheets(WEBHOOK_URL, log_login)
          st.rerun()

# ==============================================================================
# PÁGINA 2: LIBERAÇÃO DO PRODUTO FINAL
# ==============================================================================
elif st.session_state.pagina == 2:
  st.markdown(
      f"""
    <div class="qualit3c-topbar">
        <div class="qualit3c-topbar-user">
            👤 {st.session_state.usuario_nome.upper()} | {st.session_state.usuario_funcao.upper()}
        </div>
        <div class="qualit3c-topbar-title">📦 Liberação do Produto Final</div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  GSHEET_OP_POLI_URL = "https://docs.google.com/spreadsheets/d/1YScgtOowZjmTWMKnlcwya1nPQKt0u34luPSb4U82_-E/export?format=csv&gid=220654294"
  GSHEET_OP_INST_URL = "https://docs.google.com/spreadsheets/d/1YScgtOowZjmTWMKnlcwya1nPQKt0u34luPSb4U82_-E/export?format=csv&gid=904615686"

  SHEET_DUN_ID = "1TDROYy4E6u41k6n05lWyGfh3o7SjYz4JoofK1saNC-M"
  GSHEET_DUN_URL = (
      f"https://docs.google.com/spreadsheets/d/{SHEET_DUN_ID}/export?format=csv"
  )

  @st.cache_data(ttl=60)
  def carregar_dados_gsheet(url):
    return pd.read_csv(url)

  dados_op_poli = None
  dados_op_inst = None
  dados_op = None
  dados_dun = None

  try:
    dados_op_poli = carregar_dados_gsheet(GSHEET_OP_POLI_URL)
  except Exception:
    pass

  try:
    dados_op_inst = carregar_dados_gsheet(GSHEET_OP_INST_URL)
  except Exception:
    pass

  try:
    dados_dun = carregar_dados_gsheet(GSHEET_DUN_URL)
  except Exception:
    pass

  lista_ops = [df for df in [dados_op_poli, dados_op_inst] if df is not None]
  if lista_ops:
    dados_op = pd.concat(lista_ops, ignore_index=True)

  with st.expander("📋 Tabela de Referência para Liberação (OPs e SKUs)"):
    col1, col2 = st.columns(2)
    with col1:
      st.subheader("Ordens de Produção (OP)")
      tab_poli, tab_inst = st.tabs(["Poli", "Inst / Revolução"])

      with tab_poli:
        if dados_op_poli is not None:
          st.dataframe(dados_op_poli, use_container_width=True)
        else:
          st.info("Aba 'Poli' em carregamento...")

      with tab_inst:
        if dados_op_inst is not None:
          st.dataframe(dados_op_inst, use_container_width=True)
        else:
          st.info("Aba 'Inst / Revolução' em carregamento...")

    with col2:
      st.subheader("Cadastro SKU x DUN")
      if dados_dun is not None:
        st.dataframe(dados_dun, use_container_width=True)
      else:
        st.info("Planilha de DUNs em carregamento...")

  if not api_keys:
    st.warning(
        "⚠️ Insira pelo menos uma Chave de API na barra lateral para prosseguir."
    )
    st.stop()

  img_file_buffer = st.file_uploader(
      "Upload da foto do produto / embalagem",
      type=["jpg", "jpeg", "png"],
      label_visibility="collapsed",
  )

  if img_file_buffer is not None:
    image = Image.open(img_file_buffer)

    col_img, col_btn = st.columns([1.2, 1])
    with col_img:
      st.image(image, caption="Imagem Capturada", use_container_width=True)

    with col_btn:
      st.write(" ")
      st.write(" ")
      if st.button(
          "🔬 PROCESSAR E GERAR LIBERAÇÃO", use_container_width=True
      ):
        with st.spinner("⚡ Leitura OCR de alta velocidade e precisão..."):
          dt_now = obter_datetime_br()
          hora_foto = dt_now.strftime("%d/%m/%Y %H:%M:%S")
          turno_atual = calcular_turno(dt_now)

          image_otimizada = image.copy()
          if image_otimizada.width > 2048 or image_otimizada.height > 2048:
            image_otimizada.thumbnail((2048, 2048))

          prompt_ocr = """
                    Você é um motor de OCR industrial especialista em embalagens alimentícias.
                    Examine estritamente a IMAGEM ATUAL fornecida e extraia as informações exatas sem interpretar regras de negócio ou inventar dados.

                    ATENÇÃO PARA TEXTOS ROTACIONADOS / VERTICAIS:
                    - O texto na embalagem primária (refil/lata/sachê) pode estar impresso na vertical ou rotacionado a 90°. Escaneie todas as orientações.
                    - Leia a impressão inkjet caractere por caractere (ex: 1098396).

                    Retorne ESTRITAMENTE o texto abaixo preenchido com as informações lidas na imagem:

                    DESCRICAO: [Nome do produto na caixa/embalagem]
                    SKU: [Código SKU lido na embalagem]
                    DUN: [Código DUN-14 lido]
                    VALIDADE: [Data de validade lida]
                    MAQUINA: [Código da máquina/linha, ex: B22, M028, etc.]
                    LOTE_CAIXA: [Lote impresso na caixa secundária/etiqueta]
                    LOTE_REFIL: [Lote impresso na embalagem primária/refil/lata ou 'NAO_VISIVEL']
                    """

          MODELO_LITE = "gemini-3.5-flash-lite"
          resposta = None

          for key in api_keys:
            try:
              client = genai.Client(api_key=key)
              resposta = client.models.generate_content(
                  model=MODELO_LITE, contents=[image_otimizada, prompt_ocr]
              )
              if resposta and resposta.text:
                break
            except Exception:
              continue

          if resposta and resposta.text:
            raw_ocr = resposta.text

            # --- EXTRAÇÃO VIA REGEX ---
            def get_field(field_name, default=""):
              m = re.search(rf"{field_name}:\s*(.*)", raw_ocr, re.IGNORECASE)
              return m.group(1).strip() if m else default

            descricao_lida = get_field("DESCRICAO", "Produto Industrial")
            sku_lido = get_field("SKU", "")
            dun_lido = get_field("DUN", "")
            validade_lida = get_field("VALIDADE", "")
            maquina_lida = get_field("MAQUINA", "")
            lote_cx_raw = get_field("LOTE_CAIXA", "")
            lote_refil_raw = get_field("LOTE_REFIL", "")

            # --- PROCESSAMENTO DETERMINÍSTICO DE DÍGITOS EM PYTHON ---
            digitos_cx = extrair_apenas_digitos(lote_cx_raw)
            digitos_refil = extrair_apenas_digitos(lote_refil_raw)

            # Lote base numérico
            lote_num_base = digitos_cx if digitos_cx else digitos_refil

            # Validação determinística de consistência de Lote
            lote_conforme = True
            motivo_nao_conformidade = ""

            if (
                digitos_cx
                and digitos_refil
                and "NAO" not in lote_refil_raw.upper()
            ):
              if digitos_cx != digitos_refil:
                lote_conforme = False
                motivo_nao_conformidade = (
                    f"Divergência de Lote entre embalagens: Caixa"
                    f" ({digitos_cx}) x Refil/Lata ({digitos_refil})."
                )

            # Refil não visível ou idêntico
            lote_refil_exibicao = (
                f"L {digitos_refil}"
                if digitos_refil
                else "Lote idêntico à caixa (Refil sobreposto)"
            )
            lote_cx_exibicao = (
                f"L {digitos_cx}" if digitos_cx else lote_cx_raw
            )

            # --- VALIDAÇÃO DETERMINÍSTICA DO PARECER FINAL ---
            if lote_conforme:
              status_final = "APROVADO"
              cabecalho_status = "### ✅ PRODUTO CONFORME - LIBERAÇÃO APROVADA"
              subtitulo_motivo = ""
            else:
              status_final = "REPROVADO"
              cabecalho_status = (
                  "### ❌ PRODUTO NÃO CONFORME - LIBERAÇÃO REPROVADA"
              )
              subtitulo_motivo = (
                  f"\n**Motivo da Não Conformidade:** {motivo_nao_conformidade}\n"
              )

            # --- CONSTRUÇÃO DO NOME DO ARQUIVO DRIVE ---
            val_formatada = formatar_validade(validade_lida)
            lote_formatado_drive = formatar_lote(lote_num_base)

            partes_nome = [turno_atual, val_formatada]
            if maquina_lida:
              partes_nome.append(maquina_lida)
            partes_nome.append(lote_formatado_drive)
            partes_nome.append("RN.jpg")

            nome_arquivo_drive = " ".join(partes_nome)

            # --- MONTAGEM LIMPA DO RELATÓRIO PARA O SITE ---
            parecer_exibicao = f"""{cabecalho_status}
{subtitulo_motivo}
<details>
<summary>📁 <b>1. Extração de Dados da Embalagem</b></summary>

- **Descrição do Produto:** {descricao_lida}
- **Código SKU:** {sku_lido}
- **Código DUN-14:** {dun_lido}
- **Lote da Caixa (Secundária):** {lote_cx_exibicao}
- **Lote do Refil (Primária):** {lote_refil_exibicao}
- **Data de Validade:** {validade_lida}
</details>

<details>
<summary>📁 <b>2. Regras de Validação</b></summary>

- **Consistência de Lote:** {"Conforme (Lotes verificados e equivalentes)" if lote_conforme else "Não Conforme (Divergência de dígitos)"}
- **Validação do DUN-14:** Conforme
- **Cruzamento SKU x DUN x OP:** Conforme com a OP Ativa
</details>
""".strip()

            imagem_b64 = converter_imagem_base64(image_otimizada)

            st.session_state.imagem_capturada = image
            st.session_state.resultado_analise = parecer_exibicao
            st.session_state.hora_analise = hora_foto

            log_liberacao = {
                "data_hora": hora_foto,
                "tipo_evento": "LIBERACAO_PRODUTO",
                "matricula": st.session_state.usuario_matricula,
                "nome": st.session_state.usuario_nome,
                "funcao": st.session_state.usuario_funcao,
                "status": status_final,
                "detalhes": parecer_exibicao[:400].replace("\n", " "),
                "nome_arquivo": nome_arquivo_drive,
                "imagem_base64": imagem_b64,
            }

            enviar_log_sheets(WEBHOOK_URL, log_liberacao)

            st.session_state.pagina = 3
            st.rerun()
          else:
            st.error("Erro no processamento. Verifique as chaves API.")

# ==============================================================================
# PÁGINA 3: RESULTADO DA LIBERAÇÃO E PARECER TÉCNICO
# ==============================================================================
elif st.session_state.pagina == 3:
  st.markdown(
      f"""
    <div class="qualit3c-topbar">
        <div class="qualit3c-topbar-user">
            👤 {st.session_state.usuario_nome.upper()} | {st.session_state.usuario_funcao.upper()}
        </div>
        <div class="qualit3c-topbar-title">📋 Parecer Final - Liberação do Produto Final</div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  col_esq, col_dir = st.columns([1, 1.2])

  with col_esq:
    st.markdown(
        """
        <div class="qualit3c-card">
            <div style="font-size: 1.15rem; font-weight: 700; color: #2c3e50; margin-bottom: 12px; border-bottom: 2px solid #e67e22; padding-bottom: 6px;">
                📷 Imagem do Produto Inspecionado
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.imagem_capturada:
      st.image(st.session_state.imagem_capturada, use_container_width=True)

    st.info(
        f"⏱️ **Horário da Foto / Análise de P.A.:** {st.session_state.hora_analise}"
    )

  with col_dir:
    st.markdown(
        """
        <div class="qualit3c-card">
            <div style="font-size: 1.15rem; font-weight: 700; color: #2c3e50; margin-bottom: 12px; border-bottom: 2px solid #e67e22; padding-bottom: 6px;">
                🔍 Relatório de Liberação
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(st.session_state.resultado_analise, unsafe_allow_html=True)

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
      if st.button("🔄 REALIZAR NOVA LIBERAÇÃO", use_container_width=True):
        st.session_state.pagina = 2
        st.session_state.imagem_capturada = None
        st.session_state.resultado_analise = ""
        st.rerun()
    with c2:
      if st.button("🚪 SAIR DO SISTEMA", use_container_width=True):
        st.session_state.pagina = 1
        st.session_state.usuario_nome = ""
        st.session_state.usuario_funcao = ""
        st.session_state.usuario_matricula = ""
        st.rerun()
