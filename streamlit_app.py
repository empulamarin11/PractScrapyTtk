#importar librerías
import streamlit as st
import streamlit.components.v1 as components
import os
import pandas as pd
import plotly.express as px
from playwright.sync_api import sync_playwright
from utils import configurar_contexto, extraer_perfil_y_videos, guardar_json, clasificar_perfil
from grok_client import analizar_bigfive

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
                datos["clasificacion"] = clasificar_perfil(datos)   # ← LÍNEA NUEVa
                datos["bigfive"] = analizar_bigfive(datos, datos["clasificacion"])   # ← NUEVA
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
# 4. MOSTRAR RESULTADOS (con gráficas)
# ==========================================
if 'datos' in st.session_state:
    datos = st.session_state['datos']
    st.divider()

    # ---------- Encabezado del perfil ----------
    cl = datos.get("clasificacion", {})
    tamaño = cl.get("clasificacion_tamano", "—")

    st.subheader(f"✨ @{datos.get('username')}")
    st.markdown(
        f"**{datos.get('name','—')}** · "
        f"<span style='color:#FE2C55; font-weight:700;'>{tamaño.upper()}</span>",
        unsafe_allow_html=True,
    )
    st.info(f"📝 {datos.get('bio') or 'Sin biografía'}")

    # ---------- Métricas base ----------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Seguidores", f"{datos.get('seguidores', 0):,}")
    c2.metric("➕ Seguidos", f"{datos.get('seguidos', 0):,}")
    c3.metric("❤️ Likes totales", f"{datos.get('likes_totales', 0):,}")
    c4.metric("🎬 Videos", f"{datos.get('videos_totales', 0):,}")

    # ---------- Pestañas ----------
    tab_metricas, tab_videos, tab_comunidad, tab_bigfive, tab_emojis = st.tabs(
        ["📊 Métricas", "🎬 Videos", "👥 Comunidad", "🧠 Big Five (IA)", "😊 Emojis"]
    )

    # ============ TAB 1: MÉTRICAS ============
    with tab_metricas:
        eng = cl.get("engagement_promedio_pct", 0)
        col_a, col_b = st.columns(2)
        col_a.metric("🎯 Engagement promedio", f"{eng}%")
        col_b.metric("🏷️ Clasificación", tamaño.upper())

        st.divider()

        # --- Hashtags ---
        st.markdown("### 🔥 Top hashtags")
        top_h = cl.get("top_hashtags", [])
        if top_h:
            df_h = pd.DataFrame(top_h, columns=["Hashtag", "Apariciones"])
            df_h["Hashtag"] = "#" + df_h["Hashtag"]
            fig_h = px.bar(
                df_h,
                x="Hashtag",
                y="Apariciones",
                color="Apariciones",
                color_continuous_scale=["#25F4EE", "#FE2C55"],
                title="Hashtags más usados",
            )
            fig_h.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E2E8F0",
                showlegend=False,
            )
            st.plotly_chart(fig_h, use_container_width=True)
        else:
            st.info("Sin hashtags detectados en las descripciones.")

        # --- Palabras de bio ---
        st.markdown("### 📝 Top palabras en bio")
        top_p = cl.get("top_palabras_bio", [])
        if top_p:
            df_p = pd.DataFrame(top_p, columns=["Palabra", "Apariciones"])
            fig_p = px.bar(
                df_p,
                x="Palabra",
                y="Apariciones",
                color="Apariciones",
                color_continuous_scale=["#25F4EE", "#FE2C55"],
                title="Palabras más frecuentes en la biografía",
            )
            fig_p.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E2E8F0",
                showlegend=False,
            )
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("Sin palabras relevantes en la bio.")

    # ============ TAB 2: VIDEOS ============
    with tab_videos:
        videos = datos.get("ultimos_10_videos", []) or []
        if not videos:
            st.info("No se pudieron extraer videos.")
        else:
            # --- Gráfico de dispersión: vistas vs likes ---
            st.markdown("### 📈 Vistas vs Likes por video")
            df_v = pd.DataFrame(videos)
            fig_scatter = px.scatter(
                df_v,
                x="vistas",
                y="likes",
                size="comentarios",
                hover_data=["descripcion"],
                color="likes",
                color_continuous_scale=["#25F4EE", "#FE2C55"],
                title="Cada punto es un video (tamaño = comentarios)",
            )
            fig_scatter.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E2E8F0",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            # --- Gráfico de barras: vistas por video ---
            st.markdown("### 📊 Vistas por video")
            chart_df = pd.DataFrame({
                "Video": [f"#{i+1}" for i in range(len(videos))],
                "Vistas": [v.get("vistas", 0) or 0 for v in videos],
            }).set_index("Video")
            st.bar_chart(chart_df, height=300)

            # --- Tabla detallada con iframe por video ---
            st.markdown("### 🎬 Detalle de videos")
            for i, v in enumerate(videos):
                with st.expander(
                    f"▶️ Video {i+1} • {v.get('vistas', 0):,} vistas"
                ):
                    col_info, col_video = st.columns([1, 1.2])
                    with col_info:
                        st.markdown(f"""
                        <div style="background: #0F172A; padding: 15px;
                                    border-radius: 12px; border: 1px solid #334155;">
                            <p>👁️ <b>Vistas:</b> {v.get('vistas', 0):,}</p>
                            <p>❤️ <b>Likes:</b> {v.get('likes', 0):,}</p>
                            <p>💬 <b>Comentarios:</b> {v.get('comentarios', 0):,}</p>
                            <p>🔁 <b>Compartidos:</b> {v.get('compartidos', 0):,}</p>
                            <hr style="margin: 10px 0; border: none;
                                       border-top: 1px solid #334155;">
                            <p style="font-size: 13px; color: #94A3B8;">
                                <i>{v.get('descripcion', 'Sin descripción')}</i>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_video:
                        video_id = v.get('url', '').split("/")[-1]
                        iframe_html = f"""
                        <iframe src="https://www.tiktok.com/embed/v2/{video_id}"
                                style="width: 100%; height: 450px;
                                       border: none; border-radius: 12px;"
                                allow="fullscreen">
                        </iframe>
                        """
                        components.html(iframe_html, height=470)

    # ============ TAB 3: COMUNIDAD ============
    with tab_comunidad:
        col_followers, col_following = st.columns(2)

        with col_followers:
            with st.expander("👥 Ver Seguidores extraídos", expanded=True):
                seguidores = datos.get("lista_seguidores_real", "No cargado")
                if isinstance(seguidores, list):
                    st.write(", ".join(seguidores))
                    st.caption(f"Total: {len(seguidores)}")
                else:
                    st.info(seguidores)

        with col_following:
            with st.expander("➕ Ver Seguidos extraídos", expanded=True):
                seguidos = datos.get("lista_seguidos_real", "No cargado")
                if isinstance(seguidos, list):
                    st.write(", ".join(seguidos))
                    st.caption(f"Total: {len(seguidos)}")
                else:
                    st.info(seguidos)

    # ============ TAB 4: BIG FIVE ============
    with tab_bigfive:
        bf = datos.get("bigfive")
        if bf and isinstance(bf, dict):
            st.markdown("### 🧠 Estimación Big Five (Groq API)")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Apertura", bf.get("apertura", "—"))
            c2.metric("Responsabilidad", bf.get("responsabilidad", "—"))
            c3.metric("Extraversión", bf.get("extraversion", "—"))
            c4.metric("Amabilidad", bf.get("amabilidad", "—"))
            c5.metric("Neuroticismo", bf.get("neuroticismo", "—"))

             # -------- Evidencia de emojis (NUEVO) --------
            evidencia = bf.get("evidencia_emojis", "")
            if evidencia:
                st.markdown("#### 🔍 Evidencia emocional (emojis)")
                st.markdown(
                    f"""
                    <div style="
                        background: #1c2230;
                        border-left: 4px solid #25F4EE;
                        border-radius: 12px;
                        padding: 16px;
                        margin: 8px 0;
                        color: #E2E8F0;
                    ">
                        {evidencia}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Mostrar visualmente los emojis detectados
            emojis_info = datos.get("clasificacion", {}).get("emojis", {})
            top_emojis = emojis_info.get("top_emojis", [])
            if top_emojis:
                st.markdown("**Emojis más frecuentes en el perfil:**")
                emojis_html = " ".join(
                    f"<span style='font-size:1.8rem; margin:0 4px;' title='{count} apariciones'>{emoji}</span>"
                    for emoji, count in top_emojis
                )
                st.markdown(
                    f"<div style='background:#0F172A; padding:14px; border-radius:12px; "
                    f"text-align:center; border:1px solid #334155;'>{emojis_html}</div>",
                    unsafe_allow_html=True,
                )

            st.divider()

            # Gráfico de radar
            import plotly.graph_objects as go
            categorias = ["Apertura", "Responsabilidad", "Extraversión", "Amabilidad", "Neuroticismo"]
            valores = [
                bf.get("apertura", 0),
                bf.get("responsabilidad", 0),
                bf.get("extraversion", 0),
                bf.get("amabilidad", 0),
                bf.get("neuroticismo", 0),
            ]
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=valores,
                theta=categorias,
                fill='toself',
                line_color='#FE2C55',
                fillcolor='rgba(254, 44, 85, 0.3)',
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100]),
                    bgcolor="rgba(0,0,0,0)",
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E2E8F0",
                showlegend=False,
                height=400,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            st.markdown("**Justificación generada por la IA:**")
            st.info(bf.get("justificacion", "Sin justificación disponible."))

            st.warning(
                "⚠️ **Aviso:** Esta es una estimación exploratoria generada por IA "
                "a partir de textos públicos. No constituye una evaluación psicológica "
                "profesional ni un diagnóstico clínico."
            )
        else:
            st.info(
                "Big Five no disponible. Verifica que `GROQ_API_KEY` esté configurada "
                "en el archivo `.env` y que el perfil tenga suficiente texto."
            )
     # ============ TAB 5: EMOJIS ============
    with tab_emojis:
        # Buscamos los emojis en clasificacion, y si no, los calculamos al vuelo
        emojis_info = datos.get("clasificacion", {}).get("emojis")
        
        if not emojis_info:
            # Si el JSON viejo no los tenía, los calculamos ahora mismo
            from utils import analizar_emojis
            emojis_info = analizar_emojis(datos)
            datos["clasificacion"]["emojis"] = emojis_info  # Lo guardamos en memoria

        top_emojis = emojis_info.get("top_emojis", [])
        emojis_bio = emojis_info.get("emojis_bio", [])
        total = emojis_info.get("total_emojis", 0)

        if top_emojis:
            st.markdown(f"### 😊 Análisis de emojis ({total} detectados)")

            # Emojis de la bio
            if emojis_bio:
                st.markdown("**Emojis en la biografía:**")
                st.markdown(
                    f"<div style='font-size:2rem; text-align:center; "
                    f"background:#1c2230; padding:16px; border-radius:12px; "
                    f"border:1px solid #334155;'>{' '.join(emojis_bio)}</div>",
                    unsafe_allow_html=True,
                )

            st.divider()

            # Top emojis con gráfico
            st.markdown("**Top 10 emojis más frecuentes:**")
            df_em = pd.DataFrame(top_emojis, columns=["Emoji", "Apariciones"])
            st.dataframe(df_em, use_container_width=True, hide_index=True)

            # Gráfico de barras
            fig_em = px.bar(
                df_em,
                x="Emoji",
                y="Apariciones",
                color="Apariciones",
                color_continuous_scale=["#25F4EE", "#FE2C55"],
                title="Frecuencia de emojis en el perfil",
            )
            fig_em.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E2E8F0",
                showlegend=False,
            )
            st.plotly_chart(fig_em, use_container_width=True)
        else:
            st.info("No se detectaron emojis en este perfil. (Asegúrate de haber instalado 'pip install emoji')")

    # ---------- Descarga JSON ----------
    st.divider()
    st.download_button(
        "⬇️ Descargar JSON del perfil",
        data=__import__("json").dumps(datos, ensure_ascii=False, indent=2),
        file_name=f"resultado_{datos.get('username','perfil')}.json",
        mime="application/json",
    )