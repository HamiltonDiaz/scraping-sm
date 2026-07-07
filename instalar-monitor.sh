#!/bin/bash
# ============================================================================
# Script de instalación del Monitor de Vacantes - Sistema Maestro
# Ejecutar con: sudo bash instalar-monitor.sh
# ============================================================================

set -e

# Colores para mensajes
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar mensajes
info()    { echo -e "${AZUL}[INFO]${NC} $1"; }
exito()   { echo -e "${VERDE}[✓]${NC} $1"; }
advertencia() { echo -e "${AMARILLO}[!]${NC} $1"; }
error()   { echo -e "${ROJO}[✗]${NC} $1"; }

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Detectar directorio del proyecto automáticamente
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO_DIR="$SCRIPT_DIR"
VENV_PYTHON="$PROYECTO_DIR/venv/bin/python"
LOG_FILE="$PROYECTO_DIR/logs/cron-monitor.log"
CRON_MARKER="# MONITOR-VACANTES-SIS-MAESTRO"
INTERVALO_MINUTOS="${1:-2}"  # Por defecto cada 2 minutos, o pasar como argumento

# Detectar usuario real (cuando se ejecuta con sudo)
if [ -n "$SUDO_USER" ]; then
    USUARIO_REAL="$SUDO_USER"
else
    USUARIO_REAL="$USER"
fi

# Obtener el home del usuario real
HOME_USUARIO=$(eval echo "~$USUARIO_REAL")
CRONTAB_FILE="$HOME_USUARIO/crontab_backup_$(date +%Y%m%d_%H%M%S).bak"

# ============================================================================
# VALIDACIONES
# ============================================================================

echo ""
echo -e "${AZUL}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${AZUL}║  Instalador del Monitor de Vacantes - Sistema Maestro       ║${NC}"
echo -e "${AZUL}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que no se esté ejecutando como root directamente
if [ "$EUID" -ne 0 ]; then
    error "Este script debe ejecutarse con sudo"
    echo "  Uso: sudo bash $0 [intervalo_minutos]"
    echo "  Ejemplo: sudo bash $0 5"
    exit 1
fi

# Verificar que existe el directorio del proyecto
if [ ! -d "$PROYECTO_DIR" ]; then
    error "No se encuentra el directorio del proyecto: $PROYECTO_DIR"
    exit 1
fi
exito "Directorio del proyecto encontrado: $PROYECTO_DIR"

# Verificar que existe main.py
if [ ! -f "$PROYECTO_DIR/main.py" ]; then
    error "No se encuentra main.py en $PROYECTO_DIR"
    exit 1
fi
exito "Archivo main.py encontrado"

# Verificar que existe el entorno virtual
if [ ! -f "$VENV_PYTHON" ]; then
    error "No se encuentra el entorno virtual en: $VENV_PYTHON"
    advertencia "Crea el entorno virtual primero:"
    echo "  cd $PROYECTO_DIR"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi
exito "Entorno virtual encontrado: $VENV_PYTHON"

# Verificar que existe config.yaml
if [ ! -f "$PROYECTO_DIR/config/config.yaml" ]; then
    error "No se encuentra config/config.yaml"
    advertencia "Configura primero el archivo de configuración"
    exit 1
fi
exito "Archivo de configuración encontrado"

# Verificar que el usuario real existe
if ! id "$USUARIO_REAL" &>/dev/null; then
    error "No se pudo determinar el usuario real"
    exit 1
fi
exito "Usuario detectado: $USUARIO_REAL"

# ============================================================================
# CREAR DIRECTORIO DE LOGS
# ============================================================================

info "Creando directorio de logs..."
mkdir -p "$PROYECTO_DIR/logs"
chown -R "$USUARIO_REAL:$USUARIO_REAL" "$PROYECTO_DIR/logs"
exito "Directorio de logs creado: $PROYECTO_DIR/logs"

# ============================================================================
# BACKUP DEL CRONTAB ACTUAL
# ============================================================================

info "Creando backup del crontab actual..."
crontab -u "$USUARIO_REAL" -l > "$CRONTAB_FILE" 2>/dev/null || touch "$CRONTAB_FILE"
chown "$USUARIO_REAL:$USUARIO_REAL" "$CRONTAB_FILE"
exito "Backup creado en: $CRONTAB_FILE"

# ============================================================================
# VERIFICAR SI YA EXISTE UNA INSTALACIÓN PREVIA
# ============================================================================

if crontab -u "$USUARIO_REAL" -l 2>/dev/null | grep -q "$CRON_MARKER"; then
    advertencia "Ya existe una instalación previa del monitor"
    read -p "¿Deseas reemplazarla? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        info "Eliminando instalación previa..."
        crontab -u "$USUARIO_REAL" -l | grep -v "$CRON_MARKER" | grep -v "main.py --once.*scraping-sis-maestro" | crontab -u "$USUARIO_REAL" -
        exito "Instalación previa eliminada"
    else
        info "Instalación cancelada"
        exit 0
    fi
fi

# ============================================================================
# CREAR SCRIPT WRAPPER (para ejecutar con el usuario correcto)
# ============================================================================

WRAPPER_SCRIPT="$PROYECTO_DIR/scripts/ejecutar-monitor.sh"
info "Creando script wrapper en: $WRAPPER_SCRIPT"

mkdir -p "$PROYECTO_DIR/scripts"

cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Script wrapper para ejecutar el monitor desde cron
# Generado automáticamente - No editar manualmente

cd "$PROYECTO_DIR" || exit 1
export PATH="$PROYECTO_DIR/venv/bin:\$PATH"

# Ejecutar el monitor
"$VENV_PYTHON" main.py --once >> "$LOG_FILE" 2>&1

# Rotar log si es mayor a 10MB
if [ -f "$LOG_FILE" ]; then
    SIZE=\$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
    if [ "\$SIZE" -gt 10485760 ]; then
        mv "$LOG_FILE" "\${LOG_FILE}.old"
    fi
fi
EOF

chmod +x "$WRAPPER_SCRIPT"
chown "$USUARIO_REAL:$USUARIO_REAL" "$WRAPPER_SCRIPT"
exito "Script wrapper creado"

# ============================================================================
# AGREGAR CRON JOB
# ============================================================================

info "Agregando cron job (cada $INTERVALO_MINUTOS minutos)..."

# Construir la línea del cron
CRON_LINE="*/$INTERVALO_MINUTOS * * * * $WRAPPER_SCRIPT $CRON_MARKER"

# Agregar al crontab
(crontab -u "$USUARIO_REAL" -l 2>/dev/null; echo "$CRON_LINE") | crontab -u "$USUARIO_REAL" -

exito "Cron job agregado correctamente"

# ============================================================================
# VERIFICACIÓN FINAL
# ============================================================================

echo ""
echo -e "${VERDE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${VERDE}║              ✓ INSTALACIÓN COMPLETADA                        ║${NC}"
echo -e "${VERDE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${AZUL}Configuración:${NC}"
echo "  • Usuario: $USUARIO_REAL"
echo "  • Proyecto: $PROYECTO_DIR"
echo "  • Intervalo: cada $INTERVALO_MINUTOS minutos"
echo "  • Log: $LOG_FILE"
echo "  • Wrapper: $WRAPPER_SCRIPT"
echo ""
echo -e "${AZUL}Cron job instalado:${NC}"
crontab -u "$USUARIO_REAL" -l | grep "$CRON_MARKER"
echo ""
echo -e "${AMARILLO}Comandos útiles:${NC}"
echo "  • Ver logs en tiempo real:  tail -f $LOG_FILE"
echo "  • Ver cron instalado:       crontab -l"
echo "  • Probar manualmente:       sudo -u $USUARIO_REAL $WRAPPER_SCRIPT"
echo "  • Desinstalar:              sudo bash $PROYECTO_DIR/desinstalar-monitor.sh"
echo ""
exito "El monitor se ejecutará automáticamente cada $INTERVALO_MINUTOS minutos"
echo ""
