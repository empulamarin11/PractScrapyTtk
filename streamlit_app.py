#importar librerías
import streamlit as st
import streamlit.components.v1 as components
import os
from playwright.sync_api import sync_playwright
from utils import configurar_contexto, extraer_perfil_y_videos, guardar_json

STATE_FILE = "tiktok_state.json"

# CONFIGURACIÓN Y ESTILOS

st.set_page_config(page_title="TikTok", page_icon="🎵", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #E2E8F0; }
    .block-container {
        background-color: #1E293B; border-radius: 20px; padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-top: 2rem;
        max-width: 750px; border: 1px solid #334155;
    }
    h1, h2, h3 { color: #F8FAFC !important; }
    p, span, label { color: #CBD5E1 !important; }
    .stButton>button {
        background: linear-gradient(90deg, #FE2C55, #FF6B9D);
        color: white !important; border-radius: 12px; border: none; 
        font-weight: bold; padding: 10px 20px; transition: all 0.3s ease;
    }
    div[data-testid="stMetric"] {
        background-color: #0F172A; padding: 15px; border-radius: 12px; border: 1px solid #334155;
    }
    div[data-testid="stMetric"] label { color: #94A3B8 !important; }
    div[data-testid="stMetric"] div { color: #F8FAFC !important; }
    div[data-testid="stExpander"] {
        background-color: #0F172A; border-radius: 12px; border: 1px solid #334155; margin-bottom: 12px;
    }
    div[data-testid="stExpander"] summary { color: #F8FAFC !important; font-weight: 600; }
    [data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True) #poner css personaliado

# FUNCIONES (Login, Comentarios, Seguidores)

def hacer_login_manual():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = configurar_contexto(browser)
        page = context.new_page()
        page.goto("https://www.tiktok.com", timeout=60000)
        page.wait_for_timeout(3000)
        page.goto("https://www.tiktok.com/login", timeout=60000)
        
        try:
            page.wait_for_url(lambda url: "login" not in url, timeout=180000)
            page.wait_for_timeout(2000)
            context.storage_state(path=STATE_FILE)
        except Exception:
            browser.close()
            return False
        browser.close()
    return True

def extraer_comentarios(video_url):
    if not os.path.exists(STATE_FILE):
        return "Inicia sesión para ver comentarios."
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = configurar_contexto(browser, storage_state=STATE_FILE)
            page = context.new_page()
            
            comentarios_capturados = []
            def capturar(response):
                if "/api/comment/list/" in response.url:
                    try:
                        data = response.json()
                        if "comments" in data:
                            comentarios_capturados.extend(data["comments"])
                    except: pass
            
            page.on("response", capturar)
            page.goto(video_url, timeout=60000)
            page.wait_for_timeout(4000)
            
            try:
                page.locator('[data-e2e="comment-icon"]').first.click(timeout=5000)
                page.wait_for_timeout(3000)
            except: return "No se pudo abrir el panel de comentarios."
            
            intentos = 0
            while len(comentarios_capturados) < 20 and intentos < 5:
                try:
                    page.locator('[data-e2e="comment-list"]').evaluate("el => el.scrollTop = el.scrollHeight")
                    page.wait_for_timeout(2500)
                except: break
                intentos += 1
            
            browser.close()
            
            if comentarios_capturados:
                res = []
                for c in comentarios_capturados[:20]:
                    texto = c.get("text", "").replace("\n", " ")
                    usuario = c.get("user", {}).get("unique_id", "?")
                    likes = c.get("digg_count", 0)
                    res.append(f"**@{usuario}** ({likes} ❤️): {texto}")
                return "\n".join(res)
            return "No se encontraron comentarios en este video."
    except Exception as e:
        return f"Error al extraer: {str(e)[:80]}"

def extraer_seguidores_seguidos(username):
    """Extrae las listas de seguidores y seguidos usando la sesión."""
    if not os.path.exists(STATE_FILE):
        return "Requiere login", "Requiere login"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            context = configurar_contexto(browser, storage_state=STATE_FILE)
            page = context.new_page()
            page.goto(f"https://www.tiktok.com/@{username}", timeout=60000)
            page.wait_for_timeout(4000)
            
            def obtener_lista(tipo):
                boton = f'[data-e2e="{tipo}-count"]'
                modal = f'[data-e2e="{tipo}-list"]'
                try:
                    page.locator(boton).click(timeout=5000)
                    page.wait_for_selector(modal, timeout=10000)
                    page.wait_for_selector(f'{modal} [data-e2e="user-title"]', timeout=10000)
                    
                    usuarios = set()
                    for _ in range(3): # Scroll para traer varios
                        visibles = page.locator(f'{modal} [data-e2e="user-title"]').all_inner_texts()
                        usuarios.update(visibles)
                        page.locator(modal).evaluate("el => el.scrollTop = el.scrollHeight")
                        page.wait_for_timeout(2000)
                    
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                    return list(usuarios) if usuarios else "Lista vacía"
                except Exception:
                    return "No accesible / Bloqueado"
            
            seguidores = obtener_lista("followers")
            page.wait_for_timeout(2000)
            seguidos = obtener_lista("following")
            
            browser.close()
            return seguidores, seguidos
    except Exception as e:
        return f"Error: {str(e)[:30]}", f"Error: {str(e)[:30]}"

# ==========================================
# 3. INTERFAZ PRINCIPAL
# ==========================================
st.title("🎵 TikTok ")

# Control de Sesión
if os.path.exists(STATE_FILE):
    st.success(" Sesión activa. Comentarios y listas habilitados.")
    if st.button("Cerrar Sesión"):
        os.remove(STATE_FILE)
        st.rerun()
else:
    st.warning(" Inicia sesión para habilitar comentarios y listas.")
    if st.button(" Iniciar Sesión ahora"):
        with st.spinner("Se abrirá una ventana de TikTok. Inicia sesión y espera..."):
            if hacer_login_manual():
                st.rerun()

st.divider()

# Buscador
col_input, col_btn = st.columns([3, 1])
with col_input:
    username = st.text_input("Usuario de TikTok:", placeholder="Ej: valjimenezsuarez_", label_visibility="collapsed")
with col_btn:
    buscar = st.button("Buscar ✨", use_container_width=True)

if buscar and username:
    username = username.strip().lstrip("@")
    with st.spinner(f"Buscando a @{username}..."):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
                storage = STATE_FILE if os.path.exists(STATE_FILE) else None
                context = configurar_contexto(browser, storage_state=storage)
                page = context.new_page()
                page.goto("https://www.tiktok.com", timeout=60000)
                page.wait_for_timeout(4000)
                
                datos = extraer_perfil_y_videos(page, username)
                guardar_json([datos], f"resultado_{username}.json")
                browser.close()
            
            # --- EXTRACCIÓN DE SEGUIDORES Y SEGUIDOS ---
            if os.path.exists(STATE_FILE):
                with st.spinner("Extrayendo listas de seguidores/seguidos..."):
                    lista_seg, lista_sig = extraer_seguidores_seguidos(username)
                    datos["lista_seguidores_real"] = lista_seg
                    datos["lista_seguidos_real"] = lista_sig
            else:
                datos["lista_seguidores_real"] = " Inicia sesión para ver"
                datos["lista_seguidos_real"] = " Inicia sesión para ver"
            # -------------------------------------------
            
            st.session_state['datos'] = datos
        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# 4. MOSTRAR RESULTADOS
# ==========================================
if 'datos' in st.session_state:
    datos = st.session_state['datos']
    st.divider()
    
    st.subheader(f"✨ @{datos.get('username')}")
    st.markdown(f"**Nombre:** {datos.get('name', 'N/A')}")
    st.info(f"📝 **Biografía:** {datos.get('bio', 'Sin biografía')}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Seguidores", f"{datos.get('seguidores', 0):,}")
    col2.metric("➕ Seguidos", f"{datos.get('seguidos', 0):,}")
    col3.metric("❤️ Likes", f"{datos.get('likes_totales', 0):,}")
    
    # --- NUEVO: MOSTRAR LISTAS DE SEGUIDORES Y SEGUIDOS ---
    st.write("### 👥 Comunidad del perfil")
    col_followers, col_following = st.columns(2)
    
    with col_followers:
        with st.expander("👥 Ver Seguidores extraídos"):
            seguidores = datos.get("lista_seguidores_real", "No cargado")
            if isinstance(seguidores, list):
                st.write(", ".join(seguidores))
            else:
                st.info(seguidores)

    with col_following:
        with st.expander("➕ Ver Seguidos extraídos"):
            seguidos = datos.get("lista_seguidos_real", "No cargado")
            if isinstance(seguidos, list):
                st.write(", ".join(seguidos))
            else:
                st.info(seguidos)
    # ------------------------------------------------------
    
    st.write("### 🎬 Últimos Videos")
    videos = datos.get('ultimos_10_videos', [])
    
    if videos:
        for i, v in enumerate(videos):
            with st.expander(f"▶️ Video {i+1} • {v.get('vistas', 0):,} vistas"):
                col_info, col_video = st.columns([1, 1.2])
                
                with col_info:
                    st.markdown(f"""
                    <div style="background: #0F172A; padding: 15px; border-radius: 12px; border: 1px solid #334155;">
                        <p>👁️ <b>Vistas:</b> {v.get('vistas', 0):,}</p>
                        <p>❤️ <b>Likes:</b> {v.get('likes', 0):,}</p>
                        <p>💬 <b>Comentarios:</b> {v.get('comentarios', 0):,}</p>
                        <p>🔁 <b>Compartidos:</b> {v.get('compartidos', 0):,}</p>
                        <hr style="margin: 10px 0; border: none; border-top: 1px solid #334155;">
                        <p style="font-size: 13px; color: #94A3B8;"><i>{v.get('descripcion', 'Sin descripción')}</i></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if os.path.exists(STATE_FILE):
                        if st.button(f"💬 Ver hasta 20 comentarios", key=f"com_{i}"):
                            with st.spinner("Cargando comentarios..."):
                                texto_comentarios = extraer_comentarios(v.get('url', ''))
                                st.markdown(f"""
                                <div style="background: #0F172A; padding: 15px; border-radius: 12px; border: 1px solid #334155; margin-top: 10px;">
                                    {texto_comentarios.replace(chr(10), '<br><br>')}
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.caption("🔒 Inicia sesión para ver comentarios.")
                    
                with col_video:
                    video_id = v.get('url', '').split("/")[-1]
                    iframe_html = f"""
                    <iframe src="https://www.tiktok.com/embed/v2/{video_id}" 
                            style="width: 100%; height: 450px; border: none; border-radius: 12px;" 
                            allow="fullscreen">
                    </iframe>
                    """
                    components.html(iframe_html, height=470)