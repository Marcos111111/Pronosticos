import sqlite3
from config import DB_NAME

def inicializar_db():
    """Crea las tablas con la nueva estructura de 11 columnas"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Lista de tablas para los 3 modelos
    tablas = ['recoleccion_yr', 'recoleccion_mr', 'recoleccion_ec']
    
    for tabla in tablas:
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {tabla} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_campo TEXT,
            fecha_pronosticada TEXT,
            dias_antelacion INTEGER,
            temp_c REAL,
            punto_rocio_c REAL,
            humedad_relativa INTEGER,
            viento_kmh REAL,
            lluvia_mm REAL,
            presion_hpa REAL,        -- Nueva (Columna 9)
            viento_dir_deg INTEGER,  -- Nueva (Columna 10)
            fecha_consulta TEXT      -- (Columna 11)
        )''')
    
    conn.commit()
    conn.close()

def guardar_registros(datos, tabla):
    """Guarda la lista de tuplas en la tabla especificada"""
    if not datos:
        return
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # IMPORTANTE: 11 signos de pregunta para las 11 columnas (excluyendo el ID autoincremental)
    query = f'''INSERT INTO {tabla} (
                nombre_campo, fecha_pronosticada, dias_antelacion, 
                temp_c, punto_rocio_c, humedad_relativa, 
                viento_kmh, lluvia_mm, presion_hpa, 
                viento_dir_deg, fecha_consulta) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    
    try:
        cursor.executemany(query, datos)
        conn.commit()
    except Exception as e:
        print(f"Error al guardar en {tabla}: {e}")
    finally:
        conn.close()