import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
from config import DB_NAME, CAMPOS

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitoreo Agrícola v2.0", layout="wide", initial_sidebar_state="expanded")

# Estilo para mejorar visualización en móviles
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    .stDataFrame { font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---

def fecha_en_español(fecha):
    meses = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
    dias = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
    return f"{dias[fecha.weekday()]} {fecha.day} de {meses[fecha.month - 1]}"

def grados_a_direccion(grados):
    if grados is None or pd.isna(grados): return "-"
    direcciones = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return direcciones[int((grados + 22.5) % 360 // 45)]

def cargar_datos(lote_nombre, modelo_alias):
    conn = sqlite3.connect(DB_NAME)
    
    # Sincronizado con inicializar_db()
    mapeo_ids = {"recoleccion_ec": 1, "recoleccion_mr": 2, "recoleccion_yr": 3}
    m_id = mapeo_ids.get(modelo_alias)

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
        df = pd.read_sql_query(query, conn, params=(lote_nombre, m_id, lote_nombre, m_id))
        if not df.empty:
            df['fecha_pronosticada'] = pd.to_datetime(df['fecha_pronosticada'])
            df['fecha_consulta'] = pd.to_datetime(df['fecha_consulta'])
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
lote_sel = st.sidebar.selectbox("Seleccioná el Lote", [c['nombre'] for c in CAMPOS])

opciones_modelos = {
    "recoleccion_ec": "Europeo (ECMWF)",
    "recoleccion_mr": "Americano (GFS)",
    "recoleccion_yr": "Noruego (Met.no)"
}

mod_alias = st.sidebar.radio("Modelo Meteorológico", options=list(opciones_modelos.keys()), 
                             format_func=lambda x: opciones_modelos[x])

# --- LÓGICA PRINCIPAL ---
df_completo = cargar_datos(lote_sel, mod_alias)

if not df_completo.empty:
    dias_disponibles = sorted(df_completo['fecha_pronosticada'].dt.date.unique())
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Navegación")
    
    if len(dias_disponibles) > 1:
        dia_elegido = st.sidebar.select_slider(
            "Cambiar día:", 
            options=dias_disponibles,
            format_func=lambda x: x.strftime("%d/%m (Hoy)") if x == dias_disponibles[0] else x.strftime("%d/%m")
        )
    else:
        dia_elegido = dias_disponibles[0]
        st.sidebar.info(f"Día: {dia_elegido.strftime('%d/%m')}")

    df_dia = df_completo[df_completo['fecha_pronosticada'].dt.date == dia_elegido].copy()

    # --- ENCABEZADO ---
    st.title("📊 Panel Meteorológico")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"📅 {fecha_en_español(dia_elegido)}")
    with c2:
        st.info(f"**Lote:** {lote_sel} | **Modelo:** {opciones_modelos[mod_alias].split(' ')[0]}")

    # --- GRÁFICO T° vs ROCÍO ---
    st.subheader("🌡️ Temperatura y Humedad")
    df_dia['dif'] = df_dia['temp_c'] - df_dia['punto_rocio_c']
    
    fig_temp = go.Figure()

    # Conectores de alerta (Delta T)
    for _, row in df_dia.iterrows():
        color_l = "red" if row['dif'] < 8 else ("yellow" if row['dif'] < 10 else "green")
        fig_temp.add_shape(type="line", x0=row['fecha_pronosticada'], x1=row['fecha_pronosticada'],
                           y0=row['punto_rocio_c'], y1=row['temp_c'],
                           line=dict(color=color_l, width=3), layer="below")

    fig_temp.add_trace(go.Scatter(x=df_dia['fecha_pronosticada'], y=df_dia['temp_c'], name='Temp C', 
                                 line=dict(color='#ff5757', width=2), mode='lines+markers'))
    fig_temp.add_trace(go.Scatter(x=df_dia['fecha_pronosticada'], y=df_dia['punto_rocio_c'], name='Rocío C', 
                                 line=dict(color='#3ac0ff', width=2), mode='lines+markers'))

    fig_temp.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=20, b=20),
                          legend=dict(orientation="h", y=-0.2), hovermode="x unified")
    st.plotly_chart(fig_temp, use_container_width=True, config={'displayModeBar': False})

    # --- LLUVIA Y VIENTO ---
    col_lluvia, col_viento = st.columns(2)
    
    with col_lluvia:
        total_lluvia = df_dia['lluvia_mm'].sum()
        if total_lluvia > 0:
            fig_ll = px.bar(df_dia, x='fecha_pronosticada', y='lluvia_mm', title=f"Lluvia: {total_lluvia:.1f}mm",
                            color_discrete_sequence=['#00CC96'])
            fig_ll.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_ll, use_container_width=True)
        else:
            st.write("✅ Sin lluvias previstas")

    with col_viento:
        v_max = df_dia['viento_kmh'].max()
        fig_v = px.line(df_dia, x='fecha_pronosticada', y='viento_kmh', title=f"Viento Máx: {v_max} km/h",
                        color_discrete_sequence=['#AB63FA'])
        fig_v.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_v, use_container_width=True)

    # --- TABLA DETALLADA ---
    with st.expander("Ver Datos Completos"):
        df_tab = df_dia.copy()
        df_tab['Dir'] = df_tab['viento_dir_deg'].apply(grados_a_direccion)
        df_tab['Hora'] = df_tab['fecha_pronosticada'].dt.strftime('%H:%M')
        
        # Seleccionamos y renombramos para que se vea limpio
        cols = {'Hora': 'Hora', 'temp_c': 'T°C', 'punto_rocio_c': 'Rocío', 
                'humedad_relativa': 'H %', 'viento_kmh': 'V.kmh', 'Dir': 'Dir', 
                'lluvia_mm': 'Lluvia', 'presion_hpa': 'Presión'}
        st.dataframe(df_tab[cols.keys()].rename(columns=cols), hide_index=True, use_container_width=True)

else:
    st.warning("No se encontraron datos. Asegurate de que el archivo `main.py` haya terminado de correr correctamente.")
    st.info("Tip: Verificá que el archivo `monitoreo_agricola.db` exista en la carpeta del proyecto.")