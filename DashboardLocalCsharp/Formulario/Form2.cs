/*
 * Form2.cs  — Dashboard principal del dron (modo global)
 *
 * DEPENDENCIAS NuGet:
 *   - MQTTnet (3.x)
 *   - Newtonsoft.Json
 *   - Microsoft.Web.WebView2   ← necesario para WebRTC (IE11 no lo soporta)
 *
 * ESTRUCTURA DE FORMULARIO (designer):
 *   - webBrowser1          : WebBrowser  — mapa Leaflet
 *   - webView2Video        : WebView2    — stream WebRTC + captura de fotos
 *   - but_connect          : Button
 *   - despegarBtn          : Button
 *   - landBtn              : Button
 *   - RTLBtn               : Button
 *   - enviarTelemetriaBtn  : Button
 *   - detenerTelemetriaBtn : Button
 *   - btnVideoConectar     : Button      — iniciar stream WebRTC
 *   - btnVideoDetener      : Button      — detener stream
 *   - btnCapturar          : Button      — hacer foto
 *   - btnGaleria           : Button      — abrir galería
 *   - headingTrackBar      : TrackBar
 *   - velocidadTrackBar    : TrackBar
 *   - altitudebar          : TrackBar
 *   - headingLbl           : Label
 *   - velocidadLbl         : Label
 *   - alturaBox            : TextBox
 *   - altitudLbl           : Label  (telemetría)
 *   - latitudLbl           : Label
 *   - longitudLbl          : Label
 *   - headLbl              : Label
 *   - LatBox               : TextBox
 *   - LonBox               : TextBox
 *   - altitudeBox          : TextBox
 *   - panelCoco            : Panel      — contendrá los checkboxes COCO
 *   - button9..button17    : Button     — D-pad navegación
 */

using MQTTnet;
using MQTTnet.Client;
using MQTTnet.Client.Options;
using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;

namespace Formulario
{
    public partial class Form2 : Form
    {
        // ── MQTT ─────────────────────────────────────────────────────────
        private IMqttClient _client;

        // Origen único: evita colisiones si hay varias instancias abiertas
        private readonly string _origin =
            "interfazGlobal_" + Guid.NewGuid().ToString("N").Substring(0, 6);

        private string CmdTopic(string cmd) => $"{_origin}/autopilotServiceDemo/{cmd}";
        private string SubPattern => $"autopilotServiceDemo/{_origin}/#";
        private string TelemTopic => $"autopilotServiceDemo/{_origin}/telemetryInfo";

        // ── Mapa ──────────────────────────────────────────────────────────
        private bool _mapLoaded;

        // ── Video WebRTC ──────────────────────────────────────────────────
        private bool _webView2Ready;
        private bool _videoConnected;

        // ── Fotos ─────────────────────────────────────────────────────────
        private readonly string _photosDir =
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyPictures), "DroneFotos");
        private readonly List<string> _photoFiles = new List<string>();

        // ── TURN / ICE ────────────────────────────────────────────────────
        private static readonly HttpClient _http = new HttpClient();
        private const string MeteredApi =
            "https://testconection1.metered.live/api/v1/turn/credentials?apiKey=57312a00508de97f6ca0758cce3935fe7670";
        // Se rellena en InitWebView2 y se pasa al JS antes de cada handleOffer
        private string _iceConfigJson = "null";   // JSON array de RTCIceServer, o null = solo STUN

        // ── Detección COCO ────────────────────────────────────────────────
        // Exactamente las mismas clases que COCO_GRUPOS en el dashboard Python,
        // organizadas por grupo para mostrarlas igual en el panel.
        // Formato: (grupo, nombre_display, class_id_coco)
        private static readonly (string Grupo, string Label, int Id)[] CocoClasses =
        {
            // Personas
            ("Personas",    "Persona",    0),
            // Vehículos
            ("Vehículos",   "Bicicleta",  1),
            ("Vehículos",   "Coche",      2),
            ("Vehículos",   "Moto",       3),
            ("Vehículos",   "Avión",      4),
            ("Vehículos",   "Autobús",    5),
            ("Vehículos",   "Tren",       6),
            ("Vehículos",   "Camión",     7),
            // Animales
            ("Animales",    "Pájaro",    14),
            ("Animales",    "Gato",      15),
            ("Animales",    "Perro",     16),
            ("Animales",    "Caballo",   17),
            ("Animales",    "Vaca",      19),
            // Objetos
            ("Objetos",     "Mochila",   24),
            ("Objetos",     "Paraguas",  25),
            ("Objetos",     "Maleta",    28),
            ("Objetos",     "Pelota",    32),
            ("Objetos",     "Silla",     56),
            ("Objetos",     "Sofá",      57),
            // Electrónica
            ("Electrónica", "Portátil",  63),
            ("Electrónica", "Móvil",     67),
            ("Electrónica", "Reloj",     74),
            // Comida
            ("Comida",      "Banana",    46),
            ("Comida",      "Pizza",     53),
            ("Comida",      "Pastel",    55),
        };

        private readonly Dictionary<int, CheckBox> _cocoChecks = new Dictionary<int, CheckBox>();

        // ═════════════════════════════════════════════════════════════════
        //  CONSTRUCTOR
        // ═════════════════════════════════════════════════════════════════

        public Form2()
        {
            InitializeComponent();
            CheckForIllegalCrossThreadCalls = false;

            Directory.CreateDirectory(_photosDir);

            ConfigurarDpad();
            ConfigurarPanelCoco();

            this.Load += Form2_Load;
        }

        // ═════════════════════════════════════════════════════════════════
        //  ARRANQUE
        // ═════════════════════════════════════════════════════════════════

        private async void Form2_Load(object sender, EventArgs e)
        {
            await ConectarMQTT();
            InitializeMap();
            await InitWebView2();
        }

        // ═════════════════════════════════════════════════════════════════
        //  D-PAD
        // ═════════════════════════════════════════════════════════════════

        private void ConfigurarDpad()
        {
            Font lg = new Font("Arial", 14);
            Font sm = new Font("Arial", 12);

            var dirs = new[]
            {
                (button9,  "NW", "NorthWest", lg),
                (button10, "N",  "North",     lg),
                (button11, "NE", "NorthEast", lg),
                (button12, "W",  "West",      lg),
                (button13, "Stop", "Stop",    sm),
                (button14, "E",  "East",      lg),
                (button15, "SW", "SouthWest", lg),
                (button16, "S",  "South",     lg),
                (button17, "SE", "SouthEast", lg),
            };
            foreach (var (btn, text, tag, font) in dirs)
            {
                btn.Text = text;
                btn.Tag = tag;
                btn.Font = font;
                btn.Click += navButton_Click;
            }
        }

        // ═════════════════════════════════════════════════════════════════
        //  PANEL COCO — checkboxes agrupados por categoría (igual que Python)
        // ═════════════════════════════════════════════════════════════════

        private void ConfigurarPanelCoco()
        {
            panelCoco.AutoScroll = true;

            const int CBW = 108;   // ancho checkbox
            const int CBH = 20;    // alto checkbox
            const int COLS = 5;     // columnas por grupo (igual que Python COLS=5)
            const int HGAP = 4;     // gap horizontal
            const int VGAP = 3;     // gap vertical
            const int LBLH = 16;    // alto etiqueta de grupo

            int curY = 4;

            // Agrupar por nombre de grupo manteniendo el orden de aparición
            var grupos = new System.Collections.Generic.List<string>();
            foreach (var (grupo, _, __) in CocoClasses)
                if (!grupos.Contains(grupo)) grupos.Add(grupo);

            foreach (var grupoNombre in grupos)
            {
                // Etiqueta de grupo
                var lbl = new Label
                {
                    Text = grupoNombre,
                    Location = new Point(4, curY),
                    Size = new Size(panelCoco.Width > 0 ? panelCoco.Width - 8 : 600, LBLH),
                    Font = new Font("Arial", 8, FontStyle.Bold),
                    ForeColor = Color.DimGray,
                    Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                };
                panelCoco.Controls.Add(lbl);
                curY += LBLH + 2;

                // Checkboxes del grupo
                var clasesDel = new System.Collections.Generic.List<(string Label, int Id)>();
                foreach (var (g, label, id) in CocoClasses)
                    if (g == grupoNombre) clasesDel.Add((label, id));

                for (int i = 0; i < clasesDel.Count; i++)
                {
                    var (label, id) = clasesDel[i];
                    var cb = new CheckBox
                    {
                        Text = label,
                        Tag = id,
                        Location = new Point(4 + (i % COLS) * (CBW + HGAP),
                                             curY + (i / COLS) * (CBH + VGAP)),
                        Size = new Size(CBW, CBH),
                        Font = new Font("Arial", 8),
                    };
                    cb.CheckedChanged += CocoCheck_Changed;
                    _cocoChecks[id] = cb;
                    panelCoco.Controls.Add(cb);
                }

                int rows = (clasesDel.Count + COLS - 1) / COLS;
                curY += rows * (CBH + VGAP) + 6;
            }

            // Botón "Desactivar todas"
            var btnClear = new Button
            {
                Text = "✕  Desactivar todas",
                Location = new Point(4, curY + 4),
                Size = new Size(180, 24),
                Font = new Font("Arial", 8, FontStyle.Bold),
                BackColor = Color.Firebrick,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
            };
            btnClear.Click += (_, __) =>
            {
                foreach (var cb in _cocoChecks.Values) cb.Checked = false;
            };
            panelCoco.Controls.Add(btnClear);
        }

        /// <summary>
        /// Cada vez que cambia un checkbox, publica la lista de class IDs activos.
        ///
        /// Topic: webrtc/detectClasses  (topic fijo, sin prefijo de origen)
        /// Payload: JSON array de ints — p.ej. [0, 2, 15]
        ///
        /// El CameraService Python debe suscribirse a este topic y actualizar
        /// detect_object_ids. Añade en el CameraService (en on_message del cliente MQTT):
        ///
        ///   elif topic == 'webrtc/detectClasses':
        ///       ids = json.loads(payload)
        ///       detect_object_ids.clear()
        ///       detect_object_ids.update(ids)
        ///       if ids and yolo_model is None:
        ///           threading.Thread(target=load_yolo, daemon=True).start()
        ///       print(f"[COCO] Clases activas: {sorted(detect_object_ids)}")
        ///
        /// Y en ConectarMQTT del CameraService suscribirse a:
        ///   await _client.SubscribeAsync("webrtc/detectClasses");
        /// </summary>
        private void CocoCheck_Changed(object sender, EventArgs e)
        {
            var active = new List<int>();
            foreach (var kv in _cocoChecks)
                if (kv.Value.Checked) active.Add(kv.Key);

            string payload = JsonConvert.SerializeObject(active);
            // Topic fijo que el CameraService escucha
            Publish("webrtc/detectClasses", payload);
        }

        // ═════════════════════════════════════════════════════════════════
        //  MQTT
        // ═════════════════════════════════════════════════════════════════

        private async Task ConectarMQTT()
        {
            var factory = new MqttFactory();
            _client = factory.CreateMqttClient();

            var options = new MqttClientOptionsBuilder()
                .WithClientId("InterfazGlobalClient_" + Guid.NewGuid().ToString("N").Substring(0, 6))
                .WithWebSocketServer("wss://554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud:8884/mqtt")
                .WithCredentials("InterfazGlobal", "Kb2avDJmV2aj!Jz")
                .WithTls(new MqttClientOptionsBuilderTlsParameters
                {
                    UseTls = true,
                    AllowUntrustedCertificates = true,
                    SslProtocol = System.Security.Authentication.SslProtocols.Tls12,
                })
                .Build();

            _client.UseConnectedHandler(async _ =>
            {
                try
                {
                    // Telemetría + eventos autopilot
                    await _client.SubscribeAsync(SubPattern);
                    // Señalización WebRTC: oferta del CameraService
                    await _client.SubscribeAsync($"webrtc/offer/{_origin}");
                }
                catch (Exception ex)
                {
                    this.Invoke(new Action(() => MessageBox.Show($"Error suscribiéndose: {ex}")));
                }
            });

            _client.UseDisconnectedHandler(async _ =>
            {
                this.Invoke(new Action(() =>
                {
                    but_connect.Text = "Desconectado";
                    but_connect.BackColor = Color.Red;
                    but_connect.ForeColor = Color.White;
                }));
                await Task.Delay(5000);
                try { await _client.ConnectAsync(options); } catch { }
            });

            _client.UseApplicationMessageReceivedHandler(e =>
            {
                string topic = e.ApplicationMessage.Topic;
                string payload = "";
                try { payload = Encoding.UTF8.GetString(e.ApplicationMessage.Payload); } catch { }

                this.Invoke(new Action(() => ProcesarMensaje(topic, payload)));
            });

            try { await _client.ConnectAsync(options); }
            catch (Exception ex) { MessageBox.Show($"Error conectando MQTT: {ex}"); }
        }

        private void ProcesarMensaje(string topic, string payload)
        {
            if (topic == TelemTopic)
            {
                ProcesarTelemetria(payload);
                return;
            }

            // ── Señalización WebRTC ──────────────────────────────────────
            if (topic == $"webrtc/offer/{_origin}" && !string.IsNullOrEmpty(payload))
            {
                // Pasa la oferta SDP al WebView2 para que la procese
                PasarOfertaAlWebView(payload);
                return;
            }

            // ── Eventos autopilot ────────────────────────────────────────
            if (topic.EndsWith("/connected"))
            {
                but_connect.Text = "Conectado"; but_connect.BackColor = Color.Green; but_connect.ForeColor = Color.White;
            }
            else if (topic.EndsWith("/flying"))
            {
                despegarBtn.Text = "En el aire"; despegarBtn.BackColor = Color.Green; despegarBtn.ForeColor = Color.White;
            }
            else if (topic.EndsWith("/landed"))
            {
                landBtn.Text = "En tierra"; landBtn.BackColor = Color.Green; landBtn.ForeColor = Color.White;
                _ = Restart();
            }
            else if (topic.EndsWith("/atHome"))
            {
                RTLBtn.Text = "En tierra"; RTLBtn.BackColor = Color.Green; RTLBtn.ForeColor = Color.White;
                _ = Restart();
            }
        }

        private async Task Restart()
        {
            await Task.Delay(5000);
            but_connect.Text = "Armar"; but_connect.BackColor = Color.DarkOrange; but_connect.ForeColor = Color.Black;
            landBtn.Text = "Aterrizar"; landBtn.BackColor = Color.DarkOrange; landBtn.ForeColor = Color.Black;
            RTLBtn.Text = "RTL"; RTLBtn.BackColor = Color.DarkOrange; RTLBtn.ForeColor = Color.Black;
            despegarBtn.Text = "Despegar"; despegarBtn.BackColor = Color.DarkOrange; despegarBtn.ForeColor = Color.Black;
        }

        private void Publish(string topic, string payload = "")
        {
            if (_client == null || !_client.IsConnected) return;
            var msg = new MqttApplicationMessageBuilder()
                .WithTopic(topic).WithPayload(payload).Build();
            _client.PublishAsync(msg);
        }

        // ═════════════════════════════════════════════════════════════════
        //  BOTONES DE VUELO
        // ═════════════════════════════════════════════════════════════════

        private void but_connect_Click(object sender, EventArgs e)
        {
            // Descomenta si añades un CheckBox "chkReal" al formulario:
            // string p = chkReal.Checked ? "REAL" : "";
            Publish(CmdTopic("connect"), "");
            but_connect.Text = "Conectando..."; but_connect.BackColor = Color.Yellow; but_connect.ForeColor = Color.Black;
        }

        private void but_takeoff_Click(object sender, EventArgs e)
        {
            Publish(CmdTopic("arm_takeOff"), altitudebar.Value.ToString());
            despegarBtn.BackColor = Color.Yellow;
        }

        private void navButton_Click(object sender, EventArgs e) =>
            Publish(CmdTopic("go"), ((Button)sender).Tag.ToString());

        private void aterrizarBtn_Click(object sender, EventArgs e)
        {
            Publish(CmdTopic("Land"));
            landBtn.BackColor = Color.Yellow;
        }

        private void RTLBtn_Click(object sender, EventArgs e)
        {
            Publish(CmdTopic("RTL"));
            RTLBtn.BackColor = Color.Yellow;
        }

        private void enviarTelemetriaBtn_Click(object sender, EventArgs e) =>
            Publish(CmdTopic("startTelemetry"));

        private void detenerTelemetriaBtn_Click(object sender, EventArgs e) =>
            Publish(CmdTopic("stopTelemetry"));

        // ── Trackbars ────────────────────────────────────────────────────

        private void headingTrackBar_Scroll(object sender, EventArgs e) =>
            headingLbl.Text = headingTrackBar.Value.ToString();

        private void headingTrackBar_MouseUp(object sender, MouseEventArgs e) =>
            Publish(CmdTopic("changeHeading"), headingTrackBar.Value.ToString());

        private void velocidadTrackBar_Scroll(object sender, EventArgs e) =>
            velocidadLbl.Text = velocidadTrackBar.Value.ToString();

        private void velocidadTrackBar_MouseUp(object sender, MouseEventArgs e) =>
            Publish(CmdTopic("changeNavSpeed"), velocidadTrackBar.Value.ToString());

        private void altitudebar_Scroll(object sender, EventArgs e) =>
            alturaBox.Text = altitudebar.Value.ToString();

        private void altitudebar_MouseUp(object sender, MouseEventArgs e) =>
            Publish(CmdTopic("changeAltitude"), altitudebar.Value.ToString());

        // ── Goto manual ───────────────────────────────────────────────────

        private void ir_al_punto_Click(object sender, EventArgs e)
        {
            var ci = System.Globalization.CultureInfo.InvariantCulture;
            if (!double.TryParse(LatBox.Text, System.Globalization.NumberStyles.Float, ci, out double lat) ||
                !double.TryParse(LonBox.Text, System.Globalization.NumberStyles.Float, ci, out double lon) ||
                !double.TryParse(altitudeBox.Text, System.Globalization.NumberStyles.Float, ci, out double alt))
            {
                MessageBox.Show("Coordenadas no válidas. Usa punto como separador decimal.");
                return;
            }
            SendGoto(lat, lon, alt);
        }

        public void GoToFromMap(double lat, double lon) =>
            SendGoto(lat, lon, altitudebar.Value);

        private void SendGoto(double lat, double lon, double alt)
        {
            var payload = JsonConvert.SerializeObject(new { lat, lon, alt });
            Publish(CmdTopic("goto"), payload);
        }

        // ═════════════════════════════════════════════════════════════════
        //  TELEMETRÍA
        // ═════════════════════════════════════════════════════════════════

        private void ProcesarTelemetria(string payload)
        {
            try
            {
                dynamic t = JsonConvert.DeserializeObject(payload);
                double lat = t.lat != null ? (double)t.lat : 0.0;
                double lon = t.lon != null ? (double)t.lon : 0.0;
                double alt = t.alt != null ? (double)t.alt : 0.0;
                double heading = t.heading != null ? (double)t.heading : 0.0;

                altitudLbl.Text = alt.ToString("0.00");
                latitudLbl.Text = lat.ToString("0.00000000");
                longitudLbl.Text = lon.ToString("0.00000000");
                headLbl.Text = heading.ToString("0.00");

                if (lat != 0.0 || lon != 0.0)
                    UpdateMapPosition(lat, lon);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[Telemetría] {ex.Message}");
            }
        }

        // ═════════════════════════════════════════════════════════════════
        //  MAPA (WebBrowser + Leaflet)
        // ═════════════════════════════════════════════════════════════════

        [ComVisible(true)]
        public class ScriptManager
        {
            private readonly Form2 _form;
            public ScriptManager(Form2 form) { _form = form; }
            public void goTo(double lat, double lon) => _form.GoToFromMap(lat, lon);
        }

        private void InitializeMap()
        {
            _mapLoaded = false;
            webBrowser1.ScriptErrorsSuppressed = true;
            webBrowser1.IsWebBrowserContextMenuEnabled = false;
            webBrowser1.ObjectForScripting = new ScriptManager(this);
            webBrowser1.DocumentCompleted += (_, __) => _mapLoaded = true;
            webBrowser1.DocumentText = GetMapHtml();
        }

        private string GetMapHtml()
        {
            byte[] img = File.ReadAllBytes("Assets/drone-logoC.png");
            string base64 = Convert.ToBase64String(img);

            return $@"<!DOCTYPE html>
<html><head>
<meta charset='utf-8'/>
<meta http-equiv='X-UA-Compatible' content='IE=11'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.3/dist/leaflet.css'/>
<style>html,body,#map{{height:100%;margin:0;padding:0}}</style>
</head><body>
<div id='map'></div>
<script src='https://unpkg.com/leaflet@1.9.3/dist/leaflet.js'></script>
<script>
  var map = L.map('map').setView([0,0],2);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{
    attribution:'&copy; OpenStreetMap contributors'
  }}).addTo(map);

  var icon = L.icon({{iconUrl:'data:image/png;base64,{base64}',iconSize:[32,32],iconAnchor:[16,16]}});
  var marker = L.marker([0,0],{{icon:icon}}).addTo(map);
  var path = null, coords = [];

  function updatePosition(lat,lon){{
    var la=parseFloat(lat), lo=parseFloat(lon);
    if(isNaN(la)||isNaN(lo)) return;
    marker.setLatLng([la,lo]);
    map.setView([la,lo], Math.max(15,map.getZoom()));
    coords.push([la,lo]);
    if(coords.length>1){{
      if(path) path.setLatLngs(coords);
      else path=L.polyline(coords,{{color:'#ffb020',weight:3}}).addTo(map);
    }}
  }}

  map.on('click',function(e){{
    window.external.goTo(e.latlng.lat, e.latlng.lng);
  }});
</script>
</body></html>";
        }

        private void UpdateMapPosition(double lat, double lon)
        {
            if (!this.IsHandleCreated) return;
            void Exec() => webBrowser1.Document?.InvokeScript("updatePosition", new object[]
            {
                lat.ToString(System.Globalization.CultureInfo.InvariantCulture),
                lon.ToString(System.Globalization.CultureInfo.InvariantCulture),
            });

            if (!_mapLoaded)
            {
                this.BeginInvoke((Action)(async () =>
                {
                    for (int i = 0; i < 10 && !_mapLoaded; i++) await Task.Delay(200);
                    try { Exec(); } catch { }
                }));
                return;
            }
            try { Exec(); } catch { }
        }

        // ═════════════════════════════════════════════════════════════════
        //  VIDEO WebRTC  (WebView2 — Chromium)
        // ═════════════════════════════════════════════════════════════════

        private async Task InitWebView2()
        {
            try
            {
                // 1. Obtener credenciales TURN de Metered (mismo endpoint que el Python)
                await FetchTurnCredentials();

                // 2. Inicializar WebView2
                await webView2Video.EnsureCoreWebView2Async(null);
                webView2Video.CoreWebView2.WebMessageReceived += WebView2_MessageReceived;
                webView2Video.NavigateToString(GetVideoHtml());
                _webView2Ready = true;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"WebView2 no disponible: {ex.Message}\n\n" +
                                "Instala el runtime de WebView2 desde:\n" +
                                "https://developer.microsoft.com/en-us/microsoft-edge/webview2/");
            }
        }

        /// <summary>
        /// Llama a la API de Metered y construye el JSON de iceServers que
        /// se pasará al RTCPeerConnection del navegador, incluyendo TURN.
        /// Si falla (sin internet, API caída) deja _iceConfigJson en null
        /// y el WebView2 usará solo STUN de Google como fallback.
        /// </summary>
        private async Task FetchTurnCredentials()
        {
            try
            {
                string json = await _http.GetStringAsync(MeteredApi);
                // Metered devuelve: [{"urls":"turn:...","username":"x","credential":"y"}, ...]
                dynamic servers = JsonConvert.DeserializeObject(json);
                var iceServers = new List<object>();

                foreach (var s in servers)
                {
                    // urls puede ser string o array
                    object urls = s.urls is Newtonsoft.Json.Linq.JArray
                        ? (object)s.urls.ToObject<string[]>()
                        : (object)(string)s.urls;

                    if (s.username != null && s.credential != null)
                        iceServers.Add(new { urls, username = (string)s.username, credential = (string)s.credential });
                    else
                        iceServers.Add(new { urls });
                }

                // Añadir siempre STUN de Google como primer servidor
                iceServers.Insert(0, new { urls = "stun:stun.l.google.com:19302" });

                _iceConfigJson = JsonConvert.SerializeObject(iceServers);
                System.Diagnostics.Debug.WriteLine($"[ICE] {iceServers.Count} servidores cargados (incluye TURN)");
            }
            catch (Exception ex)
            {
                // Fallback graceful: solo STUN
                _iceConfigJson = JsonConvert.SerializeObject(new[]
                {
                    new { urls = "stun:stun.l.google.com:19302" },
                    new { urls = "stun:stun1.l.google.com:19302" },
                });
                System.Diagnostics.Debug.WriteLine($"[ICE] Error obteniendo TURN, usando solo STUN: {ex.Message}");
            }
        }

        /// <summary>
        /// Mensajes que llegan desde JavaScript dentro del WebView2.
        /// Formato: { "type": "photo", "data": "base64png..." }
        ///        | { "type": "answer", "sdp": "...", "sdpType": "answer" }
        ///        | { "type": "log", "msg": "..." }
        /// </summary>
        private void WebView2_MessageReceived(object sender,
            CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                // WebMessageAsJson siempre existe en todas las versiones del SDK.
                // Cuando JS hace postMessage(JSON.stringify(obj)), el WebView2
                // recibe el string y lo re-serializa como JSON string, así que
                // WebMessageAsJson contiene algo como:
                //   "{\"type\":\"log\",\"msg\":\"foo\"}"   ← string JSON con comillas externas
                // Hay que deserializarlo una vez para obtener el string interior,
                // y luego deserializarlo otra vez para obtener el objeto.
                string outerJson = e.WebMessageAsJson;
                string raw;

                // Si empieza con '"' es un JSON string (el caso normal con postMessage(string))
                // → deserializar una vez para quitar las comillas externas
                if (outerJson != null && outerJson.TrimStart().StartsWith("\""))
                    raw = JsonConvert.DeserializeObject<string>(outerJson);
                else
                    raw = outerJson;   // ya es un objeto JSON directo (raro, pero posible)

                dynamic msg = JsonConvert.DeserializeObject(raw);
                string type = (string)msg.type;

                if (type == "photo")
                {
                    GuardarFoto((string)msg.data);
                }
                else if (type == "answer")
                {
                    // Reenviar la answer SDP al CameraService por MQTT
                    string answerPayload = JsonConvert.SerializeObject(new
                    {
                        sdp = (string)msg.sdp,
                        type = (string)msg.sdpType,
                    });
                    Publish($"webrtc/answer/{_origin}", answerPayload);
                    System.Diagnostics.Debug.WriteLine("[WebRTC] Answer publicada");
                }
                else if (type == "log")
                {
                    string logMsg = (string)msg.msg;
                    System.Diagnostics.Debug.WriteLine($"[WebView2] {logMsg}");

                    // Marcar stream activo cuando el JS confirma que tiene vídeo
                    if (logMsg == "stream_active")
                        _videoConnected = true;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[WebView2Msg] {ex.Message}");
            }
        }

        // ── Señalización ──────────────────────────────────────────────────

        private void btnVideoConectar_Click(object sender, EventArgs e)
        {
            if (!_webView2Ready)
            {
                MessageBox.Show("WebView2 aún no está listo.");
                return;
            }
            // 1. Pedir stream al CameraService publicando el origen
            Publish("webrtc/request", _origin);
            // 2. El WebView2 espera la oferta (llega por MQTT → PasarOfertaAlWebView)
            webView2Video.CoreWebView2.ExecuteScriptAsync("setStatus('Esperando oferta SDP...')");
            btnVideoConectar.Enabled = false;
            btnVideoDetener.Enabled = true;
            System.Diagnostics.Debug.WriteLine($"[WebRTC] Solicitud enviada (origen={_origin})");
        }

        private void btnVideoDetener_Click(object sender, EventArgs e)
        {
            webView2Video.CoreWebView2.ExecuteScriptAsync("stopStream()");
            _videoConnected = false;
            btnVideoConectar.Enabled = true;
            btnVideoDetener.Enabled = false;
        }

        /// <summary>
        /// Pasa la oferta SDP al WebView2 de forma segura usando PostWebMessageAsJson,
        /// que no requiere ningún escaping manual y soporta cualquier contenido en el SDP.
        /// El JS la recibe en el listener de 'message' y llama a handleOffer().
        /// </summary>
        private void PasarOfertaAlWebView(string offerJson)
        {
            if (!_webView2Ready) return;
            try
            {
                // Construir el mensaje envelope que el JS espera:
                // { "type": "offer_envelope", "offer": {...}, "iceServers": [...] }
                var offer = JsonConvert.DeserializeObject(offerJson);
                var iceServers = JsonConvert.DeserializeObject(_iceConfigJson);
                string envelope = JsonConvert.SerializeObject(new
                {
                    type = "offer_envelope",
                    offer = offer,
                    iceServers = iceServers,
                });

                // PostWebMessageAsString envía el string tal cual al listener JS
                // sin ningún escaping ni inyección en código — es el método correcto
                webView2Video.CoreWebView2.PostWebMessageAsString(envelope);
                System.Diagnostics.Debug.WriteLine("[WebRTC] Oferta enviada al WebView2 (PostWebMessageAsString)");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[WebRTC] Error pasando oferta: {ex.Message}");
            }
        }

        // ── Captura de fotos ──────────────────────────────────────────────

        private void btnCapturar_Click(object sender, EventArgs e)
        {
            if (!_videoConnected)
            {
                MessageBox.Show("No hay stream de video activo.");
                return;
            }
            // Solicitar al JS que capture el frame actual y lo envíe como base64
            webView2Video.CoreWebView2.ExecuteScriptAsync("capturePhoto()");
        }

        private void GuardarFoto(string base64Png)
        {
            try
            {
                // Quitar el prefijo data URI si viene incluido
                string data = base64Png.Contains(",")
                    ? base64Png.Substring(base64Png.IndexOf(',') + 1)
                    : base64Png;

                byte[] bytes = Convert.FromBase64String(data);
                string filename = Path.Combine(_photosDir,
                    $"foto_{DateTime.Now:yyyyMMdd_HHmmss_fff}.png");
                File.WriteAllBytes(filename, bytes);
                _photoFiles.Add(filename);

                System.Diagnostics.Debug.WriteLine($"[Foto] Guardada: {filename}");
                // Notificación discreta en el título del form
                this.Text = $"Dashboard — Foto guardada ({_photoFiles.Count} total)";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error guardando foto: {ex.Message}");
            }
        }

        private void btnGaleria_Click(object sender, EventArgs e)
        {
            if (_photoFiles.Count == 0)
            {
                MessageBox.Show("Aún no hay fotos capturadas.\nUsa el botón 'Capturar foto' mientras hay stream activo.");
                return;
            }
            var galeria = new FormGallery(_photoFiles);
            galeria.Show();
        }

        // ── HTML del WebView2 (WebRTC + captura) ──────────────────────────

        private string GetVideoHtml()
        {
            return @"<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#000; }
  #container { position:relative; width:100%; height:100vh; }
  video { width:100%; height:100%; object-fit:cover; display:block; background:#000; }
  #status {
    position:absolute; bottom:8px; left:8px; right:8px;
    background:rgba(0,0,0,.65); padding:5px 10px; border-radius:5px;
    color:#00d4ff; font-family:monospace; font-size:12px; pointer-events:none;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }
  #hud {
    position:absolute; top:6px; left:8px;
    color:rgba(0,212,255,.7); font-family:monospace; font-size:11px; pointer-events:none;
  }
  #iceLog {
    position:absolute; top:22px; left:8px;
    color:rgba(255,200,0,.6); font-family:monospace; font-size:10px; pointer-events:none;
  }
</style>
</head>
<body>
<div id='container'>
  <video id='remoteVideo' autoplay playsinline muted></video>
  <div id='hud'></div>
  <div id='iceLog'></div>
  <div id='status'>Sin señal — esperando stream</div>
</div>
<script>
var pc = null;
var currentStream = null;

function setStatus(msg) { document.getElementById('status').textContent = msg; }
function setIceLog(msg) { document.getElementById('iceLog').textContent = msg; }
function send(obj)      { window.chrome.webview.postMessage(JSON.stringify(obj)); }

window.chrome.webview.addEventListener('message', function(e) {
  try {
    var msg = JSON.parse(e.data);
    if (msg.type === 'offer_envelope') handleOffer(msg.offer, msg.iceServers);
  } catch(err) {
    setStatus('Error parseando mensaje: ' + err.message);
    send({type:'log', msg:'parse_error: ' + err.message});
  }
});

async function handleOffer(offer, iceServers) {
  try {
    send({type:'log', msg:'offer_received'});
    setStatus('Oferta recibida — creando conexion...');
    if (pc) { pc.close(); pc = null; }

    var config = { iceServers: iceServers || [{urls:'stun:stun.l.google.com:19302'}] };
    send({type:'log', msg:'ice_servers: ' + config.iceServers.length});

    pc = new RTCPeerConnection(config);

    pc.ontrack = function(ev) {
      var vid = document.getElementById('remoteVideo');
      vid.srcObject = ev.streams[0] || new MediaStream([ev.track]);
      currentStream = vid.srcObject;
      vid.play().catch(function(){});
      setStatus('EN VIVO');
      setIceLog('');
      vid.onloadedmetadata = function() {
        document.getElementById('hud').textContent = vid.videoWidth + 'x' + vid.videoHeight;
      };
      send({type:'log', msg:'stream_active'});
    };

    pc.onconnectionstatechange = function() {
      var s = pc.connectionState;
      setStatus('WebRTC: ' + s);
      send({type:'log', msg:'conn_state: ' + s});
    };

    pc.oniceconnectionstatechange = function() {
      setIceLog('ICE: ' + pc.iceConnectionState);
      send({type:'log', msg:'ice_state: ' + pc.iceConnectionState});
    };

    pc.onicecandidate = function(ev) {
      if (ev.candidate)
        send({type:'log', msg:'cand: ' + (ev.candidate.type||'?') + ' ' + (ev.candidate.protocol||'?')});
    };

    await pc.setRemoteDescription(new RTCSessionDescription(offer));
    var answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    setStatus('ICE gathering...');

    await new Promise(function(resolve) {
      if (pc.iceGatheringState === 'complete') { resolve(); return; }
      var t = setTimeout(function(){ send({type:'log',msg:'ice_timeout'}); resolve(); }, 10000);
      pc.onicegatheringstatechange = function() {
        send({type:'log', msg:'gathering: ' + pc.iceGatheringState});
        if (pc.iceGatheringState === 'complete') { clearTimeout(t); resolve(); }
      };
    });

    send({ type:'log', msg:'has_relay: ' + (pc.localDescription.sdp.indexOf('relay') !== -1) });
    send({ type:'answer', sdp: pc.localDescription.sdp, sdpType: pc.localDescription.type });
    setStatus('Answer enviada — conectando P2P...');
  } catch(err) {
    setStatus('Error: ' + err.message);
    send({type:'log', msg:'handleOffer_error: ' + err.message});
  }
}

function stopStream() {
  if (pc) { pc.close(); pc = null; }
  var vid = document.getElementById('remoteVideo');
  if (vid.srcObject) { vid.srcObject.getTracks().forEach(function(t){ t.stop(); }); vid.srcObject = null; }
  currentStream = null;
  setStatus('Stream detenido');
  setIceLog('');
  document.getElementById('hud').textContent = '';
}

function capturePhoto() {
  var vid = document.getElementById('remoteVideo');
  if (!vid.srcObject || vid.readyState < 2) { send({type:'log',msg:'no_frame'}); return; }
  var c = document.createElement('canvas');
  c.width = vid.videoWidth || 640; c.height = vid.videoHeight || 480;
  c.getContext('2d').drawImage(vid, 0, 0);
  send({ type:'photo', data: c.toDataURL('image/png') });
  setStatus('Foto capturada!');
  setTimeout(function(){ setStatus('EN VIVO'); }, 1200);
}
</script>
</body>
</html>";
        }
    }
}