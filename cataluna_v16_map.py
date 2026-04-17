#!/usr/bin/env python3
"""Mapa local de V16 en Espana usando https://baliza.app/api/dgt.

Incluye filtro fijo de antiguedad: solo incidencias con <= 15 minutos.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

import requests

URL = "https://baliza.app/api/dgt"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://baliza.app/",
    "Origin": "https://baliza.app",
}

REFRESH_SECONDS = 60
HTTP_TIMEOUT = 20
HOST = "127.0.0.1"
PORT = 8088
MAX_AGE_MINUTES = 15

HTML_PAGE = """<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Mapa V16 Espana</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" integrity=\"sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=\" crossorigin=\"\"/>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #15202b;
      --muted: #4b5b6b;
      --v16: #cc4b37;
    }
    html, body { margin: 0; padding: 0; height: 100%; background: var(--bg); color: var(--text); }
    body { font-family: "Segoe UI", Tahoma, sans-serif; display: grid; grid-template-rows: auto 1fr; }
    .topbar {
      background: linear-gradient(90deg, #fff3ef, #ffffff);
      border-bottom: 1px solid #f0ddd7;
      padding: 10px 14px;
      display: flex;
      gap: 14px;
      align-items: center;
      flex-wrap: wrap;
    }
    .pill {
      background: var(--panel);
      border: 1px solid #ecd9d3;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 13px;
      white-space: nowrap;
    }
    .strong { font-weight: 700; }
    #map { width: 100%; height: 100%; }
    .leaflet-popup-content { margin: 10px 12px; }
    .muted { color: var(--muted); }
  </style>
</head>
<body>
  <div class=\"topbar\">
    <div class=\"pill\"><span class=\"strong\">Mapa V16 Espana</span></div>
    <div class=\"pill\">V16 activas: <span id=\"total\" class=\"strong\">-</span></div>
    <div class=\"pill muted\">Actualizado: <span id=\"actualizado\">-</span></div>
    <div class=\"pill\" id=\"aviso\">Fuente: baliza.app/api/dgt | Filtro: <= 15 min</div>
  </div>
  <div id=\"map\"></div>

  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\" integrity=\"sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=\" crossorigin=\"\"></script>
  <script>
    const map = L.map('map', { zoomControl: true }).setView([40.25, -3.70], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);

    function popupHtml(p) {
      return [
        `<div><strong>${p.titulo || 'V16'}</strong></div>`,
        `<div>Tipo: <strong>V16</strong></div>`,
        `<div>Carretera: ${p.carretera || '-'}</div>`,
        `<div>Hora: ${p.fecha || '-'}</div>`,
        `<div>Antiguedad: ${p.antiguedadMin != null ? p.antiguedadMin + ' min' : '-'}</div>`,
        `<div class=\"muted\">${p.descripcion || ''}</div>`,
        `<div class=\"muted\">${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}</div>`
      ].join('');
    }

    async function refresh() {
      try {
        const res = await fetch(`/api/data?t=${Date.now()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = await res.json();

        document.getElementById('total').textContent = payload.summary.total;
        document.getElementById('actualizado').textContent = payload.summary.updatedAt;
        document.getElementById('aviso').textContent = payload.summary.notice;

        markersLayer.clearLayers();
        for (const p of payload.points) {
          L.circleMarker([p.lat, p.lon], {
            radius: 7,
            color: '#cc4b37',
            weight: 1,
            fillColor: '#cc4b37',
            fillOpacity: 0.55,
          })
            .bindPopup(popupHtml(p))
            .addTo(markersLayer);
        }
      } catch (err) {
        console.error('Error actualizando datos:', err);
      }
    }

    refresh();
    setInterval(refresh, 60_000);
  </script>
</body>
</html>
"""


@dataclass
class IncidentPoint:
    id: str
    titulo: str
    descripcion: str
    carretera: str
    fecha: str
    antiguedad_min: int
    lat: float
    lon: float


_cache_lock = threading.Lock()
_cache: Dict[str, object] = {
    "updated_at_epoch": 0.0,
    "payload": {
        "summary": {
            "total": 0,
            "notice": f"Fuente: baliza.app/api/dgt | Filtro: <= {MAX_AGE_MINUTES} min",
            "updatedAt": "-",
        },
        "points": [],
    },
}


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp_epoch(item: Dict[str, Any]) -> Optional[int]:
    for key in ["timestamp", "fechaEpoch", "eventTime", "time"]:
        val = item.get(key)
        if isinstance(val, (int, float)):
            epoch = int(val)
            if epoch > 10_000_000_000:
                epoch //= 1000
            if epoch > 0:
                return epoch

    for key in ["fecha", "updatedAt", "lastUpdate", "date", "datetime", "hora"]:
        raw = item.get(key)
        if raw is None:
            continue
        txt = str(raw).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(txt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue

    return None


def extraer_lista(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def get_v16_activas() -> List[IncidentPoint]:
    response = requests.get(URL, headers=HEADERS, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    items = extraer_lista(data)

    points: List[IncidentPoint] = []
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

        lat_f = _as_float(lat)
        lon_f = _as_float(lon)
        if lat_f is None or lon_f is None:
            continue

        ts_epoch = _parse_timestamp_epoch(item)
        if ts_epoch is None:
            continue

        antiguedad = max(0, int((time.time() - ts_epoch) // 60))
        if antiguedad > MAX_AGE_MINUTES:
            continue

        event_id = str(
            item.get("id")
            or item.get("eventId")
            or item.get("identifier")
            or f"baliza:{lat_f:.5f}:{lon_f:.5f}"
        )

        points.append(
            IncidentPoint(
                id=event_id,
                titulo=str(item.get("title") or item.get("tipo") or item.get("causa") or "V16"),
                descripcion=str(item.get("description") or item.get("descripcion") or ""),
                carretera=str(item.get("road") or item.get("carretera") or item.get("via") or ""),
                fecha=str(item.get("fecha") or item.get("timestamp") or item.get("updatedAt") or ""),
                antiguedad_min=antiguedad,
                lat=lat_f,
                lon=lon_f,
            )
        )

    return points


def collect_spain_points() -> Dict[str, object]:
    try:
        points = get_v16_activas()
        notice = f"Fuente: baliza.app/api/dgt | Filtro: <= {MAX_AGE_MINUTES} min"
    except requests.RequestException as exc:
        points = []
        notice = f"Error API: {exc}"

    dedup: Dict[str, IncidentPoint] = {}
    for p in points:
        dedup.setdefault(p.id, p)
    points = list(dedup.values())

    points.sort(key=lambda p: (p.fecha, p.id))

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    return {
        "summary": {
            "total": len(points),
            "notice": notice,
            "updatedAt": now,
        },
        "points": [
            {
                "id": p.id,
                "titulo": p.titulo,
                "descripcion": p.descripcion,
                "carretera": p.carretera,
                "fecha": p.fecha,
                "antiguedadMin": p.antiguedad_min,
                "lat": p.lat,
                "lon": p.lon,
            }
            for p in points
        ],
    }


def refresh_cache(force: bool = False) -> None:
    with _cache_lock:
        age = time.time() - float(_cache["updated_at_epoch"])
        if not force and age < REFRESH_SECONDS:
            return

    payload = collect_spain_points()

    with _cache_lock:
        _cache["payload"] = payload
        _cache["updated_at_epoch"] = time.time()


def get_payload() -> Dict[str, object]:
    refresh_cache(force=False)
    with _cache_lock:
        return _cache["payload"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, content_type: str, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, "text/html; charset=utf-8", HTML_PAGE)
            return

        if self.path.startswith("/api/data"):
            payload = get_payload()
            self._send(200, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False))
            return

        self._send(404, "text/plain; charset=utf-8", "Not found")

    def log_message(self, fmt: str, *args) -> None:
        print("[HTTP]", fmt % args)


def main() -> None:
    print("Inicializando cache de datos V16 en Espana...")
    print(f"Fuente: {URL}")
    refresh_cache(force=True)

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Mapa disponible en http://{HOST}:{PORT}")
    print(f"Actualizacion de datos cada {REFRESH_SECONDS} segundos")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
