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
            FOREIGN KEY (modelo_id) REFERENCES modelos (id),
            UNIQUE(campo_id, modelo_id, fecha_pronosticada)
        )
    """)
    conn.commit()
    conn.close()

def guardar_registros(lista_datos, nombre_tabla_alias):
    if not lista_datos: return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Mapeo simple
    modelos = {"recoleccion_ec": 1, "recoleccion_mr": 2, "recoleccion_yr": 3}
    m_id = modelos.get(nombre_tabla_alias)

    for d in lista_datos:
        nombre_lote = d[0]
            
        # 1. BUSCAR EL ID REAL (Evita que el autoincremento salte)
        cursor.execute("SELECT id FROM campos WHERE nombre = ?", (nombre_lote,))
        resultado = cursor.fetchone()
            
        if resultado:
            c_id = resultado[0]
        else:
            # 2. SOLO SI NO EXISTE, LO CREAMOS
            cursor.execute("INSERT INTO campos (nombre) VALUES (?)", (nombre_lote,))
            c_id = cursor.lastrowid

         # 3. INSERTAR EL PRONÓSTICO
        try:
             cursor.execute("""
                INSERT INTO pronosticos_full (
                    campo_id, modelo_id, fecha_pronosticada, dias_antelacion, 
                    temp_c, punto_rocio_c, humedad_relativa, viento_kmh, 
                    lluvia_mm, presion_hpa, viento_dir_deg, fecha_consulta
                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c_id, m_id, d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10]))
        except sqlite3.IntegrityError:
            continue
        except Exception as e:
            print(f"Error específico insertando: {e}")

    conn.commit()
    conn.close()
    print(f"Sincronización terminada para {nombre_tabla_alias}")