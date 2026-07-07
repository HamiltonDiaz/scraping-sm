"""
scraper.py - Módulo de web scraping con requests
Usa peticiones HTTP directas al endpoint AJAX de JSF/PrimeFaces.
"""

import logging
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SistemaMaestroScraper:
    """Scraper para el portal de vacantes del Sistema Maestro usando requests."""

    URL_BASE = "https://sistemamaestro.mineducacion.gov.co/SistemaMaestro/"
    URL_BUSQUEDA = "https://sistemamaestro.mineducacion.gov.co/SistemaMaestro/busquedaVacantes.xhtml"

    def __init__(self, config: dict):
        self.url = config.get("url", self.URL_BUSQUEDA)
        self.timeout = config.get("timeout", 30)
        self.session = requests.Session()
        self.view_state = None
        
        # Configurar headers para simular navegador
        self.session.headers.update({
            "User-Agent": config.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })

    def iniciar(self):
        """Inicializa la sesión y obtiene el ViewState."""
        logger.info("Iniciando sesión y obteniendo ViewState...")
        
        try:
            response = self.session.get(self.url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            self.view_state = self._extraer_view_state(response.text)
            
            if not self.view_state:
                raise ValueError("No se pudo obtener el ViewState")
            
            logger.info(f"ViewState obtenido: {self.view_state[:50]}...")
            logger.info("Sesión iniciada correctamente.")
            
        except Exception as e:
            logger.error(f"Error al iniciar sesión: {e}")
            raise

    def _extraer_view_state(self, html: str) -> Optional[str]:
        """Extrae el ViewState del HTML de la página."""
        match = re.search(r'id=["\']javax\.faces\.ViewState["\'][^>]*value=["\']([^"\']+)["\']', html)
        if match:
            return match.group(1)
        
        match = re.search(r'name=["\']javax\.faces\.ViewState["\'][^>]*value=["\']([^"\']+)["\']', html)
        if match:
            return match.group(1)
        
        match = re.search(r'ViewState[^>]*value=["\']([^"\']+)["\']', html)
        if match:
            return match.group(1)
        
        return None

    def cerrar(self):
        """Cierra la sesión."""
        self.session.close()
        logger.info("Sesión cerrada.")

    def _generar_id_vacante(self, datos: dict) -> str:
        """Genera un ID único basado en los datos clave de la vacante."""
        clave = f"{datos.get('cargo', '')}|{datos.get('area', '')}|{datos.get('secretaria', '')}|{datos.get('municipio', '')}|{datos.get('zona', '')}|{datos.get('fecha_cierre', '')}"
        return hashlib.md5(clave.encode()).hexdigest()

    def _limpiar_valor(self, texto: str) -> str:
        """Limpia el texto extraído de un label, removiendo el prefijo."""
        # Remover prefijos como "Área:", "Secretaría de Educación:", etc.
        texto = re.sub(r'^[^:]+:\s*', '', texto)
        # Limpiar espacios extras
        return texto.strip()

    def aplicar_filtros(self, filtros: dict) -> str:
        """
        Aplica los filtros y retorna el HTML de resultados.
        """
        logger.info("Aplicando filtros de búsqueda...")

        # Mapeo de filtros a los nombres de los campos del formulario
        campos_filtro = {
            "secretaria": "form-busqueda:idInputSecretaria_input",
            "departamento": "form-busqueda:idInputDepartamento_input",
            "establecimiento": "form-busqueda:idInputEstablecimiento_input",
            "area": "form-busqueda:idInputArea_input",
            "tipo_priorizacion": "form-busqueda:idInputTipoPonderado_input"
        }

        # Construir payload base
        data = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "form-busqueda:idInputArea",
            "javax.faces.partial.execute": "@all",
            "javax.faces.partial.render": "accordion",
            "javax.faces.behavior.event": "change",
            "javax.faces.partial.event": "change",
            "javax.faces.ViewState": self.view_state,
            "form-busqueda": "form-busqueda",
            "form-busqueda:zoom-actual": "5",
            "form-busqueda:tabla-vacantes_rppDD": "24"
        }

        # Agregar campos de filtros vacíos
        for campo in campos_filtro.values():
            data[f"{campo}_focus"] = ""

        # Agregar valores de filtros configurados
        for clave, valor in filtros.items():
            if valor is None:
                continue
            
            campo = campos_filtro.get(clave)
            if campo:
                data[campo] = str(valor)
                logger.info(f"Filtro '{clave}' aplicado: {valor}")

        try:
            # Actualizar headers para petición AJAX
            self.session.headers.update({
                "X-Requested-With": "XMLHttpRequest",
                "Faces-Request": "partial/ajax",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            })
            
            response = self.session.post(
                self.url,
                data=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Actualizar ViewState si viene en la respuesta
            nuevo_view_state = self._extraer_view_state(response.text)
            if nuevo_view_state:
                self.view_state = nuevo_view_state
            
            logger.info("Filtros aplicados y respuesta recibida.")
            return response.text
            
        except Exception as e:
            logger.error(f"Error al aplicar filtros: {e}")
            return ""

    def extraer_vacantes(self, html_response: str) -> List[Dict]:
        """
        Extrae las vacantes del HTML de respuesta AJAX.
        La estructura usa divs con labels que contienen los datos.
        """
        logger.info("Extrayendo vacantes de la respuesta...")
        vacantes = []

        try:
            # La respuesta AJAX de JSF contiene XML con CDATA
            match = re.search(r'<update[^>]*id=["\']accordion["\'][^>]*><!\[CDATA\[(.*?)\]\]></update>', html_response, re.DOTALL)
            
            if not match:
                match = re.search(r'<update[^>]*><!\[CDATA\[(.*?)\]\]></update>', html_response, re.DOTALL)
            
            if match:
                html_content = match.group(1)
            else:
                html_content = html_response

            # Parsear HTML con BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Buscar todos los bloques de vacantes
            # Patrón: form-busqueda:tabla-vacantes:N:j_idt91
            vacantes_divs = soup.find_all("div", id=re.compile(r"form-busqueda:tabla-vacantes:\d+:j_idt91$"))
            
            logger.info(f"Se encontraron {len(vacantes_divs)} bloques de vacantes.")

            for vacante_div in vacantes_divs:
                try:
                    # Extraer todos los labels
                    labels = vacante_div.find_all("label")
                    
                    # Crear diccionario con los datos
                    vacante = {
                        "cargo": "",
                        "postulados": "",
                        "tipo_priorizacion": "",
                        "fecha_cierre": "",
                        "area": "",
                        "secretaria": "",
                        "zona": "",
                        "departamento": "",
                        "municipio": ""
                    }
                    
                    # Mapear labels a campos según su ID
                    for label in labels:
                        label_id = label.get("id", "")
                        texto = label.get_text(strip=True)
                        
                        # Extraer solo el valor (remover prefijo)
                        valor = self._limpiar_valor(texto)
                        
                        # Mapear según el ID del label
                        if "j_idt93" in label_id:
                            vacante["cargo"] = valor
                        elif "j_idt94" in label_id:
                            vacante["postulados"] = valor
                        elif "j_idt95" in label_id:
                            vacante["tipo_priorizacion"] = valor
                        elif "j_idt96" in label_id:
                            vacante["fecha_cierre"] = valor
                        elif "j_idt99" in label_id:
                            vacante["area"] = valor
                        elif "j_idt100" in label_id:
                            vacante["secretaria"] = valor
                        elif "j_idt101" in label_id:
                            vacante["zona"] = valor
                        elif "j_idt102" in label_id:
                            vacante["departamento"] = valor
                        elif "j_idt103" in label_id:
                            vacante["municipio"] = valor

                    # Extraer enlace (si existe)
                    enlace_tag = vacante_div.find("a", href=True)
                    if enlace_tag:
                        href = enlace_tag.get("href", "")
                        if href and href != "#" and not href.startswith("http"):
                            href = urljoin(self.URL_BASE, href)
                        vacante["enlace"] = href if href != "#" else self.url
                    else:
                        vacante["enlace"] = self.url

                    # Generar ID único
                    vacante["id"] = self._generar_id_vacante(vacante)
                    vacante["fecha_detectada"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    vacantes.append(vacante)

                except Exception as e:
                    logger.warning(f"Error al procesar una vacante: {e}")
                    continue

            logger.info(f"Se extrajeron {len(vacantes)} vacantes válidas.")

        except Exception as e:
            logger.error(f"Error al extraer vacantes: {e}")

        return vacantes

    def obtener_nuevas_vacantes(self, filtros: dict, db) -> List[Dict]:
        """
        Flujo completo: aplica filtros, extrae y filtra nuevas.
        """
        try:
            html_response = self.aplicar_filtros(filtros)
            
            if not html_response:
                return []

            vacantes = self.extraer_vacantes(html_response)

            nuevas = []
            for vacante in vacantes:
                if not db.existe_vacante(vacante["id"]):
                    nuevas.append(vacante)

            logger.info(f"Vacantes nuevas detectadas: {len(nuevas)}")
            return nuevas

        except Exception as e:
            logger.error(f"Error en el flujo de obtención: {e}", exc_info=True)
            return []