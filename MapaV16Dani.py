import requests
import json
import webbrowser
import os

URL = "https://baliza.app/api/dgt"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://baliza.app/",
    "Origin": "https://baliza.app"
}

def extraer_lista(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []

def get_v16_activas():
    r = requests.get(URL, headers=headers)
    data = r.json()

    items = extraer_lista(data)

    v16 = []

    for item in items:
        texto = str(item).lower()

        if "v16" not in texto:
            continue

        lat = (
            item.get("lat")
            or item.get("latitude")
            or item.get("latitud")
            or (item.get("position") or {}).get("lat")
        )

        lon = (
            item.get("lng")
            or item.get("lon")
            or item.get("longitude")
            or (item.get("position") or {}).get("lng")
        )

        timestamp = (
            item.get("date")
            or item.get("timestamp")
            or item.get("fecha")
            or item.get("updated_at")
        )

        if lat and lon:
            v16.append({
                "lat": lat,
                "lon": lon,
                "raw": item,
                "timestamp": timestamp
            })

    return v16


v16 = get_v16_activas()
data_json = json.dumps(v16)

html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>V16 activas</title>

  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <style>
    #map {{
      height: 100vh;
      width: 100%;
    }}
  </style>
</head>

<body>

<div style="position:absolute; top:10px; left:10px; z-index:1000; background:white; padding:10px; border-radius:8px;">
  <label>Últimos <span id="mins">15</span> min</label><br>
  <input type="range" id="slider" min="1" max="60" value="15"><br>
  <button onclick="location.reload()" style="margin-top:5px;">
    🔄 Actualizar
  </button>
</div>

<div id="map"></div>

<script>
  const puntos = {data_json};

  const map = L.map('map').setView([40.4, -3.7], 6);

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);

  let markers = [];

  function parseFecha(ts) {{
    if (!ts) return null;
    let d = new Date(ts);
    if (isNaN(d)) return null;
    return d;
  }}

  function dibujar(filtroMinutos) {{

    markers.forEach(m => map.removeLayer(m));
    markers = [];

    const ahora = new Date();

    puntos.forEach(p => {{

      let fecha = parseFecha(p.timestamp);

      if (fecha) {{
        let diffMin = (ahora - fecha) / 1000 / 60;
        if (diffMin > filtroMinutos) return;
      }}

      let info = "<div style='max-height:200px; overflow:auto; font-size:12px'>";
      info += "<b>Información de la baliza:</b><br><br>";

      for (const key in p.raw) {{
        let value = p.raw[key];

        if (typeof value === "object" && value !== null) {{
          value = JSON.stringify(value, null, 2);
        }}

        info += "<b>" + key + ":</b> " + value + "<br>";
      }}

      info += "</div>";

      let marker = L.marker([parseFloat(p.lat), parseFloat(p.lon)])
        .addTo(map)
        .bindPopup(info);

      markers.push(marker);
    }});
  }}

  const slider = document.getElementById("slider");
  const minsLabel = document.getElementById("mins");

  slider.addEventListener("input", () => {{
    minsLabel.innerText = slider.value;
    dibujar(parseInt(slider.value));
  }});

  dibujar(15);
</script>

</body>
</html>
"""

with open("mapa_v16.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Mapa generado: mapa_v16.html")

file_path = os.path.abspath("mapa_v16.html")
webbrowser.open("file://" + file_path)