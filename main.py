# main.py
from config import CAMPOS
import database as db
import weather_service as ws
from datetime import datetime

def ejecutar_sincronizacion():
    db.inicializar_db()
    
    for campo in CAMPOS:
        print(f"--- Sincronizando Lote: {campo['nombre']} ---")
        
        # 1. Obtenemos datos de la Capa de Servicio
        # (Aquí llamarías también a obtener_yr)
        datos_om = ws.obtener_datos_clima(campo['lat'], campo['lon'], campo['nombre'])
        
        # 2. Guardamos mediante la Capa de Datos
        db.guardar_registros(datos_om['mr'], "recoleccion_mr")
        db.guardar_registros(datos_om['ec'], "recoleccion_ec")
        db.guardar_registros(datos_om['yr'], "recoleccion_yr")
        
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Proceso finalizado.")

if __name__ == "__main__":
    ejecutar_sincronizacion()