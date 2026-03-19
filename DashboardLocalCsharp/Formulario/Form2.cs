using MQTTnet;
using MQTTnet.Client;
using MQTTnet.Client.Options;
using System;
using System.Globalization;
using System.Drawing;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Newtonsoft.Json;
using System.Runtime;
using System.Runtime.InteropServices;

namespace Formulario
{
    public partial class Form2 : Form
    {
        private IMqttClient client;
        private bool _mapLoaded;
        private string _droneIconUrl;

        public Form2()
        {
            InitializeComponent();

            // -----------------------
            // Inicializar el mapa ya aquí
            // -----------------------
            var factory = new MqttFactory();
            client = factory.CreateMqttClient();
            this.Load += Form2_Load; // asociar el Load 
            CheckForIllegalCrossThreadCalls = false;
            // Configuramos los 9 botones de movimiento. Todos ellos tendrán asociada la misma función
            // para gestionar el evento click, pero en el tag ponemos la palabra que identifica la dirección 
            // del movimiento, que es la palabra que hay que pasarle como parámetro al dron para que haga la
            // operación. El texto es el código de una flechita que representa la dirección del movimineto.

            Font letraGrande = new Font("Arial", 14);
            Font letraPequeña = new Font("Arial", 12);

            // Ahora configuramos los botones de navegación

            button9.Text = "NW";
            button9.Tag = "NorthWest";
            button9.Click += navButton_Click;
            button9.Font = letraGrande;


            button10.Text = "N";
            button10.Tag = "North";
            button10.Click += navButton_Click;
            button10.Font = letraGrande;


            button11.Text = "NE";
            button11.Tag = "NorthEast";
            button11.Click += navButton_Click;
            button11.Font = letraGrande;


            button12.Text = "W";
            button12.Tag = "West";
            button12.Click += navButton_Click;
            button12.Font = letraGrande;


            button13.Text = "Stop";
            button13.Tag = "Stop";
            button13.Click += navButton_Click;
            button13.Font = letraPequeña;


            button14.Text = "E";
            button14.Tag = "East";
            button14.Click += navButton_Click;
            button14.Font = letraGrande;


            button15.Text = "SW";
            button15.Tag = "SouthWest";
            button15.Click += navButton_Click;
            button15.Font = letraGrande;


            button16.Text = "S";
            button16.Tag = "South";
            button16.Click += navButton_Click;
            button16.Font = letraGrande;


            button17.Text = "SE";
            button17.Tag = "SouthEast";
            button17.Click += navButton_Click;
            button17.Font = letraGrande;

        }

        private async void Form2_Load(object sender, EventArgs e)
        {
            await ConectarMQTT();
            InitializeMap();
        }
        private async Task ConectarMQTT()
        {
            var factory = new MqttFactory();
            client = factory.CreateMqttClient();

            // Asegúrate de incluir el esquema wss:// para WebSocket seguro
            var options = new MqttClientOptionsBuilder()
                .WithClientId("InterfazGlobalClient_" + Guid.NewGuid().ToString("N").Substring(0, 6))
                .WithWebSocketServer("wss://554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud:8884/mqtt")
                .WithCredentials("InterfazGlobal", "Kb2avDJmV2aj!Jz")
                .WithTls(new MQTTnet.Client.Options.MqttClientOptionsBuilderTlsParameters
                {
                    UseTls = true,
                    AllowUntrustedCertificates = true, // sólo para pruebas; quitar en producción
                    SslProtocol = System.Security.Authentication.SslProtocols.Tls12
                    // NO usar CertificateValidationHandler en net461
                })
                .Build();

            client.UseConnectedHandler(async e =>
            {
                try
                {
                    await client.SubscribeAsync("autopilotServiceDemo/interfazGlobal/#");
                }
                catch (Exception ex)
                {
                    this.Invoke(new Action(() =>
                    {
                        MessageBox.Show($"Error suscribiéndose: {ex.ToString()}");
                    }));
                }
            });

            client.UseDisconnectedHandler(async e =>
            {
                this.Invoke(new Action(() =>
                {
                    but_connect.Text = "Desconectado";
                    but_connect.ForeColor = Color.White;
                    but_connect.BackColor = Color.Red;
                }));

                // Reintento simple tras espera
                await Task.Delay(5000);
                try
                {
                    await client.ConnectAsync(options);
                }
                catch
                {
                    // Dejar que el handler gestione reintentos silenciosos
                }
            });

            client.UseApplicationMessageReceivedHandler(e =>
            {
                string topic = e.ApplicationMessage.Topic;
                string payload = "";
                try
                {
                    payload = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                }
                catch
                {

                }
                this.Invoke(new Action(() =>
                {
                    if (topic == "autopilotServiceDemo/interfazGlobal/telemetryInfo")
                    {
                        ProcesarTelemetria(payload);
                    }
                    else if (topic == "autopilotServiceDemo/interfazGlobal/connected")
                    {
                        but_connect.Text = "Conectado";
                        but_connect.ForeColor = Color.White;
                        but_connect.BackColor = Color.Green;
                    }
                    else if (topic == "autopilotServiceDemo/interfazGlobal/flying")
                    {
                        despegarBtn.Text = "En el aire";
                        despegarBtn.ForeColor = Color.White;
                        despegarBtn.BackColor = Color.Green;
                    }
                    else if (topic == "autopilotServiceDemo/interfazGlobal/landed")
                    {
                        landBtn.Text = "En tierra";
                        landBtn.ForeColor = Color.White;
                        landBtn.BackColor = Color.Green;

                        _ = Restart();
                    }
                    else if (topic == "autopilotServiceDemo/interfazGlobal/atHome")
                    {
                        RTLBtn.Text = "En tierra";
                        RTLBtn.ForeColor = Color.White;
                        RTLBtn.BackColor = Color.Green;

                        _ = Restart();
                    }
                }));
            });

            try
            {
                await client.ConnectAsync(options);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error conectando MQTT: {ex.ToString()}");
            }
        }

        private async Task Restart()
        {
            // Espera 5 segundos sin bloquear la interfaz
            await Task.Delay(5000);

            // Restablecer los botones
            but_connect.Text = "Armar";
            but_connect.ForeColor = Color.Black;
            but_connect.BackColor = Color.DarkOrange;

            landBtn.Text = "Aterrizar";
            landBtn.ForeColor = Color.Black;
            landBtn.BackColor = Color.DarkOrange;

            RTLBtn.Text = "RTL";
            RTLBtn.ForeColor = Color.Black;
            RTLBtn.BackColor = Color.DarkOrange;
        }

        private void but_connect_Click(object sender, EventArgs e)
        {
            var message=(new MqttApplicationMessageBuilder()
                .WithTopic("interfazGlobal/autopilotServiceDemo/connect")
                .Build());
            client.PublishAsync(message);
            but_connect.BackColor = Color.Green;
            but_connect.ForeColor = Color.White;
        }

        private void but_takeoff_Click(object sender, EventArgs e)
        {
            // Click en boton para dspegar
            // Llamada no bloqueante para no bloquear el formulario
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/arm_takeOff")
            .WithPayload("5")
            .Build());
            client.PublishAsync(message);
            despegarBtn.BackColor = Color.Yellow;
        }

        private void navButton_Click(object sender, EventArgs e)
        {
            // Aqui vendremos cuando se clique cualquiera de los botones de navagación
            // En el tag del boton tenemos la dirección de navegación.
            System.Windows.Forms.Button b = (System.Windows.Forms.Button)sender;
            string tag = b.Tag.ToString();
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/go")
            .WithPayload(tag)
            .Build());
            client.PublishAsync(message);
        }

        private void aterrizarBtn_Click(object sender, EventArgs e)
        {
            // Click en el botón de aterrizar
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/Land")
            .Build());
            client.PublishAsync(message);
            landBtn.BackColor = Color.Yellow;
        }

        private void RTLBtn_Click(object sender, EventArgs e)
        {
            // Click en el botón de RTL
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/RTL")
            .Build());
            client.PublishAsync(message);
            RTLBtn.BackColor = Color.Yellow;
        }

        private void enviarTelemetriaBtn_Click(object sender, EventArgs e)
        {
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/startTelemetry")
            .Build());
            client.PublishAsync(message);
        }

        private void detenerTelemetriaBtn_Click(object sender, EventArgs e)
        {
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/stopTelemetry")
            .Build());
            client.PublishAsync(message);
        }

        private void ProcesarTelemetria(string payload)
        {
            try
            {
                // Parsear el JSON recibido en un objeto dinámico
                dynamic telemetryInfo = JsonConvert.DeserializeObject(payload);

                double lat = telemetryInfo.lat;
                double lon = telemetryInfo.lon;

                // Actualizar posición en el mapa
                UpdateMapPosition(lat, lon);

                // Asignar valores a los labels
                altitudLbl.Text = ((double)telemetryInfo.alt).ToString("0.00");
                latitudLbl.Text = ((double)telemetryInfo.lat).ToString("0.00000000"); // ajustar precisión
                longitudLbl.Text = ((double)telemetryInfo.lon).ToString("0.00000000");
                headLbl.Text = ((double)telemetryInfo.heading).ToString("0.00");
                //stateLbl.Text = telemetryInfo.state; // si quieres mostrar el estado
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error procesando telemetría: {ex.Message}");
            }
        }
        private void headingTrackBar_Scroll(object sender, EventArgs e)
        {
            // Recojo el valor del heading seleccionado
            int n = headingTrackBar.Value;
            headingLbl.Text = n.ToString();
        }


        private void headingTrackBar_MouseUp(object sender, MouseEventArgs e)
        {
            // Cuando se libera la barra de desplazamiento recojo el valor
            // definitivo para el heading y lo envío al dron
            float valorSeleccionado = headingTrackBar.Value;
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/changeHeading")
            .WithPayload(valorSeleccionado.ToString())
            .Build());
            client.PublishAsync(message);
        }

        private void velocidadTrackBar_Scroll(object sender, EventArgs e)
        {
            // Recojo y muestro el valor la velocidad según se mueve 
            // la barra de desplazamiento
            int n = velocidadTrackBar.Value;
            velocidadLbl.Text = n.ToString();

        }

        private void velocidadTrackBar_MouseUp(object sender, MouseEventArgs e)
        {
            // Cuando se libera la barra de desplazamiento recojo el valor
            // definitivo para la velocidad y lo envío al dron
            int valorSeleccionado = velocidadTrackBar.Value;
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/changeNavSpeed")
            .WithPayload(valorSeleccionado.ToString())
            .Build());
            client.PublishAsync(message);
        }

        private void altitudebar_Scroll(object sender, EventArgs e)
        {
            int n = altitudebar.Value;
            alturaBox.Text = n.ToString();
        }

        private void altitudebar_MouseUp(object sender, MouseEventArgs e)
        {
            int valorSeleccionado = altitudebar.Value;
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/changeAltitude")
            .WithPayload(valorSeleccionado.ToString())
            .Build());
            client.PublishAsync(message);
        }

        private void ir_al_punto_Click(object sender, EventArgs e)
        {
            float Lat = float.Parse(LatBox.Text);
            float Lon = float.Parse(LonBox.Text);
            float Alt = float.Parse(altitudeBox.Text);
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/goTo")
            .WithPayload((Lat+","+Lon+","+Alt).ToString())
            .Build());
            client.PublishAsync(message);
        }

        [ComVisible(true)]
        public class ScriptManager
        {
            private Form2 form;

            public ScriptManager(Form2 form)
            {
                this.form = form;
            }

            public void goTo(double lat, double lon)
            {
                form.goTo((float)lat, (float)lon);
            }
        }
        public void goTo(float Lat, float Lon)
        {
            double Alt = Convert.ToDouble(altitudLbl.Text);
            var message = (new MqttApplicationMessageBuilder()
            .WithTopic("interfazGlobal/autopilotServiceDemo/goTo")
            .WithPayload((Lat + "/" + Lon + "/" + Alt).ToString())
            .Build());
            client.PublishAsync(message);
        }

        // Reemplaza InitializeMap()
        private void InitializeMap()
        {
            _mapLoaded = false;
            webBrowser1.ScriptErrorsSuppressed = true;
            webBrowser1.IsWebBrowserContextMenuEnabled = false;
            webBrowser1.ObjectForScripting = new ScriptManager(this);
            webBrowser1.DocumentCompleted += WebBrowser1_DocumentCompleted;
            webBrowser1.DocumentText = GetMapHtml();
        }

        private void WebBrowser1_DocumentCompleted(object sender, WebBrowserDocumentCompletedEventArgs e)
        {
            _mapLoaded = true;
        }

        private string GetMapHtml()
        {
            // 1. Leer imagen y convertir a Base64
            byte[] imageBytes = System.IO.File.ReadAllBytes("Assets/drone-logoC.png");
            string base64 = Convert.ToBase64String(imageBytes);

            // 2. Insertarlo en el HTML
            return $@"<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8' />
<meta http-equiv='X-UA-Compatible' content='IE=11' />
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.3/dist/leaflet.css' />
<style>html,body,#map{{height:100%;margin:0;padding:0}}</style>
</head>
<body>
<div id='map'></div>
<script src='https://unpkg.com/leaflet@1.9.3/dist/leaflet.js'></script>
<script>
  var map = L.map('map').setView([0,0], 2);

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);

  var customIcon = L.icon({{
    iconUrl: 'data:image/png;base64,{base64}',
    iconSize: [32, 32],
    iconAnchor: [16, 32]
  }});

  var marker = L.marker([0,0], {{ icon: customIcon }}).addTo(map);

  function updatePosition(lat, lon) {{
    var la = parseFloat(lat);
    var lo = parseFloat(lon);
    if (isNaN(la) || isNaN(lo)) return;
    marker.setLatLng([la, lo]);
    map.setView([la, lo], Math.max(12, map.getZoom()));
  }}

map.on('click', function(e) {{
  var lat = e.latlng.lat;
  var lon = e.latlng.lng;

  // Llamar a tu función
  window.external.goTo(lat, lon);
}});

</script>
</body>
</html>";
        }

        private void UpdateMapPosition(double lat, double lon)
{
    if (!this.IsHandleCreated) return;

    if (!_mapLoaded)
    {
        this.BeginInvoke((Action)(async () =>
        {
            int tries = 0;
            while (!_mapLoaded && tries++ < 10)
            {
                await Task.Delay(200);
            }
            try
            {
                webBrowser1.Document.InvokeScript("updatePosition", new object[] { lat.ToString(System.Globalization.CultureInfo.InvariantCulture), lon.ToString(System.Globalization.CultureInfo.InvariantCulture) });
            }
            catch { }
        }));
        return;
    }

    try
    {
        webBrowser1.Document.InvokeScript("updatePosition", new object[] { lat.ToString(System.Globalization.CultureInfo.InvariantCulture), lon.ToString(System.Globalization.CultureInfo.InvariantCulture) });
    }
    catch { }
}
    }
}