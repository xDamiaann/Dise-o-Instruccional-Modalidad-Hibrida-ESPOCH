import os
import time
import google.generativeai as genai

# Configuración de la API de Gemini
genai.configure(api_key="AIzaSyA7bVH2D0VQfCj7ansRYiXPqSro53Ar2xM")
#AIzaSyAgJROEiX5C7SFs_WME3qAg6Kv5Y5t9n-c
#AIzaSyAgJROEiX5C7SFs_WME3qAg6Kv5Y5t9n-


# Configuración del modelo
generation_config = {
  "temperature": 0.1,
  "top_p": 0.2,
  "top_k": 0,
  "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

def leer_txt(ruta_archivo):
    with open(ruta_archivo, 'r', encoding='utf-8') as archivo_txt:
        texto = archivo_txt.read()
    return texto

def iniciar_conversacion(ruta_archivo):
    texto_txt = leer_txt(ruta_archivo)

    try:
        convo = model.start_chat(history=[])
        convo.send_message(texto_txt)
        return convo
    except genai.api_core.exceptions.InternalServerError as e:
        print("Se produjo un error interno del servidor:", e)
        print("Intentando nuevamente en 5 segundos...")
        time.sleep(5)


def mejorar_texto(texto):

    prompt = f"Crea una actividad breve basada en el siguiente texto: {texto}. Devuelve el resultado en el siguiente formato: Actividad: [Nombre de la actividad] Cómo: [Instrucciones breves para realizar la actividad]"

    try:
        convo = model.start_chat(history=[])
        response = convo.send_message(prompt) 
        respuesta = response.text.strip().replace("*", "")
        return respuesta
    except genai.api_core.exceptions.InternalServerError as e:
        print("Se produjo un error interno del servidor:", e)
        return "Error al mejorar el texto. Inténtelo de nuevo más tarde."