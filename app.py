from flask import request, jsonify, redirect
from flask import Flask, render_template, request, jsonify, send_file, redirect, session, url_for
from gemini import iniciar_conversacion
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import psycopg2
import os
import fitz  # Importar PyMuPDF
import re
import json
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer
from gemini import mejorar_texto as mejorar_texto_api

app = Flask(__name__)

# Configuración de la base de datos PostgreSQL
DATABASE_URL = "postgresql://postgres:12345@localhost:5432/chat"
conn = psycopg2.connect(DATABASE_URL, sslmode='disable')
cursor = conn.cursor()

# Generar una clave secreta aleatoria
app.secret_key = os.urandom(24)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        clave = request.form['clave']

        # Insertar datos en la base de datos
        cursor.execute("INSERT INTO usuarios (nombre, apellido, correo, clave) VALUES (%s, %s, %s, %s)",
                       (nombre, apellido, correo, clave))
        conn.commit()

        # Redirigir al inicio después de registrar
        return render_template('index.html')

    return render_template('registro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        clave = request.form['clave']

        # Verificar las credenciales en la base de datos
        cursor.execute(
            "SELECT * FROM usuarios WHERE correo = %s AND clave = %s", (correo, clave))
        usuario = cursor.fetchone()

        if usuario:
            # Establecer la sesión del usuario
            # Guardar el ID del usuario en la sesión
            session['usuario'] = usuario[0]
            # Si las credenciales son válidas, redirigir al chat
            # return redirect('/chat')
            return redirect('/SubirArchivo')

        else:
            # Si las credenciales son inválidas, mostrar un mensaje de error
            error = "Correo o contraseña incorrectos. Inténtalo de nuevo."
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/SubirArchivo')
def subirArchivo():

    # Abrir el archivo contenido.txt en modo escritura para truncar su contenido
    contenido_file = 'contenido.txt'
    with open(contenido_file, 'w') as file:
        file.truncate(0)  # Truncar el contenido del archivo

    contenido_file2 = 'planificacion.txt'
    with open(contenido_file2, 'w') as file:
        file.truncate(0)  # Truncar el contenido del archivo

    return render_template('SubirArchivo.html')


@app.route('/logout')
def logout():
    # Eliminar la sesión del usuario al cerrar sesión
    session.pop('usuario', None)
    # Redirigir al inicio después de cerrar sesión
    # Abrir el archivo contenido.txt en modo escritura para truncar su contenido
    contenido_file = 'contenido.txt'
    with open(contenido_file, 'w') as file:
        file.truncate(0)  # Truncar el contenido del archivo

    return redirect(url_for('index'))

# Función para verificar si el usuario ha iniciado sesión


def verificar_sesion():
    return 'usuario' in session


conversacion = None
conversacionSilabo = None
respuestas = []
respuestasDisenio = []
respuestas_finales = []
opcion_seleccionada = None
nivel_formacion_opcion = None
nivel_formacion_opciones = ["1", "2", "3"]


@app.route('/chat')
def chat():
    if not verificar_sesion():  # Verificar si el usuario ha iniciado sesión
        # Redirigir al usuario a la página de inicio de sesión si no ha iniciado sesión
        return redirect(url_for('login'))

    global conversacion, preguntas, preguntasDisenio, respuestas, respuestasDisenio, respuestas_finales, opcion_seleccionada, nivel_formacion_opcion, nivel_formacion_opciones, conversacionSilabo
    global conversacionPlanificacion

    preguntas = [
        "Responsable/s del Proyecto:",
        "Datos de la Institución:",
        "Aval del Consejo de Aseguramiento de la Calidad de la Educación Superior (CACES) para las IES que no cuenten con el estatus de acreditadas:",
        "Datos personales del rector o rectora:",
        "¿El proyecto curricular es experimental o innovador? Si/No:",
        "Nivel de formación:",
        "Modalidad de estudios/aprendizaje (Art. 54 del RRA)",
        "Descripción de la ejecución de la modalidad (Arts. 55, 56, 57, 58, 59 y 63 del RRA según corresponda):",
        "Itinerario/Mención (Arts.16, 21 y 119 del RRA):",
        "Perfil de ingreso:",
        "Perfil de egreso:",
        "Requisito de aprendizaje de una segunda lengua (Art. 64 del RRA):",
        "Lugar (es) de ejecución de la carrera o programa:",
        "Número de estudiantes por cohorte:",
        "Número de períodos académicos (Arts. 10, 15, 19, 113, 114, 117 y 118 del RRA):",
        "Total de créditos de la carrera o programa (Arts. 9, 19, 117 y 118 del RRA):",
        "Total de créditos del aprendizaje en contacto con el docente (Para especializaciones en el campo de conocimiento específico de la salud, Art. 115 del RRA):",
        "Total de créditos del aprendizaje autónomo (Para especializaciones en el campo de conocimiento específico de la salud, Art. 115 del RRA):",
        "Total de créditos del aprendizaje práctico-experimental (Para especializaciones en el campo de conocimiento específico de la salud, Art. 115 del RRA):",
        "Total de horas/créditos de prácticas preprofesionales (Arts. 43 y 121 del RRA para tercer nivel):",
        "Total de horas/créditos de prácticas profesionales (Para especializaciones en el campo de conocimiento específico de Salud, Art. 118 y 124 del RRA):",
        "Total de horas de las prácticas de servicio comunitario (Art. 43 del RRA para tercer nivel):",
        ""
    ]

    preguntasDisenio = [
        "Audiencia objetivo:",
        "Edades:",
        "Nivel de instrucción mínimo:",
        "Nacionalidad:",
        "Acceso a internet:",
        "Acceso a dispositivos tecnológicos:",
        "Motivación:",
        "Estilo de aprendizaje:",
        "Dosificación de la distribución de los componentes del proceso enseñanza aprendizaje:",
        "Objetivos de las Unidades",
        "",
        "",
    ]

    respuestas = []
    respuestasDisenio = []
    respuestas_finales = []
    opcion_seleccionada = None
    nivel_formacion_opcion = None
    nivel_formacion_opciones = ["1", "2", "3"]

    global temas
    conversacion = iniciar_conversacion("RRA.txt")
    conversacionSilabo = iniciar_conversacion("contenido.txt")

    response = conversacionSilabo.send_message(
        "Extrae todos los temas del silabo y enuméralos separados por un punto y coma (;). solo dame la respuesta con los temas no incluyas nada mas")

    temas = response.text.strip().replace(
        "*", "").split(";")  # Convierte la cadena en una lista

    # Envías el mensaje para obtener el total de horas
    creditos_response = conversacionSilabo.send_message(
        "Dime los creditos del silabo. La respuesta debe ser solo el número, sin texto adicional.")
    creditos_silabo = creditos_response.text.strip().replace("*", "")

    # total_horas_response = conversacionSilabo.send_message("Si los créditos de la materia son igual a 2 créditos, el total de horas será de 64 horas. Si los créditos de la materia son igual a 3 créditos, el total de horas será de 96 horas. La respuesta debe ser solo el número de horas, sin texto adicional.")
    # total_horas_silabo = total_horas_response.text.strip().replace("*", "")

    # response1 = conversacion.send_message("Dame el 80 por ciento de " + total_horas_silabo + " y la respuesta divide para 16. La respuesta debe ser solo el número, sin texto adicional.")
    # componentePE = response1.text.strip().replace("*", "")

    # response2 = conversacion.send_message("Dame el 20 por ciento de " + total_horas_silabo + " y la respuesta divide para 16. La respuesta debe ser solo el número, sin texto adicional.")
    # componenteCD = response2.text.strip().replace("*", "")

    return render_template('chat.html', temas=temas, creditos_silabo=creditos_silabo)


@app.route('/chat', methods=['POST'])
def handle_chat_post():

    global respuestas, conversacion, opcion_seleccionada, respuestas_finales, nivel_formacion_opcion, nivel_formacion_opciones, modalidad, carrera, nivel_formacion

    global conversacionSilabo, materia

    user_input = request.form['user_input']
    mensaje_pantalla = ""

    if opcion_seleccionada is None:
        if user_input == "1":

            respuestas.clear()
            opcion_seleccionada = 1
            mensaje_pantalla = 'Ingrese el nombre o los nombres que estaran a cargo del proyecto:'

        elif user_input == "2":

            respuestasDisenio.clear()
            mensaje_pantalla = 'Ingrese la audiencia objetivo <br> <p class="ejemplo">Ejemplo: Estudiantes de los primeros niveles de las carreras de la ESPOCH.</p>'

            opcion_seleccionada = 2

        elif user_input == "3":
            mensaje_pantalla = "Bienvenido a la opción 3: Preguntar al modelo"
        else:
            mensaje_pantalla = """Opción no válida. Por favor, selecciona: <br><br>
<button class="btn btn-primary" onclick="seleccionarOpcion(1)">1. Creación de carreras</button>
<button class="btn btn-primary" onclick="seleccionarOpcion(2)">2. Diseño Instruccional</button>
<button class="btn btn-primary" onclick="seleccionarOpcion(3)">3. Preguntar al modelo</button>"""

    elif opcion_seleccionada == 1:

        if len(respuestas) == len(preguntas) - 23:

            responsables = user_input
            response = conversacion.send_message(
                "Corrige faltas ortograficas y separa cada nombre completo con una coma, solo da de respuesta los nombres corregidos con la coma sin texto adicional, los nombres son: " + responsables)
            respuesta_ia = response.text.strip()
            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 22:
            response = conversacion.send_message(
                "Solo responde el nombre de la Institucion nada mas")
            respuesta_ia = response.text.strip()
            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 21:
            response = "La Espoch como Instituto Superior Cuenta con el estado de acreditadas"
            respuesta_ia = response.strip()
            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 20:
            response = conversacion.send_message(
                "Datos personales del rector o rectora")
            respuesta_ia = response.text.strip()
            respuestas.append(respuesta_ia)

            # Primera respuesta con la pregunta y la respuesta
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia} <br><strong>Gemini: </strong>{preguntas[len(respuestas)]} <br>1. Si <br>2. No <br><strong>Gemini: Seleccione una: </strong>"

        elif len(respuestas) == len(preguntas) - 19:
            if user_input == "1":
                respuestas.append("Sí")
                mensaje_pantalla += f"{preguntas[len(respuestas)]} <br>"
                mensaje_pantalla += "1. Educación superior no universitaria<br>"
                mensaje_pantalla += "2. Educación universitaria de tercer nivel o de grado<br>"
                mensaje_pantalla += "3. Educación universitaria de cuarto nivel o de posgrado<br>"
            elif user_input == "2":
                respuestas.append("No")
                mensaje_pantalla += f"{preguntas[len(respuestas)]} <br>"
                mensaje_pantalla += "1. Educación superior no universitaria<br>"
                mensaje_pantalla += "2. Educación universitaria de tercer nivel o de grado<br>"
                mensaje_pantalla += "3. Educación universitaria de cuarto nivel o de posgrado<br>"
            else:
                mensaje_pantalla = "Opción no válida. Por favor, selecciona 1 (Sí) o 2 (No)."

        elif len(respuestas) == len(preguntas) - 18:
            nivel_formacion_opcion = user_input

            if user_input in nivel_formacion_opciones:
                if user_input == "1":
                    respuestas.append("Educación superior no universitaria")
                    nivel_formacion = "Educación superior no universitaria"
                    response = conversacion.send_message(
                        "Dime el artículo 54 del RRA")
                    respuesta = response.text.strip().replace("*", "")
                    mensaje_pantalla = f"{preguntas[len(respuestas)]}: {respuesta}<br><strong>Gemini: Seleccione una: </strong>"
                elif user_input == "2":
                    respuestas.append(
                        "Educación universitaria de tercer nivel o de grado")
                    nivel_formacion = "Educación universitaria de tercer nivel o de grado"
                    response = conversacion.send_message(
                        "Dime el artículo 54 del RRA")
                    respuesta = response.text.strip().replace("*", "")
                    mensaje_pantalla = f"{preguntas[len(respuestas)]}: {respuesta}<br><strong>Gemini: Seleccione una: </strong>"
                else:

                    respuestas.append(
                        "Educación universitaria de cuarto nivel o de posgrado")
                    nivel_formacion = "Educación universitaria de cuarto nivel o de posgrado"

                    response = conversacion.send_message(
                        "Dime el artículo 54 del RRA")
                    respuesta = response.text.strip().replace("*", "")
                    mensaje_pantalla = f"{preguntas[len(respuestas)]}: {respuesta}<br><strong>Gemini: Seleccione una: </strong>"

            else:
                mensaje_pantalla = "¡Error! Por favor, ingrese una opción válida (1, 2 o 3).<br>"
                mensaje_pantalla += "1. Educación superior no universitaria<br>"
                mensaje_pantalla += "2. Educación universitaria de tercer nivel o de grado<br>"
                mensaje_pantalla += "3. Educación universitaria de cuarto nivel o de posgrado<br>"

        elif len(respuestas) == len(preguntas) - 17:

            modalidad = user_input
            response2 = conversacion.send_message(
                f"Mejora la escritura si esta con faltas ortograficas corrige solo da el nombre de la carrera sin texto adicional. carrera: "+modalidad)
            modalidadIA = response2.text.strip().replace("*", "")
            respuestas.append(modalidadIA)

            response = conversacion.send_message(f"Dime solo una breve Descripción de la ejecución de la modalidad " + modalidad +
                                                 " segun los (Arts. 55, 56, 57, 58, 59 y 63 del RRA según corresponda) si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")
            respuesta_ia = response.text.strip().replace("*", "")
            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}<br><strong>Gemini: Escriba una carrera</strong>"

        elif len(respuestas) == len(preguntas) - 15:

            carrera = user_input

            response = conversacion.send_message(
                f"menciona brevemente los (Arts.16, 21 y 119 del RRA) si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 14:

            response = conversacion.send_message(f"Por favor, describe de manera breve el perfil de ingreso ideal para la carrera de " + carrera +
                                                 ". Incluye las habilidades, conocimientos y características personales que consideres importantes para que los aspirantes tengan éxito en esta área de estudio. Si ves que las palabras tienen caracteres especiales, corrige eso y da la palabra de manera entendible. Respeta puntos, comas y saltos de línea.")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 13:

            response = conversacion.send_message(f"Por favor, describe de manera breve el perfil de egreso ideal para la carrera de " + carrera +
                                                 ". Incluye las habilidades, conocimientos y características personales que consideres importantes para que los aspirantes tengan éxito en esta área de estudio. Si ves que las palabras tienen caracteres especiales, corrige eso y da la palabra de manera entendible. Respeta puntos, comas y saltos de línea.")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 12:

            if nivel_formacion == "Educación superior no universitaria":
                respuesta = "Para el tercer nivel técnico se requerirá al menos el nivel A1 y para el tecnológico se requerirá al menos el nivel A2."
            elif nivel_formacion == "Educación universitaria de tercer nivel o de grado":
                respuesta = "Para el tercer nivel de grado se requerirá al menos el nivel B1."

            respuestas.append(respuesta)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta} <br><strong>Gemini: </strong>" + preguntas[len(respuestas)] + "<br>"
            mensaje_pantalla += "1. Sede de Chimborazo.<br>"
            mensaje_pantalla += "2. Sede de Orellana.<br>"
            mensaje_pantalla += "3. Sede de Morona Santiago.<br> <strong>Seleccione una opción: </strong>"

        elif len(respuestas) == len(preguntas) - 11:

            opcion = user_input

            if opcion in ["1", "2", "3"]:
                if opcion == "1":
                    respuestas.append("Sede de Chimborazo.")
                elif opcion == "2":
                    respuestas.append("Sede de Orellana.")
                else:
                    respuestas.append("Sede de Morona Santiago.")
                mensaje_pantalla = "Escriba el número de estudiantes por cohorte: "
            else:
                mensaje_pantalla = "Opción no válida. Por favor, selecciona 1, 2 o 3."

        elif len(respuestas) == len(preguntas) - 10:

            respuesta = user_input
            respuestas.append(respuesta)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta}"

        elif len(respuestas) == len(preguntas) - 9:

            response = conversacion.send_message(
                f"Meciona brevemente los (Arts. 10, 15, 19, 113, 114, 117 y 118 del RRA), si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"<br>{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 8:

            response = conversacion.send_message(
                f"Meciona brevemente los  (Arts. 9, 19, 117 y 118 del RRA), si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 7:

            response = conversacion.send_message(
                f"Meciona brevemente el Art. 115 del RRA, si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 6:

            response = conversacion.send_message(
                f"Meciona brevemente el Art. 115 del RRA, si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 5:

            response = conversacion.send_message(
                f"Meciona brevemente el Art. 115 del RRA, si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 4:

            response = conversacion.send_message(
                f"Meciona brevemente los Arts. 43 y 121 del RRA, si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 3:

            response = conversacion.send_message(
                f"Meciona brevemente los Art. 118 y 124 del RRA, si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 2:

            response = conversacion.send_message(
                f"Meciona brevemente el Art. 43 del RRA, si ves que las palabras tienen caracteres especiales corrige eso y da la palabra de manera entendible respeta puntos comas y saltos de linea")

            respuesta_ia = response.text.strip().replace("*", "")

            respuestas.append(respuesta_ia)
            mensaje_pantalla = f"{preguntas[len(respuestas) - 1]} {respuesta_ia}"

        elif len(respuestas) == len(preguntas) - 1:

            blanco = ""
            respuestas.append(blanco)
            mensaje_pantalla += "Gracias por responder. <a href='/download_pdf' class='btn btn-primary my-2' target='_blank'><i class='fa-solid fa-download'></i> Descargar PDF</a>"

            respuestas_finales = respuestas[:]
            opcion_seleccionada = None
            nivel_formacion_opcion = None

    elif opcion_seleccionada == 2:

        global conversacionPlanificacion
        if len(respuestasDisenio) < len(preguntasDisenio) - 1:

            if len(respuestasDisenio) == 0:

                audiencia = user_input
                response = conversacion.send_message("mejora la redacción y corrige faltas ortograficas y el entrega el texto sin texto adicional del siguiente texto: "+audiencia)
                audienciaIA = response.text.strip().replace("*", "")


                respuestasDisenio.append(audienciaIA)

                mensaje_pantalla = f'{preguntasDisenio[len(respuestasDisenio) - 1]} {audienciaIA} <br><br> Ingrese las edades de su audiencia objetivo: <br> <p class="ejemplo">Ejemplo comprendida entre 17 y 22 años</p>'

            elif len(respuestasDisenio) == 1:

                edades = user_input

                response = conversacion.send_message("mejora la redacción y corrige faltas ortograficas y el entrega el texto sin texto adicional del siguiente texto: "+edades)
                edadesIA = response.text.strip().replace("*", "")


                respuestasDisenio.append(edadesIA)

                mensaje_pantalla = f'{preguntasDisenio[len(respuestasDisenio) - 1]} {edadesIA} <br> <br> Ingrese el nivel de  Nivel de instrucción mínimo: <br> <p class="ejemplo">Ejemplo Bachillerato (Cursando los primeros niveles de la ESPOCH)</p>'

            elif len(respuestasDisenio) == 2:

                instruccion = user_input

                response = conversacion.send_message("mejora la redacción y corrige faltas ortograficas y el entrega el texto sin texto adicional del siguiente texto: "+instruccion)
                instruccionIA = response.text.strip().replace("*", "")

                respuestasDisenio.append(instruccionIA)

                mensaje_pantalla = f"{preguntasDisenio[len(respuestasDisenio) - 1]} {instruccionIA} <br> <br> Nacionalidad: Estudiantes ecuatorianos y extranjeros que cursen una carrera en la ESPOCH."

            elif len(respuestasDisenio) == 3:

                nacionalidad = "Estudiantes ecuatorianos y extranjeros que cursen una carrera en la ESPOCH."

                respuestasDisenio.append(nacionalidad)

                mensaje_pantalla = f'Ingrese si los estudiantes deberan tener acceso a internet y cuales son los que mas se usan. <br> <p class="ejemplo">Ejemplo Estudiantes que tengan acceso a internet ya sea por proveedor de datos móviles o proveedor hogar.</p> <br> <p class="ejemplo">Su respuesta sera mejorada con la ayuda de la Inteligencia Artificial</p>'

            elif len(respuestasDisenio) == 4:

                acceso_internet = user_input

                response = conversacion.send_message("Mejora la redacción del siguiente texto con el contexto de que los estudiantes deberán tener acceso a internet y cuáles son las formas más comunes de acceso. La respuesta debe ser en dos o tres líneas. Un ejemplo podría ser: Estudiantes que tengan acceso a internet ya sea por proveedor de datos móviles o proveedor hogar. Utiliza el siguiente texto: " + acceso_internet + " solo dame la version mejorada")

                acceso_internet = response.text.strip().replace("*", "")

                respuestasDisenio.append(acceso_internet)

                mensaje_pantalla = f'{preguntasDisenio[len(respuestasDisenio) - 1]} {acceso_internet} <br> <br> Ingrese si los estudiantes deberan tener acceso a dispositivos tecnológicos y cuales son los que mas se usan. <br> <p class="ejemplo">Ejemplo: Estudiantes que tienen acceso a un computador de escritorio o portátil, así como a dispositivo móvil como smartphone de gama media baja, media y media alta.</p> <br> <p class="ejemplo">Su respuesta sera mejorada con la ayuda de la Inteligencia Artificial</p>'

            elif len(respuestasDisenio) == 5:

                acceso_dispositivos = user_input

                response = conversacion.send_message("Mejora la redacción del siguiente texto con el contexto de que los estudiantes deberían tener acceso a dispositivos tecnológicos y cuáles son los que más se usan. La respuesta debe ser en dos o tres líneas. Un ejemplo podría ser: Estudiantes que tienen acceso a un computador de escritorio o portátil, así como a dispositivos móviles como smartphones de gama media baja, media y media alta. Utiliza el siguiente texto: " + acceso_dispositivos + " solo dame la version mejorada")

                acceso_dispositivos = response.text.strip().replace("*", "")

                respuestasDisenio.append(acceso_dispositivos)

                mensaje_pantalla = f'{preguntasDisenio[len(respuestasDisenio) - 1]} {acceso_dispositivos} <br> <br> Ingrese ¿Qué estrategias son efectivas para motivar a los estudiantes contemporáneos en una asignatura en línea? <br> <br> <p class="ejemplo">Su respuesta sera mejorada con la ayuda de la Inteligencia Artificial</p>'

            elif len(respuestasDisenio) == 6:

                motivacion = user_input

                response = conversacion.send_message("Refina la siguiente respuesta sobre motivación: " + motivacion +
                                                     ". La respuesta debe ser de unas 4 líneas. Un ejemplo puede ser el siguiente: dado que los estudiantes contemporáneos son nativos tecnológicos, las asignaturas en línea deben ofrecer recursos y actividades interactivas para una formación efectiva. No olvides incluir algo sobre la motivación proporcionada.")

                respuesta_ia = response.text.strip().replace("*", "")
                respuestasDisenio.append(respuesta_ia)
                mensaje_pantalla = f"{preguntasDisenio[len(respuestasDisenio) - 1]} {respuesta_ia}  <br> <br> Selecciona tu estilo de aprendizaje: <br>1. Activo <br>2. Pragmático <br>3. Reflexivo <br>4. Teórico"

            elif len(respuestasDisenio) == 7:

                estilo = user_input

                if user_input in estilo:

                    if user_input == "1":

                        estilo_aprendizaje = "Activo"
                        response = conversacion.send_message("Proporcióname el estilo de aprendizaje en el formato estilo de aprendizaje 'nombre' seguido de un breve concepto que explique qué hace este estilo de aprendizaje: "+ estilo_aprendizaje+ ". No incluyas texto adicional")

                        estilo_aprendizajeIa = response.text.strip().replace("*", "")

                        respuestasDisenio.append(estilo_aprendizajeIa)
                        mensaje_pantalla = f"{preguntasDisenio[len(respuestasDisenio) - 1]} {estilo_aprendizajeIa} <br><br>"

                    elif user_input == "2":

                        estilo_aprendizaje = "Pragmático"

                        response = conversacion.send_message("Proporcióname el estilo de aprendizaje en el formato estilo de aprendizaje 'nombre' seguido de un breve concepto que explique qué hace este estilo de aprendizaje: "+ estilo_aprendizaje + ". No incluyas texto adicional")
                        estilo_aprendizajeIa = response.text.strip().replace("*", "")
                        respuestasDisenio.append(estilo_aprendizajeIa)
                        mensaje_pantalla = f"{preguntasDisenio[len(respuestasDisenio) - 1]} {estilo_aprendizajeIa} <br><br>"

                    elif user_input == "3":

                        estilo_aprendizaje = "Reflexivo"
                        response = conversacion.send_message("Proporcióname el estilo de aprendizaje en el formato estilo de aprendizaje 'nombre' seguido de un breve concepto que explique qué hace este estilo de aprendizaje: "+ estilo_aprendizaje+ ". No incluyas texto adicional")
                        estilo_aprendizajeIa = response.text.strip().replace("*", "")

                        respuestasDisenio.append(estilo_aprendizajeIa)
                        mensaje_pantalla = f"{preguntasDisenio[len(respuestasDisenio) - 1]} {estilo_aprendizajeIa} <br><br>"
                    elif user_input == "4":

                        estilo_aprendizaje = "Teórico"
                        respuestasDisenio.append(estilo_aprendizaje)
                        mensaje_pantalla = f"{preguntasDisenio[len(respuestasDisenio) - 1]} {estilo_aprendizaje} <br><br>"

                    else:
                        mensaje_pantalla = "Opción no válida. Por favor,  Selecciona tu estilo de aprendizaje: <br>1. Activo <br>2. Pragmático <br>3. Reflexivo <br>4. Teórico"

            elif len(respuestasDisenio) == 8:

                global total_horas_silabo_num

                response = conversacionSilabo.send_message(
                    "Dime los creditos del silabo. La respuesta debe ser solo el número, sin texto adicional.")

                total_horas_silabo_num = response.text.strip().replace("*", "")

                total_horas_silabo_num = float(total_horas_silabo_num)

                if total_horas_silabo_num == 2:
                    total_horas_silabo_num = 64
                    total_horas_ap=32
                elif total_horas_silabo_num == 3:
                    total_horas_silabo_num = 96
                    total_horas_ap=48
                elif total_horas_silabo_num == 4:
                    total_horas_silabo_num = 128
                    total_horas_ap=64

                componentePE = total_horas_silabo_num * 0.8
                componenteCD = total_horas_silabo_num * 0.2

                response2 = conversacionSilabo.send_message("mejora la redaccion solo dame la respuesta de manera textual el componente practio experimental tiene " + str(
                    componentePE) + " horas, el componente contacto con el docente tiene " + str(componenteCD) + " horas y el aprendizaje autonomo tiene "+str(total_horas_ap)+ " horas" )

                respuesta_ia = response2.text.strip().replace("*", "")

                respuestasDisenio.append(respuesta_ia)
                mensaje_pantalla = f"{preguntasDisenio[len(respuestasDisenio) - 1]} {respuesta_ia}"

            elif len(respuestasDisenio) == 9:

                global objetivos_unidad

                response = conversacionSilabo.send_message(
                    "Extrae el objetivo de aprendizaje de cada unidad del documento PDF proporcionado. Presenta los objetivos de aprendizaje en una lista, indicando el número de la unidad a la que corresponde cada objetivo. Por ejemplo: 1. Unidad 1: Objetivo 1, Unidad 2: Objetivo 2 y asi sucesivamente cada objetivo")

                objetivos_unidad = response.text.strip().replace("*", "").replace(";", "\n")

                respuestasDisenio.append(objetivos_unidad)
                mensaje_pantalla = f"""
                {preguntasDisenio[len(respuestasDisenio) - 1]} {objetivos_unidad}
                <br><br>
                <p class="ejemplo">Planifica tus semanas</p>
                 <br>
                <button type="button" class="btn btn-info" data-toggle="modal" data-target="#myModal">
                Planificación Semanal
                </button>
                """
            elif len(respuestasDisenio) == 10:

                dosificacion = ""
                respuestasDisenio.append(dosificacion)
                blanco = ""
                respuestasDisenio.append(blanco)

                # {preguntasDisenio[len(respuestasDisenio) - 1]} {semana1}
                mensaje_pantalla = f"Gracias por responder. Su documento esta listo. <a href='/downloadDisenio_pdf' class='btn btn-primary my-2' target='_blank'><i class='fa-solid fa-download'></i> Descargar PDF</a>"

                respuestas_finales = respuestasDisenio[:]
                opcion_seleccionada = None

                respuestas_finales = respuestasDisenio[:]
                opcion_seleccionada = None

    return jsonify({'bot_response': mensaje_pantalla})


@app.route('/guardar_planificacion', methods=['POST'])
def guardar_planificacion():
    datos = request.json
    semana = datos['semana']
    sesiones = datos['sesiones']
    actividades = datos['actividades']
    sesiones_datos = datos['sesionesDatos']
    aprendizajeAutonomo = datos['aprendizajeAutonomo']

    contenido = {
        "Semana": semana,
        "Sesiones": sesiones,
        "Sesiones Datos": sesiones_datos,
        "Actividades": actividades,
        "aprendizajeAutonomo" : aprendizajeAutonomo,
    }

    contenido_json = json.dumps(contenido, ensure_ascii=False, indent=4)

    with open('planificacion.txt', 'a', encoding='utf-8') as file:
        file.write(contenido_json)
        file.write('\n')

    return jsonify({"message": "Datos guardados correctamente"}), 200


@app.route('/download_pdf')
def download_pdf():
    global preguntas, respuestas_finales
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    font_size = 12
    line_spacing = 15
    margin = 50
    available_width = width - 2 * margin

    current_question_index = 0

    # Función para dibujar una nueva página
    def draw_new_page():
        nonlocal c, height, margin
        c.showPage()

    while current_question_index < len(preguntas):
        # Si estamos en una nueva página, dibujar el asunto
        if current_question_index == 0:
            # Dibujar el logo
            logo_path = "static/images/logoEspoch.jpg"
            logo_width = 50  # Ajusta el ancho del logo según sea necesario
            logo_height = 50  # Ajusta la altura del logo según sea necesario
            c.drawImage(logo_path, margin, height - 90,
                        width=logo_width, height=logo_height)

            # Dibujar el título en la parte superior de la nueva página
            c.setFont("Helvetica-Bold", 16)
            # Ajusta la posición X del título para dejar espacio al logo
            title_x = margin + logo_width + 10
            c.drawString(title_x, height - 70,
                         "Escuela Superior Politécnica de Chimborazo")
            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin, height - 120, "Asunto:")
            c.setFont("Helvetica", 12)
            c.drawString(margin + 50, height - 120, "Creación de Carreras")

        # Inicializar la posición y para esta página
        y_position = height - 150

        # Iterar a través de las preguntas y respuestas para esta página
        for i in range(current_question_index, len(preguntas)):
            pregunta = preguntas[i]
            respuesta = respuestas_finales[i] if i < len(
                respuestas_finales) else "No respondida"

            # Dividir la pregunta en líneas si es necesario
            # Establecer la fuente en negrita para las preguntas
            c.setFont("Helvetica-Bold", 12)
            pregunta_lines = []
            current_line = ""
            for word in pregunta.split():
                if c.stringWidth(current_line + " " + word) < available_width:
                    current_line += f" {word}"
                else:
                    pregunta_lines.append(current_line.strip())
                    current_line = f"{word}"
            pregunta_lines.append(current_line.strip())

            for line in pregunta_lines:
                c.drawString(margin, y_position, line)
                y_position -= line_spacing

            # Ajustar la respuesta a la misma lógica de ajuste
            # Establecer la fuente normal para las respuestas
            c.setFont("Helvetica", 12)
            respuesta_lines = []
            current_line = ""
            for word in respuesta.split():
                if c.stringWidth(current_line + " " + word) < available_width:
                    current_line += f" {word}"
                else:
                    respuesta_lines.append(current_line.strip())
                    current_line = f"{word}"
            respuesta_lines.append(current_line.strip())

            # Verificar si la respuesta cabe en la página actual
            if y_position - len(respuesta_lines) * line_spacing < margin + 50:
                # Si no cabe, dibujar una nueva página y continuar allí
                draw_new_page()
                y_position = height - 50

            for line in respuesta_lines:
                c.drawString(margin, y_position, line)
                y_position -= line_spacing

            # Añadir un espacio adicional entre preguntas
            y_position -= line_spacing

        current_question_index = i + 1  # Actualizar el índice de la pregunta actual

    c.showPage()  # Asegurarse de mostrar la última página
    c.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='Creación_Carreras.pdf', mimetype='application/pdf')


@app.route('/downloadDisenio_pdf')
def downloadDisenio_pdf():
    global preguntasDisenio, respuestas_finales

    # Crear el primer PDF con preguntas y respuestas
    buffer1 = BytesIO()
    c = canvas.Canvas(buffer1, pagesize=letter)
    width, height = letter

    font_size = 12
    line_spacing = 15
    margin = 50
    available_width = width - 2 * margin

    current_question_index = 0

    def draw_new_page():
        nonlocal c, height, margin, y_position
        c.showPage()
        y_position = height - margin

    y_position = height - 150

    while current_question_index < len(preguntasDisenio):
        if current_question_index == 0:
            logo_path = "static/images/logoEspoch.jpg"
            logo_width = 50
            logo_height = 50
            c.drawImage(logo_path, margin, height - 90, width=logo_width, height=logo_height)

            c.setFont("Helvetica-Bold", 16)
            title_x = margin + logo_width + 10
            c.drawString(title_x, height - 70, "Escuela Superior Politécnica de Chimborazo")
            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin, height - 120, "Asunto:")
            c.setFont("Helvetica", 12)
            c.drawString(margin + 50, height - 120, "Diseño Instruccional")

        for i in range(current_question_index, len(preguntasDisenio)):
            pregunta = preguntasDisenio[i]
            respuesta = respuestas_finales[i] if i < len(respuestas_finales) else "No respondida"

            # Reemplazar ';' por '\n' en la respuesta
            respuesta = respuesta.replace(';', '\n')

            c.setFont("Helvetica-Bold", 12)
            pregunta_lines = []
            current_line = ""
            for word in pregunta.split():
                if c.stringWidth(current_line + " " + word) < available_width:
                    current_line += f" {word}"
                else:
                    pregunta_lines.append(current_line.strip())
                    current_line = f"{word}"
            pregunta_lines.append(current_line.strip())

            for line in pregunta_lines:
                if y_position - line_spacing < margin:
                    draw_new_page()
                c.drawString(margin, y_position, line)
                y_position -= line_spacing

            c.setFont("Helvetica", 12)
            respuesta_lines = respuesta.split('\n')

            for line in respuesta_lines:
                respuesta_line_parts = []
                current_line = ""
                for word in line.split():
                    if c.stringWidth(current_line + " " + word) < available_width:
                        current_line += f" {word}"
                    else:
                        respuesta_line_parts.append(current_line.strip())
                        current_line = f"{word}"
                respuesta_line_parts.append(current_line.strip())

                for respuesta_line in respuesta_line_parts:
                    if y_position - line_spacing < margin:
                        draw_new_page()
                    c.drawString(margin, y_position, respuesta_line)
                    y_position -= line_spacing

            y_position -= line_spacing

        current_question_index = i + 1

    c.showPage()
    c.save()

    # Guardar el primer PDF en el buffer
    buffer1.seek(0)
    pdf_content = buffer1.getvalue()

    # Crear el segundo PDF con las tablas de planificación
    buffer2 = BytesIO()
    doc = SimpleDocTemplate(buffer2, pagesize=letter)
    elements = []

    # Añadir título principal al segundo PDF
    titulo_principal_estilo = getSampleStyleSheet()['Title']
    titulo_principal = Paragraph("Dosificación Semanas", titulo_principal_estilo)
    elements.append(titulo_principal)
    elements.append(Spacer(1, 12))

    def procesar_semana(data):
        semana = data["Semana"]
        sesiones = data["Sesiones"]
        sesiones_datos = data["Sesiones Datos"]
        actividades = data["Actividades"]
        aprendizaje_autonomo = data["aprendizajeAutonomo"]

        if not aprendizaje_autonomo:
            print(f"No hay datos en aprendizaje autónomo para la semana {semana}")
        
        # Procesar sesiones
        sesiones_data = []
        for sesion in sesiones_datos:
            sesiones_data.append([
                sesion["Sesion"],
                sesion["Fecha y hora Inicial"],
                sesion["Duracion"],
                "\n".join(sesion["Temas"])
            ])

        # Procesar actividades
        actividades_data = []
        for actividad in actividades:
            actividad_paragraph = Paragraph(actividad["Actividad"], getSampleStyleSheet()['BodyText'])
            como_paragraph = Paragraph(actividad["Cómo"], getSampleStyleSheet()['BodyText'])
            actividades_data.append([
                actividad_paragraph,
                como_paragraph,
                actividad["Inicio Actividad"],
                actividad["Fin Actividad"],
                actividad["Horas Designadas"]
            ])

        # Procesar aprendizaje autónomo
        aprendizaje_autonomo_data = []
        for actividad in aprendizaje_autonomo:
            actividad_paragraph = Paragraph(actividad["Actividad"], getSampleStyleSheet()['BodyText'])
            como_paragraph = Paragraph(actividad["Cómo"], getSampleStyleSheet()['BodyText'])
            aprendizaje_autonomo_data.append([
                actividad_paragraph,
                como_paragraph,
                actividad["Inicio Actividad"],
                actividad["Fin Actividad"],
                actividad["Horas Designadas"]
            ])

        # Convertir los datos en tablas para sesiones, actividades y aprendizaje autónomo
        df_sesiones = pd.DataFrame(sesiones_data, columns=["Sesion", "Fecha y hora Inicial", "Duracion", "Temas"])
        df_actividades = pd.DataFrame(actividades_data, columns=["Actividad", "Cómo", "Inicio Actividad", "Fin Actividad", "Horas Designadas"])
        df_aprendizaje_autonomo = pd.DataFrame(aprendizaje_autonomo_data, columns=["Actividad", "Cómo", "Inicio Actividad", "Fin Actividad", "Horas Designadas"])

        sesiones_table_data = [df_sesiones.columns.to_list()] + df_sesiones.values.tolist()
        actividades_table_data = [df_actividades.columns.to_list()] + df_actividades.values.tolist()
        aprendizaje_autonomo_table_data = [df_aprendizaje_autonomo.columns.to_list()] + df_aprendizaje_autonomo.values.tolist()

        # Título de la semana
        titulo_estilo = getSampleStyleSheet()['Heading3']
        titulo_estilo.alignment = 0
        titulo_estilo.fontName = 'Helvetica'
        titulo = Paragraph(f"Semana {semana}", titulo_estilo)
        elements.append(titulo)
        elements.append(Spacer(1, 12))

        ancho_tabla = letter[0] * 0.9

        # Crear tablas para sesiones, actividades y aprendizaje autónomo
        table_sesiones = Table(sesiones_table_data, colWidths=[ancho_tabla * 0.15, ancho_tabla * 0.2, ancho_tabla * 0.15, ancho_tabla * 0.5], repeatRows=1)
        table_actividades = Table(actividades_table_data, colWidths=[ancho_tabla * 0.20, ancho_tabla * 0.35, ancho_tabla * 0.17, ancho_tabla * 0.17, ancho_tabla * 0.18], repeatRows=1)
        table_aprendizaje_autonomo = Table(aprendizaje_autonomo_table_data, colWidths=[ancho_tabla * 0.20, ancho_tabla * 0.35, ancho_tabla * 0.17, ancho_tabla * 0.17, ancho_tabla * 0.18], repeatRows=1)

        # Estilos de tabla
        table_sesiones.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (3, 0), (3, -1), 5),
            ('RIGHTPADDING', (3, 0), (3, -1), 5),
        ]))

        table_actividades.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TEXTWRAP', (0, 0), (-1, -1), 'WRAP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        table_aprendizaje_autonomo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TEXTWRAP', (0, 0), (-1, -1), 'WRAP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        # Añadir tablas al PDF
        elements.append(Paragraph("Componente de contacto con el docente", titulo_estilo)) 
        elements.append(table_sesiones)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Componente práctico experimental ", titulo_estilo)) 
        elements.append(table_actividades)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Aprendizaje Autónomo", titulo_estilo))  # Título para aprendizaje autónomo
        elements.append(table_aprendizaje_autonomo)
        elements.append(Spacer(1, 24))

    # Leer el archivo de planificación
    with open('planificacion.txt', 'r', encoding='utf-8') as file:
        json_buffer = ""
        for line in file:
            json_buffer += line.strip()
            try:
                data = json.loads(json_buffer)
                procesar_semana(data)
                json_buffer = ""
            except json.JSONDecodeError:
                pass

    doc.build(elements)
    tables_content = buffer2.getvalue()

    # Crear un PDF final combinando ambos PDFs
    final_buffer = BytesIO()
    from PyPDF2 import PdfReader, PdfWriter

    writer = PdfWriter()

    # Añadir el primer PDF (preguntas y respuestas)
    pdf_reader1 = PdfReader(BytesIO(pdf_content))
    for page in pdf_reader1.pages:
        writer.add_page(page)

    # Añadir el segundo PDF (planificación)
    pdf_reader2 = PdfReader(BytesIO(tables_content))
    for page in pdf_reader2.pages:
        writer.add_page(page)

    writer.write(final_buffer)

    final_buffer.seek(0)
    return send_file(final_buffer, as_attachment=True, download_name='diseño_instruccional.pdf', mimetype='application/pdf')


@app.route('/guardar', methods=['POST'])
def guardar_archivo():
    contenido = request.data

    try:
        documento = fitz.open(stream=contenido, filetype="pdf")
        texto = ""
        for pagina in documento:
            texto += pagina.get_text()

        # Eliminar espacios innecesarios:
        texto_sin_espacios_extra = ' '.join(texto.split())

        with open('contenido.txt', 'w', encoding='utf-8') as f:
            f.write(texto_sin_espacios_extra)

        # Devolver un mensaje de éxito
        return jsonify({'message': 'Archivo guardado correctamente.', 'redirect': '/chat'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/verDisenio')
def verDisenio():
    return render_template('chatDisenio.html')


@app.route('/mejorar_texto', methods=['POST'])
def mejorar_texto_ruta():
    if request.method == 'POST':
        texto = request.form.get('texto')  # Obtén el texto del formulario
        texto_mejorado = mejorar_texto_api(texto)
        return jsonify({'texto_mejorado': texto_mejorado})
    else:
        return jsonify({'error': 'Método no permitido.'}), 405


if __name__ == '__main__':
    app.run(debug=True)
