import requests
from datetime import datetime, timedelta
from config import USER_AGENT

def obtener_yr(lat, lon, nombre_campo):
    """Motor Met.no (Modelo Noruego)"""
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={lat}&lon={lon}"
    headers = {'User-Agent': USER_AGENT}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        data_json = res.json()
        timeseries = data_json['properties']['timeseries']
        ahora = datetime.now()
        registros = []
        
        for ts in timeseries:
            fecha_dt = datetime.strptime(ts['time'], "%Y-%m-%dT%H:%M:%SZ") - timedelta(hours=3)
            diff = (fecha_dt.date() - ahora.date()).days
            
            if 0 <= diff <= 3:
                data = ts.get('data', {})
                det = data.get('instant', {}).get('details', {})
                
                # El orden debe coincidir EXACTO con tu database.py
                registros.append((
                    nombre_campo, 
                    fecha_dt.strftime("%Y-%m-%d %H:%M"),
                    diff,
                    det.get('air_temperature'),
                    det.get('dew_point_temperature'),
                    det.get('relative_humidity'),
                    round(det.get('wind_speed', 0) * 3.6, 1), # km/h
                    data.get('next_1_hours', {}).get('details', {}).get('precipitation_amount', 0),
                    det.get('air_pressure_at_sea_level'), # PRESIÓN
                    det.get('wind_from_direction'),        # DIRECCIÓN GRADOS
                    ahora.strftime("%Y-%m-%d %H:%M")
                ))
        return registros
    except Exception as e:
        print(f"Error YR en {nombre_campo}: {e}")
        return []

def procesar_open_meteo(url, nombre_campo, label):
    """Procesador para GFS y ECMWF"""
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        h = res.json()['hourly']
        ahora = datetime.now()
        registros = []
        
        for i in range(len(h['time'])):
            t_str = h['time'][i].replace("T", " ")
            fecha_dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M")
            diff = (fecha_dt.date() - ahora.date()).days
            
            if 0 <= diff <= 3:
                registros.append((
                    nombre_campo, 
                    fecha_dt.strftime("%Y-%m-%d %H:%M"), 
                    diff,
                    h['temperature_2m'][i], 
                    h['dew_point_2m'][i], 
                    h['relative_humidity_2m'][i], 
                    h['wind_speed_10m'][i], 
                    h['precipitation'][i],
                    h['pressure_msl'][i],           # PRESIÓN
                    h['wind_direction_10m'][i],     # DIRECCIÓN GRADOS
                    ahora.strftime("%Y-%m-%d %H:%M")
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