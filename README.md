# Practica Scrapy TikTok
# 🕷️ Scraper de TikTok — Práctica Universitaria

Scraper desarrollado **desde cero** con Python, Playwright y Streamlit para extraer datos públicos de perfiles de TikTok y presentarlos en un Dashboard web interactivo, sin usar APIs oficiales ni librerías de terceros especializadas. Proyecto académico con fines educativos, ejecutado en entorno controlado.

---

## 📋 Tabla de contenido

- [Descripción](#-descripción)
- [Características](#-características)
- [Arquitectura del proyecto](#-arquitectura-del-proyecto)
- [Requisitos previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Datos extraídos](#-datos-extraídos)
- [Consideraciones éticas y legales](#-consideraciones-éticas-y-legales)
- [Seguridad](#-seguridad)
- [Tecnologías utilizadas](#-tecnologías-utilizadas)
- [Autor](#-autor)

---

## 📖 Descripción

Este proyecto implementa un **scraper modular** para TikTok usando **Playwright** como motor de automatización de navegador y **Streamlit** para la interfaz gráfica. El objetivo es demostrar el proceso completo de extracción de datos de una aplicación web moderna:

1. Renderizado dinámico de JavaScript mediante un navegador real.
2. Manejo de **cookies anónimas** (`ttwid`, `msToken`, `_ttp`) que TikTok asigna a cualquier visitante.
3. Extracción de datos estructurados desde el JSON oculto `__UNIVERSAL_DATA_FOR_REHYDRATION__` que TikTok incrusta en el HTML.
4. Captura de respuestas XHR (llamadas internas a `/api/post/item_list` y `/api/comment/list/`) al hacer scroll.
5. Persistencia de sesión con `storage_state` para desbloquear datos que requieren autenticación (como los comentarios y las listas de seguidores).
6. Presentación de resultados en un Dashboard web moderno, con reproductor de videos integrado.

El scraper ofrece **dos modos de ejecución**:

| Modo | Requiere login | Datos que obtiene |
|---|---|---|
| **Anónimo** | ❌ No | Perfil, bio, stats, últimos 10 videos (con vistas, likes, comentarios, compartidos) |
| **Autenticado** | ✅ Sí (una vez) | Todo lo anterior **+** reproducción de video **+** extracción de hasta 20 comentarios reales **+** listas parciales de seguidores y seguidos |


---

## ✨ Características

- ✅ Extracción desde el **JSON oculto** de TikTok (más estable que los selectores CSS).
- ✅ Manejo automático de **cookies anónimas**.
- ✅ **Scroll dinámico** para cargar más videos y comentarios.
- ✅ **Captura de XHR** para no depender del DOM al extraer comentarios.
- ✅ **Persistencia de sesión** con `storage_state` (login solo la primera vez).
- ✅ **Medidas anti-detección**: ocultar `navigator.webdriver`, User-Agent realista, pausas prudenciales.
- ✅ **Interfaz web (Streamlit)**: Dashboard con modo oscuro, tarjetas expandibles y diseño responsive.
- ✅ **Reproductor integrado**: Reproduce videos de TikTok directamente en la interfaz sin salir de la app.
- ✅ **Extracción de listas**: Obtiene los nombres de los primeros seguidores y seguidos del perfil.
- ✅ Resultados exportados a **JSON estructurado**.
- ✅ Código **modular** (utils compartidas + scrapers independientes + interfaz web).

---

## 🏗️ Arquitectura del proyecto

```
PractScrapyTtk/
├── main.py                     # Menú unificado (punto de entrada)
├── utils.py                    # Funciones compartidas (contexto, extracción, guardado)
├── scrapytiktokanonimo.py          # Modo 1: sin login
├── scrapytiktoklogin.py      # Modo 2: con login (seguidores/seguidos)
├── streamlit_app.py      # Interfaz gráfica
├── requirements.txt            # Dependencias del proyecto
├── .gitignore                  # Exclusiones de Git
├── README.md                   # Este archivo
│
├── tiktok_state.json           # (generado) Estado de sesión — NO se sube
├── resultados_anonimo.json     # (generado) Resultados del modo 1 — NO se sube
└── resultados_autenticado.json # (generado) Resultados del modo 2 — NO se sube
```

---

## 🔧 Requisitos previos

Antes de instalar el proyecto, asegúrate de tener:

- **Python 3.9 o superior** → [python.org](https://www.python.org/downloads/)
- **Git** → [git-scm.com](https://git-scm.com/)
- **Conexión a internet** (para descargar Playwright y acceder a TikTok)

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

---

## 🎮 Uso

### Iniciar el programa

Con el entorno virtual activado ejecuta:

```bash
streamlit run streamlit_app.py
```
Se abrirá una pestaña en tu navegador (usualmente en http://localhost:8501) con el Dashboard.

Modo Anónimo: Puedes buscar perfiles directamente.

Modo Autenticado: Haz clic en "Iniciar Sesión". Se abrirá una ventana de Chromium. Ingresa tus credenciales y espera a que TikTok te redirija a tu feed principal. La ventana se cerrará y tu sesión se guardará en tiktok_state.json.

Búsqueda: Ingresa el username y presiona "Buscar ✨".

Videos: Haz clic en cada tarjeta para ver los detalles y reproducir el video.

Comentarios: Si tienes sesión activa, presiona "💬 Ver hasta 20 comentarios" dentro de la tarjeta de un video.

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

Por cada perfil, el scraper genera un objeto JSON con esta estructura:

```json
{
  "username": "mau_12",
  "name": "Mauricio",
  "bio": "Estudiante de ingeniería",
  "seguidores": 1523,
  "seguidos": 312,
  "likes_totales": 45600,
  "videos_totales": 87,
  "ultimos_12_videos": [
    {
      "url": "https://www.tiktok.com/@mau_12/video/7300000000000000000",
      "descripcion": "Mi primer video con Playwright 🚀",
      "vistas": 12500,
      "likes": 850,
      "comentarios": 42,
      "compartidos": 18
    }
  ],
  "lista_seguidos": "⚠️ Requiere login (modo autenticado)",
  "lista_seguidores": "⚠️ Requiere login (modo autenticado)"
}
```

### Disponibilidad de datos según el modo

| Dato | Modo anónimo | Modo autenticado |
|---|---|---|
| Username, Name, Bio | ✅ | ✅ |
| Nº de seguidores | ✅ | ✅ |
| Nº de seguidos | ✅ | ✅ |
| Últimos 10 videos | ✅ | ✅ |
| Vistas, likes, comentarios, compartidos | ✅ | ✅ |
| Reproducción de video en Dashboard | ✅ | ✅ |
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
GitHub: [@ErickMau](https://github.com/ErickMau)

---

## 📄 Licencia

Proyecto con fines exclusivamente **académicos y educativos**. No se permite su uso comercial. Los datos extraídos pertenecen a sus respectivos autores.