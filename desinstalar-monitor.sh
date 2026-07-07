#!/bin/bash
# ============================================================================
# Script de desinstalación del Monitor de Vacantes - Sistema Maestro
# Ejecutar con: sudo bash desinstalar-monitor.sh
# ============================================================================

set -e

# Colores para mensajes
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${AZUL}[INFO]${NC} $1"; }
exito()   { echo -e "${VERDE}[✓]${NC} $1"; }
advertencia() { echo -e "${AMARILLO}[!]${NC} $1"; }
error()   { echo -e "${ROJO}[✗]${NC} $1"; }

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO_DIR="$SCRIPT_DIR"
CRON_MARKER="# MONITOR-VACANTES-SIS-MAESTRO"
LOG_FILE="$PROYECTO_DIR/logs/cron-monitor.log"

# Detectar usuario real
if [ -n "$SUDO_USER" ]; then
    USUARIO_REAL="$SUDO_USER"
else
    USUARIO_REAL="$USER"
fi

HOME_USUARIO=$(eval echo "~$USUARIO_REAL")

# ============================================================================
# VALIDACIONES
# ============================================================================

echo ""
echo -e "${ROJO}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${ROJO}║  Desinstalador del Monitor de Vacantes - Sistema Maestro    ║${NC}"
echo -e "${ROJO}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    error "Este script debe ejecutarse con sudo"
    echo "  Uso: sudo bash $0"
    exit 1
fi

# ============================================================================
# VERIFICAR SI EXISTE EL CRON JOB
# ============================================================================

info "Verificando si existe el cron job..."

if ! crontab -u "$USUARIO_REAL" -l 2>/dev/null | grep -q "$CRON_MARKER"; then
    advertencia "No se encontró una instalación previa del monitor"
    echo "  No hay cron job con el marcador: $CRON_MARKER"
    exit 0
fi

exito "Cron job encontrado:"
crontab -u "$USUARIO_REAL" -l | grep "$CRON_MARKER"
echo ""

# ============================================================================
# CONFIRMAR DESINSTALACIÓN
# ============================================================================

read -p "¿Estás seguro de desinstalar el monitor? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    info "Desinstalación cancelada"
    exit 0
fi

# ============================================================================
# BACKUP DEL CRONTAB
# ============================================================================

info "Creando backup del crontab actual..."
CRONTAB_BACKUP="$HOME_USUARIO/crontab_backup_antes_desinstalar_$(date +%Y%m%d_%H%M%S).bak"
crontab -u "$USUARIO_REAL" -l > "$CRONTAB_BACKUP" 2>/dev/null || touch "$CRONTAB_BACKUP"
chown "$USUARIO_REAL:$USUARIO_REAL" "$CRONTAB_BACKUP"
exito "Backup creado en: $CRONTAB_BACKUP"

# ============================================================================
# ELIMINAR CRON JOB
# ============================================================================

info "Eliminando cron job..."

# Eliminar solo las líneas del monitor (usando el marcador)
crontab -u "$USUARIO_REAL" -l | grep -v "$CRON_MARKER" | grep -v "ejecutar-monitor.sh" | crontab -u "$USUARIO_REAL" -

exito "Cron job eliminado"

# ============================================================================
# ELIMINAR SCRIPT WRAPPER
# ============================================================================

WRAPPER_SCRIPT="$PROYECTO_DIR/scripts/ejecutar-monitor.sh"

if [ -f "$WRAPPER_SCRIPT" ]; then
    info "Eliminando script wrapper..."
    rm -f "$WRAPPER_SCRIPT"
    exito "Script wrapper eliminado"
    
    # Eliminar directorio scripts si está vacío
    if [ -d "$PROYECTO_DIR/scripts" ] && [ -z "$(ls -A $PROYECTO_DIR/scripts)" ]; then
        rmdir "$PROYECTO_DIR/scripts"
        exito "Directorio scripts eliminado (estaba vacío)"
    fi
fi

# ============================================================================
# OPCIONAL: ELIMINAR LOGS
# ============================================================================

if [ -f "$LOG_FILE" ]; then
    echo ""
    read -p "¿Deseas eliminar también los logs? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        info "Eliminando logs..."
        rm -f "$LOG_FILE"
        rm -f "${LOG_FILE}.old"
        exito "Logs eliminados"
    else
        info "Logs conservados en: $LOG_FILE"
    fi
fi

# ============================================================================
# OPCIONAL: ELIMINAR BASE DE DATOS
# ============================================================================

DB_FILE="$PROYECTO_DIR/data/vacantes.db"

if [ -f "$DB_FILE" ]; then
    echo ""
    read -p "¿Deseas eliminar también la base de datos de vacantes? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        info "Eliminando base de datos..."
        rm -f "$DB_FILE"
        exito "Base de datos eliminada"
    else
        info "Base de datos conservada en: $DB_FILE"
    fi
fi

# ============================================================================
# VERIFICACIÓN FINAL
# ============================================================================

echo ""
echo -e "${VERDE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${VERDE}║              ✓ DESINSTALACIÓN COMPLETADA                     ║${NC}"
echo -e "${VERDE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${AZUL}Resumen:${NC}"
echo "  • Cron job: ELIMINADO"
echo "  • Script wrapper: ELIMINADO"
echo "  • Proyecto: CONSERVADO en $PROYECTO_DIR"
echo "  • Backup del crontab: $CRONTAB_BACKUP"
echo ""
echo -e "${AMARILLO}Verificación:${NC}"
echo "  • Crontab actual:"
if crontab -u "$USUARIO_REAL" -l 2>/dev/null | grep -q .; then
    crontab -u "$USUARIO_REAL" -l | sed 's/^/      /'
else
    echo "      (vacío)"
fi
echo ""
echo -e "${AZUL}Si deseas reinstalar en el futuro:${NC}"
echo "  sudo bash $PROYECTO_DIR/instalar-monitor.sh [intervalo_minutos]"
echo ""
exito "Desinstalación completada exitosamente"
echo ""
