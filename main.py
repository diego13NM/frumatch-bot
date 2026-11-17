import requests

# Configuración de URLs y credenciales
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx0M1KRzACthrtiI8SK-tzfeRj-SeoEACULnKjj8h9YPSPeiqyz0e3h1TYWgwhT3MA/exec"
PHONE_NUMBER_ID = "1458999290628642"
ACCESS_TOKEN = "EAANpPiPVMPkBS3MosiVUxiWXCoKZBQn0ZCHMgnaNsxBqXsxF01QaTDmnIVR6iwqjRTjZCoKZBYWv2SCNzK1qrJLBZBfZBnKQFZATtVUl4bGX8Op19f3UfzzuFon362nYB9hLlh4G30RF67ETH6hDofVAqUPP8e81rCZAovPJN3rWOlvXMTGPPgbUZBTALjmGt11sdXkQuZAvwZA77VU2akzZCfEUGHGQjD5CZCjaLRbQqjJEkNMcVKqWmZCm2xV8dZBPzHNRI3VjRr6cekwgzGnQzIrb9Ia0CNqNXKakFCDDfZCqtwZDZD"

def guardar_lote_inventario(id_lote, fruta, cantidad_kg, estado_maduracion, fecha_registro, fecha_caducidad):
    """Envía un registro de inventario a Google Sheets vía Apps Script"""
    payload = {
        "id_lote": id_lote,
        "fruta": fruta,
        "cantidad_kg": cantidad_kg,
        "estado_maduracion": estado_maduracion,
        "fecha_registro": fecha_registro,
        "fecha_caducidad": fecha_caducidad
    }
    
    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ Lote {id_lote} ({fruta}) guardado exitosamente en Google Sheets.")
        else:
            print(f"❌ Error al guardar en Sheets: Código {response.status_code}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    print("Enviando registro de prueba a la base de datos...")
    guardar_lote_inventario(
        id_lote="LOTE-001",
        fruta="Banano",
        cantidad_kg=50,
        estado_maduracion="Pintón",
        fecha_registro="2026-03-30",
        fecha_caducidad="2026-04-05"
    )