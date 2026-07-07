"""debug_ajax.py - Ver qué devuelve la petición AJAX"""

import requests
import re

url = "https://sistemamaestro.mineducacion.gov.co/SistemaMaestro/busquedaVacantes.xhtml"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
})

# Obtener ViewState
response = session.get(url, timeout=30)
match = re.search(r'id=["\']javax\.faces\.ViewState["\'][^>]*value=["\']([^"\']+)["\']', response.text)
view_state = match.group(1) if match else None

print(f"✓ ViewState obtenido: {view_state[:50]}...")

# Hacer petición AJAX
session.headers.update({
    "X-Requested-With": "XMLHttpRequest",
    "Faces-Request": "partial/ajax",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
})

data = {
    "javax.faces.partial.ajax": "true",
    "javax.faces.source": "form-busqueda:idInputArea",
    "javax.faces.partial.execute": "@all",
    "javax.faces.partial.render": "accordion",
    "javax.faces.behavior.event": "change",
    "javax.faces.partial.event": "change",
    "javax.faces.ViewState": view_state,
    "form-busqueda": "form-busqueda",
    "form-busqueda:zoom-actual": "5",
    "form-busqueda:tabla-vacantes_rppDD": "24"
}

response = session.post(url, data=data, timeout=30)

print(f"✓ Status: {response.status_code}")
print(f"✓ Content-Type: {response.headers.get('Content-Type')}")
print(f"✓ Tamaño respuesta: {len(response.text)} bytes\n")

# Guardar respuesta completa
with open("debug_ajax_response.xml", "w", encoding="utf-8") as f:
    f.write(response.text)

print("✓ Respuesta guardada en: debug_ajax_response.xml\n")

# Buscar patrones de vacantes
print("🔍 Buscando patrones de vacantes en la respuesta...")

# Buscar si hay "tabla-vacantes" en la respuesta
if "tabla-vacantes" in response.text:
    print("✓ Encontrado 'tabla-vacantes' en la respuesta")
    
    # Contar cuántas veces aparece
    count = response.text.count("tabla-vacantes:")
    print(f"  → 'tabla-vacantes:' aparece {count} veces")
else:
    print("✗ NO se encontró 'tabla-vacantes' en la respuesta")

# Buscar si hay "j_idt91" (patrón de bloques de vacantes)
if "j_idt91" in response.text:
    print("✓ Encontrado 'j_idt91' en la respuesta")
    count = response.text.count("j_idt91")
    print(f"  → 'j_idt91' aparece {count} veces")
else:
    print("✗ NO se encontró 'j_idt91' en la respuesta")

# Mostrar estructura de la respuesta
print("\n📋 Estructura de la respuesta:")
print("=" * 60)

# Buscar tags <update>
updates = re.findall(r'<update[^>]*id=["\']([^"\']+)["\']', response.text)
print(f"Tags <update> encontrados: {len(updates)}")
for update_id in updates[:10]:
    print(f"  - {update_id}")

# Mostrar primeros 1000 caracteres
print("\n📝 Primeros 1000 caracteres de la respuesta:")
print("=" * 60)
print(response.text[:1000])