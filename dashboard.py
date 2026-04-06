import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
from config import DB_NAME, CAMPOS


st.set_page_config(page_title="Monitoreo Agrícola v2.0", layout="wide", initial_sidebar_state="expanded")

# --- AJUSTE VISUAL PARA CELULAR ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE UTILIDAD ---

def fecha_en_español(fecha):
    meses = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
    dias = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
    
    dia_semana = dias[fecha.weekday()]
    mes = meses[fecha.month - 1]
    
    return f"{dia_semana} {fecha.day} de {mes}"

def grados_a_direccion(grados):
    if grados is None or pd.isna(grados): return "-"
    direcciones = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    indice = int((grados + 22.5) % 360 // 45)
    return direcciones[indice]

def cargar_datos(lote_seleccionado, modelo_recibido):
    conn = sqlite3.connect('monitoreo_agricola.db')
    
    mapeo_ids = {"recoleccion_ec": 1, "recoleccion_mr": 2, "recoleccion_yr": 3}
    m_id = mapeo_ids.get(modelo_recibido)

    # ESTA QUERY BUSCA LA ÚLTIMA HORA DE ACTIVIDAD Y TRAE TODO LO QUE SE SUBIÓ AHÍ
    # Usamos un margen de 1 hora para capturar los 4 días si el bot tardó en subir.
    query = """
    SELECT * FROM pronosticos_full 
    WHERE campo_id = (SELECT id FROM campos WHERE nombre = ?) 
      AND modelo_id = ?
      AND fecha_consulta >= (
          SELECT datetime(MAX(fecha_consulta), '-1 hour') 
          FROM pronosticos_full 
          WHERE campo_id = (SELECT id FROM campos WHERE nombre = ?)
            AND modelo_id = ?
      )
    ORDER BY fecha_pronosticada ASC
    """
    
    try:
        params = (lote_seleccionado, m_id, lote_seleccionado, m_id)
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df['fecha_pronosticada'] = pd.to_datetime(df['fecha_pronosticada'])
            # DEBUG PARA VOS:
            print(f"DEBUG Dashboard: Cargadas {len(df)} filas.")
            print(f"Días detectados: {df['fecha_pronosticada'].dt.date.unique()}")
            
        return df
    except Exception as e:
        print(f"Error en Dashboard: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- SIDEBAR (CONFIGURACIÓN) ---
st.sidebar.header("⚙️ Configuración")
lote_seleccionado = st.sidebar.selectbox("Seleccioná el Lote", [c['nombre'] for c in CAMPOS])

opciones_modelos = {
    "recoleccion_ec": "Europeo (ECMWF)",
    "recoleccion_mr": "Americano (GFS)",
    "recoleccion_yr": "Noruego (Met.no)"
}

modelo_tabla = st.sidebar.radio(
    "Modelo Meteorológico",
    options=list(opciones_modelos.keys()),
    format_func=lambda x: opciones_modelos[x]
)

# --- PROCESAMIENTO ---
df_completo = cargar_datos(lote_seleccionado, modelo_tabla)

# --- DIAGNÓSTICO ---
print("--- REVISIÓN DE LA TABLA COMPLETA ---")
print(df_completo[['fecha_consulta', 'fecha_pronosticada']].head(30))
print(f"Tipos de datos:\n{df_completo.dtypes}")
   
if not df_completo.empty:
    print(f"DEBUG: Fecha consulta detectada: {df_completo['fecha_consulta'].iloc[0]}")
    dias_disponibles = sorted(df_completo['fecha_pronosticada'].dt.date.unique())
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Navegación Temporal")

    # --- CAMBIO AQUÍ: Validación de rango ---
    if len(dias_disponibles) > 1:
        dia_elegido = st.sidebar.select_slider(
            "Deslizá para cambiar de día:",
            options=dias_disponibles,
            format_func=lambda x: x.strftime("%d/%m (Hoy)") if x == dias_disponibles[0] else x.strftime("%d/%m")
        )
    else:
        # Si hay un solo día, no dibujamos slider, solo fijamos la variable
        dia_elegido = dias_disponibles[0]
        st.sidebar.info(f"Visualizando: {dia_elegido.strftime('%d/%m')}")

    df_dia = df_completo[df_completo['fecha_pronosticada'].dt.date == dia_elegido].copy()

    # --- ENCABEZADO ---
    st.title("📊 Panel de Control Meteorológico")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📅 Pronóstico: {fecha_en_español(dia_elegido)}")
    with col2:
        st.info(f"**Lote:** {lote_seleccionado}\n\n**Modelo:** {opciones_modelos[modelo_tabla]}")

    # --- GRÁFICO TEMPERATURA VS ROCÍO (CONECTORES) ---
    st.subheader("🌡️ Temperatura vs Punto de Rocío")
    
    df_dia['dif'] = df_dia['temp_c'] - df_dia['punto_rocio_c']
    fig_temp = go.Figure()

    # 1. Dibujamos los conectores (Los palitos verticales)
    for i in range(len(df_dia)):
        row = df_dia.iloc[i]
        # Tus reglas de color exactas
        if row['dif'] < 8:
            color_p = "red"
        elif 8 <= row['dif'] < 10:
            color_p = "yellow"
        else:
            color_p = "green"

        fig_temp.add_shape(
            type="line",
            x0=row['fecha_pronosticada'], x1=row['fecha_pronosticada'],
            y0=row['punto_rocio_c'], y1=row['temp_c'],
            line=dict(color=color_p, width=3),
            layer="below"
        )

    # 2. Líneas y Puntos
    fig_temp.add_trace(go.Scatter(
        x=df_dia['fecha_pronosticada'], y=df_dia['temp_c'],
        name='temp_c', mode='lines+markers',
        line=dict(color='#ff5757', width=1.5),
        marker=dict(size=6, color='#ff5757')
    ))
    
    fig_temp.add_trace(go.Scatter(
        x=df_dia['fecha_pronosticada'], y=df_dia['punto_rocio_c'],
        name='punto_rocio_c', mode='lines+markers',
        line=dict(color='#3ac0ff', width=1.5),
        marker=dict(size=6, color='#3ac0ff')
    ))

    # 3. Línea de Alerta 2°C
    fig_temp.add_shape(
        type="line",
        x0=df_dia['fecha_pronosticada'].min(), x1=df_dia['fecha_pronosticada'].max(),
        y0=2, y1=2, line=dict(color="orange", width=2, dash="dash")
    )

    # --- CONFIGURACIÓN FINAL PARA MÓVIL ---
    fig_temp.update_layout(
        template="plotly_dark",
        hovermode="x unified",
        xaxis_title="Hora",
        yaxis_title="Temperatura (°C)",
        height=450, # Altura fija para que no se vea "aplastado" en el celu
        margin=dict(l=10, r=10, t=30, b=60), # Más margen abajo para la leyenda
        legend=dict(
            orientation="h", 
            yanchor="bottom", y=-0.5, # Mandamos la leyenda abajo del gráfico
            xanchor="center", x=0.5
        )
    )
        
    # Esto hace que las horas no se pisen en pantallas chicas
    fig_temp.update_xaxes(dtick=3600000 * 3, tickformat="%H:%M") 

    # IMPORTANTE: El config={'displayModeBar': False} apaga la barrita de herramientas 
    # que molesta cuando querés hacer scroll con el dedo.
    st.plotly_chart(fig_temp, use_container_width=True, config={'displayModeBar': False})

    # --- GRÁFICO DE LLUVIA ---
    if df_dia['lluvia_mm'].sum() > 0:
        fig_lluvia = px.bar(df_dia, x='fecha_pronosticada', y='lluvia_mm',
                           title="Precipitación Estimada (mm)",
                           color_discrete_sequence=['#00CC96'], text="lluvia_mm")
        fig_lluvia.update_traces(textposition="outside", texttemplate='%{text}mm')
        fig_lluvia.update_layout(template="plotly_dark")
        st.plotly_chart(fig_lluvia, use_container_width=True)
    else:
        st.success("No se detectan lluvias para este día.")

    # --- TABLA DE DATOS DETALLADOS ---
    st.subheader("📊 Desglose de Datos")
    df_final = df_dia.copy()
    df_final['Viento_Dir'] = df_final['viento_dir_deg'].apply(grados_a_direccion)
    
    # Columnas a quitar
    borrar = ['id', 'nombre_lote', 'dias_antelacion', 'lluvia', 'viento_dir_deg', 'dif', 'nombre_campo', 'fecha_consulta']
    df_final = df_final.drop(columns=[c for c in borrar if c in df_final.columns])
    
    # Reordenar viento al lado de kmh
    columnas = list(df_final.columns)
    if 'viento_kmh' in columnas and 'Viento_Dir' in columnas:
        columnas.remove('Viento_Dir')
        idx = columnas.index('viento_kmh')
        columnas.insert(idx + 1, 'Viento_Dir')
        df_final = df_final[columnas]
    
    st.dataframe(df_final, use_container_width=True, hide_index=True)

else:
    st.warning(f"⚠️ No hay datos para el modelo {opciones_modelos[modelo_tabla]} en el lote {lote_seleccionado}.")
