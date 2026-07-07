"""
notifier.py - Módulo de notificaciones
Soporta Telegram (oficial) y WhatsApp (vía CallMeBot).
"""

import logging
import requests
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Notifier(ABC):
    """Clase abstracta para notificaciones."""

    @abstractmethod
    def enviar(self, mensaje: str) -> bool:
        """Envía una notificación. Retorna True si fue exitoso."""
        pass


class TelegramNotifier(Notifier):
    """Notificador usando la API oficial de Telegram Bot."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def enviar(self, mensaje: str) -> bool:
        """
        Envía un mensaje por Telegram.

        Args:
            mensaje: Texto a enviar (soporta HTML).

        Returns:
            True si se envió correctamente.
        """
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": mensaje,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            logger.info("Notificación enviada por Telegram.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar por Telegram: {e}")
            return False


class WhatsAppNotifier(Notifier):
    """Notificador usando CallMeBot (gratuito)."""

    def __init__(self, phone_number: str, api_key: str):
        self.phone_number = phone_number
        self.api_key = api_key
        self.base_url = "https://api.callmebot.com/whatsapp.php"

    def enviar(self, mensaje: str) -> bool:
        """
        Envía un mensaje por WhatsApp vía CallMeBot.

        Args:
            mensaje: Texto a enviar (solo texto plano).

        Returns:
            True si se envió correctamente.
        """
        try:
            params = {
                "phone": self.phone_number,
                "text": mensaje,
                "apikey": self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            # CallMeBot retorna "200" en el body si fue exitoso
            if response.status_code == 200 and "error" not in response.text.lower():
                logger.info("Notificación enviada por WhatsApp.")
                return True
            else:
                logger.error(f"Error de CallMeBot: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar por WhatsApp: {e}")
            return False


def formatear_mensaje(vacante: dict) -> str:
    """
    Formatea los datos de una vacante en un mensaje legible.
    """
    mensaje = "🎓 <b>NUEVA VACANTE DETECTADA</b> 🎓\n\n"
    mensaje += f"💼 <b>Cargo:</b> {vacante.get('cargo', 'N/A')}\n"
    mensaje += f"📚 <b>Área:</b> {vacante.get('area', 'N/A')}\n"
    mensaje += f"🏛️ <b>Secretaría:</b> {vacante.get('secretaria', 'N/A')}\n"
    mensaje += f"📍 <b>Zona:</b> {vacante.get('zona', 'N/A')}\n"
    mensaje += f"🏙️ <b>Departamento:</b> {vacante.get('departamento', 'N/A')}\n"
    mensaje += f"📌 <b>Municipio:</b> {vacante.get('municipio', 'N/A')}\n"
    mensaje += f"👥 <b>Postulados:</b> {vacante.get('postulados', 'N/A')}\n"
    mensaje += f"🎯 <b>Tipo:</b> {vacante.get('tipo_priorizacion', 'N/A')}\n"
    mensaje += f"📅 <b>Cierre:</b> {vacante.get('fecha_cierre', 'N/A')}\n"

    enlace = vacante.get("enlace")
    if enlace and enlace != "#":
        mensaje += f"\n🔗 <a href=\"{enlace}\">Ver detalle</a>\n"

    mensaje += f"\n⏰ <i>Detectada: {vacante.get('fecha_detectada', 'N/A')}</i>"

    return mensaje


def crear_notificador(config: dict) -> Notifier:
    """
    Fábrica de notificadores según la configuración.

    Args:
        config: Diccionario de configuración (sección 'notificacion').

    Returns:
        Instancia del notificador apropiado.
    """
    tipo = config.get("tipo", "telegram").lower()

    if tipo == "telegram":
        telegram_cfg = config.get("telegram", {})
        if not telegram_cfg.get("bot_token") or not telegram_cfg.get("chat_id"):
            raise ValueError("Falta bot_token o chat_id en la configuración de Telegram.")
        return TelegramNotifier(telegram_cfg["bot_token"], telegram_cfg["chat_id"])

    elif tipo == "whatsapp":
        whatsapp_cfg = config.get("whatsapp", {})
        if not whatsapp_cfg.get("phone_number") or not whatsapp_cfg.get("api_key"):
            raise ValueError("Falta phone_number o api_key en la configuración de WhatsApp.")
        return WhatsAppNotifier(whatsapp_cfg["phone_number"], whatsapp_cfg["api_key"])

    else:
        raise ValueError(f"Tipo de notificación no soportado: {tipo}")