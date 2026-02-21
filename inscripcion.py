import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF  # pip install fpdf2
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pandas as pd
import datetime
import re
import time
import hmac
import gspread.exceptions

# ==============================
# GOOGLE SHEETS
# ==============================
@st.cache_resource
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"].to_dict()
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("GlamourProspectosDB").sheet1
    except Exception as e:
        st.error(f"Error conectando Google Sheets: {str(e)}")
        st.stop()

sheet = get_gsheet()

@st.cache_data(ttl=300)
def get_headers():
    return sheet.row_values(1)

@st.cache_data(ttl=60)
def get_dataframe():
    try:
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

# Credenciales
gmail_user = st.secrets["gmail_user"]
gmail_pass = st.secrets["gmail_pass"]
studio_email = "glamourcam.studio@gmail.com"
ADMIN_PASSWORD = st.secrets["admin_password"]

# ==============================
# LOGIN + RATE LIMIT
# ==============================
def check_password():
    return st.session_state.get("authenticated", False)

def login():
    st.title("Login - GlamourCam Studios")

    if "login_attempts" not in st.session_state:
        st.session_state["login_attempts"] = 0
    if "lockout_time" not in st.session_state:
        st.session_state["lockout_time"] = None

    if st.session_state.get("lockout_time") and datetime.datetime.now() < st.session_state["lockout_time"]:
        tiempo_restante = (st.session_state["lockout_time"] - datetime.datetime.now()).seconds // 60
        st.error(f"Demasiados intentos. Espera {tiempo_restante + 1} minutos.")
        st.stop()

    password = st.text_input("Contraseña de entrevistador", type="password")

    if st.button("Ingresar"):
        if not password:
            st.warning("Ingresa la contraseña.")
            return

        if hmac.compare_digest(password, ADMIN_PASSWORD):
            st.session_state["authenticated"] = True
            st.session_state["login_attempts"] = 0
            st.session_state["lockout_time"] = None
            st.success("¡Bienvenido!")
            st.rerun()
        else:
            st.session_state["login_attempts"] += 1
            restantes = max(0, 5 - st.session_state["login_attempts"])
            if st.session_state["login_attempts"] >= 5:
                st.session_state["lockout_time"] = datetime.datetime.now() + datetime.timedelta(minutes=5)
                st.session_state["login_attempts"] = 0
                st.error("Cuenta bloqueada por 5 minutos.")
            else:
                st.error(f"Contraseña incorrecta. Intentos restantes: {restantes}")
            st.rerun()

page = st.sidebar.selectbox("Paso", ["Pre-Inscripción", "Entrevista Prospecto", "Test Arquetipos", "Evaluación", "Dashboard"])

if page != "Pre-Inscripción" and not check_password():
    login()
    st.stop()

# ==============================
# EMAIL
# ==============================
def send_email(to, subject, body, attachment_bytes=None, filename="documento.pdf"):
    try:
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        if attachment_bytes:
            part = MIMEApplication(attachment_bytes, Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"No se pudo enviar correo: {str(e)}")
        return False

# ==============================
# VALIDACIONES
# ==============================
def validar_email(email):
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))

def validar_nombre(nombre):
    return len(nombre.strip()) >= 3

def validar_telefono(tel):
    cleaned = re.sub(r'[^0-9+]', '', tel)
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15

def validar_edad_minima(fecha_nacimiento):
    hoy = datetime.date.today()
    
    if fecha_nacimiento > hoy:
        return False, "La fecha de nacimiento no puede ser futura."
    
    edad = hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )
    
    if edad < 18:
        return False, f"Debe tener al menos 18 años (edad actual: {edad})"
    
    if edad > 55:
        return False, f"La edad máxima permitida es 55 años (edad actual: {edad})"
    
    return True, f"Edad válida: {edad} años (prospecto permitido)"

# Estilo visual
gold = "#A1783A"
black = "#0d0d0d"
st.markdown(f"""
    <style>
        .stApp {{background-color: {black}; color: white;}}
        h1, h2, h3 {{color: {gold};}}
        .stButton > button {{background-color: {gold}; color: {black}; font-weight: bold;}}
    </style>
""", unsafe_allow_html=True)

st.image("https://glamourcamstudio.com/wp-content/uploads/2024/09/Recurso-8.svg", use_column_width=True)

# =============================================================================
# DASHBOARD
# =============================================================================
if page == "Dashboard":
    st.title("Dashboard Ejecutivo - GlamourCam Studios")
    try:
        df = get_dataframe()
        if not df.empty:
            st.subheader("Resumen General")
            cols = st.columns(4)
            cols[0].metric("Total Pre-Inscritas", len(df))
            entrevistadas = 0
            evaluadas = 0
            if "Estado" in df.columns:
                entrevistadas = len(df[df["Estado"] == "Entrevistado"])
                evaluadas = len(df[df["Estado"] == "Evaluado"])
            cols[1].metric("Entrevistadas", entrevistadas)
            cols[2].metric("Evaluadas", evaluadas)
            aprobadas = 0
            if "Clasificacion" in df.columns:
                aprobadas = len(df[df['Clasificacion'].fillna("").str.contains("Muy Bueno|Bueno", na=False)])
            porc = (aprobadas / len(df) * 100) if len(df) > 0 else 0
            cols[3].metric("Aprobadas", aprobadas, f"{porc:.1f}%")

            if "Estado" in df.columns:
                st.subheader("Distribución por Estado")
                fig = px.pie(df, names="Estado", title="Estados")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Tabla de Prospectos")
            cols_vis = ['Documento_ID', 'Nombre', 'Estado', 'Arquetipo', 'Score_Total', 'Clasificacion']
            cols_exist = [c for c in cols_vis if c in df.columns]
            if cols_exist:
                filtro = st.multiselect("Filtrar estado", options=df["Estado"].unique(), default=df["Estado"].unique())
                df_f = df[df["Estado"].isin(filtro)] if filtro else df
                st.dataframe(df_f[cols_exist])
        else:
            st.info("Aún no hay registros.")
    except Exception as e:
        st.error(f"Error en dashboard: {str(e)}")

# =============================================================================
# TEST ARQUETIPOS (Itaca - 20 preguntas completas)
# =============================================================================
questions = [
    {"num": 1, "text": "¿Cuál es tu ARQUETIPO? Cuando te diriges a las personas, utilizas palabras...", "options": {"a": "Impositivas, acusadoras, de reclamo.", "b": "De cortesía, educadas, simpáticas, neutras.", "c": "Escogidas, abstractas, complicadas, utilizas oraciones largas.", "d": "Jocosas, confiadas. A veces sin sentido o relación."}},
    {"num": 2, "text": "Con cuál de estas palabras te identificas más...", "options": {"a": "Independiente.", "b": "Disciplinado.", "c": "Pacífico.", "d": "Divertido."}},
    {"num": 3, "text": "Los contenidos más comunes en tus temas de conversación son:", "options": {"a": "Anécdotas, historias familiares, amistad.", "b": "Estadísticas, aspectos técnicos, tecnología, detalles y curiosidades.", "c": "De chistes, actividades amenas, lo que serás en el futuro, las cosas que sabes hacer.", "d": "De poder, influencia, control."}},
    {"num": 4, "text": "Cuando entablas una relación interpersonal, tu comunicación tiene un estilo...", "options": {"a": "Concreto y especializado, cuidadoso del estilo y confiabilidad de la información.", "b": "A veces vago, original, ocurrente. Orientado a ser el centro de atención.", "c": "Directo, concreto y orientado hacia el control. Las cosas son blancas o negras.", "d": "A ratos poco concreto, muy explicativo y cuidadoso, orientado a no dañar al otro."}},
    {"num": 5, "text": "Te caracterizas por ser una persona...", "options": {"a": "Mucho movimiento, gesticulaciones y expresión facial abundante.", "b": "Erguida, rápida y tensa, a veces rígida corporalmente.", "c": "Movimientos lentos y poca gesticulación, el cuerpo protege a la persona.", "d": "Controlas tus movimientos, quieres que sean perfectos y equilibrados. Extrema rigidez"}},
    {"num": 6, "text": "Con cuál de estas descripciones te identificas más:", "options": {"a": "Perfeccionista, todo tiene que estar en su lugar.", "b": "Comprensivo, comprensiva, entiendes los problemas de los demás.", "c": "Simpático, simpática, te invitan a fiestas y reuniones, te gusta la fiesta.", "d": "Osado-Osada, tomas riesgos basados en instintos. Eres impulsivo-impulsiva."}},
    {"num": 7, "text": "En conversaciones tu energía vocal es:", "options": {"a": "Bajo y monótono (poca modulación).", "b": "Lineal con tendencia a la pronunciación acentuada y seca.", "c": "Alto con modulaciones variadas. Tu ánimo la influyen a menudo.", "d": "Alto, intenso, avasallante a veces, duro y tenso. Algunos dicen que eres gritón."}},
    {"num": 8, "text": "Tu velocidad al hablar es...", "options": {"a": "Moderada, pausada.", "b": "Rápida.", "c": "Rápida y tajante.", "d": "Lenta con ritmo característico."}},
    {"num": 9, "text": "Tu expresión facial más común es...", "options": {"a": "Relajada, sonriente, muchas muecas y buen contacto visual.", "b": "Dura y seria, entrecejo fruncido, a veces dientes apretados y mirada fija.", "c": "Relajada, sonriente, muchas expresiones de empatía, cariño, etc.", "d": "Calmada, fija y sin expresiones evidentes. Imperturbable a veces."}},
    {"num": 10, "text": "En el escenario de ventas, su mayor fortaleza es:", "options": {"a": "Preparar la estrategia para lograr la reunión, la venta o la negociación.", "b": "Desarrollar relaciones, caerle bien al cliente.", "c": "La acción: visitar clientes, llamadas telefónicas, cerrar el negocio.", "d": "Descubrir nuevas formas de lograr más ventas, mantener una actitud positiva."}},
    {"num": 11, "text": "En actividades cotidianas te caracterizas por:", "options": {"a": "Ser más bien lento, no funcionas con precisión o te cuesta concentrarte.", "b": "Ser más bien metódico, calmado y muy ordenado.", "c": "Ser ansioso, muy rápido, poco ordenado y te aburres con facilidad.", "d": "Querer todo a la vez."}},
    {"num": 12, "text": "¿Qué actitud asumes frente a los errores de los otros?", "options": {"a": "Corriges, sufres mucho, piensas que es falta de precisión.", "b": "Haces frecuentemente caso omiso y tomas en cuenta a la persona y su esfuerzo personal.", "c": "Poco tolerante, acusas inmediatamente. Los hechos son los hechos.", "d": "Corriges evitando hacerlo sentir mal. Te involucras, aunque tengas que hacer sacrificios."}},
    {"num": 13, "text": "De tu participación en un grupo, por lo general te interesa obtener...", "options": {"a": "Ser conocido, reconocimiento a tus méritos. Proyectarte", "b": "Influencias, contactos importantes. Hay objetivos detrás de las cosas que haces.", "c": "Amistades y sinceridad.", "d": "Conocimiento y sabiduría. Una conversación intelectual."}},
    {"num": 14, "text": "Por lo general, tu estado de ánimo es...", "options": {"a": "Explosivo, ansioso, tenso, invasivo.", "b": "Calmado, buena disposición.", "c": "Calmado, tenso, imperturbable, prefieres estar solo.", "d": "Impulsivo, explosivo, alegre, irrelevante."}},
    {"num": 15, "text": "En tu casa o en la oficina eres...", "options": {"a": "Poco ordenado, aunque puedes mejorarlo, siempre serás despreocupado.", "b": "Eres extremadamente metódico, ordenado, detallista y cuidadoso.", "c": "Poco ordenado, creativo, te gusta pasar de un tema a otro cuando deja de ser novedoso.", "d": "Organizado, rápido, no te gusta perder el tiempo."}},
    {"num": 16, "text": "Tu energía, la orientas fundamentalmente en la vida a...", "options": {"a": "En lograr tus metas principalmente en el campo del conocimiento y perfección.", "b": "Quedar bien ante la gente, lograr ser reconocido y admirado.", "c": "Lograr tus metas, lo que te has propuesto. Alcanzar el poder.", "d": "En ser feliz, aceptado y querido."}},
    {"num": 17, "text": "¿Qué actitudes asumes en situaciones de conflicto?", "options": {"a": "Puedes estallar y por lo general si te vas por la tangente. Sin embargo, eres bueno escuchando cuando te lo propones y puedes negociar.", "b": "Explosivo, atacas y defiendes apasionadamente tus opiniones. Te cuesta admitir equivocaciones. Frecuentemente no dejas hablar y a veces no escuchas.", "c": "Evitas las confrontaciones y las situaciones tensas. Sabes ceder y quedar amigo.", "d": "Eres racional y calculador, escondes y manejas tus emociones. Infléxible con tus reglas"}},
    {"num": 18, "text": "En la negociación...", "options": {"a": "Presionas.", "b": "Concilias.", "c": "Analizas.", "d": "Enfrías situaciones."}},
    {"num": 19, "text": "Cuando tomas decisiones te motiva...", "options": {"a": "La amistad, el sentimiento.", "b": "La información que posees.", "c": "Tu olfato/intuición.", "d": "Lograr tu resultado final."}},
    {"num": 20, "text": "En la negociación...", "options": {"a": "Te gusta demostrar que tienes la razón.", "b": "Te gusta sobresalir.", "c": "Te gusta tener el control.", "d": "Te gusta sentirte bien."}}
]

mappings = [
    {"a": "G", "b": "A", "c": "SR", "d": "M"},
    {"a": "G", "b": "SR", "c": "A", "d": "M"},
    {"a": "A", "b": "SR", "c": "M", "d": "G"},
    {"a": "SR", "b": "M", "c": "G", "d": "A"},
    {"a": "M", "b": "G", "c": "A", "d": "SR"},
    {"a": "SR", "b": "A", "c": "M", "d": "G"},
    {"a": "A", "b": "SR", "c": "M", "d": "G"},
    {"a": "SR", "b": "M", "c": "G", "d": "A"},
    {"a": "M", "b": "G", "c": "A", "d": "SR"},
    {"a": "SR", "b": "A", "c": "G", "d": "M"},
    {"a": "A", "b": "SR", "c": "M", "d": "G"},
    {"a": "SR", "b": "M", "c": "G", "d": "A"},
    {"a": "M", "b": "G", "c": "A", "d": "SR"},
    {"a": "G", "b": "A", "c": "SR", "d": "M"},
    {"a": "A", "b": "SR", "c": "M", "d": "G"},
    {"a": "SR", "b": "M", "c": "G", "d": "A"},
    {"a": "M", "b": "G", "c": "A", "d": "SR"},
    {"a": "G", "b": "A", "c": "SR", "d": "M"},
    {"a": "A", "b": "SR", "c": "M", "d": "G"},
    {"a": "SR", "b": "M", "c": "G", "d": "A"}
]

archetypes = {"G": "El Guerrero", "A": "El Amante", "SR": "El Sabio Rey", "M": "El Mago"}

# =============================================================================
# PRE-INSCRIPCIÓN
# =============================================================================
if page == "Pre-Inscripción":
    st.title("Pre-Inscripción - GlamourCam Studios")
    with st.form("pre_prospecto"):
        st.subheader("Datos Personales")
        nombre = st.text_input("Nombres y apellidos")
        tipo_id = st.selectbox("Tipo Identificación", ["C.C", "C.E", "P.P.T", "Pasaporte", "L.C"])
        documento_id = st.text_input("Número de Documento").strip()  # ← strip() añadido
        whatsapp = st.text_input("WhatsApp / Celular")
        email = st.text_input("E-mail")
        direccion = st.text_input("Dirección de residencia")
        barrio = st.text_input("Barrio")
        departamento = st.text_input("Departamento")
        ciudad = st.text_input("Ciudad")
        genero = st.radio("Género", ["Masculino", "Femenino"])
        orientacion = st.text_input("Orientación Sexual")
        estado_civil = st.radio("Estado Civil", ["Soltero", "Casado", "Viudo", "Separado", "Unión Libre"])
        sangre = st.text_input("Tipo de Sangre")
        hijos = st.radio("¿Tienes Hijos?", ["Sí", "No"])
        num_hijos = st.number_input("Si sí, ¿Cuántos?", min_value=0, disabled=(hijos == "No"))
        nacimiento_lugar = st.text_input("Lugar de Nacimiento")
        nacimiento_fecha = st.date_input(
            "Fecha de Nacimiento",
            min_value=datetime.date(1950, 1, 1),
            max_value=datetime.date.today(),
            value=datetime.date(2000, 1, 1),
            format="DD/MM/YYYY"
        )
        medio = st.radio("Medio por el cual te enteraste de Nosotros", [
            "Redes Sociales", "Página web", "Anuncios en internet",
            "Referido o voz a voz", "Otros"
        ])
        medio_otro = st.text_input("Si otros, especifica", disabled=(medio != "Otros"))
        st.subheader("Formación Académica")
        estudios = st.radio("Nivel de estudios", [
            "Primaria", "Secundaria", "Técnico/Tecnólogo",
            "Universitario", "Especialista/Maestría"
        ])
        estudios_det = st.text_input("Especifica (si Técnico, Universitario o posgrado)", disabled=(estudios in ["Primaria", "Secundaria"]))
        ingles = st.radio("Nivel de Inglés", ["Básico", "Intermedio", "Avanzado", "Nulo"])
        computacion = st.radio("Manejo en Computación", ["Muy bueno", "Bueno", "Regular", "Malo", "Muy malo"])
        exp_laboral = st.text_area("Experiencia Laboral General")
        acuerdo_pre = st.checkbox("Acepto autorización preliminar de datos")
        submit_pre = st.form_submit_button("Enviar Pre-Inscripción")

    if submit_pre:
        last_time = st.session_state.get("last_submit_time", 0)
        current_time = time.time()
        if current_time - last_time < 30:
            st.warning("⏳ Debes esperar 30 segundos antes de enviar otro formulario.")
            st.stop()
        st.session_state["last_submit_time"] = current_time

        if not acuerdo_pre:
            st.error("Debes aceptar la autorización.")
            st.stop()

        if not validar_nombre(nombre):
            st.error("Nombre inválido (mínimo 3 caracteres).")
            st.stop()
        if not validar_email(email):
            st.error("Correo inválido.")
            st.stop()
        if not validar_telefono(whatsapp):
            st.error("Teléfono inválido.")
            st.stop()
        if not documento_id:
            st.error("Documento requerido.")
            st.stop()

        edad_valida, mensaje_edad = validar_edad_minima(nacimiento_fecha)
        if not edad_valida:
            st.error(mensaje_edad)
            st.stop()

        try:
            sheet.find(documento_id, in_column=1)
            st.error("Este número de documento ya fue registrado.")
            st.stop()
        except gspread.exceptions.CellNotFound:
            pass
        except Exception as e:
            st.error(f"Error al verificar documento: {str(e)}")
            st.stop()

        try:
            headers = get_headers()
            header_map = {col: i+1 for i, col in enumerate(headers)}
            data = {
                "Documento_ID": documento_id,
                "Nombre": nombre,
                "Tipo_ID": tipo_id,
                "WhatsApp": whatsapp,
                "Email": email,
                "Direccion": direccion,
                "Barrio": barrio,
                "Departamento": departamento,
                "Ciudad": ciudad,
                "Genero": genero,
                "Orientacion": orientacion,
                "Estado_Civil": estado_civil,
                "Sangre": sangre,
                "Hijos": hijos,
                "Num_Hijos": num_hijos if hijos == "Sí" else "",
                "Nacimiento_Lugar": nacimiento_lugar,
                "Nacimiento_Fecha": str(nacimiento_fecha),
                "Medio": medio,
                "Medio_Otro": medio_otro,
                "Estudios": estudios,
                "Estudios_Det": estudios_det,
                "Ingles": ingles,
                "Computacion": computacion,
                "Exp_Laboral": exp_laboral,
                "Fecha_Pre": str(datetime.datetime.now()),
                "Estado": "Pre-inscrito"
            }
            ordered_row = [data.get(col, "") for col in headers]
            sheet.append_row(ordered_row)
        except Exception as e:
            st.error(f"Error al guardar en base de datos: {str(e)}")
            st.stop()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_fill_color(131, 197, 190)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_text_color(13, 13, 13)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 12, "DOCUMENTO DE PERFIL DEL PROSPECTO A MODELO", ln=1, align="C")
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, "Bienvenido a GlamourCam Studios, somos un estudio que busca mejorar la calidad de vida de nuestros modelos formando y desarrollando personas íntegras, a través de herramientas, servicios y acompañamiento personalizado e integral.")
        pdf.ln(8)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Datos Personales", border=1, ln=1, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Nombres y apellidos: {nombre}", border=1, ln=1)
        pdf.cell(0, 6, f"Identificación: {tipo_id} Número: {documento_id}", border=1, ln=1)
        pdf.cell(0, 6, f"WhatsApp/Celular: {whatsapp} E-mail: {email}", border=1, ln=1)
        pdf.cell(0, 6, f"Dirección: {direccion} Barrio: {barrio} Ciudad: {ciudad} Departamento: {departamento}", border=1, ln=1)
        pdf.cell(0, 6, f"Género: {genero} Orientación Sexual: {orientacion}", border=1, ln=1)
        pdf.cell(0, 6, f"Estado Civil: {estado_civil} Tipo de Sangre: {sangre}", border=1, ln=1)
        pdf.cell(0, 6, f"Hijos: {hijos} Cantidad: {num_hijos if hijos == 'Sí' else 'N/A'}", border=1, ln=1)
        pdf.cell(0, 6, f"Lugar de Nacimiento: {nacimiento_lugar} Fecha: {nacimiento_fecha}", border=1, ln=1)
        pdf.cell(0, 6, f"Medio de enterarse: {medio} {medio_otro if medio == 'Otros' else ''}", border=1, ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Formación Académica", border=1, ln=1, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Nivel de estudios: {estudios} {estudios_det if estudios not in ['Primaria', 'Secundaria'] else ''}", border=1, ln=1)
        pdf.cell(0, 6, f"Nivel de Inglés: {ingles}", border=1, ln=1)
        pdf.cell(0, 6, f"Manejo en Computación: {computacion}", border=1, ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Experiencia Laboral General", border=1, ln=1, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, f"{exp_laboral or 'No especificado'}", border=1)
        pdf_bytes = pdf.output(dest='S')

        send_email(email, "Gracias por tu Pre-Inscripción", "Nos pondremos en contacto para agendar tu entrevista presencial. ¡Gracias!", pdf_bytes, f"Pre_{documento_id}.pdf")
        send_email(studio_email, f"Nueva Pre-Inscripción: {documento_id}", "PDF adjunto para entrevista.", pdf_bytes, f"Pre_{documento_id}.pdf")
        st.success("✅ Pre-inscripción enviada correctamente. Revisa tu correo.")

# =============================================================================
# ENTREVISTA PROSPECTO (placeholder)
# =============================================================================
elif page == "Entrevista Prospecto":
    st.title("Entrevista Prospecto - GlamourCam Studios")
    st.info("Implementa aquí tu formulario completo de entrevista + lógica de token")

# =============================================================================
# TEST ARQUETIPOS
# =============================================================================
elif page == "Test Arquetipos":
    st.title("Test de Arquetipos - Itaca")
    documento_id = st.text_input("Número de Documento (opcional para guardar)").strip()
    scores = {"G": 0, "A": 0, "SR": 0, "M": 0}

    with st.form("arquetipos"):
        for q in questions:
            st.subheader(f"Pregunta {q['num']}: {q['text']}")
            ans = st.radio("Selecciona:", list(q["options"].keys()), format_func=lambda k: q["options"][k], key=f"q{q['num']}")
            archetype = mappings[q['num']-1].get(ans)
            if archetype:
                scores[archetype] += 1

        if st.form_submit_button("Calcular Arquetipo"):
            max_score = max(scores.values())
            dominantes = [archetypes[k] for k, v in scores.items() if v == max_score]
            resultado = ", ".join(dominantes)
            st.success(f"Arquetipo dominante: **{resultado}**")

            if documento_id:
                try:
                    cell = sheet.find(documento_id, in_column=1)
                    headers = get_headers()
                    header_map = {col: i+1 for i, col in enumerate(headers)}
                    if "Arquetipo" in header_map:
                        sheet.update_cell(cell.row, header_map["Arquetipo"], resultado)
                        st.success("Resultado guardado.")
                except gspread.exceptions.CellNotFound:
                    st.warning("Documento no encontrado en la base.")
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

# =============================================================================
# EVALUACIÓN (completa y corregida)
# =============================================================================
elif page == "Evaluación":
    st.title("Evaluación - GlamourCam Studios")
    documento_id = st.text_input("Número de Documento (ID)").strip()
    if documento_id:
        try:
            cell = sheet.find(documento_id, in_column=1)
            if not cell:
                st.error("ID no encontrado.")
                st.stop()

            row_values = sheet.row_values(cell.row)
            headers = get_headers()
            data = dict(zip(headers, row_values))

            st.write("**Datos Prospecto (resumen)**")
            st.write(f"Nombre: {data.get('Nombre', 'N/A')}")
            st.write(f"Arquetipo: {data.get('Arquetipo', 'No disponible')}")

            # Categorías y subcriterios
            categorias = {
                "Actitud y Valores (20%)": [
                    "Actitud positiva", "Franqueza/Integridad", "Responsabilidad",
                    "Tolerancia a la presión", "Disciplina personal", "Nivel de compromiso",
                    "Dinamismo/Energía", "Resiliencia emocional"
                ],
                "Presentación, Imagen y Personalidad (25%)": [
                    "Presentación personal", "Higiene", "Expresión y desenvolvimiento",
                    "Timidez (inversa)", "Extrovertida", "Confianza en cámara",
                    "Creatividad en autoexpresión"
                ],
                "Aptitudes y Comportamientos (25%)": [
                    "Iniciativa/Autonomía", "Orientado a resultados", "Proactividad",
                    "Capacidad de aprendizaje", "Adaptabilidad", "Habilidades de ventas/persuasión",
                    "Manejo de tiempo"
                ],
                "Conocimientos y Background (30%)": [
                    "Manejo de inglés", "Manejo de PC", "Nivel ortográfico",
                    "Experiencia laboral", "Plataformas webcam", "Habilidades digitales",
                    "Seguridad online"
                ]
            }

            pesos = {
                "Actitud y Valores (20%)": 0.20,
                "Presentación, Imagen y Personalidad (25%)": 0.25,
                "Aptitudes y Comportamientos (25%)": 0.25,
                "Conocimientos y Background (30%)": 0.30
            }

            scores_cats = {}

            with st.form("evaluacion"):
                for cat, items in categorias.items():
                    st.subheader(cat)
                    cat_total = 0
                    for item in items:
                        score = st.slider(
                            item,
                            min_value=1,
                            max_value=4,
                            value=2,
                            step=1,
                            key=f"{cat}_{item}"
                        )
                        cat_total += score
                    avg_cat = (cat_total / (len(items) * 4)) * 100
                    scores_cats[cat] = avg_cat

                comentarios = st.text_area("Comentarios / Observaciones generales")
                submit_eval = st.form_submit_button("Calcular Evaluación Final")

            if submit_eval:
                total_score = sum(scores_cats[cat] * pesos[cat] for cat in scores_cats)
                arq_bonus = 5 if data.get("Arquetipo", "").strip() in ["El Mago", "El Amante"] else 0
                total_score = min(total_score + arq_bonus, 100)
                total_score = round(total_score, 1)  # ← Redondeo a 1 decimal

                if total_score > 80:
                    clasif = "Muy Bueno - Perfil Ideal"
                elif total_score >= 50:
                    clasif = "Bueno - Potencial con entrenamiento"
                else:
                    clasif = "Malo - No recomendado en este momento"

                st.success(f"**Score Total: {total_score}%** - **{clasif}**")

                col1, col2 = st.columns(2)
                with col1:
                    fig_bar = px.bar(
                        x=list(scores_cats.keys()),
                        y=list(scores_cats.values()),
                        title="Puntuación por Categoría (%)",
                        color=list(scores_cats.values()),
                        color_continuous_scale="YlOrRd"
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                with col2:
                    fig_radar = go.Figure(data=go.Scatterpolar(
                        r=list(scores_cats.values()),
                        theta=list(scores_cats.keys()),
                        fill='toself'
                    ))
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        showlegend=False,
                        title="Radar de Fortalezas"
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

                # Guardar en Sheets
                try:
                    headers = get_headers()
                    header_map = {col: i+1 for i, col in enumerate(headers)}
                    updates = {
                        "Score_Total": total_score,
                        "Clasificacion": clasif,
                        "Comentarios": comentarios,
                        "Fecha_Eval": str(datetime.datetime.now()),
                        "Estado": "Evaluado"
                    }
                    batch = []
                    for key, value in updates.items():
                        if key in header_map:
                            batch.append({
                                "range": gspread.utils.rowcol_to_a1(cell.row, header_map[key]),
                                "values": [[value]]
                            })
                    if batch:
                        sheet.batch_update(batch)
                    st.success("Evaluación guardada en la base de datos.")
                except Exception as e:
                    st.error(f"Error al guardar evaluación: {str(e)}")

                # Generar PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "Reporte de Evaluación - GlamourCam Studios", ln=1, align="C")
                pdf.ln(5)
                pdf.set_font("Arial", size=12)
                pdf.cell(0, 8, f"Prospecto ID: {documento_id}", ln=1)
                pdf.cell(0, 8, f"Nombre: {data.get('Nombre', 'N/A')}", ln=1)
                pdf.cell(0, 8, f"Arquetipo: {data.get('Arquetipo', 'No disponible')}", ln=1)
                pdf.cell(0, 8, f"Score Final: {total_score}% - {clasif}", ln=1)
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 8, "Puntuación por Categoría:", ln=1)
                pdf.set_font("Arial", size=11)
                for cat, score in scores_cats.items():
                    pdf.cell(0, 6, f"{cat}: {score:.1f}%", ln=1)
                pdf.ln(5)
                pdf.multi_cell(0, 8, f"Comentarios: {comentarios or 'Sin comentarios adicionales.'}")
                pdf_bytes = pdf.output(dest='S')

                st.download_button(
                    label="⬇️ Descargar Reporte PDF",
                    data=pdf_bytes,
                    file_name=f"Evaluacion_{documento_id}.pdf",
                    mime="application/pdf"
                )

                # Enviar por email al estudio
                send_email(
                    studio_email,
                    f"Evaluación Completada: {documento_id} - {clasif}",
                    f"Score: {total_score}% - {clasif}\n\nComentarios: {comentarios or 'N/A'}",
                    pdf_bytes,
                    f"Evaluacion_{documento_id}.pdf"
                )

        except Exception as e:
            st.error(f"Error al cargar o procesar evaluación: {str(e)}")

# Fin del código - versión corregida y completa
