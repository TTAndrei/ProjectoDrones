namespace Formulario
{
    partial class Form2
    {
        private System.ComponentModel.IContainer components = null;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
                components.Dispose();
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        private void InitializeComponent()
        {
            // ── instancias ────────────────────────────────────────────────
            this.mainLayout = new System.Windows.Forms.TableLayoutPanel();
            this.leftPanel = new System.Windows.Forms.TableLayoutPanel();
            this.rightPanel = new System.Windows.Forms.TableLayoutPanel();
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.altitudebar = new System.Windows.Forms.TrackBar();
            this.label1 = new System.Windows.Forms.Label();
            this.alturaBox = new System.Windows.Forms.TextBox();
            this.but_connect = new System.Windows.Forms.Button();
            this.landBtn = new System.Windows.Forms.Button();
            this.despegarBtn = new System.Windows.Forms.Button();
            this.RTLBtn = new System.Windows.Forms.Button();
            this.groupBox2 = new System.Windows.Forms.GroupBox();
            this.label11 = new System.Windows.Forms.Label();
            this.label10 = new System.Windows.Forms.Label();
            this.label8 = new System.Windows.Forms.Label();
            this.altitudeBox = new System.Windows.Forms.TextBox();
            this.LonBox = new System.Windows.Forms.TextBox();
            this.LatBox = new System.Windows.Forms.TextBox();
            this.label6 = new System.Windows.Forms.Label();
            this.ir_al_punto = new System.Windows.Forms.Button();
            this.button9 = new System.Windows.Forms.Button();
            this.button10 = new System.Windows.Forms.Button();
            this.button11 = new System.Windows.Forms.Button();
            this.button12 = new System.Windows.Forms.Button();
            this.button13 = new System.Windows.Forms.Button();
            this.button14 = new System.Windows.Forms.Button();
            this.button15 = new System.Windows.Forms.Button();
            this.button16 = new System.Windows.Forms.Button();
            this.button17 = new System.Windows.Forms.Button();
            this.telemSliderPanel = new System.Windows.Forms.Panel();
            this.groupBox4 = new System.Windows.Forms.GroupBox();
            this.label7 = new System.Windows.Forms.Label();
            this.headLbl = new System.Windows.Forms.Label();
            this.longitudLbl = new System.Windows.Forms.Label();
            this.latitudLbl = new System.Windows.Forms.Label();
            this.altitudLbl = new System.Windows.Forms.Label();
            this.label2 = new System.Windows.Forms.Label();
            this.label3 = new System.Windows.Forms.Label();
            this.label5 = new System.Windows.Forms.Label();
            this.button22 = new System.Windows.Forms.Button();
            this.button23 = new System.Windows.Forms.Button();
            this.label9 = new System.Windows.Forms.Label();
            this.velocidadLbl = new System.Windows.Forms.Label();
            this.velocidadTrackBar = new System.Windows.Forms.TrackBar();
            this.label4 = new System.Windows.Forms.Label();
            this.headingLbl = new System.Windows.Forms.Label();
            this.headingTrackBar = new System.Windows.Forms.TrackBar();
            this.webBrowser1 = new System.Windows.Forms.WebBrowser();
            this.groupBoxVideo = new System.Windows.Forms.GroupBox();
            this.videoLayout = new System.Windows.Forms.TableLayoutPanel();
            this.webView2Video = new Microsoft.Web.WebView2.WinForms.WebView2();
            this.videoBtnPanel = new System.Windows.Forms.TableLayoutPanel();
            this.btnVideoConectar = new System.Windows.Forms.Button();
            this.btnVideoDetener = new System.Windows.Forms.Button();
            this.btnCapturar = new System.Windows.Forms.Button();
            this.btnGaleria = new System.Windows.Forms.Button();
            this.groupBoxCoco = new System.Windows.Forms.GroupBox();
            this.panelCoco = new System.Windows.Forms.Panel();

            ((System.ComponentModel.ISupportInitialize)(this.headingTrackBar)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.velocidadTrackBar)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.altitudebar)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.webView2Video)).BeginInit();
            this.mainLayout.SuspendLayout();
            this.leftPanel.SuspendLayout();
            this.rightPanel.SuspendLayout();
            this.groupBox1.SuspendLayout();
            this.groupBox2.SuspendLayout();
            this.groupBox4.SuspendLayout();
            this.telemSliderPanel.SuspendLayout();
            this.groupBoxVideo.SuspendLayout();
            this.videoLayout.SuspendLayout();
            this.videoBtnPanel.SuspendLayout();
            this.groupBoxCoco.SuspendLayout();
            this.SuspendLayout();

            // ────────────────────────────────────────────────────────────
            //  mainLayout  (raíz — fill completo del form)
            //  col 0: controles fija 380 px
            //  col 1: mapa+video+coco — resto
            // ────────────────────────────────────────────────────────────
            this.mainLayout.ColumnCount = 2;
            this.mainLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Absolute, 380F));
            this.mainLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.mainLayout.RowCount = 1;
            this.mainLayout.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.mainLayout.Dock = System.Windows.Forms.DockStyle.Fill;
            this.mainLayout.Padding = new System.Windows.Forms.Padding(4);
            this.mainLayout.Name = "mainLayout";

            // ────────────────────────────────────────────────────────────
            //  leftPanel  (3 filas: Control | Movimiento | Telem+sliders)
            // ────────────────────────────────────────────────────────────
            this.leftPanel.ColumnCount = 1;
            this.leftPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.leftPanel.RowCount = 3;
            this.leftPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 262F));
            this.leftPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 332F));
            this.leftPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.leftPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.leftPanel.Padding = new System.Windows.Forms.Padding(0, 0, 6, 0);
            this.leftPanel.Name = "leftPanel";

            // ── groupBox1 — Control ──────────────────────────────────────
            this.groupBox1.Controls.Add(this.but_connect);
            this.groupBox1.Controls.Add(this.alturaBox);
            this.groupBox1.Controls.Add(this.label1);
            this.groupBox1.Controls.Add(this.despegarBtn);
            this.groupBox1.Controls.Add(this.altitudebar);
            this.groupBox1.Controls.Add(this.landBtn);
            this.groupBox1.Controls.Add(this.RTLBtn);
            this.groupBox1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBox1.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F, System.Drawing.FontStyle.Bold);
            this.groupBox1.Margin = new System.Windows.Forms.Padding(2);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.TabIndex = 42; this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Control";

            this.but_connect.Anchor = ((System.Windows.Forms.AnchorStyles)(System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right));
            this.but_connect.BackColor = System.Drawing.Color.FromArgb(255, 192, 128);
            this.but_connect.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.but_connect.Location = new System.Drawing.Point(8, 28);
            this.but_connect.Name = "but_connect";
            this.but_connect.Size = new System.Drawing.Size(348, 34);
            this.but_connect.TabIndex = 2;
            this.but_connect.Text = "Conectar";
            this.but_connect.UseVisualStyleBackColor = false;
            this.but_connect.Click += new System.EventHandler(this.but_connect_Click);

            this.alturaBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.alturaBox.Location = new System.Drawing.Point(8, 74);
            this.alturaBox.Name = "alturaBox";
            this.alturaBox.Size = new System.Drawing.Size(58, 26);

            this.label1.AutoSize = true;
            this.label1.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F);
            this.label1.Location = new System.Drawing.Point(72, 78);
            this.label1.Name = "label1"; this.label1.Text = "metros";

            this.despegarBtn.BackColor = System.Drawing.Color.FromArgb(255, 192, 128);
            this.despegarBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.despegarBtn.Location = new System.Drawing.Point(158, 70);
            this.despegarBtn.Name = "despegarBtn";
            this.despegarBtn.Size = new System.Drawing.Size(198, 34);
            this.despegarBtn.Text = "Despegar";
            this.despegarBtn.UseVisualStyleBackColor = false;
            this.despegarBtn.Click += new System.EventHandler(this.but_takeoff_Click);

            this.altitudebar.Anchor = ((System.Windows.Forms.AnchorStyles)(System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right));
            this.altitudebar.Location = new System.Drawing.Point(8, 116);
            this.altitudebar.Maximum = 100;
            this.altitudebar.Name = "altitudebar";
            this.altitudebar.Size = new System.Drawing.Size(350, 45);
            this.altitudebar.TabIndex = 40;
            this.altitudebar.Scroll += new System.EventHandler(this.altitudebar_Scroll);
            this.altitudebar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.altitudebar_MouseUp);

            this.landBtn.BackColor = System.Drawing.Color.FromArgb(255, 192, 128);
            this.landBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.landBtn.Location = new System.Drawing.Point(8, 192);
            this.landBtn.Name = "landBtn";
            this.landBtn.Size = new System.Drawing.Size(168, 34);
            this.landBtn.Text = "Aterrizar";
            this.landBtn.UseVisualStyleBackColor = false;
            this.landBtn.Click += new System.EventHandler(this.aterrizarBtn_Click);

            this.RTLBtn.BackColor = System.Drawing.Color.FromArgb(255, 192, 128);
            this.RTLBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.RTLBtn.Location = new System.Drawing.Point(188, 192);
            this.RTLBtn.Name = "RTLBtn";
            this.RTLBtn.Size = new System.Drawing.Size(168, 34);
            this.RTLBtn.Text = "RTL";
            this.RTLBtn.UseVisualStyleBackColor = false;
            this.RTLBtn.Click += new System.EventHandler(this.RTLBtn_Click);

            // ── groupBox2 — Movimiento ────────────────────────────────────
            this.groupBox2.Controls.Add(this.button9);
            this.groupBox2.Controls.Add(this.button10);
            this.groupBox2.Controls.Add(this.button11);
            this.groupBox2.Controls.Add(this.button12);
            this.groupBox2.Controls.Add(this.button13);
            this.groupBox2.Controls.Add(this.button14);
            this.groupBox2.Controls.Add(this.button15);
            this.groupBox2.Controls.Add(this.button16);
            this.groupBox2.Controls.Add(this.button17);
            this.groupBox2.Controls.Add(this.label8);
            this.groupBox2.Controls.Add(this.label10);
            this.groupBox2.Controls.Add(this.label11);
            this.groupBox2.Controls.Add(this.LatBox);
            this.groupBox2.Controls.Add(this.LonBox);
            this.groupBox2.Controls.Add(this.altitudeBox);
            this.groupBox2.Controls.Add(this.label6);
            this.groupBox2.Controls.Add(this.ir_al_punto);
            this.groupBox2.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBox2.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F, System.Drawing.FontStyle.Bold);
            this.groupBox2.Margin = new System.Windows.Forms.Padding(2);
            this.groupBox2.Name = "groupBox2";
            this.groupBox2.TabIndex = 43; this.groupBox2.TabStop = false;
            this.groupBox2.Text = "Movimiento";

            // D-pad (3×3 grid, cada botón 88×64, gap 4)
            int bw = 88, bh = 62, bx0 = 10, by0 = 26, gap = 4;
            ConfigDpad(this.button9, "NW", "NorthWest", bx0, by0, bw, bh);
            ConfigDpad(this.button10, "N", "North", bx0 + (bw + gap), by0, bw, bh);
            ConfigDpad(this.button11, "NE", "NorthEast", bx0 + (bw + gap) * 2, by0, bw, bh);
            ConfigDpad(this.button12, "W", "West", bx0, by0 + (bh + gap), bw, bh);
            ConfigDpad(this.button13, "Stop", "Stop", bx0 + (bw + gap), by0 + (bh + gap), bw, bh);
            ConfigDpad(this.button14, "E", "East", bx0 + (bw + gap) * 2, by0 + (bh + gap), bw, bh);
            ConfigDpad(this.button15, "SW", "SouthWest", bx0, by0 + (bh + gap) * 2, bw, bh);
            ConfigDpad(this.button16, "S", "South", bx0 + (bw + gap), by0 + (bh + gap) * 2, bw, bh);
            ConfigDpad(this.button17, "SE", "SouthEast", bx0 + (bw + gap) * 2, by0 + (bh + gap) * 2, bw, bh);

            // Fila de coordenadas goto
            int gy = by0 + (bh + gap) * 3 + 8;
            this.label8.AutoSize = true; this.label8.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label8.Location = new System.Drawing.Point(12, gy); this.label8.Name = "label8"; this.label8.Text = "Lat";
            this.label10.AutoSize = true; this.label10.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label10.Location = new System.Drawing.Point(104, gy); this.label10.Name = "label10"; this.label10.Text = "Lon";
            this.label11.AutoSize = true; this.label11.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label11.Location = new System.Drawing.Point(210, gy); this.label11.Name = "label11"; this.label11.Text = "Alt";
            this.label6.AutoSize = true; this.label6.Location = new System.Drawing.Point(0, 0); this.label6.Name = "label6"; this.label6.Size = new System.Drawing.Size(0, 0);

            int fy = gy + 18;
            this.LatBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.LatBox.Location = new System.Drawing.Point(12, fy); this.LatBox.Name = "LatBox"; this.LatBox.Size = new System.Drawing.Size(78, 24);
            this.LonBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.LonBox.Location = new System.Drawing.Point(100, fy); this.LonBox.Name = "LonBox"; this.LonBox.Size = new System.Drawing.Size(78, 24);
            this.altitudeBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.altitudeBox.Location = new System.Drawing.Point(200, fy); this.altitudeBox.Name = "altitudeBox"; this.altitudeBox.Size = new System.Drawing.Size(60, 24);
            this.ir_al_punto.BackColor = System.Drawing.Color.FromArgb(255, 192, 128);
            this.ir_al_punto.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.ir_al_punto.Location = new System.Drawing.Point(270, fy - 2);
            this.ir_al_punto.Name = "ir_al_punto";
            this.ir_al_punto.Size = new System.Drawing.Size(86, 28);
            this.ir_al_punto.Text = "Ir al punto";
            this.ir_al_punto.UseVisualStyleBackColor = false;

            // ── telemSliderPanel — Telemetría + sliders ───────────────────
            this.telemSliderPanel.Controls.Add(this.groupBox4);
            this.telemSliderPanel.Controls.Add(this.label9);
            this.telemSliderPanel.Controls.Add(this.velocidadLbl);
            this.telemSliderPanel.Controls.Add(this.velocidadTrackBar);
            this.telemSliderPanel.Controls.Add(this.label4);
            this.telemSliderPanel.Controls.Add(this.headingLbl);
            this.telemSliderPanel.Controls.Add(this.headingTrackBar);
            this.telemSliderPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.telemSliderPanel.Margin = new System.Windows.Forms.Padding(2);
            this.telemSliderPanel.Name = "telemSliderPanel";

            // groupBox4 — Telemetría (posición fija dentro del panel)
            this.groupBox4.Controls.Add(this.label3); this.groupBox4.Controls.Add(this.latitudLbl);
            this.groupBox4.Controls.Add(this.label2); this.groupBox4.Controls.Add(this.altitudLbl);
            this.groupBox4.Controls.Add(this.label5); this.groupBox4.Controls.Add(this.longitudLbl);
            this.groupBox4.Controls.Add(this.label7); this.groupBox4.Controls.Add(this.headLbl);
            this.groupBox4.Controls.Add(this.button23); this.groupBox4.Controls.Add(this.button22);
            this.groupBox4.Anchor = ((System.Windows.Forms.AnchorStyles)(System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right));
            this.groupBox4.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F, System.Drawing.FontStyle.Bold);
            this.groupBox4.Location = new System.Drawing.Point(0, 0);
            this.groupBox4.Name = "groupBox4";
            this.groupBox4.Size = new System.Drawing.Size(372, 150);
            this.groupBox4.TabIndex = 41; this.groupBox4.TabStop = false;
            this.groupBox4.Text = "Telemetría";

            int lw = 60;
            this.label3.AutoSize = true; this.label3.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label3.Location = new System.Drawing.Point(4, 28); this.label3.Name = "label3"; this.label3.Text = "Latitud";
            this.latitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle; this.latitudLbl.Location = new System.Drawing.Point(58, 26); this.latitudLbl.Name = "latitudLbl"; this.latitudLbl.Size = new System.Drawing.Size(lw, 22);
            this.label2.AutoSize = true; this.label2.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label2.Location = new System.Drawing.Point(130, 28); this.label2.Name = "label2"; this.label2.Text = "Altitud";
            this.altitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle; this.altitudLbl.Location = new System.Drawing.Point(186, 26); this.altitudLbl.Name = "altitudLbl"; this.altitudLbl.Size = new System.Drawing.Size(lw, 22);
            this.label5.AutoSize = true; this.label5.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label5.Location = new System.Drawing.Point(4, 60); this.label5.Name = "label5"; this.label5.Text = "Longitud";
            this.longitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle; this.longitudLbl.Location = new System.Drawing.Point(64, 58); this.longitudLbl.Name = "longitudLbl"; this.longitudLbl.Size = new System.Drawing.Size(lw, 22);
            this.label7.AutoSize = true; this.label7.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label7.Location = new System.Drawing.Point(138, 60); this.label7.Name = "label7"; this.label7.Text = "Heading";
            this.headLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle; this.headLbl.Location = new System.Drawing.Point(196, 58); this.headLbl.Name = "headLbl"; this.headLbl.Size = new System.Drawing.Size(lw, 22);
            this.button23.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.button23.Location = new System.Drawing.Point(4, 94); this.button23.Name = "button23"; this.button23.Size = new System.Drawing.Size(122, 26); this.button23.Text = "Iniciar telemetría"; this.button23.UseVisualStyleBackColor = true; this.button23.Click += new System.EventHandler(this.enviarTelemetriaBtn_Click);
            this.button22.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.button22.Location = new System.Drawing.Point(136, 94); this.button22.Name = "button22"; this.button22.Size = new System.Drawing.Size(122, 26); this.button22.Text = "Parar telemetría"; this.button22.UseVisualStyleBackColor = true; this.button22.Click += new System.EventHandler(this.detenerTelemetriaBtn_Click);

            // Sliders bajo el groupBox4
            this.label9.AutoSize = true; this.label9.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label9.Location = new System.Drawing.Point(0, 158); this.label9.Name = "label9"; this.label9.Text = "Velocidad (m/s)";
            this.velocidadLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle; this.velocidadLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F); this.velocidadLbl.ForeColor = System.Drawing.Color.Red; this.velocidadLbl.Location = new System.Drawing.Point(110, 156); this.velocidadLbl.Name = "velocidadLbl"; this.velocidadLbl.Size = new System.Drawing.Size(42, 22); this.velocidadLbl.Text = "0"; this.velocidadLbl.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            this.velocidadTrackBar.Anchor = ((System.Windows.Forms.AnchorStyles)(System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right)); this.velocidadTrackBar.Location = new System.Drawing.Point(0, 180); this.velocidadTrackBar.Name = "velocidadTrackBar"; this.velocidadTrackBar.Size = new System.Drawing.Size(368, 45); this.velocidadTrackBar.TabIndex = 46; this.velocidadTrackBar.Scroll += new System.EventHandler(this.velocidadTrackBar_Scroll); this.velocidadTrackBar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.velocidadTrackBar_MouseUp);
            this.label4.AutoSize = true; this.label4.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F); this.label4.Location = new System.Drawing.Point(0, 228); this.label4.Name = "label4"; this.label4.Text = "Heading (°)";
            this.headingLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle; this.headingLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F); this.headingLbl.ForeColor = System.Drawing.Color.Red; this.headingLbl.Location = new System.Drawing.Point(82, 226); this.headingLbl.Name = "headingLbl"; this.headingLbl.Size = new System.Drawing.Size(42, 22); this.headingLbl.Text = "0"; this.headingLbl.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            this.headingTrackBar.Anchor = ((System.Windows.Forms.AnchorStyles)(System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right)); this.headingTrackBar.Location = new System.Drawing.Point(0, 250); this.headingTrackBar.Maximum = 360; this.headingTrackBar.Name = "headingTrackBar"; this.headingTrackBar.Size = new System.Drawing.Size(368, 45); this.headingTrackBar.TabIndex = 44; this.headingTrackBar.Scroll += new System.EventHandler(this.headingTrackBar_Scroll); this.headingTrackBar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.headingTrackBar_MouseUp);

            // Añadir filas al leftPanel
            this.leftPanel.Controls.Add(this.groupBox1, 0, 0);
            this.leftPanel.Controls.Add(this.groupBox2, 0, 1);
            this.leftPanel.Controls.Add(this.telemSliderPanel, 0, 2);

            // ────────────────────────────────────────────────────────────
            //  rightPanel  (3 filas: mapa 38% | vídeo 44% | coco 18%)
            // ────────────────────────────────────────────────────────────
            this.rightPanel.ColumnCount = 1;
            this.rightPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.rightPanel.RowCount = 3;
            this.rightPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 38F));
            this.rightPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 44F));
            this.rightPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 18F));
            this.rightPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.rightPanel.Padding = new System.Windows.Forms.Padding(2);
            this.rightPanel.Name = "rightPanel";

            // ── mapa ──────────────────────────────────────────────────────
            this.webBrowser1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.webBrowser1.IsWebBrowserContextMenuEnabled = false;
            this.webBrowser1.Margin = new System.Windows.Forms.Padding(3);
            this.webBrowser1.MinimumSize = new System.Drawing.Size(18, 16);
            this.webBrowser1.Name = "webBrowser1";
            this.webBrowser1.TabIndex = 51;

            // ── groupBoxVideo ─────────────────────────────────────────────
            this.groupBoxVideo.Controls.Add(this.videoLayout);
            this.groupBoxVideo.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBoxVideo.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.groupBoxVideo.Margin = new System.Windows.Forms.Padding(3);
            this.groupBoxVideo.Name = "groupBoxVideo";
            this.groupBoxVideo.TabIndex = 60; this.groupBoxVideo.TabStop = false;
            this.groupBoxVideo.Text = "Cámara WebRTC";

            // videoLayout: vídeo (100%) | botones (160px fijos)
            this.videoLayout.ColumnCount = 2;
            this.videoLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.videoLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Absolute, 158F));
            this.videoLayout.RowCount = 1;
            this.videoLayout.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.videoLayout.Dock = System.Windows.Forms.DockStyle.Fill;
            this.videoLayout.Padding = new System.Windows.Forms.Padding(4);
            this.videoLayout.Name = "videoLayout";

            this.webView2Video.Dock = System.Windows.Forms.DockStyle.Fill;
            this.webView2Video.Name = "webView2Video";
            this.webView2Video.ZoomFactor = 1D;

            // Botones vídeo
            this.videoBtnPanel.ColumnCount = 1;
            this.videoBtnPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.videoBtnPanel.RowCount = 4;
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.videoBtnPanel.Padding = new System.Windows.Forms.Padding(3);
            this.videoBtnPanel.Name = "videoBtnPanel";

            MakeVideoBtn(this.btnVideoConectar, "Conectar video", System.Drawing.Color.SteelBlue, true);
            MakeVideoBtn(this.btnVideoDetener, "Detener video", System.Drawing.Color.Firebrick, false);
            MakeVideoBtn(this.btnCapturar, "Capturar foto", System.Drawing.Color.DarkGreen, true);
            MakeVideoBtn(this.btnGaleria, "Ver galeria", System.Drawing.Color.DarkSlateBlue, true);
            this.btnVideoConectar.Click += new System.EventHandler(this.btnVideoConectar_Click);
            this.btnVideoDetener.Click += new System.EventHandler(this.btnVideoDetener_Click);
            this.btnCapturar.Click += new System.EventHandler(this.btnCapturar_Click);
            this.btnGaleria.Click += new System.EventHandler(this.btnGaleria_Click);

            this.videoBtnPanel.Controls.Add(this.btnVideoConectar, 0, 0);
            this.videoBtnPanel.Controls.Add(this.btnVideoDetener, 0, 1);
            this.videoBtnPanel.Controls.Add(this.btnCapturar, 0, 2);
            this.videoBtnPanel.Controls.Add(this.btnGaleria, 0, 3);

            this.videoLayout.Controls.Add(this.webView2Video, 0, 0);
            this.videoLayout.Controls.Add(this.videoBtnPanel, 1, 0);

            // ── groupBoxCoco ──────────────────────────────────────────────
            this.groupBoxCoco.Controls.Add(this.panelCoco);
            this.groupBoxCoco.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBoxCoco.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.groupBoxCoco.Margin = new System.Windows.Forms.Padding(3);
            this.groupBoxCoco.Name = "groupBoxCoco";
            this.groupBoxCoco.TabIndex = 61; this.groupBoxCoco.TabStop = false;
            this.groupBoxCoco.Text = "Deteccion de objetos COCO";

            this.panelCoco.AutoScroll = true;
            this.panelCoco.Dock = System.Windows.Forms.DockStyle.Fill;
            this.panelCoco.Name = "panelCoco";

            // Añadir a rightPanel
            this.rightPanel.Controls.Add(this.webBrowser1, 0, 0);
            this.rightPanel.Controls.Add(this.groupBoxVideo, 0, 1);
            this.rightPanel.Controls.Add(this.groupBoxCoco, 0, 2);

            // Añadir columnas al mainLayout
            this.mainLayout.Controls.Add(this.leftPanel, 0, 0);
            this.mainLayout.Controls.Add(this.rightPanel, 1, 0);

            // ────────────────────────────────────────────────────────────
            //  Form2
            // ────────────────────────────────────────────────────────────
            this.AutoScaleDimensions = new System.Drawing.SizeF(8F, 16F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(1400, 900);
            this.MinimumSize = new System.Drawing.Size(900, 600);
            this.Controls.Add(this.mainLayout);
            this.Name = "Form2";
            this.Text = "Dashboard Dron";

            ((System.ComponentModel.ISupportInitialize)(this.headingTrackBar)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.velocidadTrackBar)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.altitudebar)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.webView2Video)).EndInit();
            this.mainLayout.ResumeLayout(false);
            this.leftPanel.ResumeLayout(false);
            this.rightPanel.ResumeLayout(false);
            this.groupBox1.ResumeLayout(false);
            this.groupBox1.PerformLayout();
            this.groupBox2.ResumeLayout(false);
            this.groupBox2.PerformLayout();
            this.groupBox4.ResumeLayout(false);
            this.groupBox4.PerformLayout();
            this.telemSliderPanel.ResumeLayout(false);
            this.telemSliderPanel.PerformLayout();
            this.groupBoxVideo.ResumeLayout(false);
            this.videoLayout.ResumeLayout(false);
            this.videoBtnPanel.ResumeLayout(false);
            this.groupBoxCoco.ResumeLayout(false);
            this.ResumeLayout(false);
            this.PerformLayout();
        }

        // ── helpers privados (no polutan el designer visual) ─────────────

        private static void ConfigDpad(System.Windows.Forms.Button b,
            string text, string tag, int x, int y, int w, int h)
        {
            b.BackColor = System.Drawing.Color.FromArgb(255, 192, 128);
            b.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            b.Location = new System.Drawing.Point(x, y);
            b.Name = b.Name;   // ya tiene nombre del constructor
            b.Size = new System.Drawing.Size(w, h);
            b.Tag = tag;
            b.Text = text;
            b.UseVisualStyleBackColor = false;
        }

        private static void MakeVideoBtn(System.Windows.Forms.Button b,
            string text, System.Drawing.Color bg, bool enabled)
        {
            b.BackColor = bg;
            b.ForeColor = System.Drawing.Color.White;
            b.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            b.Text = text;
            b.Dock = System.Windows.Forms.DockStyle.Fill;
            b.Enabled = enabled;
            b.Margin = new System.Windows.Forms.Padding(3);
            b.UseVisualStyleBackColor = false;
        }

        #endregion

        // ── declaraciones ─────────────────────────────────────────────────
        private System.Windows.Forms.TableLayoutPanel mainLayout;
        private System.Windows.Forms.TableLayoutPanel leftPanel;
        private System.Windows.Forms.TableLayoutPanel rightPanel;
        private System.Windows.Forms.TableLayoutPanel videoLayout;
        private System.Windows.Forms.TableLayoutPanel videoBtnPanel;
        private System.Windows.Forms.Panel telemSliderPanel;
        private System.Windows.Forms.Button ir_al_punto;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.TrackBar headingTrackBar;
        private System.Windows.Forms.Label headingLbl;
        private System.Windows.Forms.Label label9;
        private System.Windows.Forms.Label velocidadLbl;
        private System.Windows.Forms.TrackBar velocidadTrackBar;
        private System.Windows.Forms.GroupBox groupBox4;
        private System.Windows.Forms.Label label7;
        private System.Windows.Forms.Label headLbl;
        private System.Windows.Forms.Label longitudLbl;
        private System.Windows.Forms.Label latitudLbl;
        private System.Windows.Forms.Label altitudLbl;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.Button button22;
        private System.Windows.Forms.Button button23;
        private System.Windows.Forms.GroupBox groupBox2;
        private System.Windows.Forms.Label label11;
        private System.Windows.Forms.Label label10;
        private System.Windows.Forms.Label label8;
        private System.Windows.Forms.TextBox altitudeBox;
        private System.Windows.Forms.TextBox LonBox;
        private System.Windows.Forms.TextBox LatBox;
        private System.Windows.Forms.Label label6;
        private System.Windows.Forms.Button button17;
        private System.Windows.Forms.Button button16;
        private System.Windows.Forms.Button button15;
        private System.Windows.Forms.Button button14;
        private System.Windows.Forms.Button button13;
        private System.Windows.Forms.Button button12;
        private System.Windows.Forms.Button button11;
        private System.Windows.Forms.Button button10;
        private System.Windows.Forms.Button button9;
        private System.Windows.Forms.GroupBox groupBox1;
        private System.Windows.Forms.TrackBar altitudebar;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.TextBox alturaBox;
        private System.Windows.Forms.Button but_connect;
        private System.Windows.Forms.Button landBtn;
        private System.Windows.Forms.Button despegarBtn;
        private System.Windows.Forms.Button RTLBtn;
        private System.Windows.Forms.WebBrowser webBrowser1;
        private System.Windows.Forms.GroupBox groupBoxVideo;
        private Microsoft.Web.WebView2.WinForms.WebView2 webView2Video;
        private System.Windows.Forms.Button btnVideoConectar;
        private System.Windows.Forms.Button btnVideoDetener;
        private System.Windows.Forms.Button btnCapturar;
        private System.Windows.Forms.Button btnGaleria;
        private System.Windows.Forms.GroupBox groupBoxCoco;
        private System.Windows.Forms.Panel panelCoco;
    }
}