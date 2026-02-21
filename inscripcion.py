import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
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
import uuid
import hmac

# ==============================
# 🔒 GOOGLE SHEETS SECURE SETUP
# ==============================
@st.cache_resource
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        service_account_info = st.secrets["gcp_service_account"].to_dict()
        service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("GlamourProspectosDB").sheet1
        return sheet
    except Exception as e:
        st.error(f"⚠️ Error conectando con Google Sheets: {str(e)}")
        st.stop()

sheet = get_gsheet()

@st.cache_data(ttl=300)
def get_headers():
    return sheet.row_values(1)

@st.cache_data(ttl=60)
def get_dataframe():
    return pd.DataFrame(sheet.get_all_records())

# Email config
gmail_user = st.secrets["gmail_user"]
gmail_pass = st.secrets["gmail_pass"]
studio_email = "glamourcam.studio@gmail.com"

ADMIN_PASSWORD = st.secrets["admin_password"]

# ==============================
# 🔐 AUTENTICACIÓN + RATE LIMIT (5 intentos / 5 min)
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
        if hmac.compare_digest(password, ADMIN_PASSWORD):
            st.session_state["authenticated"] = True
            st.session_state["login_attempts"] = 0
            st.session_state["lockout_time"] = None
            st.success("¡Bienvenido!")
            st.rerun()
        else:
            st.session_state["login_attempts"] += 1
            if st.session_state["login_attempts"] >= 5:
                st.session_state["lockout_time"] = datetime.datetime.now() + datetime.timedelta(minutes=5)
                st.session_state["login_attempts"] = 0
            st.error(f"Contraseña incorrecta. Intentos restantes: {5 - st.session_state['login_attempts']}")

# Sidebar primero
page = st.sidebar.selectbox("Paso", ["Pre-Inscripción", "Entrevista Prospecto", "Test Arquetipos", "Evaluación", "Dashboard"])

if page != "Pre-Inscripción" and not check_password():
    login()
    st.stop()

# ==============================
# 📧 EMAIL SERVICE
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
        st.warning(f"⚠️ No se pudo enviar el correo: {str(e)}")
        return False

# ==============================
# 🔒 VALIDACIONES
# ==============================
def validar_email(email):
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))

def validar_nombre(nombre):
    return len(nombre.strip()) >= 3

def validar_telefono(tel):
    cleaned = tel.replace("+", "").replace("-", "").replace(" ", "")
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15

def validar_documento(doc):
    cleaned = doc.replace(".", "").replace(" ", "")
    return cleaned.isdigit() and 5 <= len(cleaned) <= 12

# Colors Glamour
gold = "#A1783A"
black = "#0d0d0d"
st.markdown(
    f"""
    <style>
        .stApp {{background-color: {black}; color: white;}}
        h1, h2, h3 {{color: {gold};}}
        .stButton > button {{background-color: {gold}; color: {black}; font-weight: bold;}}
        .stTextInput > div > div > input {{background-color: #1a1a1a; color: white;}}
        .stSelectbox > div > div > select {{background-color: #1a1a1a; color: white;}}
    </style>
    """,
    unsafe_allow_html=True
)

logo_url = "https://glamourcamstudio.com/wp-content/uploads/2024/09/Recurso-8.svg"
st.image(logo_url, use_column_width=True)

# =============================================================================
# DASHBOARD (totalmente blindado)
# =============================================================================
if page == "Dashboard":
    st.title("Dashboard Ejecutivo - GlamourCam Studios")
    try:
        df = get_dataframe()
        if not df.empty:
            st.subheader("Resumen General")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Pre-Inscritas", len(df))
            entrevistadas = len(df[df["Estado"] == "Entrevistado"]) if "Estado" in df.columns else 0
            evaluadas = len(df[df["Estado"] == "Evaluado"]) if "Estado" in df.columns else 0
            col2.metric("Entrevistadas", entrevistadas)
            col3.metric("Evaluadas", evaluadas)
            aprobadas = len(df[df['Clasificacion'].str.contains("Muy Bueno|Bueno", na=False)]) if "Clasificacion" in df.columns else 0
            porcentaje = (aprobadas / len(df) * 100) if len(df) > 0 else 0
            col4.metric("Aprobadas", aprobadas, f"{porcentaje:.1f}%")

            st.subheader("Distribución por Estado")
            if "Estado" in df.columns:
                fig_pie = px.pie(df, names='Estado', title="Estados de Prospectos")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Columna 'Estado' aún no existe.")

            st.subheader("Score Promedio por Estado")
            if "Score_Total" in df.columns and "Estado" in df.columns:
                st.dataframe(df.groupby('Estado')['Score_Total'].mean().round(1))
            else:
                st.info("Aún no hay evaluaciones o columna 'Score_Total'.")

            st.subheader("Tabla de Prospectos (filtrable)")
            cols = ['Documento_ID', 'Nombre', 'Estado', 'Arquetipo', 'Score_Total', 'Clasificacion']
            existing_cols = [c for c in cols if c in df.columns]
            if existing_cols:
                filtro_estado = st.multiselect("Filtrar por estado", options=df['Estado'].unique() if "Estado" in df.columns else [], default=[])
                df_filtrado = df[df['Estado'].isin(filtro_estado)] if filtro_estado and "Estado" in df.columns else df
                st.dataframe(df_filtrado[existing_cols])
            else:
                st.info("No hay columnas principales aún.")
        else:
            st.info("Aún no hay prospectos registrados.")
    except Exception as e:
        st.error(f"Error cargando dashboard: {str(e)}")

# =============================================================================
# TEST DE ARQUETIPOS COMPLETO
# =============================================================================
questions = [
    {"num": 1, "text": "¿Cuál es tu ARQUETIPO? Cuando te diriges a las personas, utilizas palabras...", "options": {"a": "Impositivas, acusadoras, de reclamo.", "b": "De cortesía, educadas, simpáticas, neutras.", "c": "Escogidas, abstractas, complicadas, utilizas oraciones largas.", "d": "Jocosas, confiadas. A veces sin sentido o relación."}},
    {"num": 2, "text": "Con cuál de estas palabras te identificas más...", "options": {"a": "Independiente.", "b": "Disciplinado.", "c": "Pacífico.", "d": "Divertido."}},
    {"num": 3, "text": "Los contenidos más comunes en tus temas de conversación son:", "options": {"a": "Anecdotas, historias familiares, amistad.", "b": "Estadísticas, aspectos técnicos, tecnología, detalles y curiosidades.", "c": "De chistes, actividades amenas, lo que serás en el futuro, las cosas que sabes hacer.", "d": "De poder, influencia, control."}},
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
    {"num": 17, "text": "¿Qué actitudes asumes en situaciones de conflicto?", "options": {"a": "Puedes estallar y por lo general si te vas por la tangente. Sin embargo, eres bueno escuchando cuando te lo propones y puedes negociar.", "b": "Explosivo, atacas y defiendes apasionadamente tus opiniones. Te cuesta admitir equivocaciones. Frecuentemente no dejas hablar y a veces no escuchas.", "c": "Evitas las confrontaciones y las situaciones tensas. Sabes ceder y quedar amigo.", "d": "Eres racional y calculador, escondes y maneja tus emociones. Infléxible con tus reglas"}},
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
        tipo_id = st.selectbox("Tipo Identificación", ["C.C", "C.E", "PPT", "Pasaporte", "DNI"])
        documento_id = st.text_input("Número de Documento (ID Único)")
        whatsapp = st.text_input("WhatsApp/Celular")
        email = st.text_input("E-mail")
        direccion = st.text_input("Dirección de residencia")
        departamento = st.text_input("Departamento")
        ciudad = st.text_input("Ciudad")
        barrio = st.text_input("Barrio")
        genero = st.radio("Género", ["Masculino", "Femenino"])
        orientacion = st.text_input("Orientación Sexual")
        estado_civil = st.radio("Estado Civil", ["Soltero", "Casado", "Viudo", "Separado", "Unión Libre"])
        sangre = st.text_input("Tipo de Sangre")
        hijos = st.radio("¿Tienes Hijos?", ["Si", "No"])
        num_hijos = st.number_input("Si sí, ¿Cuántos?", min_value=0, disabled=(hijos == "No"))
        nacimiento_lugar = st.text_input("Lugar de Nacimiento")
        nacimiento_fecha = st.date_input("Fecha de Nacimiento")
        medio = st.radio("Medio por el cuál te enteraste", ["Redes Sociales", "Página web", "Anuncios en internet", "Referido o voz a voz", "Otros"])
        medio_otro = st.text_input("Si otros, especifica", disabled=(medio != "Otros"))
        st.subheader("Formación Académica")
        estudios = st.radio("Nivel de estudios", ["Primaria", "Secundaria", "Técnico/Tecnólogo", "Universitario", "Especialista/Maestría"])
        estudios_det = st.text_input("Especifica (si aplica)", disabled=(estudios in ["Primaria", "Secundaria"]))
        ingles = st.radio("Nivel de Inglés", ["Básico", "Intermedio", "Avanzado", "Nulo"])
        computacion = st.radio("Manejo en Computación", ["Muy bueno", "Bueno", "Regular", "Malo", "Muy malo"])
        ortografico = st.radio("Nivel ortográfico", ["Muy bueno", "Bueno", "Regular", "Malo", "Muy malo"])
        st.subheader("Experiencia Laboral General")
        exp_laboral = st.text_area("Detalla tu experiencia laboral")
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

        try:
            df = get_dataframe()
            headers = get_headers()
            if "Documento_ID" in headers and documento_id in df["Documento_ID"].values:
                st.error("Este número de documento ya fue registrado.")
                st.stop()
            data = {
                "Documento_ID": documento_id,
                "Nombre": nombre,
                "Tipo_ID": tipo_id,
                "WhatsApp": whatsapp,
                "Email": email,
                "Direccion": direccion,
                "Departamento": departamento,
                "Ciudad": ciudad,
                "Barrio": barrio,
                "Genero": genero,
                "Orientacion": orientacion,
                "Estado_Civil": estado_civil,
                "Sangre": sangre,
                "Hijos": hijos,
                "Num_Hijos": num_hijos,
                "Nacimiento_Lugar": nacimiento_lugar,
                "Nacimiento_Fecha": str(nacimiento_fecha),
                "Medio": medio,
                "Medio_Otro": medio_otro,
                "Estudios": estudios,
                "Estudios_Det": estudios_det,
                "Ingles": ingles,
                "Computacion": computacion,
                "Ortografico": ortografico,
                "Exp_Laboral": exp_laboral,
                "Fecha_Pre": str(datetime.datetime.now()),
                "Estado": "Pre-inscrito"
            }
            ordered_row = [data.get(col, "") for col in headers]
            sheet.append_row(ordered_row)
            get_dataframe.clear()
        except Exception as e:
            st.error(f"Error al guardar en base de datos: {str(e)}")
            st.stop()

        # PDF pre-inscripción (alineado con imagen escaneada)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_fill_color(131, 197, 190)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_text_color(13, 13, 13)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 12, "DOCUMENTO DE PERFIL DEL PROSPECTO A MODELO", ln=1, align="C")
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, "Bienvenido a GlamourCams Studios, somos un estudio que busca mejorar la calidad de vida de nuestros modelos formando y desarrollando personas íntegras, a través de herramientas, servicios y acompañamiento personalizado e integral.")
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
        pdf.cell(0, 6, f"Hijos: {hijos} Cantidad: {num_hijos if hijos == 'Si' else 'N/A'}", border=1, ln=1)
        pdf.cell(0, 6, f"Lugar de Nacimiento: {nacimiento_lugar} Fecha: {nacimiento_fecha}", border=1, ln=1)
        pdf.cell(0, 6, f"Medio de enterarse: {medio} {medio_otro if medio == 'Otros' else ''}", border=1, ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Formación Académica", border=1, ln=1, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Nivel de estudios: {estudios} {estudios_det if estudios not in ['Primaria', 'Secundaria'] else ''}", border=1, ln=1)
        pdf.cell(0, 6, f"Nivel de Inglés: {ingles}", border=1, ln=1)
        pdf.cell(0, 6, f"Manejo en Computación: {computacion}", border=1, ln=1)
        pdf.cell(0, 6, f"Nivel ortográfico: {ortografico}", border=1, ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Experiencia Laboral General", border=1, ln=1, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, f"{exp_laboral or 'No especificado'}", border=1)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Información Adicional", border=1, ln=1, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, "Otro trabajo o busca otro diferente: ______________________________", border=1)
        pdf.multi_cell(0, 6, "Disponibilidad horaria (horas y horario): ______________________________", border=1)
        pdf.multi_cell(0, 6, "Razones para este trabajo: ______________________________", border=1)
        pdf.multi_cell(0, 6, "Expectativas del trabajo y estudio: ______________________________", border=1)
        pdf.multi_cell(0, 6, "Acerca de mí (hobbies): ______________________________", border=1)
        pdf.multi_cell(0, 6, "Disgustos (personal, laboral, sexual): ______________________________", border=1)
        pdf.cell(0, 6, "Sugerencia de Nombre Artístico: ______________________________", border=1, ln=1)
        pdf.multi_cell(0, 6, "Fetiches de interés: ______________________________", border=1)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Campos a completar en entrevista (dejar en blanco)", border=1, ln=1, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, "Contacto Emergencia Nombre: ______________________________", border=1, ln=1)
        pdf.cell(0, 6, "Parentesco: ______________________________", border=1, ln=1)
        pdf.cell(0, 6, "Tel Emergencia: ______________________________", border=1, ln=1)
        pdf.cell(0, 6, "Experiencia Webcam: ______________________________", border=1, ln=1)
        pdf.cell(0, 6, "Firma Física: ______________________________  Fecha: _______________", border=1, ln=1)
        pdf_bytes = pdf.output(dest='S').encode('latin-1')

        send_email(email, "Gracias por tu Pre-Inscripción", "Nos pondremos en contacto para agendar tu entrevista presencial. ¡Gracias!", pdf_bytes, f"Pre_{documento_id}.pdf")
        send_email(studio_email, f"Nueva Pre-Inscripción: {documento_id}", "PDF adjunto para entrevista.", pdf_bytes, f"Pre_{documento_id}.pdf")
        st.success("✅ Pre-inscripción enviada correctamente. Revisa tu correo.")

# =============================================================================
# ENTREVISTA PROSPECTO (con modo prospecto por token)
# =============================================================================
elif page == "Entrevista Prospecto":
    st.title("Entrevista Prospecto - GlamourCam Studios")

    # Detectar si entra por token (modo prospecto) o logueado (modo admin)
    query_params = st.query_params
    modo_prospecto = False
    token_valido = False

    if "token" in query_params and "id" in query_params:
        token = query_params["token"][0]
        doc_id_param = query_params["id"][0]
        df = get_dataframe()
        headers = get_headers()
        if "Temp_Token" in headers and "Token_Expira" in headers and doc_id_param in df['Documento_ID'].values:
            row = df[df['Documento_ID'] == doc_id_param]
            if not row.empty and row['Temp_Token'].iloc[0] == token:
                expira_str = row['Token_Expira'].iloc[0]
                expira = datetime.datetime.fromisoformat(expira_str)
                if expira > datetime.datetime.now():
                    token_valido = True
                    modo_prospecto = True
                    documento_id = doc_id_param
                    # Consumir token
                    row_idx = df.index[df['Documento_ID'] == doc_id_param].tolist()[0] + 2
                    sheet.update_cell(row_idx, headers.index("Temp_Token") + 1, "")
                    sheet.update_cell(row_idx, headers.index("Token_Expira") + 1, "")
                    get_dataframe.clear()
                    st.success("✅ Acceso válido por link temporal. Completa tu información.")
                else:
                    st.error("El link ha expirado (24h). Solicita uno nuevo al estudio.")
                    st.stop()
            else:
                st.error("Token inválido o ya utilizado.")
                st.stop()
        else:
            st.error("Link inválido.")
            st.stop()
    else:
        # Modo admin (logueado)
        documento_id = st.text_input("Número de Documento (ID)")
        if not documento_id:
            st.info("Ingresa el número de documento para continuar.")
            st.stop()

    # Cargar datos pre-inscripción
    df = get_dataframe()
    headers = get_headers()
    if documento_id in df['Documento_ID'].values:
        pre_data = df[df['Documento_ID'] == documento_id].to_dict('records')[0]
        nombre = pre_data.get("Nombre", "N/A")
        tipo_id = pre_data.get("Tipo_ID", "N/A")
        documento_id_val = pre_data.get("Documento_ID", "N/A")
        whatsapp = pre_data.get("WhatsApp", "N/A")
        email = pre_data.get("Email", "")
        direccion = pre_data.get("Direccion", "")
        departamento = pre_data.get("Departamento", "")
        ciudad = pre_data.get("Ciudad", "")
        barrio = pre_data.get("Barrio", "")
        genero = pre_data.get("Genero", "")
        orientacion = pre_data.get("Orientacion", "")
        estado_civil = pre_data.get("Estado_Civil", "")
        sangre = pre_data.get("Sangre", "")
        hijos = pre_data.get("Hijos", "")
        num_hijos = pre_data.get("Num_Hijos", "")
        nacimiento_lugar = pre_data.get("Nacimiento_Lugar", "")
        nacimiento_fecha = pre_data.get("Nacimiento_Fecha", "")
        medio = pre_data.get("Medio", "")
        medio_otro = pre_data.get("Medio_Otro", "")
        estudios = pre_data.get("Estudios", "")
        estudios_det = pre_data.get("Estudios_Det", "")
        ingles = pre_data.get("Ingles", "")
        computacion = pre_data.get("Computacion", "")
        ortografico = pre_data.get("Ortografico", "")
        exp_laboral = pre_data.get("Exp_Laboral", "")

        st.write("Datos Pre-Inscripción Cargados:")
        st.json(pre_data)

        with st.form("entrevista_prospecto"):
            st.subheader("Contacto de Emergencia")
            emerg_nombre = st.text_input("Nombres y Apellidos")
            emerg_parentesco = st.radio("Parentesco", ["Mamá", "Papá", "Tío/Tía", "Sobrina/Sobrino", "Primo/Prima", "Amigo/Amiga", "Otros"])
            emerg_parent_otro = st.text_input("Si otros, especifica", disabled=(emerg_parentesco != "Otros"))
            emerg_tel = st.text_input("Teléfono de contacto")
            emerg_sabe = st.radio("¿Tu contacto de emergencia sabe que quieres ser modelo webcam?", ["Si", "No"])

            st.subheader("Experiencia Webcam")
            exp_webcam = st.radio("¿Tienes experiencia como modelo webcam?", ["Si", "No"])
            exp_tiempo = st.text_input("Si sí, ¿Cuánto tiempo?", disabled=(exp_webcam == "No"))
            exp_donde = st.text_input("¿Dónde?", disabled=(exp_webcam == "No"))
            exp_tipo = st.radio("Tipo de páginas trabajadas", ["Públicas", "Privadas", "Ambas"], disabled=(exp_webcam == "No"))
            exp_cuales = st.text_input("¿Cuáles?", disabled=(exp_webcam == "No"))
            consentimiento_fam = st.radio("¿Cuentas con consentimiento familiar?", ["Si", "No"])

            st.subheader("Información Adicional (Salud)")
            enfermedades = st.multiselect("Enfermedades que padece o padeció", ["Diabetes", "Epilepsia", "Hipertensión", "Asma", "Túnel Carpiano", "Otras"])
            enfermedades_otras = st.text_input("Si otras, especifica", disabled=("Otras" not in enfermedades))
            eps = st.radio("Tiene EPS", ["SÍ", "NO"])
            eps_cual = st.text_input("Si sí, ¿Cuál?", disabled=(eps == "NO"))

            st.subheader("Información Privada (solo entrevista)")
            otro_trabajo = st.radio("¿Otro trabajo o busca otro diferente?", ["Si", "No"])
            disponibilidad = st.text_area("Disponibilidad horaria (horas y horario)")
            razones = st.text_area("Razones para este trabajo")
            expectativas = st.text_area("Expectativas del trabajo y estudio")
            acerca_mi = st.text_area("Acerca de mí (hobbies)")
            disgustos = st.text_area("Disgustos (personal, laboral, sexual)")
            nombre_artistico = st.text_input("Sugerencia de Nombre Artístico")
            fetiches = st.text_area("Fetiches de interés")

            acuerdo_full = st.checkbox("Acepto el compromiso full (autorizo tratamiento de datos, etc.)")
            submit_ent = st.form_submit_button("Completar Entrevista" if modo_prospecto else "Completar Entrevista (Admin)")

        if submit_ent:
            if not acuerdo_full:
                st.error("Debes aceptar el acuerdo.")
                st.stop()

            data_update = {
                "Emerg_Nombre": emerg_nombre,
                "Emerg_Parentesco": emerg_parentesco,
                "Emerg_Parentesco_Otro": emerg_parent_otro,
                "Emerg_Tel": emerg_tel,
                "Emerg_Sabe": emerg_sabe,
                "Exp_Webcam": exp_webcam,
                "Exp_Tiempo": exp_tiempo,
                "Exp_Donde": exp_donde,
                "Exp_Tipo": exp_tipo,
                "Exp_Cuales": exp_cuales,
                "Consentimiento_Fam": consentimiento_fam,
                "Enfermedades": ', '.join(enfermedades),
                "Enfermedades_Otras": enfermedades_otras,
                "EPS": eps,
                "EPS_Cual": eps_cual,
                "Otro_Trabajo": otro_trabajo,
                "Disponibilidad": disponibilidad,
                "Razones": razones,
                "Expectativas": expectativas,
                "Acerca_Mi": acerca_mi,
                "Disgustos": disgustos,
                "Nombre_Artistico": nombre_artistico,
                "Fetiches": fetiches,
                "Fecha_Entrevista": str(datetime.datetime.now()),
                "Acuerdo_Full": "Si",
                "Estado": "Entrevistado"
            }
            row_idx = df.index[df['Documento_ID'] == documento_id].tolist()[0] + 2
            try:
                # Batch update optimizado
                updates_batch = []
                for key, value in data_update.items():
                    if key in headers:
                        col_idx = headers.index(key) + 1
                        updates_batch.append({
                            "range": f"{gspread.utils.rowcol_to_a1(row_idx, col_idx)}",
                            "values": [[value]]
                        })
                if updates_batch:
                    sheet.batch_update(updates_batch)
                get_dataframe.clear()
            except Exception as e:
                st.error(f"Error guardando entrevista: {str(e)}")
                st.stop()

            # Generar PDF (igual para admin y prospecto)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(131, 197, 190)
            pdf.rect(0, 0, 210, 297, 'F')
            pdf.set_text_color(13, 13, 13)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 12, "DOCUMENTO DE PERFIL DEL PROSPECTO A MODELO", ln=1, align="C")
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, "Bienvenido a GlamourCams Studios...")
            pdf.ln(8)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Datos Personales", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 6, f"Nombres y apellidos: {nombre}", border=1, ln=1)
            pdf.cell(0, 6, f"Identificación: {tipo_id} Número: {documento_id_val}", border=1, ln=1)
            pdf.cell(0, 6, f"WhatsApp/Celular: {whatsapp} E-mail: {email}", border=1, ln=1)
            pdf.cell(0, 6, f"Dirección: {direccion} Barrio: {barrio} Ciudad: {ciudad} Departamento: {departamento}", border=1, ln=1)
            pdf.cell(0, 6, f"Género: {genero} Orientación Sexual: {orientacion}", border=1, ln=1)
            pdf.cell(0, 6, f"Estado Civil: {estado_civil} Tipo de Sangre: {sangre}", border=1, ln=1)
            pdf.cell(0, 6, f"Hijos: {hijos} Cantidad: {num_hijos if hijos == 'Si' else 'N/A'}", border=1, ln=1)
            pdf.cell(0, 6, f"Lugar de Nacimiento: {nacimiento_lugar} Fecha: {nacimiento_fecha}", border=1, ln=1)
            pdf.cell(0, 6, f"Medio de enterarse: {medio} {medio_otro if medio == 'Otros' else ''}", border=1, ln=1)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Formación Académica", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 6, f"Nivel de estudios: {estudios} {estudios_det if estudios not in ['Primaria', 'Secundaria'] else ''}", border=1, ln=1)
            pdf.cell(0, 6, f"Nivel de Inglés: {ingles}", border=1, ln=1)
            pdf.cell(0, 6, f"Manejo en Computación: {computacion}", border=1, ln=1)
            pdf.cell(0, 6, f"Nivel ortográfico: {ortografico}", border=1, ln=1)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Experiencia Laboral General", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, f"{exp_laboral or 'No especificado'}", border=1)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Información Adicional", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, f"Otro trabajo o busca otro diferente: {otro_trabajo}", border=1)
            pdf.multi_cell(0, 6, f"Disponibilidad horaria (horas y horario): {disponibilidad}", border=1)
            pdf.multi_cell(0, 6, f"Razones para este trabajo: {razones}", border=1)
            pdf.multi_cell(0, 6, f"Expectativas del trabajo y estudio: {expectativas}", border=1)
            pdf.multi_cell(0, 6, f"Acerca de mí (hobbies): {acerca_mi}", border=1)
            pdf.multi_cell(0, 6, f"Disgustos (personal, laboral, sexual): {disgustos}", border=1)
            pdf.cell(0, 6, f"Sugerencia de Nombre Artístico: {nombre_artistico}", border=1, ln=1)
            pdf.multi_cell(0, 6, f"Fetiches de interés: {fetiches}", border=1)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Contacto de Emergencia", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 6, f"Nombres y Apellidos: {emerg_nombre}", border=1, ln=1)
            pdf.cell(0, 6, f"Parentesco: {emerg_parentesco} {emerg_parent_otro if emerg_parentesco == 'Otros' else ''}", border=1, ln=1)
            pdf.cell(0, 6, f"Teléfono de contacto: {emerg_tel}", border=1, ln=1)
            pdf.cell(0, 6, f"Sabe que quieres ser modelo webcam: {emerg_sabe}", border=1, ln=1)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Experiencia Webcam", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 6, f"Experiencia como modelo webcam: {exp_webcam}", border=1, ln=1)
            pdf.cell(0, 6, f"Cuánto tiempo: {exp_tiempo}", border=1, ln=1)
            pdf.cell(0, 6, f"Dónde: {exp_donde}", border=1, ln=1)
            pdf.cell(0, 6, f"Tipo de páginas trabajadas: {exp_tipo}", border=1, ln=1)
            pdf.cell(0, 6, f"Cuáles: {exp_cuales}", border=1, ln=1)
            pdf.cell(0, 6, f"Consentimiento familiar: {consentimiento_fam}", border=1, ln=1)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Información Adicional (Salud)", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, f"Enfermedades que padece o padeció: {', '.join(enfermedades)} {enfermedades_otras if 'Otras' in enfermedades else ''}", border=1)
            pdf.cell(0, 6, f"Tiene EPS: {eps} {eps_cual if eps == 'SÍ' else ''}", border=1, ln=1)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Compromiso con GlamourCam Studios", border=1, ln=1, fill=True)
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, f"Yo, {nombre}, identificado con {tipo_id} N° {documento_id_val}. A través de este compromiso, declaro que he venido por cuenta propia a las instalaciones de GlamourCam Studios sin que alguien o algo me hubiese obligado, amenazada o presionado a hacerlo, declaro que soy mayor de edad y soy residente permanente en Colombia.\n\nMe comprometo a no revelar ninguna información a la cual tenga acceso en las instalaciones del estudio, asimismo declarar ser autónomo en las decisiones a tomar, y también autorizo al tratamiento de mi información y documentos personales con el fin de continuar con el proceso de selección.")
            pdf.ln(5)
            pdf.multi_cell(0, 6, "______________________________\nFIRMA DEL PROSPECTO")
            pdf_bytes = pdf.output(dest='S').encode('latin-1')

            st.download_button("⬇️ Descargar PDF para Firma", pdf_bytes, f"Perfil_{documento_id}.pdf", "application/pdf")
            send_email(studio_email, f"Entrevista Completada: {documento_id}", "PDF adjunto para impresión y firma.", pdf_bytes, f"Perfil_{documento_id}.pdf")
            if modo_prospecto:
                st.success("¡Gracias! Tu información ha sido enviada al estudio. Te contactaremos pronto.")
            else:
                st.success("Entrevista completada (modo admin). Descarga el PDF para impresión y firma manual.")
    else:
        st.error("ID no encontrado.")

# =============================================================================
# TEST DE ARQUETIPOS
# =============================================================================
elif page == "Test Arquetipos":
    st.title("Test de Arquetipos - GlamourCam (Itaca)")
    documento_id = st.text_input("Número de Documento (ID, opcional para guardar)")
    scores = {"G": 0, "A": 0, "SR": 0, "M": 0}
    answers = {}

    with st.form("arquetipos_form"):
        for i, q in enumerate(questions):
            st.subheader(f"Pregunta {q['num']}: {q['text']}")
            answer = st.radio(
                "Elige una opción:",
                list(q['options'].keys()),
                format_func=lambda x: f"{x}) {q['options'][x]}",
                key=f"q{i}"
            )
            answers[i] = answer
        submit_arq = st.form_submit_button("Calcular Arquetipo")

    if submit_arq:
        for i, ans in answers.items():
            archetype = mappings[i][ans]
            scores[archetype] += 1
        max_score = max(scores.values())
        dominants = [archetypes[key] for key, value in scores.items() if value == max_score]
        arq_result = ', '.join(dominants)
        st.success(f"Arquetipo dominante: {arq_result}")

        if documento_id:
            df = get_dataframe()
            headers = get_headers()
            if documento_id in df['Documento_ID'].values:
                row_idx = df.index[df['Documento_ID'] == documento_id].tolist()[0] + 2
                try:
                    if "Arquetipo" in headers:
                        col_idx = headers.index("Arquetipo") + 1
                        sheet.update_cell(row_idx, col_idx, arq_result)
                        get_dataframe.clear()
                        st.success("Arquetipo guardado en BD.")
                    else:
                        st.warning("Columna 'Arquetipo' no existe en Google Sheets. Agrégala manualmente.")
                except Exception as e:
                    st.error(f"Error guardando arquetipo: {str(e)}")

# =============================================================================
# EVALUACIÓN
# =============================================================================
elif page == "Evaluación":
    st.title("Evaluación - GlamourCam Studios")
    documento_id = st.text_input("Número de Documento (ID)")
    if documento_id:
        df = get_dataframe()
        headers = get_headers()
        if documento_id in df['Documento_ID'].values:
            data = df[df['Documento_ID'] == documento_id].to_dict('records')[0]
            st.write("Datos Prospecto:", data)
            st.write("Arquetipo:", data.get("Arquetipo", "No disponible"))

            categorias = {
                "Actitud y Valores": ["Actitud positiva", "Franqueza/Integridad", "Responsabilidad", "Tolerancia a la presión", "Disciplina personal", "Nivel de compromiso", "Dinamismo/Energía", "Resiliencia emocional"],
                "Presentación e Imagen": ["Presentación personal", "Higiene", "Expresión y desenvolvimiento", "Timidez (inversa)", "Extrovertida", "Confianza en cámara", "Creatividad en autoexpresión"],
                "Aptitudes y Comportamientos": ["Iniciativa/Autonomía", "Orientado a resultados", "Proactividad", "Capacidad de aprendizaje", "Adaptabilidad", "Habilidades de ventas/persuasión", "Manejo de tiempo"],
                "Conocimientos y Background": ["Manejo de inglés", "Manejo de PC", "Nivel ortográfico", "Experiencia laboral", "Plataformas webcam", "Habilidades digitales", "Seguridad online"]
            }
            pesos = {"Actitud y Valores": 0.20, "Presentación e Imagen": 0.25, "Aptitudes y Comportamientos": 0.25, "Conocimientos y Background": 0.30}

            scores_cats = {}
            with st.form("evaluacion"):
                for cat, items in categorias.items():
                    st.subheader(cat)
                    cat_total = 0
                    for item in items:
                        score = st.slider(item, 1, 4, 2, key=f"{cat}_{item}")
                        cat_total += score
                    avg_cat = (cat_total / (len(items) * 4)) * 100
                    scores_cats[cat] = avg_cat
                comentarios = st.text_area("Comentarios / Observaciones")
                submit_eval = st.form_submit_button("Calcular Evaluación")

            if submit_eval:
                total_score = sum(scores_cats[cat] * pesos[cat] for cat in scores_cats)
                arq_bonus = 5 if data.get("Arquetipo") in ["El Mago", "El Amante"] else 0
                total_score = min(total_score + arq_bonus, 100)
                if total_score > 80:
                    clasif = "Muy Bueno - Perfil Ideal"
                elif total_score >= 50:
                    clasif = "Bueno - Potencial con entrenamiento"
                else:
                    clasif = "Regular/Bajo - No recomendado en este momento"
                st.success(f"Score Total: {total_score:.1f}% - {clasif}")

                col1, col2 = st.columns(2)
                with col1:
                    fig_bar = px.bar(x=list(scores_cats.keys()), y=list(scores_cats.values()), title="Puntuación por Categoría")
                    st.plotly_chart(fig_bar, use_container_width=True)
                with col2:
                    fig_radar = go.Figure(data=go.Scatterpolar(r=list(scores_cats.values()), theta=list(scores_cats.keys()), fill='toself'))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="Radar de Fortalezas")
                    st.plotly_chart(fig_radar, use_container_width=True)

                row_idx = df.index[df['Documento_ID'] == documento_id].tolist()[0] + 2
                updates = {
                    "Score_Total": total_score,
                    "Clasificacion": clasif,
                    "Comentarios": comentarios,
                    "Fecha_Eval": str(datetime.datetime.now()),
                    "Estado": "Evaluado"
                }
                try:
                    batch_updates = []
                    for key, value in updates.items():
                        if key in headers:
                            col_idx = headers.index(key) + 1
                            batch_updates.append({
                                "range": f"{gspread.utils.rowcol_to_a1(row_idx, col_idx)}",
                                "values": [[value]]
                            })
                    if batch_updates:
                        sheet.batch_update(batch_updates)
                    get_dataframe.clear()
                except Exception as e:
                    st.error(f"Error guardando evaluación: {str(e)}")

                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "Reporte de Evaluación - GlamourCam Studios", ln=1, align="C")
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 8, f"Candidata: {data.get('Nombre', 'Anónima')}", ln=1)
                pdf.cell(0, 8, f"Arquetipo: {data.get('Arquetipo', 'No disponible')}", ln=1)
                pdf.cell(0, 8, f"Puntuación Total: {total_score:.1f}% - {clasif}", ln=1)
                pdf.ln(5)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Detalles por Categoría:", ln=1)
                pdf.set_font("Arial", size=10)
                for cat, score in scores_cats.items():
                    pdf.cell(0, 6, f"{cat}: {score:.1f}%", ln=1)
                pdf.ln(5)
                pdf.multi_cell(0, 8, f"Comentarios: {comentarios or 'Sin comentarios'}")
                pdf_bytes = pdf.output(dest='S').encode('latin-1')

                st.download_button("⬇️ Descargar Reporte PDF", pdf_bytes, f"Evaluacion_{documento_id}.pdf")
                send_email(studio_email, f"Evaluación Completada: {documento_id}", "PDF adjunto con resultados.", pdf_bytes, f"Eval_{documento_id}.pdf")
        else:
            st.error("ID no encontrado.")
