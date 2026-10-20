import streamlit as st
from playwright.sync_api import sync_playwright
from utils import configurar_contexto, extraer_perfil_y_videos, guardar_json

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="TikTok Analytics", page_icon="🎵", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161A25; border-right: 1px solid #2D3748; }
    
    /* Botones principales */
    .stButton>button {
        background-color: #FF2B5E; color: white; border-radius: 8px; border: none; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background-color: #E01F4E; color: white; }
    
    /* Tarjetas de métricas */
    div[data-testid="stMetric"] {
        background-color: #1A202C; padding: 15px; border-radius: 10px; border: 1px solid #2D3748;
    }
    
    /* Estilo para los Expanders (Tarjetas de videos) */
    div[data-testid="stExpander"] {
        background-color: #1A202C;
        border: 1px solid #2D3748;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    div[data-testid="stExpander"] summary {
        font-size: 16px;
        font-weight: bold;
        color: #FF2B5E; /* Color rosa para el título del video */
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 🎵 TikTok Analytics")
    st.caption("Panel de consulta de contenido público")
    st.divider()
    st.markdown("### Estado del navegador")
    st.success("Playwright (Chromium)\nconectado")
    st.divider()
    st.markdown("### Funciones disponibles")
    st.markdown("• Consultar perfil y estadísticas\n\n• Explorar hasta 10 publicaciones\n\n• Reproducir videos")

# --- ENCABEZADO PRINCIPAL ---
st.markdown("""
<div style="background: linear-gradient(90deg, #1A202C, #2D1B36); padding: 20px; border-radius: 15px; margin-bottom: 20px; border: 1px solid #4A235A;">
    <h1 style="margin:0; color: white;">TikTok Analytics 🔴</h1>
    <p style="margin:5px 0 0 0; color: #A0AEC0;">Dashboard de perfiles, publicaciones y comentarios públicos</p>
    <span style="background: #276749; color: #9AE6B4; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">Playwright + Streamlit</span>
</div>
""", unsafe_allow_html=True)

# --- FORMULARIO DE BÚSQUEDA ---
with st.container():
    st.markdown("### Buscar perfil de TikTok")
    username = st.text_input("Usuario o enlace del perfil", placeholder="ej: valjimenezsuarez_")
    buscar = st.button("🔍 Consultar perfil")

if buscar:
    username = username.strip().lstrip("@")
    if not username:
        st.warning("Ingresa un username válido.")
    else:
        with st.spinner(f"Extrayendo datos de @{username}..."):
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
                    context = configurar_contexto(browser)
                    page = context.new_page()
                    page.goto("https://www.tiktok.com", timeout=60000)
                    page.wait_for_timeout(6000)
                    
                    # Llamada a TU función original
                    datos = extraer_perfil_y_videos(page, username)
                    guardar_json([datos], f"resultado_{username}.json")
                    browser.close()
                
                st.session_state['datos'] = datos
                
            except Exception as e:
                st.error(f"Error con @{username}: {e}")

# --- MOSTRAR RESULTADOS SI EXISTEN ---
if 'datos' in st.session_state:
    datos = st.session_state['datos']
    
    st.markdown("### Resumen del perfil")
    st.caption(f"@{datos.get('username')}")
    
    # --- TARJETAS DE MÉTRICAS ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="👤 Nombre", value=datos.get('name', 'N/A')[:20])
    with col2:
        st.metric(label="👥 Seguidores", value=f"{datos.get('seguidores', 0):,}")
    with col3:
        st.metric(label="➕ Seguidos", value=f"{datos.get('seguidos', 0):,}")
    with col4:
        st.metric(label="📰 Publicaciones", value=len(datos.get('ultimos_10_videos', [])))

    st.divider()
    
    # --- SECCIÓN DE VIDEOS CON EXPANDERS ---
    st.markdown("### 📱 Publicaciones recientes")
    st.caption("Haz clic en la flecha de cada video para ver sus estadísticas y reproducirlo.")
    
    videos = datos.get('ultimos_10_videos', [])
    
    if videos:
        for i, v in enumerate(videos):
            vistas_str = f"{v.get('vistas', 0):,}"
            # El título de la tarjeta (siempre visible)
            titulo_tarjeta = f"🎬 Video {i+1} • {vistas_str} vistas • ❤️ {v.get('likes', 0)}"
            
            # Al abrir el expander, se muestran los detalles
            with st.expander(titulo_tarjeta):
                # Dividimos en 2 columnas: Izquierda datos, Derecha video
                col_info, col_video = st.columns([1, 1.5])
                
                with col_info:
                    st.markdown(f"""
                    <div style="background-color: #0E1117; padding: 15px; border-radius: 10px; border: 1px solid #2D3748;">
                        <h4 style="color: #FF2B5E; margin-top:0;">📊 Estadísticas</h4>
                        <p>👁️ <b>Vistas:</b> {vistas_str}</p>
                        <p>❤️ <b>Likes:</b> {v.get('likes', 0):,}</p>
                        <p>💬 <b>Comentarios:</b> {v.get('comentarios', 0):,}</p>
                        <p>🔁 <b>Compartidos:</b> {v.get('compartidos', 0):,}</p>
                        <hr style="border-color: #2D3748;">
                        <p style="font-size: 13px; color: #A0AEC0;"><b>Descripción:</b><br>{v.get('descripcion', '(Sin descripción)')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botón simulado para comentarios (opcional)
                    st.button(f"💬 Ver comentarios del Video {i+1}", key=f"btn_com_{i}")
                    
                with col_video:
                    url_video = v.get('url')
                    if url_video:
                        st.video(url_video)
                    else:
                        st.warning("No hay URL de video disponible.")
    else:
        st.info("No se encontraron videos en este perfil.")