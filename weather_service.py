import requests
from datetime import datetime, timedelta
from config import USER_AGENT

def obtener_yr(lat, lon, nombre_campo):
    """Motor Met.no - Guarda día completo + pronóstico (11 campos)"""
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={lat}&lon={lon}"
    headers = {'User-Agent': USER_AGENT}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        data_json = res.json()
        timeseries = data_json['properties']['timeseries']
        
        # 'ahora' solo para la marca de consulta y límite de 4 días
        ahora = datetime.now().replace(minute=0, second=0, microsecond=0)
        inicio_hoy = ahora.replace(hour=0) # Desde las 00:00 de hoy
        limite_futuro = ahora + timedelta(days=4)
        
        registros = []
        for ts in timeseries:
            fecha_dt = datetime.strptime(ts['time'], "%Y-%m-%dT%H:%M:%SZ") - timedelta(hours=3)
            
            # FILTRO: Desde el inicio de hoy hasta 4 días adelante
            if inicio_hoy <= fecha_dt <= limite_futuro:
                data = ts.get('data', {})
                det = data.get('instant', {}).get('details', {})
                diff_dias = (fecha_dt.date() - ahora.date()).days
                
                # TUPLA COMPLETA DE 11 ELEMENTOS
                registros.append((
                    nombre_campo,                                   # 1
                    fecha_dt.strftime("%Y-%m-%d %H:%M"),            # 2
                    diff_dias,                                      # 3
                    det.get('air_temperature'),                     # 4
                    det.get('dew_point_temperature'),               # 5
                    det.get('relative_humidity'),                   # 6
                    round(det.get('wind_speed', 0) * 3.6, 1),       # 7
                    data.get('next_1_hours', {}).get('details', {}).get('precipitation_amount', 0), # 8
                    det.get('air_pressure_at_sea_level'),           # 9
                    det.get('wind_from_direction'),                 # 10
                    ahora.strftime("%Y-%m-%d %H:%M")                # 11
                ))
        return registros
    except Exception as e:
        print(f"Error YR en {nombre_campo}: {e}")
        return []

def procesar_open_meteo(url, nombre_campo, label):
    """Procesador GFS/ECMWF - Guarda día completo + pronóstico (11 campos)"""
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        h = res.json()['hourly']
        
        ahora = datetime.now().replace(minute=0, second=0, microsecond=0)
        inicio_hoy = ahora.replace(hour=0) # Desde las 00:00 de hoy
        limite_futuro = ahora + timedelta(days=4)
        registros = []
        for i in range(len(h['time'])):
            t_str = h['time'][i].replace("T", " ")
            fecha_dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M")
            
            # FILTRO: Captura todo el día de hoy + los próximos 4 días
            if inicio_hoy <= fecha_dt <= limite_futuro:
                diff = (fecha_dt.date() - ahora.date()).days
                
                # TUPLA COMPLETA DE 11 ELEMENTOS
                registros.append((
                    nombre_campo,                          # 1
                    fecha_dt.strftime("%Y-%m-%d %H:%M"),   # 2
                    diff,                                  # 3
                    h['temperature_2m'][i],                # 4
                    h['dew_point_2m'][i],                  # 5
                    h['relative_humidity_2m'][i],          # 6
                    h['wind_speed_10m'][i],                # 7
                    h['precipitation'][i],                 # 8
                    h['pressure_msl'][i],                  # 9
                    h['wind_direction_10m'][i],            # 10
                    ahora.strftime("%Y-%m-%d %H:%M")       # 11
                ))
        return registros
    except Exception as e:
        print(f"Error {label} en {nombre_campo}: {e}")
        return []

def obtener_datos_clima(lat, lon, nombre_campo):
    """Orquestador con nuevas variables"""
    # URLs actualizadas con pressure_msl y wind_direction_10m
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = (f"&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,"
              f"precipitation,wind_speed_10m,pressure_msl,wind_direction_10m" # <--- NUEVOS
              f"&timezone=America%2FArgentina%2FBuenos_Aires&forecast_days=4&past_days=1")

    url_mr = f"{base_url}?latitude={lat}&longitude={lon}{params}&models=gfs_seamless"
    url_ec = f"{base_url}?latitude={lat}&longitude={lon}{params}&models=ecmwf_ifs025"

    return {
        "yr": obtener_yr(lat, lon, nombre_campo),
        "mr": procesar_open_meteo(url_mr, nombre_campo, "GFS"),
        "ec": procesar_open_meteo(url_ec, nombre_campo, "ECMWF")
    }