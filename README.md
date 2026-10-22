# Practica Scrapy TikTok & Big Five
# 🕷️ Scraper de TikTok - Valor de en los Datos y Análisis Psicométrico

Scraper desarrollado **desde cero** con Python, Playwright y Streamlit para extraer datos públicos de perfiles de TikTok y presentarlos en un Dashboard web interactivo, sin usar APIs oficiales. Además, el proyecto implementa un módulo de **Inteligencia Artificial** para analizar el contenido y estimar la personalidad del creador usando el modelo psicológico **Big Five (OCEAN)**. Proyecto académico con fines educativos, ejecutado en entorno controlado.

---

## 📋 Tabla de contenido

- [Descripción](#-descripción)
- [Características](#-características)
- [Arquitectura del proyecto](#-arquitectura-del-proyecto)
- [🧠 Funcionamiento Interno y Decisiones Técnicas (Relevante)](#-funcionamiento-interno-y-decisiones-técnicas-relevante)
- [Requisitos previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Datos extraídos](#-datos-extraídos)
- [Consideraciones éticas y legales](#-consideraciones-éticas-y-legales)
- [Seguridad](#-seguridad)
- [Tecnologías utilizadas](#-tecnologías-utilizadas)
- [Autor](#-autor)
- [🎯 El Resultado Final](#-El Resultado Final)

---

## 📖 Descripción

Este proyecto implementa un **scraper modular** para TikTok usando **Playwright** como motor de automatización de navegador y **Streamlit** para la interfaz gráfica. El objetivo es demostrar el proceso completo de extracción de datos de una aplicación web moderna y darles valor:

1. Renderizado dinámico de JavaScript mediante un navegador real.
2. Manejo de **cookies anónimas** (`ttwid`, `msToken`, `_ttp`) que TikTok asigna a cualquier visitante.
3. Extracción de datos estructurados desde el JSON oculto `__UNIVERSAL_DATA_FOR_REHYDRATION__` que TikTok incrusta en el HTML.
4. Captura de respuestas XHR (llamadas internas a `/api/post/item_list` y `/api/comment/list/`) al hacer scroll.
5. Persistencia de sesión con `storage_state` para desbloquear datos que requieren autenticación (como las listas de seguidores).
6. **Análisis de Emojis:** Extracción de señales emocionales del texto usando la librería `emoji`.
7. **Estimación Big Five con IA:** Uso de la API de **Groq** (LLM) para procesar los textos y estimar rasgos de personalidad (Apertura, Responsabilidad, Extraversión, Amabilidad, Neuroticismo).
8. Presentación de resultados en un Dashboard web moderno con gráficos interactivos de `Plotly`.

El proyecto ofrece **dos modos de ejecución** y una interfaz web:

| Modo | Requiere login | Datos que obtiene |
|---|---|---|
| **Anónimo** | ❌ No | Perfil, bio, stats, últimos 10 videos (con vistas, likes, comentarios, compartidos), análisis de emojis y estimación Big Five. |
| **Autenticado** | ✅ Sí (una vez) | Todo lo anterior **+** reproducción de video **+** extracción de hasta 20 comentarios reales **+** listas parciales de seguidores y seguidos. |


---

## ✨ Características

- ✅ Extracción desde el **JSON oculto** de TikTok (más estable que los selectores CSS).
- ✅ Manejo automático de **cookies anónimas**.
- ✅ **Scroll dinámico** para cargar más videos y comentarios.
- ✅ **Captura de XHR** para no depender del DOM al extraer comentarios.
- ✅ **Persistencia de sesión** con `storage_state` (login solo la primera vez).
- ✅ **Medidas anti-detección**: ocultar `navigator.webdriver`, User-Agent realista, pausas prudenciales.
- ✅ **Interfaz web (Streamlit)**: Dashboard con modo oscuro, tarjetas expandibles y gráficos Plotly.
- ✅ **Reproductor integrado**: Reproduce videos de TikTok directamente en la interfaz sin salir de la app.
- ✅ **Extracción de listas**: Obtiene los nombres de los primeros seguidores y seguidos del perfil.
- ✅ **Análisis Psicométrico (Big Five)**: IA generativa que interpreta la biografía, descripciones y emojis para generar un arquetipo de personalidad y una conclusión analítica.
- ✅ Resultados exportados a **JSON estructurado**.
- ✅ Código **modular** (utils compartidas + scrapers independientes + interfaz web + módulo de IA).

---
## 🏗️ Arquitectura del proyecto

```
PractScrapyTtk/
├── main.py # Menú unificado (punto de entrada CLI)
├── utils.py # Funciones compartidas (contexto, scraping, clasificación, emojis)
├── grok_client.py # Conexión con la API de Groq y Prompt Big Five
├── scrapytiktokanonimo.py # Modo 1: sin login
├── scrapytiktoklogin.py # Modo 2: con login (seguidores/seguidos)
├── streamlit_app.py # Interfaz gráfica (Dashboard + gráficas Plotly)
├── requirements.txt # Dependencias del proyecto
├── .env # Archivo oculto con la API Key de Groq
├── .gitignore # Exclusiones de Git (protege .env y sesiones)
├── README.md # Este archivo
│
├── tiktok_state.json # (generado) Estado de sesión — NO se sube
├── resultado_*.json # (generado) Resultados del scraping — NO se sube
```

---

## 🧠 Funcionamiento Interno y Decisiones Técnicas (Relevante)

Esta sección explica el **por qué** detrás del código, demostrando el dominio técnico del proyecto.

### 1. Evasión Anti-Detección y Navegador Real
TikTok detecta bots fácilmente. Para evitarlo, inyectamos un script que oculta la propiedad `navigator.webdriver` antes de cargar la página.
```python
# utils.py
context.add_init_script(
    "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
)
```
---

### 2. Extracción mediante JSON Oculto (rehydration)
En lugar de raspar selectores CSS (que cambian constantemente), leemos el bloque JSON que TikTok usa para hidratar su propio React.

```python
# utils.py
raw_json = page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").inner_text()
data = json.loads(raw_json)
user_detail = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]
```
### 3. Intercepción de XHR (Lazy Loading)
Al hacer scroll, TikTok hace peticiones en segundo plano. Interceptamos las respuestas para no perder datos.

```python
# utils.py
def capturar(response):
    if "/api/post/item_list" in response.url:
        respuestas_api.append(response.json())
page.on("response", capturar)
```
### 4. Análisis de Emojis
Los emojis son señales paralingüísticas. Usamos la librería emoji para extraerlos de la bio y videos, y contarlos usando Counter.

```python
# utils.py
import emoji
def extraer_emojis(texto: str) -> list[str]:
    return [e['emoji'] for e in emoji.emoji_list(texto)]
```

### 5. Big Five e Inteligencia Artificial
El módulo grok_client.py construye un Prompt estricto y lo envía a la API de Groq (que usa el SDK de OpenAI). La IA devuelve un JSON con los 5 rasgos (0-100) y una conclusión interpretativa.

```python
# grok_client.py
client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3
)
```
### 6. Visualización con Plotly
El Dashboard renderiza los 5 rasgos de personalidad en un Gráfico de Radar (Telaraña) y las métricas de videos en gráficos de dispersión y barras.

```python
# streamlit_app.py
fig_radar = go.Figure(data=go.Scatterpolar(
    r=valores, theta=categorias, fill='toself', line_color='#FE2C55'
))
st.plotly_chart(fig_radar, use_container_width=True)
```

## 🔧 Requisitos previos

Antes de instalar el proyecto, asegúrate de tener:

- **Python 3.9 o superior** → [python.org](https://www.python.org/downloads/)
- **Git** → [git-scm.com](https://git-scm.com/)
- **Conexión a internet** (para descargar Playwright y acceder a TikTok)
- **API KEY** Una API Key gratuita de Groq Console para habilitar el análisis Big Five.

> ⚠️ En Windows, durante la instalación de Python, **marca la casilla "Add Python to PATH"**. Sin esto, los comandos `python` y `pip` no funcionarán.

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/<tu-usuario>/PractScrapyTtk.git
cd PractScrapyTtk
```

> Reemplaza `<tu-usuario>` por tu usuario real de GitHub.

### 2. Crear el entorno virtual

**En Windows (Git Bash / MINGW64):**

```bash
python -m venv venv
source venv/Scripts/activate
```

**En Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

Sabrás que el entorno está activo cuando veas `(venv)` al inicio de tu prompt.

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
pip install streamlit
```
### 4. Instalar el navegador de Playwright

Playwright necesita su propio navegador Chromium (no usa el de tu sistema):

```bash
playwright install chromium
```

Este paso descarga ~150 MB y **solo se hace la primera vez**.

### 5. Configurar la API Key (Big Five)

Crea un archivo llamado `.env` en la raíz del proyecto y agrega tu clave:
```env
GROQ_API_KEY=tu_api_key_de_groq_aqui
```
(Si no pones la clave, el programa funcionará igual, pero la pestaña de Big Five mostrará un mensaje de error)


## 🎮 Uso

### Iniciar el programa

Con el entorno virtual activado ejecuta:

```bash
streamlit run streamlit_app.py
```
Se abrirá una pestaña en tu navegador (usualmente en http://localhost:8501) con el Dashboard.

Modo Anónimo: Puedes buscar perfiles directamente.

Modo Autenticado: Haz clic en "Iniciar Sesión". Se abrirá una ventana de Chromium. Ingresa tus credenciales y espera a que TikTok te redirija a tu feed principal. La ventana se cerrará y tu sesión se guardará en tiktok_state.json.

Búsqueda: Ingresa el username y presiona "Buscar ".

Videos: Haz clic en cada tarjeta para ver los detalles y reproducir el video.

Comentarios: Si tienes sesión activa, presiona "leer comentarios" dentro de la tarjeta de un video.

Listas de Comunidad: Debajo de las métricas, encontrarás las flechitas desplegables para ver los seguidores y seguidos extraídos.

### Opción B: Consola

```bash
python main.py
```

Verás un menú como este:

```
=============================================
      SCRAPER DE TIKTOK — MENÚ PRINCIPAL
=============================================
1. Modo anónimo   (sin login)
2. Modo autenticado (con login)
3. Salir
=============================================
Elige una opción (1/2/3):
```

### Modo 1 — Anónimo

1. Selecciona `1`.
2. Ingresa los usernames separados por coma: `mau_12,companero_1,companero_2`
3. El programa abrirá un navegador, obtendrá las cookies anónimas y extraerá los datos.
4. Los resultados se guardan en **`resultados_anonimo.json`**.

### Modo 2 — Autenticado

1. Selecciona `2`.
2. Ingresa los usernames.
3. **La primera vez**, se abrirá una ventana de TikTok donde deberás **iniciar sesión manualmente** con tu cuenta.
4. Cuando estés dentro, vuelve a la terminal y pulsa `ENTER`.
5. La sesión se guarda en `tiktok_state.json`.
6. En ejecuciones posteriores, el login se omite automáticamente.
7. Los resultados se guardan en **`resultados_autenticado.json`**.

---

## 📊 Datos extraídos

Por cada perfil, el scraper genera un objeto JSON con esta estructura (ampliada con IA):

```json
{
  "username": "mau_12",
  "name": "Mauricio",
  "bio": "Estudiante de ingeniería 🚀",
  "seguidores": 1523,
  "seguidos": 312,
  "likes_totales": 45600,
  "videos_totales": 87,
  "ultimos_10_videos": [
    {
      "url": "https://www.tiktok.com/@mau_12/video/7300000000000000000",
      "descripcion": "Mi primer video con Playwright 🚀",
      "vistas": 12500,
      "likes": 850,
      "comentarios": 42,
      "compartidos": 18
    }
  ],
  "clasificacion": {
    "clasificacion_tamano": "micro",
    "engagement_promedio_pct": 6.8,
    "emojis": {
      "top_emojis": [["🚀", 3], ["🔥", 2]],
      "total_emojis": 5
    }
  },
  "bigfive": {
    "apertura": 85,
    "responsabilidad": 70,
    "extraversion": 60,
    "amabilidad": 75,
    "neuroticismo": 30,
    "perfil_arquetipo": "Creativo-Explorador",
    "justificacion": "El uso de emojis como 🚀 y el tono del texto...",
    "evidencia_emojis": "Los emojis 🚀🔥 indican entusiasmo...",
    "conclusion": "Este perfil proyecta una personalidad..."
  },
  "lista_seguidos": "⚠️ Requiere login (modo autenticado)",
  "lista_seguidores": "⚠️ Requiere login (modo autenticado)"
}
```
---

## 🎯 El Resultado Final

El verdadero valor del proyecto no está solo en extraer datos o pintar una gráfica, sino en **generar una conclusión interpretativa automática** (lo que en marketing se llama *Insight*). 

Después de que la IA (Groq) analiza la bio, los hashtags, los videos y los emojis, el Dashboard no solo muestra 5 números, sino que genera un **Perfil Psicométrico** con los siguientes entregables:

1. **Arquetipo del Creador (Etiqueta):**
   La IA clasifica al usuario en una categoría de marca personal (Ej: *"Creativo-Explorador"*, *"Líder-Comunicador"* o *"Artista-Introspectivo"*). Esto permite entender de un vistazo qué tipo de contenido consume su audiencia.
   
2. **Rasgos Dominante y Débil:**
   Identifica automáticamente cuál es su mayor fortaleza (ej. una Apertura de 90) y su punto más bajo (ej. una Extraversión de 30). Esto es oro puro para un *Community Manager*, ya que le dice si el creador es mejor para hacer videos hablando a cámara o para hacer contenido visual/artístico en silencio.

3. **La Conclusión Interpretativa (El Párrafo de Valor):**
   Este es el entregable estrella. El sistema redacta un texto profesional explicando:
   *   **Cómo se proyecta:** Si es una persona auténtica, ruidosa o reservada.
   *   **Qué valores comunica:** Si habla de superación, de arte, de humor o de drama.
   *   **Qué comunidad atrae:** El tipo de personas que se sienten identificadas con él.
   *   **Recomendación práctica:** Un consejo estratégico (ej. *"Se recomienda sistematizar las llamadas a la acción para convertir engagement en comunidad activa"*).

4. **Evidencia Emocional (Justificación de Emojis):**
   La IA explica **por qué** tomó esas decisiones, citando los emojis reales encontrados (Ej. *"El uso recurrente de 🚀 y 🌍 sugiere una mentalidad abierta y enfocada en el crecimiento"*).

**¿Para qué sirve esto en la vida real?** 
Este módulo transforma un simple scraper en una herramienta de **Inteligencia de Negocios**. Una agencia de marketing podría usar esta app para:
*   Hacer *scouting* y encontrar influencers cuyo perfil psicológico encaje con la imagen de una marca.
*   Analizar a la competencia y entender por qué conectan con su público.
*   Darle a un creador un "diagnóstico" de su marca personal sin pagar a un psicólogo o consultor.

---

### Disponibilidad de datos según el modo

| Dato | Modo anónimo | Modo autenticado |
|---|---|---|
| Username, Name, Bio | ✅ | ✅ |
| Nº de seguidores | ✅ | ✅ |
| Nº de seguidos | ✅ | ✅ |
| Últimos 10 videos | ✅ | ✅ |
| Vistas, likes, comentarios, compartidos | ✅ | ✅ |
| Análisis de Emojis y big Five (IA) | ✅ | ✅ |
| Reproducción de video en un panel | ✅ | ✅ |
| Comentarios reales (hasta 20) | ❌ Bloqueado por TikTok | ✅ |
| Lista de seguidores/seguidos | ❌ Bloqueado por TikTok | ⚠️ Limitado (TikTok bloquea fácilmente) |

> **Nota técnica**: TikTok retiró el acceso anónimo a la lista de comentarios y de seguidores de perfiles públicos. Es una limitación de la plataforma, no del scraper.

---

## ⚖️ Consideraciones éticas y legales

Este proyecto se desarrolla bajo los siguientes principios:

1. **Consentimiento explícito**: Todos los perfiles scrapeados pertenecen a personas que autorizaron su uso para esta práctica académica.
2. **Perfiles públicos únicamente**: No se accede a contenido privado ni se intentan saltar restricciones de privacidad.
3. **Sin cookies de terceros**: El modo autenticado usa **únicamente** las credenciales del usuario ejecutor, nunca las de otros.
4. **Uso académico**: El código no se emplea con fines comerciales ni de monetización.
5. **Respeto a los ToS**: Se implementan pausas entre peticiones y medidas de bajo perfil para evitar cargas abusivas sobre los servidores de TikTok.
6. **Captchas**: Si aparece uno, el script debe detenerse. **No se implementa resolución automática de captchas**, ya que eso violaría los Términos de Servicio.

---

## 🔐 Seguridad

El archivo `.gitignore` excluye automáticamente:

- `tiktok_state.json` → **contiene tus cookies de sesión**. Si se filtra, alguien podría acceder a tu cuenta.
- `resultados_*.json` → contienen datos personales de terceros.
- `venv/` y `__pycache__/` → archivos generados localmente.

**Nunca hagas commit de `tiktok_state.json`**. Si por accidente lo subes:

```bash
git rm --cached tiktok_state.json
git commit -m "Remove session state from repo"
```

Y **cambia la contraseña de tu cuenta de TikTok** inmediatamente.

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.9+ | Lenguaje base |
| Playwright | 1.48+ | Automatización de navegador |
| Chromium | (vía Playwright) | Navegador headless/visible |
| Streamlit | 1.30+ | Interfaz gráfica web adatado al celular de igual forma web |
| Pandas | 2.0+ | Estructuración de datos para gráficas |
| Plotly | 5.0+ | Gráficos interactivos (Radar, Dispersión) |
| OpenAI SDK | 1.0+ | Conexión con la API de Groq |
| python-dotenv | 1.0+ | Gestión segura de la API Key |
| Emoji | 2.0+ | Extracción de señales emocionales |
| JSON | (stdlib) | Serialización de resultados |

**No se utilizan**:

- ❌ APIs oficiales de TikTok
- ❌ Librerías de scraping prefabricadas (`tiktok-api-unofficial`, `TikTokApi`, etc.)
- ❌ Servicios de terceros (Apify, BrightData, etc.)

El scraping se implementa **desde cero** siguiendo los requisitos de la práctica.

---

## 👤 Autor

**Erick Mauricio**  
Práctica universitaria — Ingeniería  
GitHub: [@empulamarin11](https://github.com/empulamarin11)

---

## 📄 Licencia

Proyecto con fines exclusivamente **académicos y educativos**. No se permite su uso comercial. Los datos extraídos pertenecen a sus respectivos autores.