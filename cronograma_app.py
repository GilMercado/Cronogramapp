import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import date, timedelta, datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Cronograma de Producción", layout="wide")

# Autenticación con múltiples usuarios y roles
usuarios = {
    "gil": {"password": "123", "rol": "admin"}
},
    "lector": {"password": "view123", "rol": "lectura"}
}

usuario = st.text_input("👤 Usuario")
password = st.text_input("🔒 Contraseña", type="password")

if usuario not in usuarios or password != usuarios[usuario]["password"]:
    st.warning("🔐 Acceso restringido. Ingresa credenciales válidas.")
    st.stop()

rol_usuario = usuarios[usuario]["rol"]

st.title("📅 Generador de Cronograma de Producción Audiovisual")

with st.sidebar:
    st.header("Datos del Proyecto")
    proyecto = st.text_input("Nombre del Proyecto", "CHIPOCLES")
    fecha_inicio = st.date_input("Fecha de Inicio", date.today())
    fases = [
        ("ESCRITURA", "Cuarto de Escritura"),
        ("SOFT SOFT PRE", "PDT & PRESUPUESTO"),
        ("SOFT PRE", "GL"),
        ("PREPRODUCCIÓN", None),
        ("SHOOT", None),
        ("WRAP", None),
        ("POST", None)
    ]
    duraciones = {}
    for fase, subfase in fases:
        label = f"Duración de '{fase}' (días)"
        duraciones[fase] = st.number_input(label, min_value=1, value=5)

if st.button("Generar Cronograma"):
    registros = []
    fecha_actual = fecha_inicio
    timestamp = datetime.now().isoformat(timespec='seconds')

    for i, (fase, subfase) in enumerate(fases, start=1):
        duracion = duraciones[fase]
        fecha_final = fecha_actual + timedelta(days=duracion - 1)
        semanas = duracion / 7

        registros.append({
            "PROYECTO": proyecto,
            "#": i,
            "FASE": fase,
            "SUB-FASE": subfase if subfase else "-",
            "INICIO": fecha_actual,
            "FINAL": fecha_final,
            "DÍAS": duracion,
            "SEMANAS": round(semanas, 2),
            "EDITADO_POR": usuario,
            "FECHA_CAMBIO": timestamp
        })

        fecha_actual = fecha_final + timedelta(days=1)

    df = pd.DataFrame(registros)
    st.subheader("📄 Cronograma Generado")
    st.dataframe(df, use_container_width=True)

    # Gantt chart
    st.subheader("📊 Visualización Gantt")
    fig = px.timeline(
        df,
        x_start="INICIO",
        x_end="FINAL",
        y="FASE",
        color="FASE",
        title=f"Cronograma del Proyecto: {proyecto}"
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

    # Save to SQLite database
    conn = sqlite3.connect("cronogramas.db")
    df.to_sql("cronograma", conn, if_exists="append", index=False)
    conn.close()
    st.success("✅ Cronograma guardado en la base de datos.")

    # Save to Google Sheets
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Cronogramas_Produccion").sheet1
        sheet.append_rows(df.values.tolist(), value_input_option="USER_ENTERED")
        st.success("✅ Cronograma exportado a Google Sheets.")
    except Exception as e:
        st.warning(f"⚠️ Error exportando a Google Sheets: {e}")

    # CSV download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar como CSV", csv, f"cronograma_{proyecto}.csv", "text/csv")

    # PDF export
    def export_pdf(dataframe):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Cronograma: {proyecto}", ln=1, align="C")
        pdf.ln(5)
        for i, row in dataframe.iterrows():
            linea = f"{row['FASE']}: {row['INICIO']} - {row['FINAL']} ({row['DÍAS']} días)"
            pdf.cell(200, 10, txt=linea, ln=1)
        buffer = BytesIO()
        pdf.output(buffer)
        return buffer

    pdf_buffer = export_pdf(df)
    st.download_button("📄 Descargar como PDF", data=pdf_buffer.getvalue(), file_name=f"cronograma_{proyecto}.pdf", mime="application/pdf")

# Vista de todos los cronogramas guardados
st.header("📂 Cronogramas Guardados")
conn = sqlite3.connect("cronogramas.db")
df_all = pd.read_sql("SELECT * FROM cronograma", conn)
conn.close()

# Filtros
proyectos = df_all['PROYECTO'].unique().tolist()
selected_proyecto = st.selectbox("Filtrar por Proyecto", ["Todos"] + proyectos)

if selected_proyecto != "Todos":
    df_all = df_all[df_all['PROYECTO'] == selected_proyecto]

fecha_min = pd.to_datetime(df_all["INICIO"]).min().date()
fecha_max = pd.to_datetime(df_all["FINAL"]).max().date()
fecha_rango = st.date_input("Filtrar por Rango de Fechas", [fecha_min, fecha_max])

if len(fecha_rango) == 2:
    df_all = df_all[(pd.to_datetime(df_all["INICIO"]).dt.date >= fecha_rango[0]) &
                    (pd.to_datetime(df_all["FINAL"]).dt.date <= fecha_rango[1])]

# Edición directa
st.markdown("### ✏️ Editar Cronogramas")
if rol_usuario == "admin":
    edited_df = st.data_editor(df_all, use_container_width=True, num_rows="dynamic")
    if st.button("Guardar Cambios"):
        edited_df["EDITADO_POR"] = usuario
        edited_df["FECHA_CAMBIO"] = datetime.now().isoformat(timespec='seconds')
        conn = sqlite3.connect("cronogramas.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cronograma")
        edited_df.to_sql("cronograma", conn, if_exists="append", index=False)
        conn.close()
        st.success("✅ Cambios guardados correctamente en la base de datos.")
else:
    st.dataframe(df_all, use_container_width=True)
    st.info("🛈 Solo lectura. Inicia sesión como admin para editar.")

# Log de auditoría
st.markdown("### 📜 Historial de Cambios")
if "EDITADO_POR" in df_all.columns and "FECHA_CAMBIO" in df_all.columns:
    df_audit = df_all[["PROYECTO", "FASE", "EDITADO_POR", "FECHA_CAMBIO"]].drop_duplicates()
    df_audit = df_audit.sort_values("FECHA_CAMBIO", ascending=False)
    st.dataframe(df_audit, use_container_width=True)

# Importar cronogramas desde CSV
st.markdown("### ⬆️ Importar Cronograma desde CSV")
archivo_csv = st.file_uploader("Selecciona un archivo CSV para importar", type="csv")
if archivo_csv and rol_usuario == "admin":
    try:
        df_import = pd.read_csv(archivo_csv)
        df_import["EDITADO_POR"] = usuario
        df_import["FECHA_CAMBIO"] = datetime.now().isoformat(timespec='seconds')
        conn = sqlite3.connect("cronogramas.db")
        df_import.to_sql("cronograma", conn, if_exists="append", index=False)
        conn.close()
        st.success("✅ Archivo importado correctamente.")
    except Exception as e:
        st.error(f"❌ Error al importar archivo: {e}")
