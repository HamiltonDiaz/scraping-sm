"""
database.py - Módulo de gestión de base de datos SQLite
Maneja el historial de vacantes para evitar notificaciones duplicadas.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """Gestiona la base de datos de vacantes notificadas."""

    def __init__(self, db_path: str = "data/vacantes.db", dias_retencion: int = 90):
        """
        Inicializa la conexión a la base de datos.

        Args:
            db_path: Ruta al archivo SQLite.
            dias_retencion: Días para conservar registros antiguos.
        """
        self.db_path = db_path
        self.dias_retencion = dias_retencion

        # Crear directorio si no existe
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._crear_tabla()
        self._limpiar_antiguos()

    def _crear_tabla(self):
        """Crea la tabla de vacantes si no existe."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vacantes (
                id TEXT PRIMARY KEY,
                area TEXT,
                secretaria TEXT,
                municipio TEXT,
                establecimiento TEXT,
                fecha_cierre TEXT,
                tipo_priorizacion TEXT,
                enlace TEXT,
                fecha_detectada TEXT,
                fecha_notificada TEXT
            )
        """)
        self.conn.commit()
        logger.debug("Tabla de vacantes verificada/creada.")

    def _limpiar_antiguos(self):
        """Elimina registros más antiguos que los días de retención."""
        fecha_limite = datetime.now() - timedelta(days=self.dias_retencion)
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM vacantes WHERE fecha_detectada < ?",
            (fecha_limite.isoformat(),)
        )
        eliminados = cursor.rowcount
        self.conn.commit()
        if eliminados > 0:
            logger.info(f"Se eliminaron {eliminados} registros antiguos.")

    def existe_vacante(self, vacante_id: str) -> bool:
        """
        Verifica si una vacante ya fue registrada.

        Args:
            vacante_id: Identificador único de la vacante.

        Returns:
            True si ya existe, False en caso contrario.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM vacantes WHERE id = ?", (vacante_id,))
        return cursor.fetchone() is not None

    def registrar_vacante(self, vacante: dict) -> bool:
        """
        Registra una nueva vacante en la base de datos.

        Args:
            vacante: Diccionario con los datos de la vacante.
                     Debe contener al menos 'id'.

        Returns:
            True si se registró correctamente, False si ya existía.
        """
        if self.existe_vacante(vacante["id"]):
            logger.debug(f"Vacante {vacante['id']} ya registrada. Omitiendo.")
            return False

        ahora = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO vacantes
            (id, area, secretaria, municipio, establecimiento,
             fecha_cierre, tipo_priorizacion, enlace,
             fecha_detectada, fecha_notificada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacante.get("id"),
            vacante.get("area"),
            vacante.get("secretaria"),
            vacante.get("municipio"),
            vacante.get("establecimiento"),
            vacante.get("fecha_cierre"),
            vacante.get("tipo_priorizacion"),
            vacante.get("enlace"),
            ahora,
            ahora
        ))
        self.conn.commit()
        logger.info(f"Vacante registrada: {vacante['id']}")
        return True

    def contar_vacantes(self) -> int:
        """Retorna el número total de vacantes registradas."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vacantes")
        return cursor.fetchone()[0]

    def obtener_historial(self, limite: int = 20) -> list:
        """
        Obtiene las últimas vacantes registradas.

        Args:
            limite: Número máximo de registros a retornar.

        Returns:
            Lista de diccionarios con las vacantes.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM vacantes
            ORDER BY fecha_detectada DESC
            LIMIT ?
        """, (limite,))
        return [dict(row) for row in cursor.fetchall()]

    def cerrar(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            logger.debug("Conexión a base de datos cerrada.")

    def limpiar_historial(self):
        """Elimina todos los registros del historial."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM vacantes")
        eliminados = cursor.rowcount
        self.conn.commit()
        logger.info(f"Historial limpiado. Se eliminaron {eliminados} registros.")
        return eliminados            