import os
import requests
import smtplib
import datetime
from datetime import timedelta
from email.mime.text import MIMEText

URL = "https://www.juntadeandalucia.es/justicia/citaprevia/cita/calendarioServicio"
PARAMS = {
    "idServicio": "59",
    "numSolicitantesCalendario": "1",
    "buscarPrimerHuecoLibre": "true",
    "idCliente": "4"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.juntadeandalucia.es/justicia/citaprevia/?idCliente=4"
}

def check_citas_dinamico():
    print("Consultando API para próximas fechas...")
    disponibles = []
    
    # Revisa los próximos 60 días, pero se detiene si hay un error
    for i in range(60):
        fecha_a_revisar = datetime.date.today() + timedelta(days=i)
        PARAMS["fecha"] = str(fecha_a_revisar)
        
        r = requests.get(URL, params=PARAMS, headers=HEADERS)
        
        try:
            data = r.json()
        except Exception as e:
            print(f"Error al parsear JSON para {fecha_a_revisar}:", e)
            print("Respuesta:", r.text)
            break # Rompe el bucle si hay un error de JSON
        
        # Si el resultado es ERROR, significa que no hay más fechas disponibles
        if data.get('result') == 'ERROR':
            print(f"La API ha dejado de devolver datos. Búsqueda finalizada en {fecha_a_revisar}.")
            break
        
        # Si el resultado es OK, procede con la lógica normal
        if "calendario" in data and "dias" in data["calendario"]:
            for d in data["calendario"]["dias"]:
                franjas = d.get("franjas")
                if franjas:
                    huecos_libres = [f for f in franjas if f.get("huecosLibres", 0) > 0]
                    if huecos_libres:
                        disponibles.append((d["fecha"], huecos_libres))
        else:
            print(f"Estructura inesperada para {fecha_a_revisar}:", data)
    return disponibles

def send_email(citas):
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASS = os.environ.get("SMTP_PASS")
    TO_EMAIL = os.environ.get("TO_EMAIL")

    if not SMTP_USER or not SMTP_PASS or not TO_EMAIL:
        print("ERROR: Falta alguna variable de entorno SMTP_USER/SMTP_PASS/TO_EMAIL")
        return

    msg_text = "¡Hay citas disponibles!\n\n"
    for fecha, franjas in citas:
        franjas_str = [f"{f['horaInicio']} - {f['horaFin']} ({f['huecosLibres']} libres)" for f in franjas]
        msg_text += f"- {fecha}: {', '.join(franjas_str)}\n"

    msg = MIMEText(msg_text)
    msg["Subject"] = "Citas disponibles Registro Civil Málaga"
    msg["From"] = SMTP_USER
    msg["To"] = TO_EMAIL

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [TO_EMAIL], msg.as_string())
        print("Correo enviado correctamente.")
    except Exception as e:
        print("Error al enviar correo:", e)

if __name__ == "__main__":
    citas = check_citas_dinamico()
    if citas:
        print("Citas con huecos libres encontradas:", citas)
        send_email(citas)
    else:
        print("No hay citas disponibles con huecos libres.")
