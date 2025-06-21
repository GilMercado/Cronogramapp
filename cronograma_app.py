import streamlit as st 
import pandas as pd 
from openpyxl import load_workbook 
from datetime import date 
import tempfile

st.set_page_config(page_title="Actualizar Cronograma", layout="centered") 
st.title("🎬 Actualizador de Cronograma de Producción")

archivo = st.file_uploader("📤 Sube el archivo original de cronograma (.xlsx)", type="xlsx")

if archivo: 
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") 
    temp.write(archivo.read()) 
    temp.seek(0)

wb = load_workbook(temp.name)
ws = wb.active

st.markdown("Modifica la información del proyecto sin alterar el formato del archivo original.")

nombre_proyecto = st.text_input("Nombre del Proyecto", value="Nuevo Proyecto")
fecha_actualizacion = st.date_input("Fecha de Actualización", date.today())

inicio_filas = 5
fin_filas = 18

for fila in range(inicio_filas, fin_filas + 1):
    fase = ws[f"C{fila}"].value
    if fase:
        nueva_fecha_inicio = st.date_input(f"Inicio de '{fase}'", value=date.today(), key=f"ini_{fila}")
        nueva_fecha_fin = st.date_input(f"Fin de '{fase}'", value=date.today(), key=f"fin_{fila}")
        ws[f"G{fila}"] = nueva_fecha_inicio
        ws[f"H{fila}"] = nueva_fecha_fin

ws["E2"] = f"FECHA DE ACTUALIZACIÓN: {fecha_actualizacion.strftime('%d.%m.%y')}"
ws["B1"] = nombre_proyecto

nombre_salida = f"cronograma_actualizado_{nombre_proyecto}.xlsx"
wb.save(nombre_salida)

with open(nombre_salida, "rb") as file:
    st.success("✅ Archivo actualizado correctamente.")
    st.download_button(
        "📥 Descargar archivo Excel actualizado",
        data=file.read(),
        file_name=nombre_salida,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

