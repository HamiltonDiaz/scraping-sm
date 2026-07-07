# 🎓 Monitor de Vacantes — Sistema Maestro MinEducación

Sistema automatizado de monitoreo de vacantes docentes publicadas en el portal del **Sistema Maestro del Ministerio de Educación de Colombia** (`sistemamaestro.mineducacion.gov.co`).

Realiza peticiones HTTP directas al endpoint AJAX/JSF del portal, extrae las vacantes con BeautifulSoup y envía notificaciones inmediatas por **Telegram** o **WhatsApp** cuando detecta nuevas oportunidades.

---

## 🚀 Características

- ✅ Monitoreo automático con intervalo configurable (por defecto cada 15 min)
- ✅ Filtros personalizables: Secretaría, Departamento, Municipio, Área, Tipo de priorización
- ✅ Detección inmediata de nuevas vacantes (sin duplicados)
- ✅ Notificaciones por **Telegram** (API oficial) y/o **WhatsApp** (CallMeBot)
- ✅ Historial en SQLite con retención configurable (por defecto 90 días)
- ✅ Scraping mediante peticiones HTTP directas al endpoint AJAX de JSF/PrimeFaces
- ✅ Despliegue automático en **GitHub Actions** (cada 15 minutos, sin servidor)
- ✅ Instalación como cron job local con script bash incluido
- ✅ Script de diagnóstico para depuración del portal

---

## 📦 Instalación

### Requisitos previos

- Python 3.10+
- pip

### Pasos

```bash
# Clonar repositorio
git clone https://github.com/HamiltonDiaz/scraping-sm.git
cd scraping-sm

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

> **Nota:** `playwright` está listado en `requirements.txt` pero el scraper actualmente usa `requests` + `BeautifulSoup`. No es necesario instalar los navegadores de Playwright para el funcionamiento normal.

---

## ⚙️ Configuración

Edita `config/config.yaml` con tus datos:

```yaml
scraper:
  url: "https://sistemamaestro.mineducacion.gov.co/SistemaMaestro/busquedaVacantes.xhtml"
  interval_minutes: 15   # Intervalo de verificación en minutos
  timeout: 30            # Tiempo máximo de espera (segundos)
  headless: false
  user_agent: "Mozilla/5.0 ..."

filtros:
  secretaria: null                # Ej: "Secretaría de Educación de Bogotá"
  departamento: null              # Código numérico o null (Ej: 41 = Huila)
  municipio: null
  area: 14                        # Código numérico del área (14 = Inglés)
  tipo_priorizacion: null

notificacion:
  tipo: "telegram"                # "telegram", "whatsapp" o "ambos"
  telegram:
    bot_token: "TU_BOT_TOKEN"     # Obtén con @BotFather
    chat_id: "TU_CHAT_ID"         # Obtén con @userinfobot
  whatsapp:
    phone_number: null            # Formato: +573001234567
    api_key: null                 # API key de CallMeBot

database:
  path: "data/vacantes.db"
  dias_retencion: 90

logging:
  level: "INFO"                   # DEBUG, INFO, WARNING, ERROR
  file: "logs/monitor.log"
  max_size_mb: 10
```

### Configurar Telegram

1. Habla con [@BotFather](https://t.me/BotFather) en Telegram y crea un bot → obtén el `bot_token`
2. Habla con [@userinfobot](https://t.me/userinfobot) → obtén tu `chat_id`
3. Pega ambos valores en `config/config.yaml`

### Configurar WhatsApp (CallMeBot)

1. Guarda el número `+34 644 59 08 55` como "CallMeBot"
2. Envía el mensaje `I accept callmebot` a ese número por WhatsApp
3. Obtén tu API key en [callmebot.com/myaccount](https://www.callmebot.com/myaccount/)
4. Configura `phone_number` y `api_key` en el YAML

---

## 🏃 Uso

```bash
# Activar el entorno virtual (si no está activo)
source venv/bin/activate

# Monitoreo continuo (respeta el interval_minutes del config)
python main.py

# Ejecución única (un solo ciclo de scraping)
python main.py --once

# Ver estadísticas y últimas 10 vacantes detectadas
python main.py --stats

# Limpiar historial (las vacantes se tratarán como nuevas en el próximo ciclo)
python main.py --reset

# Usar un archivo de configuración alternativo
python main.py --config ruta/a/mi-config.yaml
```

---

## 🖥️ Instalación como cron job local

El script `instalar-monitor.sh` configura el monitor para ejecutarse automáticamente mediante cron.

```bash
# Instalar con intervalo de 30 minutos (por defecto: 2 minutos)
sudo bash instalar-monitor.sh 30
```

El script:

- Valida el entorno virtual y la configuración
- Crea un script wrapper en `scripts/ejecutar-monitor.sh`
- Agrega el cron job al usuario actual
- Gestiona la rotación de logs (>10 MB)

```bash
# Comandos útiles post-instalación
tail -f logs/cron-monitor.log   # Ver logs en tiempo real
crontab -l                       # Ver cron instalado
sudo bash desinstalar-monitor.sh # Desinstalar
```

---

## 🌐 Despliegue en GitHub Actions

El workflow `.github/workflows/main.yml` ejecuta el monitor cada **15 minutos** de forma gratuita sin necesidad de un servidor.

### Configuración

1. Sube el código a tu repositorio en GitHub
2. Ve a **Settings → Secrets and variables → Actions**
3. Crea el siguiente secret:

| Secret | Descripción |
| --- | --- |
| `CONFIG_YAML` | Contenido completo de tu `config/config.yaml` (con tokens reales) |

1. El workflow se activa automáticamente cada 15 minutos

### ¿Qué hace el workflow?

```txt
1. Clona el repositorio
2. Configura Python 3.10
3. Instala dependencias (requirements.txt)
4. Reconstruye config/config.yaml desde el secret CONFIG_YAML
5. Ejecuta: python main.py --once
6. Si hay nuevas vacantes → hace commit de vacantes.db y push al repo
```

> El archivo `data/vacantes.db` se actualiza en el propio repositorio para persistir el historial entre ejecuciones del workflow.

---

## 📁 Estructura del proyecto

```txt
scraping-sis-maestro/
├── main.py                # Script principal: orquesta scraping, BD y notificaciones
├── scraper.py             # Web scraping HTTP/AJAX contra el portal JSF/PrimeFaces
├── database.py            # Gestión del historial SQLite (deduplicación)
├── notifier.py            # Notificaciones: Telegram (oficial) y WhatsApp (CallMeBot)
├── diagnostico.py         # Script de depuración para inspeccionar respuestas AJAX
├── instalar-monitor.sh    # Instalador de cron job local
├── desinstalar-monitor.sh # Desinstalador del cron job
├── requirements.txt       # Dependencias Python
├── config/
│   └── config.yaml        # Configuración principal (filtros, notificaciones, BD, logs)
├── data/
│   └── vacantes.db        # Base de datos SQLite (auto-generada)
├── logs/
│   └── monitor.log        # Log rotativo del monitor
└── .github/
    └── workflows/
        └── main.yml       # Workflow de GitHub Actions (ejecución automática)
```

---

## 🔧 Cómo funciona el scraper

El scraper evita el uso de un navegador completo (Playwright/Selenium) realizando peticiones HTTP directas al endpoint AJAX del portal JSF/PrimeFaces:

1. **GET inicial** → obtiene la página y extrae el `ViewState` (token de sesión JSF)
2. **POST AJAX** → envía los filtros configurados simulando la interacción del formulario
3. **Parseo XML/CDATA** → extrae el bloque `<update id="accordion">` de la respuesta
4. **BeautifulSoup** → parsea el HTML interno y localiza los `div` de cada vacante
5. **Deduplicación** → cada vacante obtiene un ID MD5 basado en sus datos clave; si ya está en SQLite, se omite
6. **Notificación** → las vacantes nuevas se formatean y envían por el canal configurado

### Campos extraídos por vacante

| Campo | Descripción |
| --- | --- |
| `cargo` | Nombre del cargo/plaza |
| `area` | Área o asignatura |
| `secretaria` | Secretaría de Educación |
| `departamento` | Departamento |
| `municipio` | Municipio |
| `zona` | Zona (urbana/rural) |
| `postulados` | Número de postulados actuales |
| `tipo_priorizacion` | Tipo de priorización/ponderación |
| `fecha_cierre` | Fecha límite de postulación |
| `enlace` | URL de detalle de la vacante |

---

## 🛠️ Diagnóstico

Si el portal cambia su estructura HTML, usa `diagnostico.py` para inspeccionar la respuesta AJAX:

```bash
python diagnostico.py
# Guarda la respuesta completa en debug_ajax_response.xml
# Muestra los tags <update> disponibles y los patrones de vacantes encontrados
```

Si los selectores dejan de funcionar, edita en `scraper.py`:

- `aplicar_filtros()` → nombres de campos del formulario (`campos_filtro`)
- `extraer_vacantes()` → patrón regex de los `div` de vacantes y mapeo de `label` IDs

---

## 📋 Dependencias

| Paquete | Versión | Uso |
| --- | --- | --- |
| `requests` | 2.32.3 | Peticiones HTTP al portal |
| `beautifulsoup4` | 4.12.3 | Parseo del HTML de respuesta |
| `pyyaml` | 6.0.1 | Lectura del archivo de configuración |
| `python-telegram-bot` | 21.3 | SDK de Telegram (referencia) |
| `playwright` | 1.45.0 | Incluido en requirements (no usado actualmente) |

---

## ⚠️ Consideraciones

- El portal usa sesiones JSF; si la sesión expira, el scraper la renueva automáticamente en el siguiente ciclo.
- Los IDs de los `label` del portal (e.g., `j_idt93`, `j_idt99`) pueden cambiar si el portal se actualiza. Usa `diagnostico.py` para identificar los nuevos IDs.
- El token y chat_id de Telegram **nunca deben subirse al repositorio**. Usa el secret `CONFIG_YAML` en GitHub Actions o variables de entorno locales.
- Para GitHub Actions gratuito, el mínimo intervalo de cron es 5 minutos (el workflow usa 15 minutos).
