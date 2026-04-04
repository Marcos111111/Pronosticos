import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import DB_NAME, CAMPOS

# Configuración de página
st.set_page_config(page_title="Monitoreo Agrícola v2.0", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS Y TÍTULO ---
st.title("📊 Panel de Control Meteorológico")
st.markdown(f"**Base de datos:** `{DB_NAME}` | **Estado:** Operacional ✅")

# --- CAPA DE DATOS ---
def grados_a_direccion(grados):
    if grados is None: return "-"
    # Definimos los sectores (cada uno de 45°)
    direcciones = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    # Sumamos 22.5 para centrar el rango y dividimos por 45
    indice = int((grados + 22.5) % 360 // 45)
    return direcciones[indice]

def cargar_datos(tabla, lote):
    try:
        conn = sqlite3.connect(DB_NAME)
        # Traemos solo la última foto completa (última fecha_consulta)
        query = f"""
            SELECT * FROM {tabla} 
            WHERE nombre_campo = '{lote}' 
            AND fecha_consulta = (SELECT MAX(fecha_consulta) FROM {tabla} WHERE nombre_campo = '{lote}')
            ORDER BY fecha_pronosticada ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['fecha_pronosticada'] = pd.to_datetime(df['fecha_pronosticada'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al conectar con la DB: {e}")
        return pd.DataFrame()

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("⚙️ Configuración")

# 1. Selector de Lote
lote_seleccionado = st.sidebar.selectbox("Seleccioná el Lote", [c['nombre'] for c in CAMPOS])

# 2. Selector de Modelo (Diccionario para evitar nombres repetidos)
opciones_modelos = {
    "recoleccion_ec": "Europeo (ECMWF)",
    "recoleccion_mr": "Americano (GFS)",
    "recoleccion_yr": "Noruego (Met.no)"
}

modelo_tabla = st.sidebar.radio(
    "Modelo Meteorológico",
    options=list(opciones_modelos.keys()),
    format_func=lambda x: opciones_modelos[x],
    key="modelo_radio"
)

# --- PROCESAMIENTO ---
df_completo = cargar_datos(modelo_tabla, lote_seleccionado)

if not df_completo.empty:
    # 3. Navegador de Días (Slider)
    dias_disponibles = df_completo['fecha_pronosticada'].dt.date.unique()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Navegación Temporal")
    
    dia_elegido = st.sidebar.select_slider(
        "Deslizá para cambiar de día:",
        options=dias_disponibles,
        format_func=lambda x: x.strftime("%d/%m (Hoy)") if x == dias_disponibles[0] else x.strftime("%d/%m")
    )

    # Filtramos el DataFrame para mostrar solo el día seleccionado
    df_dia = df_completo[df_completo['fecha_pronosticada'].dt.date == dia_elegido].copy()

    # --- VISUALIZACIÓN ---
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"📅 Pronóstico: {dia_elegido.strftime('%A %d de %B')}")
    with col2:
        st.info(f"**Lote:** {lote_seleccionado}\n\n**Modelo:** {opciones_modelos[modelo_tabla]}")

    # 1. Buscamos la hora actual del sistema
    hora_actual_sistema = datetime.now().hour
    
    # 2. Filtramos el DataFrame para encontrar la fila que coincide con esta hora
    df_ahora = df_dia[df_dia['fecha_pronosticada'].dt.hour == hora_actual_sistema]

    if not df_ahora.empty:
        actual = df_ahora.iloc[0]
        
        # --- PROCESAMOS LA DIRECCIÓN DEL VIENTO ---
        # Usamos la función que pusiste arriba del todo
        direccion_letras = grados_a_direccion(actual['viento_dir_deg'])
        
        # Creamos 5 columnas para que entre todo cómodo
        c1, c2, c3, c4, c5 = st.columns(5)
        
        c1.metric("Temperatura", f"{actual['temp_c']}°C")
        c2.metric("Punto Rocío", f"{actual['punto_rocio_c']}°C")
        c3.metric("Presión", f"{actual['presion_hpa']} hPa")
        c4.metric("Vel. Viento", f"{actual['viento_kmh']} km/h")
        c5.metric("Dir. Viento", direccion_letras)
    else:
        # Si por alguna razón no hay datos de esta hora, mostramos un aviso
        st.write("Seleccioná 'Hoy' en el navegador para ver las métricas en tiempo real.")

    # --- GRÁFICO DE TEMPERATURA Y ROCÍO (VERSIÓN LIMPIA CON MÁS REFERENCIAS) ---
    st.subheader(f"🌡️ Análisis Térmico: {lote_seleccionado}")

    fig_temp = px.line(df_dia, 
                    x='fecha_pronosticada', 
                    y=['temp_c', 'punto_rocio_c'],
                    title=f"Temperatura vs Punto de Rocío - {dia_elegido.strftime('%d/%m')}",
                    markers=True,
                    line_shape="spline",
                    labels={'value': 'Grados (°C)', 'variable': 'Medición'},
                    color_discrete_map={'temp_c': '#FF4B4B', 'punto_rocio_c': '#00BFFF'})
    # AJUSTE DE INTERVALOS EN EL EJE X (TIEMPO)
    fig_temp.update_xaxes(
        dtick=3600000,  #1 hora en ms
        tickformat="%H:%M", # Formato de 24hs (Ej: 02:00, 04:00...)
        gridcolor='rgba(255, 255, 255, 0.1)',
        showgrid=True
    )

    # AGREGAMOS LAS REFERENCIAS INTERMEDIAS AQUÍ:
    fig_temp.update_yaxes(
        dtick=2,             # Una línea de cuadrícula CADA 1 GRADO
        gridcolor='rgba(255, 255, 255, 0.15)', # Cuadrícula visible pero sutil
        zeroline=True, 
        zerolinecolor='white', # El cero bien marcado
        zerolinewidth=2
    )

    # Mantenemos las líneas de alerta que ya teníamos
    fig_temp.add_hline(y=2, line_dash="dot", line_color="orange", annotation_text="Alerta 2°C")
    fig_temp.add_hline(y=0, line_color="blue", line_width=1.5)

    fig_temp.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Hora",
        yaxis_title="Temperatura (°C)"
    )

    st.plotly_chart(fig_temp, use_container_width=True)

    # Gráfico de Precipitación
    if df_dia['lluvia_mm'].sum() > 0:
        fig_lluvia = px.bar(df_dia, x='fecha_pronosticada', y='lluvia_mm',
                           title="Precipitación Estimada (mm)",
                           color_discrete_sequence=['#00CC96'],
                           text="lluvia_mm")
        fig_lluvia.update_traces(textposition="outside", texttemplate='%{text}mm')
        st.plotly_chart(fig_lluvia, use_container_width=True)
    else:
        st.success("No se detectan lluvias para este día en este modelo.")

# --- TABLA DE DATOS DETALLADOS ---
st.subheader("📊 Desglose de Datos")

if not df_dia.empty:
    # 1. Forzamos una copia nueva para que no use el caché
    df_final = df_dia.copy()
    
    # 2. Agregamos las letras (Asegurate que la función esté definida arriba)
    df_final['Viento_Dir'] = df_final['viento_dir_deg'].apply(grados_a_direccion)
    
    # 3. Lista de columnas que QUEREMOS BORRAR (revisá que se llamen así en tu DB)
    borrar = ['id', 'nombre_lote', 'dias_antelacion', 'lluvia', 'viento_dir_deg']
    
    # Borramos de forma segura
    df_final = df_final.drop(columns=[c for c in borrar if c in df_final.columns])
    
    # 4. Reordenar: Viento_Dir al lado de viento_kmh
    columnas = list(df_final.columns)
    if 'viento_kmh' in columnas and 'Viento_Dir' in columnas:
        columnas.remove('Viento_Dir')
        idx = columnas.index('viento_kmh')
        columnas.insert(idx + 1, 'Viento_Dir')
        df_final = df_final[columnas]
    
    # 5. MOSTRAR LA TABLA NUEVA
    st.dataframe(df_final, use_container_width=True, hide_index=True)

else:
    st.warning(f"⚠️ No hay datos para el modelo {opciones_modelos[modelo_tabla]} en el lote {lote_seleccionado}.")
    st.info("Asegurate de haber ejecutado `main.py` recientemente.")
