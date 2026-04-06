import sqlite3

DB_NAME = 'monitoreo_agricola.db'

def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Crear tablas
    cursor.execute("CREATE TABLE IF NOT EXISTS campos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS modelos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)")
    
    # 2. IMPORTANTE: Insertar los modelos. Sin esto, el resto falla.
    modelos_base = [('ECMWF',), ('GFS',), ('MET_NORWAY',)]
    cursor.executemany("INSERT OR IGNORE INTO modelos (nombre) VALUES (?)", modelos_base)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pronosticos_full (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campo_id INTEGER,
        modelo_id INTEGER,
        fecha_pronosticada TEXT,
        dias_antelacion INTEGER,
        temp_c REAL,
        punto_rocio_c REAL,
        humedad_relativa INTEGER,
        viento_kmh REAL,
        viento_dir_deg INTEGER,
        lluvia_mm REAL,
        presion_hpa REAL,
        fecha_consulta TEXT,
        FOREIGN KEY (campo_id) REFERENCES campos (id),
        FOREIGN KEY (modelo_id) REFERENCES modelos (id)
        )
    """)
    conn.commit()
    conn.close()

def guardar_registros(lista_datos, nombre_tabla_alias):
    if not lista_datos: return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ASIGNACIÓN FIJA DE IDs (Basado en tu tabla 'modelos')
    modelos = {"recoleccion_ec": 1, "recoleccion_mr": 2, "recoleccion_yr": 3}
    m_id = modelos.get(nombre_tabla_alias)

    for d in lista_datos:
        nombre_lote = d[0]
        
        # Obtener el ID del campo
        cursor.execute("SELECT id FROM campos WHERE nombre = ?", (nombre_lote,))
        resultado = cursor.fetchone()
        if resultado:
            c_id = resultado[0]
        else:
            # 2. SI NO EXISTE, LO CREAMOS AL VUELO
            # Esto evita que el campo_id sea 0
            cursor.execute("INSERT INTO campos (nombre) VALUES (?)", (nombre_lote,))
            c_id = cursor.lastrowid
            print(f"Nuevo campo registrado: {nombre_lote} (ID: {c_id})")

        try:
            # ORDEN EXACTO SEGÚN TU IMAGEN (image_b5afb4.png)
            cursor.execute("""
                INSERT INTO pronosticos_full (
                    campo_id, modelo_id, fecha_pronosticada, dias_antelacion, 
                    temp_c, punto_rocio_c, humedad_relativa, viento_kmh, 
                    viento_dir_deg, lluvia_mm, presion_hpa, fecha_consulta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c_id,  # 1. campo_id
                m_id,  # 2. modelo_id (VALOR FIJO 1, 2 o 3)
                d[1],  # 3. fecha_pronosticada
                d[2],  # 4. dias_antelacion
                d[3],  # 5. temp_c
                d[4],  # 6. punto_rocio_c
                d[5],  # 7. humedad_relativa
                d[6],  # 8. viento_kmh
                d[7],  # 9. viento_dir_deg
                d[8],  # 10. lluvia_mm
                d[9],  # 11. presion_hpa
                d[10]  # 12. fecha_consulta
            ))
        except Exception as e:
            print(f"Error: {e}")

    conn.commit()
    conn.close()
    print(f"Sincronización terminada para {nombre_tabla_alias}")