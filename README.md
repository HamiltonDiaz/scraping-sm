sudo bash instalar-monitor.sh 30 

# 🎓 Monitor de Vacantes - Sistema Maestro MinEducación

Sistema automatizado de monitoreo de vacantes docentes publicadas en el portal del Sistema Maestro del Ministerio de Educación de Colombia.

## 🚀 Características

- ✅ Monitoreo automático cada 2 minutos (configurable)
- ✅ Filtros personalizables (Secretaría, Municipio, Área, etc.)
- ✅ Detección inmediata de nuevas vacantes
- ✅ Notificaciones por Telegram (oficial) o WhatsApp (CallMeBot)
- ✅ Historial SQLite para evitar duplicados
- ✅ Manejo de JSF/PrimeFaces con Playwright
- ✅ Despliegue gratuito en GitHub Actions, Railway, Oracle Cloud, etc.

## 📦 Instalación

```bash
# Clonar repositorio
git clone <tu-repo>
cd scraping-sis-maestro

# Crear entorno virtual
sudo apt install python3.12-venv  # Solo la primera vez
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

## ⚙️ Configuración

Edita `config/config.yaml` con tus datos:

```yaml
filtros:
  area: "Matemáticas"
  municipio: "Bogotá D.C."

notificacion:
  tipo: "telegram"
  telegram:
    bot_token: "TU_TOKEN"
    chat_id: "TU_CHAT_ID"
```

## 🏃 Uso

```bash
# Monitoreo continuo
python main.py

# Ejecución única
python main.py --once

# Ver estadísticas
python main.py --stats
```

## 🌐 Despliegue en GitHub Actions

1. Sube el código a GitHub
2. Ve a Settings → Secrets and variables → Actions
3. Agrega los secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. El workflow se ejecuta cada 15 minutos automáticamente

## 📁 Estructura

```
├── scraper.py       # Web scraping con Playwright
├── database.py      # Gestión de SQLite
├── notifier.py      # Notificaciones Telegram/WhatsApp
├── main.py          # Script principal
├── config/          # Configuración
├── data/            # Base de datos (auto-generada)
└── logs/            # Logs del sistema
```

## 🔧 Ajustar selectores del portal

Si el portal cambia su estructura, edita `scraper.py` en el método `aplicar_filtros()` y actualiza los selectores CSS/XPath según la nueva estructura HTML.