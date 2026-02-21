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

# Config Google Sheets (add JSON key to Streamlit Secrets as 'gcp_service_account' - dict)
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)
sheet = client.open("GlamourProspectosDB").sheet1  # Create Sheet with columns: Documento_ID, Nombre, Tipo_ID, WhatsApp, Email, Direccion, Departamento, Ciudad, Barrio, Genero, Orientacion, Estado_Civil, Sangre, Hijos, Num_Hijos, Nacimiento_Lugar, Nacimiento_Fecha, Medio, Medio_Otro, Estudios, Estudios_Det, Ingles, Computacion, Ortografico, Exp_Laboral, Otro_Trabajo, Disponibilidad, Razones, Expectativas, Acerca_Mi, Disgustos, Nombre_Artistico, Fetiches, Fecha_Pre, Emerg_Nombre, Emerg_Parentesco, Emerg_Parentesco_Otro, Emerg_Tel, Emerg_Sabe, Exp_Webcam, Exp_Tiempo, Exp_Donde, Exp_Tipo, Exp_Cuales, Consentimiento_Fam, Enfermedades, Enfermedades_Otras, EPS, EPS_Cual, Fecha_Entrevista, Acuerdo_Full, Firma_Tipo, Arquetipo, Score_Total, Clasificacion, Comentarios, Fecha_Eval

# Email config (add to Secrets: gmail_user, gmail_pass)
gmail_user = st.secrets["gmail_user"]
gmail_pass = st.secrets["gmail_pass"]
studio_email = "glamourcam.studio@gmail.com"  # Your email

# Colors Glamour
gold = "#A1783A"
black = "#0d0d0d"
st.markdown(f"<style>.stApp {{background-color: {black}; color: white;}} h1, h2 {{color: {gold};}} .stButton > button {{background-color: {gold}; color: {black};}}</style>", unsafe_allow_html=True)

logo_url = "https://via.placeholder.com/300x100/A1783A/0D0D0D?text=GlamourCam+Logo"  # Replace with your GitHub raw URL
st.image(logo_url, use_column_width=True)

page = st.sidebar.selectbox("Paso", ["Pre-Inscripción", "Entrevista Prospecto", "Test Arquetipos", "Evaluación"])

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

        st.subheader("Información Adicional")
        otro_trabajo = st.text_area("¿Tiene otro trabajo o busca otro diferente?")
        disponibilidad = st.text_area("Disponibilidad horaria (horas y horario)")
        razones = st.text_area("Razones para este trabajo")
        expectativas = st.text_area("Expectativas del trabajo y estudio")
        acerca_mi = st.text_area("Acerca de mí (hobbies)")
        disgustos = st.text_area("¿Qué te disgusta (personal, laboral, sexual)?")
        nombre_artistico = st.text_input("Sugerencia de Nombre Artístico")
        fetiches = st.text_area("Fetiches de interés")

        acuerdo_pre = st.checkbox("Acepto autorización preliminar de datos")
        submit_pre = st.form_submit_button("Enviar Pre-Inscripción")

    if submit_pre and acuerdo_pre and documento_id:
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
            "Otro_Trabajo": otro_trabajo,
            "Disponibilidad": disponibilidad,
            "Razones": razones,
            "Expectativas": expectativas,
            "Acerca_Mi": acerca_mi,
            "Disgustos": disgustos,
            "Nombre_Artistico": nombre_artistico,
            "Fetiches": fetiches,
            "Fecha_Pre": str(datetime.datetime.now())
        }
        df = pd.DataFrame(sheet.get_all_records())
        if documento_id in df['Documento_ID'].values:
            st.error("ID ya existe. Contacta al estudio.")
        else:
            sheet.append_row(list(data.values()))
            # Generate PDF pre-filled with blanks for interview
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Pre-Inscripción - GlamourCam Studios", ln=1, align="C")
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 8, f"Nombre: {nombre}", ln=1)
            pdf.cell(0, 8, f"Documento: {tipo_id} {documento_id}", ln=1)
            # ... Add all pre fields filled
            # Blanks for interview
            pdf.cell(0, 8, "Contacto Emergencia Nombre: ____________________", ln=1)
            pdf.cell(0, 8, "Parentesco: ____________________", ln=1)
            pdf.cell(0, 8, "Tel Emergencia: ____________________", ln=1)
            pdf.cell(0, 8, "Emerg Sabe: ____________________", ln=1)
            pdf.cell(0, 8, "Exp Webcam: ____________________", ln=1)
            # ... Add all blanks for remaining fields
            pdf.ln(10)
            pdf.multi_cell(0, 8, "Espacio para Firma Física: ______________________________")
            pdf_bytes = pdf.output(dest='S').encode('latin-1')

            # Email to prospecto: Thanks
            msg_prosp = MIMEMultipart()
            msg_prosp['From'] = gmail_user
            msg_prosp['To'] = email
            msg_prosp['Subject'] = "Gracias por tu Pre-Inscripción en GlamourCam Studios"
            msg_prosp.attach(MIMEText("Nos pondremos en contacto para agendar tu entrevista presencial. ¡Gracias!"))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, email, msg_prosp.as_string())

            # Email to studio: PDF for print
            msg_studio = MIMEMultipart()
            msg_studio['From'] = gmail_user
            msg_studio['To'] = studio_email
            msg_studio['Subject'] = f"Nueva Pre-Inscripción: {documento_id}"
            msg_studio.attach(MIMEText("PDF para impresión adjunto. Completa en entrevista."))
            part = MIMEApplication(pdf_bytes, Name=f"Pre_{documento_id}.pdf")
            part['Content-Disposition'] = 'attachment; filename="pre.pdf"'
            msg_studio.attach(part)
            server.sendmail(gmail_user, studio_email, msg_studio.as_string())
            server.quit()

            st.success("Pre-inscripción enviada. Recibirás un email de confirmación.")

elif page == "Entrevista Prospecto":
    st.title("Entrevista Prospecto - GlamourCam Studios")
    documento_id = st.text_input("Número de Documento (ID)")
    if documento_id:
        df = pd.DataFrame(sheet.get_all_records())
        if documento_id in df['Documento_ID'].values:
            pre_data = df[df['Documento_ID'] == documento_id].to_dict('records')[0]
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

                acuerdo_full = st.checkbox("Acepto el compromiso full (autorizo tratamiento de datos, etc.)")
                submit_ent = st.form_submit_button("Completar Entrevista")

            if submit_ent and acuerdo_full:
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
                    "Fecha_Entrevista": str(datetime.datetime.now()),
                    "Acuerdo_Full": "Si"
                }
                row_idx = df.index[df['Documento_ID'] == documento_id].tolist()[0] + 2  # 1-based
                for key, value in data_update.items():
                    col_idx = sheet.row_values(1).index(key) + 1
                    sheet.update_cell(row_idx, col_idx, value)
                st.success("Entrevista completada. Imprime PDF completo para firma física desde Sheets o genera aquí.")
                # Optional: Generate full PDF here if needed

        else:
            st.error("ID no encontrado. Verifica pre-inscripción.")

elif page == "Test Arquetipos":
    st.title("Test de Arquetipos - GlamourCam Studios")
    documento_id = st.text_input("Número de Documento (ID, opcional para integrado)")
    # Full arquetipos code from original PDF
    questions = [ # Paste full questions array from first response
    ]
    mappings = [ # Paste full mappings
    ]
    archetypes = {"G": "El Guerrero", "A": "El Amante", "SR": "El Sabio Rey", "M": "El Mago"}

    scores = {"G": 0, "A": 0, "SR": 0, "M": 0}
    answers = {}

    with st.form("arquetipos_form"):
        for i, q in enumerate(questions):
            st.subheader(f"Pregunta {q['num']}: {q['text']}")
            answer = st.radio("Elige una opción:", list(q['options'].keys()), format_func=lambda x: f"{x}) {q['options'][x]}", key=f"q{i}")
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
            df = pd.DataFrame(sheet.get_all_records())
            if documento_id in df['Documento_ID'].values:
                row_idx = df.index[df['Documento_ID'] == documento_id].tolist()[0] + 2
                col_idx = sheet.row_values(1).index("Arquetipo") + 1
                sheet.update_cell(row_idx, col_idx, arq_result)
                st.success("Arquetipo guardado en BD.")

elif page == "Evaluación":
    st.title("Evaluación - GlamourCam Studios")
    documento_id = st.text_input("Número de Documento (ID)")
    if documento_id:
        df = pd.DataFrame(sheet.get_all_records())
        if documento_id in df['Documento_ID'].values:
            data = df[df['Documento_ID'] == documento_id].to_dict('records')[0]
            st.write("Datos Prospecto:", data)
            st.write("Arquetipo:", data.get("Arquetipo", "No disponible"))
            # Full evaluation code with sliders, categories, weights, charts, PDF as in previous responses
            categorias = { # Paste from previous
            }
            pesos = { # Paste
            }
            scores_cats = {}
            with st.form("evaluacion"):
                for cat, items in categorias.items():
                    st.subheader(cat)
                    cat_total = 0
                    for item in items:
                        score = st.slider(item, 1, 4, 2)
                        cat_total += score
                    avg_cat = (cat_total / (len(items) * 4)) * 100
                    scores_cats[cat] = avg_cat
                comentarios = st.text_area("Comentarios")
                submit_eval = st.form_submit_button("Calcular Evaluación")

            if submit_eval:
                total_score = sum(scores_cats[cat] * pesos[cat] for cat in scores_cats)
                arq_bonus = 5 if data.get("Arquetipo") in ["El Mago", "El Amante"] else 0
                total_score = min(total_score + arq_bonus, 100)
                if total_score > 80:
                    clasif = "Muy Bueno"
                elif total_score >= 50:
                    clasif = "Bueno"
                else:
                    clasif = "Malo"
                st.success(f"Score: {total_score:.2f}% - {clasif}")

                # Charts (bar and radar)
                col1, col2 = st.columns(2)
                with col1:
                    fig_bar = px.bar(x=list(scores_cats.keys()), y=list(scores_cats.values()), title="Por Categoría", color_continuous_scale="YlOrBr")
                    st.plotly_chart(fig_bar)
                with col2:
                    fig_radar = go.Figure(data=go.Scatterpolar(r=list(scores_cats.values()), theta=list(scores_cats.keys()), fill='toself'))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="Radar")
                    st.plotly_chart(fig_radar)

                # Update Sheet
                row_idx = df.index[df['Documento_ID'] == documento_id].tolist()[0] + 2
                sheet.update_cell(row_idx, sheet.row_values(1).index("Score_Total") + 1, total_score)
                sheet.update_cell(row_idx, sheet.row_values(1).index("Clasificacion") + 1, clasif)
                sheet.update_cell(row_idx, sheet.row_values(1).index("Comentarios") + 1, comentarios)
                sheet.update_cell(row_idx, sheet.row_values(1).index("Fecha_Eval") + 1, str(datetime.datetime.now()))

                # PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "Evaluación - GlamourCam Studios", ln=1, align="C")
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 8, f"ID: {documento_id}", ln=1)
                pdf.cell(0, 8, f"Score: {total_score:.2f}% - {clasif}", ln=1)
                # Add charts as text (or skip for simple)
                pdf.multi_cell(0, 8, f"Comentarios: {comentarios}")
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("Descargar PDF Evaluación", pdf_bytes, f"Eval_{documento_id}.pdf")

                # Email studio PDF
                msg = MIMEMultipart()
                msg['From'] = gmail_user
                msg['To'] = studio_email
                msg['Subject'] = f"Evaluación Completada: {documento_id}"
                msg.attach(MIMEText("PDF adjunto."))
                part = MIMEApplication(pdf_bytes, Name=f"Eval_{documento_id}.pdf")
                part['Content-Disposition'] = 'attachment; filename="eval.pdf"'
                msg.attach(part)
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(gmail_user, gmail_pass)
                server.sendmail(gmail_user, studio_email, msg.as_string())
                server.quit()
        else:

            st.error("ID no encontrado.")
