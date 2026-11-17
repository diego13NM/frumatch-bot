from pyngrok import ngrok
import time

# Crear el túnel apuntando al puerto 5000 donde corre Flask
public_url = ngrok.connect(5000).public_url

print("\n" + "="*50)
print(f"🔗 URL Pública de ngrok: {public_url}")
print("="*50 + "\n")
print("Mantén este script corriendo junto con app.py para recibir mensajes.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Túnel finalizado.")