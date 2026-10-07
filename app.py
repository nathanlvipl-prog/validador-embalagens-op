import streamlit as st
import pandas as pd
from PIL import Image
from google import genai
from datetime import datetime
import requests

# ==============================================================================
# CONFIGURAÇÃO GERAL E LINK DO WEBHOOK GOOGLE SHEETS
# ==============================================================================
WEBHOOK_URL = "SUA_URL_DO_WEBHOOK_AQUI"

st.set_page_config(
    page_title="Qualit3c - Liberação do Produto Final", 
    page_icon="📦", 
    layout="wide"
)

# 2. DICIONÁRIO DE MATRÍCULAS E COLABORADORES
CADASTRO_COLABORADORES = {
    "32164": "SILVIO NATHANAEL MEDEIROS DA SILVA",
    "32177": "EMANUEL LUCAS SEVERIANO DE SOUSA"
}

# 3. GERENCIAMENTO DE SESSÃO / NAVEGAÇÃO
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

# Dados do resultado da imagem (Página 3)
if "imagem_capturada" not in st.session_state:
    st.session_state.imagem_capturada = None
if "resultado_analise" not in st.session_state:
    st.session_state.resultado_analise = ""
if "hora_analise" not in st.session_state:
    st.session_state.hora_analise = ""

# 4. FUNÇÃO PARA ENVIAR LOGS PARA O GOOGLE SHEETS
def enviar_log_sheets(webhook_url, dados):
    """Envia os dados de registro via HTTP POST para o Google Apps Script"""
    if not webhook_url or webhook_url == "SUA_URL_DO_WEBHOOK_AQUI":
        return
    try:
        requests.post(webhook_url, json=dados, timeout=5)
    except Exception as e:
        print(f"Erro ao salvar registro no Google Sheets: {e}")

# 5. ESTILIZAÇÃO CSS
st.markdown("""
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

    /* Estilo para as caixas retráteis (<details>) */
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
""", unsafe_allow_html=True)


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
        raw_api_keys = st.sidebar.text_input("Chave(s) API do Gemini (separadas por vírgula):", type="password")

    api_keys = [k.strip() for k in raw_api_keys.split(",") if k.strip()] if raw_api_keys else []


# ==============================================================================
# PÁGINA 1: IDENTIFICAÇÃO DO VALIDADOR
# ==============================================================================
if st.session_state.pagina == 1:
    col_left, col_center, col_right = st.columns([1, 1.8, 1])
    
    with col_center:
        st.markdown("""
        <div class="login-container">
            <div class="qualit3c-logo">Qualit<span>3c</span></div>
            <div class="qualit3c-subtitle">SISTEMA DE CONTROLE DE QUALIDADE</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_login"):
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
                    nome_colaborador = CADASTRO_COLABORADORES.get(
                        mat_clean, 
                        f"COLABORADOR {mat_clean}"
                    )
                    
                    hora_agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
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
                        "detalhes": f"Acesso ao sistema às {hora_agora}"
                    }
                    enviar_log_sheets(WEBHOOK_URL, log_login)
                    st.rerun()


# ==============================================================================
# PÁGINA 2: LIBERAÇÃO DO PRODUTO FINAL
# ==============================================================================
elif st.session_state.pagina == 2:
    st.markdown(f"""
    <div class="qualit3c-topbar">
        <div class="qualit3c-topbar-user">
            👤 {st.session_state.usuario_nome.upper()} | {st.session_state.usuario_funcao.upper()}
        </div>
        <div class="qualit3c-topbar-title">📦 Liberação do Produto Final</div>
    </div>
    """, unsafe_allow_html=True)

    SHEET_OP_ID = "1YScgtOowZjmTWMKnlcwya1nPQKt0u34luPSb4U82_-E"
    SHEET_DUN_ID = "1TDROYy4E6u41k6n05lWyGfh3o7SjYz4JoofK1saNC-M"
    GSHEET_OP_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_OP_ID}/export?format=csv"
    GSHEET_DUN_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_DUN_ID}/export?format=csv"

    @st.cache_data(ttl=60)
    def carregar_dados_gsheet(url):
        return pd.read_csv(url)

    dados_op = None
    dados_dun = None
    try:
        dados_op = carregar_dados_gsheet(GSHEET_OP_URL)
        dados_dun = carregar_dados_gsheet(GSHEET_DUN_URL)
    except Exception:
        pass

    with st.expander("📋 Tabela de Referência para Liberação (OPs e SKUs)"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ordem de Produção (OP)")
            if dados_op is not None:
                st.dataframe(dados_op, use_container_width=True)
            else:
                st.info("Planilha de OPs em carregamento...")
        with col2:
            st.subheader("Cadastro SKU x DUN")
            if dados_dun is not None:
                st.dataframe(dados_dun, use_container_width=True)
            else:
                st.info("Planilha de DUNs em carregamento...")

    if not api_keys:
        st.warning("⚠️ Insira pelo menos uma Chave de API na barra lateral para prosseguir.")
        st.stop()

    img_file_buffer = st.file_uploader(
        "Upload da foto do produto / embalagem", 
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )

    if img_file_buffer is not None:
        image = Image.open(img_file_buffer)
        
        col_img, col_btn = st.columns([1.2, 1])
        with col_img:
            st.image(image, caption="Imagem Capturada", use_container_width=True)
        
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("🔬 PROCESSAR E GERAR LIBERAÇÃO", use_container_width=True):
                with st.spinner("⚡ Executando análise de P.A...."):
                    hora_foto = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    image_otimizada = image.copy()
                    image_otimizada.thumbnail((1024, 1024))
                    
                    contexto_op = ""
                    if dados_op is not None:
                        contexto_op += f"\n\n--- TABELA DE ORDEM DE PRODUÇÃO (OP) ATIVA ---\n{dados_op.to_string(index=False)}"
                    if dados_dun is not None:
                        contexto_op += f"\n\n--- TABELA DE REFERÊNCIA CADASTRO SKU x DUN-14 ---\n{dados_dun.to_string(index=False)}"
                    
                    prompt = f"""
                    Você é um validador de qualidade responsável pela LIBERAÇÃO DO PRODUTO FINAL na linha de produção.
                    Validador: {st.session_state.usuario_nome} | {st.session_state.usuario_funcao} (Matrícula: {st.session_state.usuario_matricula}).

                    Analise a imagem capturada e gere a resposta rigorosamente no seguinte formato:

                    1. RESULTADO DE CONFORMIDADE (DEVE FICAR NO TOPO, DIRETO E RESUMIDO):
                       - Se aprovado:
                         ### ✅ PRODUTO CONFORME - LIBERAÇÃO APROVADA
                       - Se reprovado:
                         ### ❌ PRODUTO NÃO CONFORME - LIBERAÇÃO REPROVADA
                         **Motivo da Não Conformidade:** [Descreva em uma frase bem objetiva onde está o erro, ex: "Divergência de lote entre Caixa (L1097543) e Refil (L1098543)" ou "DUN-14 com quantidade incorreta de dígitos"].

                    2. TÓPICOS 1 E 2 (DEVEM FICAR DENTRO DE BLOCOS RETRÁTEIS <details>):

                    <details>
                    <summary>📁 <b>1. Extração de Dados da Embalagem</b></summary>

                    - **Descrição do Produto:** [Descrição lida]
                    - **Código SKU:** [SKU lido]
                    - **Código DUN-14:** [DUN lido]
                    - **Lote da Caixa (Secundária):** [Lote lido na caixa]
                    - **Lote do Refil (Primária):** [Lote lido no refil]
                    - **Data de Validade:** [Validade lida]
                    </details>

                    <details>
                    <summary>📁 <b>2. Regras de Validação</b></summary>

                    - **Consistência de Lote:** [Status do lote]
                    - **Validação do DUN-14:** [Status do DUN]
                    - **Cruzamento SKU x DUN x OP:** [Status do cruzamento com a tabela]
                    </details>

                    REGRAS CRÍTICAS DE VALIDAÇÃO:
                    - Se o Lote da Caixa for diferente do Lote do Refil -> REPROVAR IMEDIATAMENTE e detalhar no Motivo da Não Conformidade.
                    - Se o DUN não possuir exatamente 14 dígitos numéricos -> REPROVAR IMEDIATAMENTE.
                    - Se o SKU ou DUN não corresponderem às tabelas ativas -> REPROVAR IMEDIATAMENTE.
                    {contexto_op}
                    """
                    
                    MODELO_LITE = "gemini-3.5-flash-lite"
                    resposta = None
                    
                    for key in api_keys:
                        try:
                            client = genai.Client(api_key=key)
                            resposta = client.models.generate_content(
                                model=MODELO_LITE,
                                contents=[image_otimizada, prompt]
                            )
                            if resposta and resposta.text:
                                break
                        except Exception:
                            continue
                    
                    if resposta and resposta.text:
                        parecer_texto = resposta.text
                        status_final = "APROVADO" if "PRODUTO CONFORME" in parecer_texto else "REPROVADO"
                        
                        st.session_state.imagem_capturada = image
                        st.session_state.resultado_analise = parecer_texto
                        st.session_state.hora_analise = hora_foto
                        st.session_state.pagina = 3
                        
                        log_liberacao = {
                            "data_hora": hora_foto,
                            "tipo_evento": "LIBERACAO_PRODUTO",
                            "matricula": st.session_state.usuario_matricula,
                            "nome": st.session_state.usuario_nome,
                            "funcao": st.session_state.usuario_funcao,
                            "status": status_final,
                            "detalhes": parecer_texto[:400].replace("\n", " ")
                        }
                        enviar_log_sheets(WEBHOOK_URL, log_liberacao)
                        st.rerun()
                    else:
                        st.error("Erro no processamento. Verifique as chaves API.")


# ==============================================================================
# PÁGINA 3: RESULTADO DA LIBERAÇÃO E PARECER TÉCNICO
# ==============================================================================
elif st.session_state.pagina == 3:
    st.markdown(f"""
    <div class="qualit3c-topbar">
        <div class="qualit3c-topbar-user">
            👤 {st.session_state.usuario_nome.upper()} | {st.session_state.usuario_funcao.upper()}
        </div>
        <div class="qualit3c-topbar-title">📋 Parecer Final - Liberação do Produto Final</div>
    </div>
    """, unsafe_allow_html=True)

    col_esq, col_dir = st.columns([1, 1.2])

    with col_esq:
        st.markdown("""
        <div class="qualit3c-card">
            <div style="font-size: 1.15rem; font-weight: 700; color: #2c3e50; margin-bottom: 12px; border-bottom: 2px solid #e67e22; padding-bottom: 6px;">
                📷 Imagem do Produto Inspecionado
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.imagem_capturada:
            st.image(st.session_state.imagem_capturada, use_container_width=True)
        
        st.info(f"⏱️ **Horário da Foto / Análise de P.A.:** {st.session_state.hora_analise}")

    with col_dir:
        st.markdown("""
        <div class="qualit3c-card">
            <div style="font-size: 1.15rem; font-weight: 700; color: #2c3e50; margin-bottom: 12px; border-bottom: 2px solid #e67e22; padding-bottom: 6px;">
                🔍 Relatório de Liberação
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Exibe o resultado com HTML permitido para que as caixas retráteis funcionem
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
