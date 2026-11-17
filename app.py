import os
import requests
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURACIÓN DE CREDENCIALES Y URLS ---
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "FRUMATCH_TOKEN_SECRETO_2026")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "TOKEN_EN_RENDER")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "1458999290628642")
GOOGLE_SCRIPT_URL = os.environ.get("GOOGLE_SCRIPT_URL", "URL_EN_RENDER")
usuarios_memoria = {}

FRUTAS = {
    "1": "Banano",
    "2": "Aguacate",
    "3": "Fresa"
}

UNIDADES = {
    "1": "Kg",
    "2": "Lb"
}

TIPOS_SALIDA = {
    "1": "Venta",
    "2": "Merma"
}

# --- FUNCIONES DE COMUNICACIÓN CON GOOGLE SHEETS ---

def llamar_apps_script(payload):
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error comunicando con Sheets: {e}")
        return None

def responder_whatsapp(numero_destino, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto}
    }
    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Error al responder a WhatsApp: {e}")

# --- RUTAS DE FLASK (WEBHOOK) ---

@app.route("/", methods=["GET"])
def home():
    return "Servidor FRUMATCH activo 24/7", 200

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        return challenge, 200
    return "Token de verificación incorrecto", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    body = request.get_json()

    try:
        if body.get("entry") and body["entry"][0].get("changes"):
            value = body["entry"][0]["changes"][0]["value"]
            if "messages" in value:
                mensaje_obj = value["messages"][0]
                numero_remitente = mensaje_obj["from"]
                texto_recibido = mensaje_obj.get("text", {}).get("body", "").strip()
                texto_lower = texto_recibido.lower()

                # --- COMANDO DE DEMOSTRACIÓN EN VIVO DE ALERTA ---
                if texto_lower in ["alerta", "alertas", "demo"]:
                    res = llamar_apps_script({"accion": "alertas"})
                    criticos = res.get("criticos", []) if res else []

                    if not criticos:
                        msg = (
                            "✅ *Sin alertas críticas*\n\n"
                            "Todos tus lotes activos tienen más de 2 días de vida útil.\n\n"
                            "Escribe *inicio* para volver al menú."
                        )
                        usuarios_memoria[numero_remitente] = {"estado": "INICIO"}
                    else:
                        lista = ""
                        for c in criticos:
                            lista += f" • *{c['fruta']}* ({c['cantidad']} {c['unidad']}) - Lote `{c['id_lote']}` | Vence en *{c['dias_restantes']} día(s)*\n"

                        msg = (
                            "⚠️ *ALERTA DE MADUREZ FRUMATCH*\n\n"
                            "Los siguientes lotes entraron en zona crítica de maduración (≤ 2 días):\n\n"
                            f"{lista}\n"
                            "¿Deseas publicarlos en oferta de liquidación rápida para compradores aliados?\n\n"
                            "1️⃣ Sí, publicar ofertas ahora 🤝\n"
                            "2️⃣ No, volver al menú principal"
                        )
                        usuarios_memoria[numero_remitente] = {"estado": "ALERTA_DECISION"}

                    responder_whatsapp(numero_remitente, msg)
                    return "OK", 200

                # --- REINICIO AL MENÚ PRINCIPAL ---
                if texto_lower in ["hola", "inicio", "menu", "menú", "0"] or numero_remitente not in usuarios_memoria:
                    usuarios_memoria[numero_remitente] = {"estado": "INICIO"}

                    menu_principal = (
                        "¡Hola! Soy *FRU*, tu asistente inteligente de *FRUMATCH* 🍎🍌\n"
                        "Te ayudo a controlar la maduración de tu inventario y reducir la merma.\n\n"
                        "¿Qué acción deseas realizar hoy?\n\n"
                        "1️⃣ Registrar inventario de fruta\n"
                        "2️⃣ Consultar nivel de madurez o caducidad\n"
                        "3️⃣ Registrar salida (Venta o Merma)\n\n"
                        "👉 Responde con el número 1, 2 o 3."
                    )
                    responder_whatsapp(numero_remitente, menu_principal)
                    return "OK", 200

                estado_actual = usuarios_memoria[numero_remitente].get("estado")

                # --- DECISIÓN DESDE ALERTA (MATCH) ---
                if estado_actual == "ALERTA_DECISION":
                    if texto_lower in ["1", "si", "sí"]:
                        res = llamar_apps_script({"accion": "publicar_ofertas"})
                        publicados = res.get("publicados", []) if res else []

                        if publicados:
                            detalle = "\n".join([f" • {p}" for p in publicados])
                            msg = (
                                "🤝 *¡Ofertas publicadas en FRUMATCH!*\n\n"
                                "Los siguientes lotes quedaron activos en el canal de liquidación para compradores aliados:\n\n"
                                f"{detalle}\n\n"
                                "Escribe *inicio* para realizar otra acción."
                            )
                        else:
                            msg = "⚠️ No se encontraron lotes críticos pendientes por publicar.\n\nEscribe *inicio* para volver al menú."

                        usuarios_memoria[numero_remitente] = {"estado": "INICIO"}
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        usuarios_memoria[numero_remitente] = {"estado": "INICIO"}
                        responder_whatsapp(numero_remitente, "Entendido, no se publicaron ofertas. Escribe *inicio* para ver el menú.")
                    return "OK", 200

                # --- MENÚ PRINCIPAL ---
                if estado_actual == "INICIO":
                    if texto_recibido == "1":
                        usuarios_memoria[numero_remitente]["estado"] = "REG_ELIGIENDO_FRUTA"
                        msg = (
                            "Excelente. ¿Qué fruta vas a registrar hoy? 📝\n\n"
                            "1️⃣ Banano 🍌\n"
                            "2️⃣ Aguacate 🥑\n"
                            "3️⃣ Fresa 🍓\n\n"
                            "👉 Responde con 1, 2 o 3."
                        )
                        responder_whatsapp(numero_remitente, msg)
                    elif texto_recibido == "2":
                        usuarios_memoria[numero_remitente]["estado"] = "CON_ELIGIENDO_FRUTA"
                        msg = (
                            "Excelente. ¿Qué fruta deseas consultar? 🔍\n\n"
                            "1️⃣ Banano 🍌\n"
                            "2️⃣ Aguacate 🥑\n"
                            "3️⃣ Fresa 🍓\n\n"
                            "👉 Responde con 1, 2 o 3."
                        )
                        responder_whatsapp(numero_remitente, msg)
                    elif texto_recibido == "3":
                        usuarios_memoria[numero_remitente]["estado"] = "SAL_ELIGIENDO_FRUTA"
                        msg = (
                            "Cierre de inventario. ¿De qué fruta vas a reportar salida? 📉\n\n"
                            "1️⃣ Banano 🍌\n"
                            "2️⃣ Aguacate 🥑\n"
                            "3️⃣ Fresa 🍓\n\n"
                            "👉 Responde con 1, 2 o 3."
                        )
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(numero_remitente, "👉 Responde con el número 1, 2 o 3.")

                # --- FLUJO 1: REGISTRO ---
                elif estado_actual == "REG_ELIGIENDO_FRUTA":
                    if texto_recibido in FRUTAS:
                        fruta = FRUTAS[texto_recibido]
                        usuarios_memoria[numero_remitente]["fruta"] = fruta
                        usuarios_memoria[numero_remitente]["estado"] = "REG_ELIGIENDO_UNIDAD"
                        msg = (
                            f"Perfecto. ¿En qué unidad registrarás el lote de {fruta}?\n\n"
                            "1️⃣ Kilos (Kg)\n"
                            "2️⃣ Libras (Lb)\n\n"
                            "👉 Responde con 1 o 2."
                        )
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(numero_remitente, "👉 Responde con 1, 2 o 3.")

                elif estado_actual == "REG_ELIGIENDO_UNIDAD":
                    if texto_recibido in UNIDADES:
                        unidad = UNIDADES[texto_recibido]
                        usuarios_memoria[numero_remitente]["unidad"] = unidad
                        usuarios_memoria[numero_remitente]["estado"] = "REG_INGRESANDO_CANTIDAD"
                        msg = (
                            f"Entendido ({unidad}).\n\n"
                            "¿Qué cantidad deseas registrar? 🔢\n\n"
                            "👉 Escribe solo el número (usa el punto '.' para decimales, Ej: 15 o 20.5)"
                        )
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(numero_remitente, "👉 Responde con 1 o 2.")

                elif estado_actual == "REG_INGRESANDO_CANTIDAD":
                    cantidad_limpia = texto_recibido.replace(",", ".")

                    if cantidad_limpia.replace(".", "", 1).isdigit() and float(cantidad_limpia) > 0:
                        memoria = usuarios_memoria[numero_remitente]
                        fruta = memoria.get("fruta", "Fruta")
                        unidad = memoria.get("unidad", "Kg")

                        res = llamar_apps_script({
                            "accion": "registrar",
                            "fruta": fruta,
                            "cantidad": cantidad_limpia,
                            "unidad": unidad
                        })

                        if res and res.get("status") == "success":
                            msg = (
                                f"¡Listo! Se registraron exitosamente {cantidad_limpia} {unidad} de {fruta} en el inventario.\n\n"
                                f"Escribe *inicio* para realizar otra acción."
                            )
                        else:
                            msg = "❌ Error al guardar en el inventario. Escribe *inicio* para intentar nuevamente."

                        usuarios_memoria[numero_remitente] = {"estado": "INICIO"}
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(
                            numero_remitente,
                            "👉 Escribe solo el número utilizando punto '.' para los decimales (Ej: 15 o 20.5)"
                        )

                # --- FLUJO 2: CONSULTA DE MADUREZ Y CADUCIDAD ---
                elif estado_actual == "CON_ELIGIENDO_FRUTA":
                    if texto_recibido in FRUTAS:
                        fruta_seleccionada = FRUTAS[texto_recibido]
                        responder_whatsapp(numero_remitente, f"Consultando inventario de {fruta_seleccionada}...")

                        res = llamar_apps_script({"accion": "consultar", "fruta": fruta_seleccionada})
                        lotes = res.get("lotes", []) if res and res.get("status") == "success" else []

                        if not lotes:
                            msg = (
                                f"No hay inventario activo de {fruta_seleccionada}.\n\n"
                                f"No se encontraron lotes registrados de esta fruta en Google Sheets.\n\n"
                                f"Escribe *inicio* para volver al menú."
                            )
                        else:
                            msg = f"*REPORTE DE MADUREZ: {fruta_seleccionada.upper()}*\n\n"
                            for index, lote in enumerate(lotes, 1):
                                msg += (
                                    f"*Lote {index} ({lote['id_lote']})*\n"
                                    f" • Cantidad: {lote['cantidad']} {lote['unidad']}\n"
                                    f" • Registrado el: {lote['fecha_registro']}\n"
                                    f" • Estado Agronómico: *{lote['estado_maduracion']}*\n"
                                    f" • Días de vida útil restante: *{lote['dias_restantes']} día(s)*\n\n"
                                )
                            msg += "Escribe *inicio* para realizar otra acción."

                        usuarios_memoria[numero_remitente] = {"estado": "INICIO"}
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(numero_remitente, "👉 Responde con 1, 2 o 3.")

                # --- FLUJO 3: REGISTRO DE SALIDA (VENTA O MERMA) ---
                elif estado_actual == "SAL_ELIGIENDO_FRUTA":
                    if texto_recibido in FRUTAS:
                        fruta = FRUTAS[texto_recibido]
                        usuarios_memoria[numero_remitente]["fruta"] = fruta
                        usuarios_memoria[numero_remitente]["estado"] = "SAL_ELIGIENDO_TIPO"
                        msg = (
                            f"Entendido ({fruta}). ¿Cuál fue el motivo de la salida?\n\n"
                            "1️⃣ Venta (Fruta vendida) 💰\n"
                            "2️⃣ Merma (Fruta dañada o pérdida) 🗑️\n\n"
                            "👉 Responde con 1 o 2."
                        )
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(numero_remitente, "👉 Responde con 1, 2 o 3.")

                elif estado_actual == "SAL_ELIGIENDO_TIPO":
                    if texto_recibido in TIPOS_SALIDA:
                        tipo_salida = TIPOS_SALIDA[texto_recibido]
                        usuarios_memoria[numero_remitente]["tipo_salida"] = tipo_salida
                        usuarios_memoria[numero_remitente]["estado"] = "SAL_ELIGIENDO_UNIDAD"
                        msg = (
                            f"Motivo: *{tipo_salida}*.\n\n"
                            "¿En qué unidad vas a reportar la salida?\n\n"
                            "1️⃣ Kilos (Kg)\n"
                            "2️⃣ Libras (Lb)\n\n"
                            "👉 Responde con 1 o 2."
                        )
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(numero_remitente, "👉 Responde con 1 o 2.")

                elif estado_actual == "SAL_ELIGIENDO_UNIDAD":
                    if texto_recibido in UNIDADES:
                        unidad = UNIDADES[texto_recibido]
                        usuarios_memoria[numero_remitente]["unidad"] = unidad
                        usuarios_memoria[numero_remitente]["estado"] = "SAL_INGRESANDO_CANTIDAD"
                        msg = (
                            f"Entendido ({unidad}).\n\n"
                            "¿Qué cantidad salió del inventario? 🔢\n\n"
                            "👉 Escribe solo el número (usa el punto '.' para decimales, Ej: 10 o 12.5)"
                        )
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(numero_remitente, "👉 Responde con 1 o 2.")

                elif estado_actual == "SAL_INGRESANDO_CANTIDAD":
                    cantidad_limpia = texto_recibido.replace(",", ".")

                    if cantidad_limpia.replace(".", "", 1).isdigit() and float(cantidad_limpia) > 0:
                        memoria = usuarios_memoria[numero_remitente]
                        fruta = memoria.get("fruta", "Fruta")
                        tipo_salida = memoria.get("tipo_salida", "Venta")
                        unidad = memoria.get("unidad", "Kg")

                        responder_whatsapp(numero_remitente, f"Actualizando inventario de {fruta} por FEFO...")
                        resultado = llamar_apps_script({
                            "accion": "salida",
                            "fruta": fruta,
                            "tipo_salida": tipo_salida,
                            "cantidad": cantidad_limpia,
                            "unidad": unidad
                        })

                        if resultado and resultado.get("status") == "success":
                            afectados = resultado.get("lotes_afectados", [])
                            faltante = resultado.get("faltante_kg", 0)

                            if not afectados:
                                msg = (
                                    f"⚠️ No hay inventario activo de {fruta} para descontar.\n\n"
                                    f"Escribe *inicio* para volver al menú."
                                )
                            else:
                                detalle_lotes = "\n".join([f" • {item}" for item in afectados])
                                msg = (
                                    f"✅ *Salida registrada ({tipo_salida})*\n"
                                    f"Se descontaron {cantidad_limpia} {unidad} de {fruta} del inventario más antiguo:\n\n"
                                    f"{detalle_lotes}\n"
                                )
                                if faltante > 0:
                                    msg += f"\n⚠️ Nota: Faltaron {faltante} Kg por descontar porque no había más inventario registrado.\n"
                                msg += "\nEscribe *inicio* para realizar otra acción."
                        else:
                            msg = "❌ Error al actualizar el inventario. Escribe *inicio* para intentar nuevamente."

                        usuarios_memoria[numero_remitente] = {"estado": "INICIO"}
                        responder_whatsapp(numero_remitente, msg)
                    else:
                        responder_whatsapp(
                            numero_remitente,
                            "👉 Escribe solo el número utilizando punto '.' para los decimales (Ej: 10 o 12.5)"
                        )

    except Exception as e:
        print(f"Error procesando mensaje: {e}")

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)