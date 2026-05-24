import requests
import json
import webbrowser
import os
import xml.etree.ElementTree as ET

URL_DGT = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/xml,text/xml,*/*",
}

def local_name(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag

def norm_name(tag):
    return local_name(tag).lower()

def first_text(elem, posibles):
    posibles = {p.lower() for p in posibles}
    for child in elem.iter():
        if norm_name(child.tag) in posibles and child.text and child.text.strip():
            return child.text.strip()
    return None

import unicodedata

def normalizar_texto(txt):
    if not txt:
        return ""
    txt = str(txt).lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    return txt

def all_text(elem):
    return " ".join(t.strip() for t in elem.itertext() if t and t.strip())

from datetime import datetime, timezone
from collections import Counter

def parse_fecha_dgt(txt):
    if not txt:
        return None

    txt = txt.strip()

    try:
        if txt.endswith("Z"):
            txt = txt[:-1] + "+00:00"
        return datetime.fromisoformat(txt)
    except Exception:
        return None


def get_xsi_type(elem):
    for k, v in elem.attrib.items():
        if k.endswith("}type") or k == "type":
            return v or ""
    return ""


def extraer_incidencias_dgt():
    r = requests.get(URL_DGT, headers=headers, timeout=30)

    print("HTTP:", r.status_code)
    print("Content-Type:", r.headers.get("content-type"))
    print("Inicio respuesta:", r.text[:300])

    r.raise_for_status()

    root = ET.fromstring(r.content)

    puntos = []
    vistos = set()
    contador_tipos = Counter()
    contador_obstruccion = Counter()

    ahora = datetime.now(timezone.utc)

    for record in root.iter():
        if norm_name(record.tag) != "situationrecord":
            continue

        tipo_xsi = get_xsi_type(record)
        tipo_xsi_l = tipo_xsi.lower()

        tipo_obstruccion = first_text(record, [
            "vehicleObstructionType",
            "obstructionType"
        ])

        tipo_obstruccion_l = (tipo_obstruccion or "").lower()

        contador_tipos[tipo_xsi or "SIN_TIPO"] += 1
        contador_obstruccion[tipo_obstruccion or "SIN_OBSTRUCTION_TYPE"] += 1

        lat = first_text(record, ["latitude"])
        lon = first_text(record, ["longitude"])

        if not lat or not lon:
            continue

        status = first_text(record, ["validityStatus"])
        status_l = (status or "").lower()

        inicio = first_text(record, [
            "overallStartTime",
            "situationRecordCreationTime"
        ])

        fin = first_text(record, [
            "overallEndTime",
            "validityTimeSpecificationEndTime"
        ])

        fecha_fin = parse_fecha_dgt(fin)

        # Solo eventos activos o controlados por ventana de validez
        if status_l and status_l not in [
            "active",
            "definedbyvaliditytime"
        ]:
            continue

        # Si ya terminó, fuera
        if fecha_fin and fecha_fin < ahora:
            continue

        texto = normalizar_texto(all_text(record))
        tipo_xsi_n = normalizar_texto(tipo_xsi)
        tipo_obstruccion_n = normalizar_texto(tipo_obstruccion)

        texto_total = " ".join([
            texto,
            tipo_xsi_n,
            tipo_obstruccion_n
        ])

        # Quitamos cosas claramente ajenas a una baliza/vehículo parado.
        excluir = [
            "roadworks",
            "road works",
            "maintenance",
            "weather",
            "meteorological",
            "abnormaltraffic",
            "abnormal traffic",
            "networkmanagement",
            "network management",
            "generalinstruction",
            "general instruction",
            "poorroadinfrastructure",
            "poor road infrastructure",
            "trafficflow",
            "traffic flow",
            "congestion",
            "retencion",
            "retenciones",
            "restriccion",
            "restricciones",
            "corte total",
            "carril cerrado",
            "carriles cerrados",
            "obras",
            "meteorologia",
            "viento",
            "nieve",
            "hielo",
            "lluvia",
            "niebla"
        ]

        if any(x in texto_total for x in excluir):
            continue

        # Filtro medio: vehículo detenido / averiado / parado / obstáculo por vehículo.
        # No exigimos que venga como VehicleObstruction porque muchos registros no lo traen así.
        incluir = [
            "vehicleobstruction",
            "vehicle obstruction",
            "brokendownvehicle",
            "broken down vehicle",
            "stationaryvehicle",
            "stationary vehicle",
            "stoppedvehicle",
            "stopped vehicle",
            "vehicleoffroad",
            "vehicle off road",
            "abandonedvehicle",
            "abandoned vehicle",

            "vehicleonfire",
            "vehicle on fire",
            "disabled vehicle",
            "immobilised vehicle",
            "immobilized vehicle",

            "vehiculo averiado",
            "vehiculo detenido",
            "vehiculo parado",
            "vehiculo inmovilizado",
            "vehiculo obstaculizando",
            "vehiculo en arcen",
            "vehiculo en el arcen",
            "vehiculo incendiado",
            "vehiculo ardiendo",
            "vehiculo siniestrado",
            "vehiculo accidentado",

            "averia de vehiculo",
            "averia vehiculo",
            "coche averiado",
            "turismo averiado",
            "camion averiado",
            "furgoneta averiada",
            "coche incendiado",

            "obstaculo por vehiculo",
            "obstruccion por vehiculo"
        ]

        if not any(x in texto_total for x in incluir):
            continue

        # Dedupe: el XML puede traer varios registros para una misma incidencia.
        try:
            clave = (
                round(float(lat), 5),
                round(float(lon), 5)
            )
        except Exception:
            clave = (lat, lon)

        if clave in vistos:
            continue

        vistos.add(clave)

        road = first_text(record, ["roadName"])
        province = first_text(record, ["province"])
        municipality = first_text(record, ["municipality"])
        km = first_text(record, ["kilometerPoint"])

        timestamp = first_text(record, [
            "situationRecordVersionTime",
            "situationRecordCreationTime",
            "overallStartTime"
        ])

        puntos.append({
            "lat": lat,
            "lon": lon,
            "timestamp": timestamp,
            "road": road,
            "province": province,
            "municipality": municipality,
            "km": km,
            "status": status,
            "tipo": tipo_xsi,
            "tipo_obstruccion": tipo_obstruccion,
            "raw_text": all_text(record)[:1000]
        })

    print()
    print("Resumen de tipos DATEX encontrados:")
    for k, v in contador_tipos.most_common(20):
        print(v, "-", k)

    print()
    print("Resumen de tipos de obstrucción:")
    for k, v in contador_obstruccion.most_common(20):
        print(v, "-", k)

    return puntos

v16 = extraer_incidencias_dgt()

print("Puntos extraídos:", len(v16))

data_json = json.dumps(v16, ensure_ascii=False)

html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>V16 / Incidencias DGT activas</title>

  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <style>
    html, body {{
      margin: 0;
      padding: 0;
      height: 100%;
    }}

    #map {{
      height: 100vh;
      width: 100%;
    }}

    .panel {{
      position: absolute;
      top: 10px;
      left: 10px;
      z-index: 1000;
      background: white;
      padding: 12px;
      border-radius: 10px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.25);
      font-family: Arial, sans-serif;
      font-size: 14px;
    }}

    .contador {{
      position: absolute;
      right: 10px;
      bottom: 10px;
      z-index: 1000;
      background: white;
      padding: 10px 14px;
      border-radius: 10px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.25);
      font-family: Arial, sans-serif;
      font-size: 15px;
    }}

    .beacon {{
      font-size: 28px;
      filter: drop-shadow(2px 3px 3px rgba(0,0,0,0.45));
    }}
  </style>
</head>

<body>

<div class="panel">
  <b>🚨 Servicio operativo</b><br>
  Puntos cargados: <b>{len(v16)}</b><br>
  <button onclick="location.reload()" style="margin-top:8px;">
    🔄 Actualizar
  </button>
</div>

<div class="contador">
  🚨 Activas <b>{len(v16)}</b>
</div>

<div id="map"></div>

<script>
  const puntos = {data_json};

  const map = L.map('map').setView([40.4, -3.7], 6);

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);

  const iconoBaliza = L.divIcon({{
    html: '<div class="beacon">🚨</div>',
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -10]
  }});

  const markers = [];

  puntos.forEach(p => {{
    const lat = parseFloat(p.lat);
    const lon = parseFloat(p.lon);

    if (isNaN(lat) || isNaN(lon)) return;

    let info = `
      <div style="max-height:260px; overflow:auto; font-size:13px">
        <b>Incidencia / posible baliza V16</b><br><br>
        <b>Carretera:</b> ${{p.road || "-"}}
        <br><b>Provincia:</b> ${{p.province || "-"}}
        <br><b>Municipio:</b> ${{p.municipality || "-"}}
        <br><b>KM:</b> ${{p.km || "-"}}
        <br><b>Estado:</b> ${{p.status || "-"}}
        <br><b>Tipo:</b> ${{p.tipo || "-"}}
        <br><b>Obstrucción:</b> ${{p.tipo_obstruccion || "-"}}
        <br><b>Fecha:</b> ${{p.timestamp || "-"}}
        <br><br>
        <a href="https://www.google.com/maps?q=${{lat}},${{lon}}" target="_blank">
          Abrir en Google Maps
        </a>
        <br>
        <a href="https://waze.com/ul?ll=${{lat}},${{lon}}&navigate=yes" target="_blank">
          Abrir en Waze
        </a>
        <br><br>
        <details>
          <summary>Ver texto bruto</summary>
          <pre style="white-space:pre-wrap">${{p.raw_text || ""}}</pre>
        </details>
      </div>
    `;

    const marker = L.marker([lat, lon], {{ icon: iconoBaliza }})
      .addTo(map)
      .bindPopup(info);

    markers.push(marker);
  }});

  if (markers.length > 0) {{
    const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.15));
  }}
</script>

</body>
</html>
"""

with open("mapa_v16.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Mapa generado: mapa_v16.html")

file_path = os.path.abspath("mapa_v16.html")
webbrowser.open("file://" + file_path)