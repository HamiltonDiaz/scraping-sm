"""
main.py - Script principal del monitor de vacantes
Orquesta el scraping, la base de datos y las notificaciones.
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml

from scraper import SistemaMaestroScraper
from database import Database
from notifier import crear_notificador, formatear_mensaje


def configurar_logging(config: dict):
    """Configura el sistema de logs."""
    log_cfg = config.get("logging", {})
    log_file = log_cfg.get("file", "logs/monitor.log")
    nivel = getattr(logging, log_cfg.get("level", "INFO").upper())

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_cfg.get("max_size_mb", 10) * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))

    logging.basicConfig(level=nivel, handlers=[file_handler, console_handler])


def cargar_configuracion(ruta: str = "config/config.yaml") -> dict:
    """Carga la configuración desde archivo YAML."""
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ejecutar_ciclo(config: dict, db: Database, notifier) -> int:
    """
    Ejecuta un ciclo de monitoreo: scraping + notificación.

    Returns:
        Número de vacantes nuevas detectadas.
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info(f"Iniciando ciclo de monitoreo - {datetime.now()}")

    scraper = SistemaMaestroScraper(config["scraper"])

    try:
        scraper.iniciar()
        nuevas = scraper.obtener_nuevas_vacantes(config["filtros"], db)

        if nuevas:
            logger.info(f"¡{len(nuevas)} nueva(s) vacante(s) detectada(s)!")
            for vacante in nuevas:
                if db.registrar_vacante(vacante):
                    mensaje = formatear_mensaje(vacante)
                    notifier.enviar(mensaje)
                    time.sleep(1)
        else:
            logger.info("No se detectaron vacantes nuevas en este ciclo.")

        return len(nuevas)

    except Exception as e:
        logger.error(f"Error durante el ciclo: {e}", exc_info=True)
        return 0
    finally:
        scraper.cerrar()


def mostrar_estadisticas(db: Database):
    """Muestra estadísticas del sistema."""
    total = db.contar_vacantes()
    print(f"\n📊 Estadísticas del Monitor")
    print(f"{'=' * 40}")
    print(f"Total de vacantes registradas: {total}")
    print(f"\n📋 Últimas 10 vacantes:")
    for v in db.obtener_historial(10):
        print(f"  • [{v['fecha_detectada']}] {v.get('area', 'N/A')} - {v.get('municipio', 'N/A')}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Monitor de vacantes - Sistema Maestro MinEducación"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Ejecutar un solo ciclo y salir"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Mostrar estadísticas y salir"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Limpiar historial de vacantes (todas se considerarán nuevas)"
    )
    parser.add_argument(
        "--config", default="config/config.yaml",
        help="Ruta al archivo de configuración"
    )
    args = parser.parse_args()

    config = cargar_configuracion(args.config)
    configurar_logging(config)
    logger = logging.getLogger(__name__)

    db_cfg = config.get("database", {})
    db = Database(
        db_path=db_cfg.get("path", "data/vacantes.db"),
        dias_retencion=db_cfg.get("dias_retencion", 90)
    )

    # ✅ NUEVO: Modo reset
    if args.reset:
        respuesta = input("⚠️  ¿Estás seguro de limpiar todo el historial? (s/n): ")
        if respuesta.lower() == 's':
            eliminados = db.limpiar_historial()
            print(f"✅ Historial limpiado. Se eliminaron {eliminados} registros.")
            print("💡 Ahora ejecuta 'python main.py --once' para detectar vacantes nuevamente.")
        else:
            print("❌ Operación cancelada.")
        db.cerrar()
        return

    if args.stats:
        mostrar_estadisticas(db)
        db.cerrar()
        return

    try:
        notifier = crear_notificador(config["notificacion"])
    except ValueError as e:
        logger.error(f"Error de configuración de notificaciones: {e}")
        db.cerrar()
        sys.exit(1)

    if args.once:
        logger.info("Modo de ejecución única (--once)")
        ejecutar_ciclo(config, db, notifier)
        db.cerrar()
        return

    intervalo = config["scraper"].get("interval_minutes", 2) * 60
    logger.info(f"Iniciando monitoreo continuo cada {intervalo // 60} minuto(s)...")
    logger.info("Presiona Ctrl+C para detener.")

    try:
        while True:
            ejecutar_ciclo(config, db, notifier)
            logger.info(f"Próximo ciclo en {intervalo // 60} minuto(s)...")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        logger.info("\nMonitoreo detenido por el usuario.")
    finally:
        db.cerrar()


if __name__ == "__main__":
    main()