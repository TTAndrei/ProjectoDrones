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
            this.mainLayout = new System.Windows.Forms.TableLayoutPanel();
            this.leftPanel = new System.Windows.Forms.TableLayoutPanel();
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.but_connect = new System.Windows.Forms.Button();
            this.alturaBox = new System.Windows.Forms.TextBox();
            this.label1 = new System.Windows.Forms.Label();
            this.despegarBtn = new System.Windows.Forms.Button();
            this.altitudebar = new System.Windows.Forms.TrackBar();
            this.landBtn = new System.Windows.Forms.Button();
            this.RTLBtn = new System.Windows.Forms.Button();
            this.groupBox2 = new System.Windows.Forms.GroupBox();
            this.button9 = new System.Windows.Forms.Button();
            this.button10 = new System.Windows.Forms.Button();
            this.button11 = new System.Windows.Forms.Button();
            this.button12 = new System.Windows.Forms.Button();
            this.button13 = new System.Windows.Forms.Button();
            this.button14 = new System.Windows.Forms.Button();
            this.button15 = new System.Windows.Forms.Button();
            this.button16 = new System.Windows.Forms.Button();
            this.button17 = new System.Windows.Forms.Button();
            this.label8 = new System.Windows.Forms.Label();
            this.label10 = new System.Windows.Forms.Label();
            this.label11 = new System.Windows.Forms.Label();
            this.LatBox = new System.Windows.Forms.TextBox();
            this.LonBox = new System.Windows.Forms.TextBox();
            this.altitudeBox = new System.Windows.Forms.TextBox();
            this.telemSliderPanel = new System.Windows.Forms.Panel();
            this.groupBox4 = new System.Windows.Forms.GroupBox();
            this.label3 = new System.Windows.Forms.Label();
            this.latitudLbl = new System.Windows.Forms.Label();
            this.label2 = new System.Windows.Forms.Label();
            this.altitudLbl = new System.Windows.Forms.Label();
            this.label5 = new System.Windows.Forms.Label();
            this.longitudLbl = new System.Windows.Forms.Label();
            this.label7 = new System.Windows.Forms.Label();
            this.headLbl = new System.Windows.Forms.Label();
            this.button23 = new System.Windows.Forms.Button();
            this.button22 = new System.Windows.Forms.Button();
            this.label9 = new System.Windows.Forms.Label();
            this.velocidadLbl = new System.Windows.Forms.Label();
            this.velocidadTrackBar = new System.Windows.Forms.TrackBar();
            this.label4 = new System.Windows.Forms.Label();
            this.headingLbl = new System.Windows.Forms.Label();
            this.headingTrackBar = new System.Windows.Forms.TrackBar();
            this.rightPanel = new System.Windows.Forms.TableLayoutPanel();
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
            this.mainLayout.SuspendLayout();
            this.leftPanel.SuspendLayout();
            this.groupBox1.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.altitudebar)).BeginInit();
            this.groupBox2.SuspendLayout();
            this.telemSliderPanel.SuspendLayout();
            this.groupBox4.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.velocidadTrackBar)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.headingTrackBar)).BeginInit();
            this.rightPanel.SuspendLayout();
            this.groupBoxVideo.SuspendLayout();
            this.videoLayout.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.webView2Video)).BeginInit();
            this.videoBtnPanel.SuspendLayout();
            this.groupBoxCoco.SuspendLayout();
            this.SuspendLayout();
            // 
            // mainLayout
            // 
            this.mainLayout.ColumnCount = 2;
            this.mainLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Absolute, 428F));
            this.mainLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.mainLayout.Controls.Add(this.leftPanel, 0, 0);
            this.mainLayout.Controls.Add(this.rightPanel, 1, 0);
            this.mainLayout.Dock = System.Windows.Forms.DockStyle.Fill;
            this.mainLayout.Location = new System.Drawing.Point(0, 0);
            this.mainLayout.Name = "mainLayout";
            this.mainLayout.Padding = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.mainLayout.RowCount = 1;
            this.mainLayout.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.mainLayout.Size = new System.Drawing.Size(1575, 1050);
            this.mainLayout.TabIndex = 0;
            // 
            // leftPanel
            // 
            this.leftPanel.ColumnCount = 1;
            this.leftPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.leftPanel.Controls.Add(this.groupBox1, 0, 0);
            this.leftPanel.Controls.Add(this.groupBox2, 0, 1);
            this.leftPanel.Controls.Add(this.telemSliderPanel, 0, 2);
            this.leftPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.leftPanel.Location = new System.Drawing.Point(7, 8);
            this.leftPanel.Name = "leftPanel";
            this.leftPanel.Padding = new System.Windows.Forms.Padding(0, 0, 6, 0);
            this.leftPanel.RowCount = 3;
            this.leftPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 328F));
            this.leftPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 415F));
            this.leftPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.leftPanel.Size = new System.Drawing.Size(422, 1034);
            this.leftPanel.TabIndex = 0;
            // 
            // groupBox1
            // 
            this.groupBox1.Controls.Add(this.but_connect);
            this.groupBox1.Controls.Add(this.alturaBox);
            this.groupBox1.Controls.Add(this.label1);
            this.groupBox1.Controls.Add(this.despegarBtn);
            this.groupBox1.Controls.Add(this.altitudebar);
            this.groupBox1.Controls.Add(this.landBtn);
            this.groupBox1.Controls.Add(this.RTLBtn);
            this.groupBox1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBox1.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F, System.Drawing.FontStyle.Bold);
            this.groupBox1.Location = new System.Drawing.Point(3, 3);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.Size = new System.Drawing.Size(410, 322);
            this.groupBox1.TabIndex = 42;
            this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Control";
            // 
            // but_connect
            // 
            this.but_connect.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.but_connect.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.but_connect.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.but_connect.Location = new System.Drawing.Point(9, 35);
            this.but_connect.Name = "but_connect";
            this.but_connect.Size = new System.Drawing.Size(392, 43);
            this.but_connect.TabIndex = 2;
            this.but_connect.Text = "Conectar";
            this.but_connect.UseVisualStyleBackColor = false;
            this.but_connect.Click += new System.EventHandler(this.but_connect_Click);
            // 
            // alturaBox
            // 
            this.alturaBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.alturaBox.Location = new System.Drawing.Point(9, 92);
            this.alturaBox.Name = "alturaBox";
            this.alturaBox.Size = new System.Drawing.Size(64, 32);
            this.alturaBox.TabIndex = 3;
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F);
            this.label1.Location = new System.Drawing.Point(81, 97);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(71, 25);
            this.label1.TabIndex = 4;
            this.label1.Text = "metros";
            // 
            // despegarBtn
            // 
            this.despegarBtn.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.despegarBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.despegarBtn.Location = new System.Drawing.Point(177, 88);
            this.despegarBtn.Name = "despegarBtn";
            this.despegarBtn.Size = new System.Drawing.Size(222, 43);
            this.despegarBtn.TabIndex = 5;
            this.despegarBtn.Text = "Despegar";
            this.despegarBtn.UseVisualStyleBackColor = false;
            this.despegarBtn.Click += new System.EventHandler(this.but_takeoff_Click);
            // 
            // altitudebar
            // 
            this.altitudebar.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.altitudebar.Location = new System.Drawing.Point(9, 145);
            this.altitudebar.Maximum = 100;
            this.altitudebar.Name = "altitudebar";
            this.altitudebar.Size = new System.Drawing.Size(579, 69);
            this.altitudebar.TabIndex = 40;
            this.altitudebar.Scroll += new System.EventHandler(this.altitudebar_Scroll);
            this.altitudebar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.altitudebar_MouseUp);
            // 
            // landBtn
            // 
            this.landBtn.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.landBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.landBtn.Location = new System.Drawing.Point(9, 240);
            this.landBtn.Name = "landBtn";
            this.landBtn.Size = new System.Drawing.Size(189, 43);
            this.landBtn.TabIndex = 41;
            this.landBtn.Text = "Aterrizar";
            this.landBtn.UseVisualStyleBackColor = false;
            this.landBtn.Click += new System.EventHandler(this.aterrizarBtn_Click);
            // 
            // RTLBtn
            // 
            this.RTLBtn.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.RTLBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F);
            this.RTLBtn.Location = new System.Drawing.Point(212, 240);
            this.RTLBtn.Name = "RTLBtn";
            this.RTLBtn.Size = new System.Drawing.Size(189, 43);
            this.RTLBtn.TabIndex = 42;
            this.RTLBtn.Text = "RTL";
            this.RTLBtn.UseVisualStyleBackColor = false;
            this.RTLBtn.Click += new System.EventHandler(this.RTLBtn_Click);
            // 
            // groupBox2
            // 
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
            this.groupBox2.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBox2.Font = new System.Drawing.Font("Microsoft Sans Serif", 11F, System.Drawing.FontStyle.Bold);
            this.groupBox2.Location = new System.Drawing.Point(3, 331);
            this.groupBox2.Name = "groupBox2";
            this.groupBox2.Size = new System.Drawing.Size(410, 409);
            this.groupBox2.TabIndex = 43;
            this.groupBox2.TabStop = false;
            this.groupBox2.Text = "Movimiento";
            // 
            // button9
            // 
            this.button9.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button9.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button9.Location = new System.Drawing.Point(12, 32);
            this.button9.Name = "button9";
            this.button9.Size = new System.Drawing.Size(99, 77);
            this.button9.TabIndex = 0;
            this.button9.Tag = "NorthWest";
            this.button9.Text = "NW";
            this.button9.UseVisualStyleBackColor = false;
            // 
            // button10
            // 
            this.button10.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button10.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button10.Location = new System.Drawing.Point(114, 32);
            this.button10.Name = "button10";
            this.button10.Size = new System.Drawing.Size(99, 77);
            this.button10.TabIndex = 1;
            this.button10.Tag = "North";
            this.button10.Text = "N";
            this.button10.UseVisualStyleBackColor = false;
            // 
            // button11
            // 
            this.button11.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button11.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button11.Location = new System.Drawing.Point(219, 32);
            this.button11.Name = "button11";
            this.button11.Size = new System.Drawing.Size(99, 77);
            this.button11.TabIndex = 2;
            this.button11.Tag = "NorthEast";
            this.button11.Text = "NE";
            this.button11.UseVisualStyleBackColor = false;
            this.button11.Click += new System.EventHandler(this.button11_Click);
            // 
            // button12
            // 
            this.button12.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button12.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button12.Location = new System.Drawing.Point(12, 115);
            this.button12.Name = "button12";
            this.button12.Size = new System.Drawing.Size(99, 77);
            this.button12.TabIndex = 3;
            this.button12.Tag = "West";
            this.button12.Text = "W";
            this.button12.UseVisualStyleBackColor = false;
            // 
            // button13
            // 
            this.button13.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button13.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Bold);
            this.button13.Location = new System.Drawing.Point(114, 115);
            this.button13.Name = "button13";
            this.button13.Size = new System.Drawing.Size(99, 77);
            this.button13.TabIndex = 4;
            this.button13.Tag = "Stop";
            this.button13.Text = "Stop";
            this.button13.UseVisualStyleBackColor = false;
            // 
            // button14
            // 
            this.button14.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button14.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button14.Location = new System.Drawing.Point(219, 115);
            this.button14.Name = "button14";
            this.button14.Size = new System.Drawing.Size(99, 77);
            this.button14.TabIndex = 5;
            this.button14.Tag = "East";
            this.button14.Text = "E";
            this.button14.UseVisualStyleBackColor = false;
            // 
            // button15
            // 
            this.button15.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button15.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button15.Location = new System.Drawing.Point(12, 197);
            this.button15.Name = "button15";
            this.button15.Size = new System.Drawing.Size(99, 77);
            this.button15.TabIndex = 6;
            this.button15.Tag = "SouthWest";
            this.button15.Text = "SW";
            this.button15.UseVisualStyleBackColor = false;
            // 
            // button16
            // 
            this.button16.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button16.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button16.Location = new System.Drawing.Point(114, 197);
            this.button16.Name = "button16";
            this.button16.Size = new System.Drawing.Size(99, 77);
            this.button16.TabIndex = 7;
            this.button16.Tag = "South";
            this.button16.Text = "S";
            this.button16.UseVisualStyleBackColor = false;
            // 
            // button17
            // 
            this.button17.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button17.Font = new System.Drawing.Font("Microsoft Sans Serif", 13F, System.Drawing.FontStyle.Bold);
            this.button17.Location = new System.Drawing.Point(219, 197);
            this.button17.Name = "button17";
            this.button17.Size = new System.Drawing.Size(99, 77);
            this.button17.TabIndex = 8;
            this.button17.Tag = "SouthEast";
            this.button17.Text = "SE";
            this.button17.UseVisualStyleBackColor = false;
            // 
            // label8
            // 
            this.label8.AutoSize = true;
            this.label8.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label8.Location = new System.Drawing.Point(14, 288);
            this.label8.Name = "label8";
            this.label8.Size = new System.Drawing.Size(35, 22);
            this.label8.TabIndex = 9;
            this.label8.Text = "Lat";
            // 
            // label10
            // 
            this.label10.AutoSize = true;
            this.label10.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label10.Location = new System.Drawing.Point(117, 288);
            this.label10.Name = "label10";
            this.label10.Size = new System.Drawing.Size(40, 22);
            this.label10.TabIndex = 10;
            this.label10.Text = "Lon";
            // 
            // label11
            // 
            this.label11.AutoSize = true;
            this.label11.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label11.Location = new System.Drawing.Point(237, 288);
            this.label11.Name = "label11";
            this.label11.Size = new System.Drawing.Size(31, 22);
            this.label11.TabIndex = 11;
            this.label11.Text = "Alt";
            // 
            // LatBox
            // 
            this.LatBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.LatBox.Location = new System.Drawing.Point(14, 311);
            this.LatBox.Name = "LatBox";
            this.LatBox.Size = new System.Drawing.Size(88, 28);
            this.LatBox.TabIndex = 12;
            // 
            // LonBox
            // 
            this.LonBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.LonBox.Location = new System.Drawing.Point(112, 311);
            this.LonBox.Name = "LonBox";
            this.LonBox.Size = new System.Drawing.Size(88, 28);
            this.LonBox.TabIndex = 13;
            // 
            // altitudeBox
            // 
            this.altitudeBox.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.altitudeBox.Location = new System.Drawing.Point(225, 311);
            this.altitudeBox.Name = "altitudeBox";
            this.altitudeBox.Size = new System.Drawing.Size(67, 28);
            this.altitudeBox.TabIndex = 14;
            // 
            // telemSliderPanel
            // 
            this.telemSliderPanel.Controls.Add(this.groupBox4);
            this.telemSliderPanel.Controls.Add(this.label9);
            this.telemSliderPanel.Controls.Add(this.velocidadLbl);
            this.telemSliderPanel.Controls.Add(this.velocidadTrackBar);
            this.telemSliderPanel.Controls.Add(this.label4);
            this.telemSliderPanel.Controls.Add(this.headingLbl);
            this.telemSliderPanel.Controls.Add(this.headingTrackBar);
            this.telemSliderPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.telemSliderPanel.Location = new System.Drawing.Point(3, 746);
            this.telemSliderPanel.Name = "telemSliderPanel";
            this.telemSliderPanel.Size = new System.Drawing.Size(410, 285);
            this.telemSliderPanel.TabIndex = 44;
            // 
            // groupBox4
            // 
            this.groupBox4.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.groupBox4.Controls.Add(this.label3);
            this.groupBox4.Controls.Add(this.latitudLbl);
            this.groupBox4.Controls.Add(this.label2);
            this.groupBox4.Controls.Add(this.altitudLbl);
            this.groupBox4.Controls.Add(this.label5);
            this.groupBox4.Controls.Add(this.longitudLbl);
            this.groupBox4.Controls.Add(this.label7);
            this.groupBox4.Controls.Add(this.headLbl);
            this.groupBox4.Controls.Add(this.button23);
            this.groupBox4.Controls.Add(this.button22);
            this.groupBox4.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F, System.Drawing.FontStyle.Bold);
            this.groupBox4.Location = new System.Drawing.Point(0, 0);
            this.groupBox4.Name = "groupBox4";
            this.groupBox4.Size = new System.Drawing.Size(410, 188);
            this.groupBox4.TabIndex = 41;
            this.groupBox4.TabStop = false;
            this.groupBox4.Text = "Telemetría";
            // 
            // label3
            // 
            this.label3.AutoSize = true;
            this.label3.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label3.Location = new System.Drawing.Point(4, 35);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(64, 22);
            this.label3.TabIndex = 0;
            this.label3.Text = "Latitud";
            // 
            // latitudLbl
            // 
            this.latitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.latitudLbl.Location = new System.Drawing.Point(87, 32);
            this.latitudLbl.Name = "latitudLbl";
            this.latitudLbl.Size = new System.Drawing.Size(70, 27);
            this.latitudLbl.TabIndex = 1;
            // 
            // label2
            // 
            this.label2.AutoSize = true;
            this.label2.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label2.Location = new System.Drawing.Point(174, 37);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(60, 22);
            this.label2.TabIndex = 2;
            this.label2.Text = "Altitud";
            // 
            // altitudLbl
            // 
            this.altitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.altitudLbl.Location = new System.Drawing.Point(264, 37);
            this.altitudLbl.Name = "altitudLbl";
            this.altitudLbl.Size = new System.Drawing.Size(68, 27);
            this.altitudLbl.TabIndex = 3;
            // 
            // label5
            // 
            this.label5.AutoSize = true;
            this.label5.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label5.Location = new System.Drawing.Point(4, 75);
            this.label5.Name = "label5";
            this.label5.Size = new System.Drawing.Size(79, 22);
            this.label5.TabIndex = 4;
            this.label5.Text = "Longitud";
            // 
            // longitudLbl
            // 
            this.longitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.longitudLbl.Location = new System.Drawing.Point(87, 74);
            this.longitudLbl.Name = "longitudLbl";
            this.longitudLbl.Size = new System.Drawing.Size(68, 27);
            this.longitudLbl.TabIndex = 5;
            // 
            // label7
            // 
            this.label7.AutoSize = true;
            this.label7.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label7.Location = new System.Drawing.Point(174, 75);
            this.label7.Name = "label7";
            this.label7.Size = new System.Drawing.Size(77, 22);
            this.label7.TabIndex = 6;
            this.label7.Text = "Heading";
            // 
            // headLbl
            // 
            this.headLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.headLbl.Location = new System.Drawing.Point(264, 74);
            this.headLbl.Name = "headLbl";
            this.headLbl.Size = new System.Drawing.Size(68, 27);
            this.headLbl.TabIndex = 7;
            // 
            // button23
            // 
            this.button23.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.button23.Location = new System.Drawing.Point(4, 117);
            this.button23.Name = "button23";
            this.button23.Size = new System.Drawing.Size(138, 32);
            this.button23.TabIndex = 8;
            this.button23.Text = "Iniciar telemetría";
            this.button23.UseVisualStyleBackColor = true;
            this.button23.Click += new System.EventHandler(this.enviarTelemetriaBtn_Click);
            // 
            // button22
            // 
            this.button22.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.button22.Location = new System.Drawing.Point(153, 117);
            this.button22.Name = "button22";
            this.button22.Size = new System.Drawing.Size(138, 32);
            this.button22.TabIndex = 9;
            this.button22.Text = "Parar telemetría";
            this.button22.UseVisualStyleBackColor = true;
            this.button22.Click += new System.EventHandler(this.detenerTelemetriaBtn_Click);
            // 
            // label9
            // 
            this.label9.AutoSize = true;
            this.label9.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label9.Location = new System.Drawing.Point(0, 197);
            this.label9.Name = "label9";
            this.label9.Size = new System.Drawing.Size(134, 22);
            this.label9.TabIndex = 42;
            this.label9.Text = "Velocidad (m/s)";
            // 
            // velocidadLbl
            // 
            this.velocidadLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.velocidadLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F);
            this.velocidadLbl.ForeColor = System.Drawing.Color.Red;
            this.velocidadLbl.Location = new System.Drawing.Point(132, 197);
            this.velocidadLbl.Name = "velocidadLbl";
            this.velocidadLbl.Size = new System.Drawing.Size(47, 27);
            this.velocidadLbl.TabIndex = 43;
            this.velocidadLbl.Text = "0";
            this.velocidadLbl.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            // 
            // velocidadTrackBar
            // 
            this.velocidadTrackBar.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.velocidadTrackBar.Location = new System.Drawing.Point(0, 225);
            this.velocidadTrackBar.Name = "velocidadTrackBar";
            this.velocidadTrackBar.Size = new System.Drawing.Size(598, 69);
            this.velocidadTrackBar.TabIndex = 46;
            this.velocidadTrackBar.Scroll += new System.EventHandler(this.velocidadTrackBar_Scroll);
            this.velocidadTrackBar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.velocidadTrackBar_MouseUp);
            // 
            // label4
            // 
            this.label4.AutoSize = true;
            this.label4.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F);
            this.label4.Location = new System.Drawing.Point(0, 298);
            this.label4.Name = "label4";
            this.label4.Size = new System.Drawing.Size(101, 22);
            this.label4.TabIndex = 47;
            this.label4.Text = "Heading (°)";
            // 
            // headingLbl
            // 
            this.headingLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.headingLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F);
            this.headingLbl.ForeColor = System.Drawing.Color.Red;
            this.headingLbl.Location = new System.Drawing.Point(94, 300);
            this.headingLbl.Name = "headingLbl";
            this.headingLbl.Size = new System.Drawing.Size(47, 27);
            this.headingLbl.TabIndex = 48;
            this.headingLbl.Text = "0";
            this.headingLbl.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            // 
            // headingTrackBar
            // 
            this.headingTrackBar.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.headingTrackBar.Location = new System.Drawing.Point(0, 331);
            this.headingTrackBar.Maximum = 360;
            this.headingTrackBar.Name = "headingTrackBar";
            this.headingTrackBar.Size = new System.Drawing.Size(598, 69);
            this.headingTrackBar.TabIndex = 44;
            this.headingTrackBar.Scroll += new System.EventHandler(this.headingTrackBar_Scroll);
            this.headingTrackBar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.headingTrackBar_MouseUp);
            // 
            // rightPanel
            // 
            this.rightPanel.ColumnCount = 1;
            this.rightPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.rightPanel.Controls.Add(this.webBrowser1, 0, 0);
            this.rightPanel.Controls.Add(this.groupBoxVideo, 0, 1);
            this.rightPanel.Controls.Add(this.groupBoxCoco, 0, 2);
            this.rightPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.rightPanel.Location = new System.Drawing.Point(435, 8);
            this.rightPanel.Name = "rightPanel";
            this.rightPanel.Padding = new System.Windows.Forms.Padding(3, 3, 3, 3);
            this.rightPanel.RowCount = 3;
            this.rightPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 38F));
            this.rightPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 44F));
            this.rightPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 18F));
            this.rightPanel.Size = new System.Drawing.Size(1133, 1034);
            this.rightPanel.TabIndex = 1;
            // 
            // webBrowser1
            // 
            this.webBrowser1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.webBrowser1.IsWebBrowserContextMenuEnabled = false;
            this.webBrowser1.Location = new System.Drawing.Point(6, 6);
            this.webBrowser1.MinimumSize = new System.Drawing.Size(21, 20);
            this.webBrowser1.Name = "webBrowser1";
            this.webBrowser1.Size = new System.Drawing.Size(1121, 384);
            this.webBrowser1.TabIndex = 51;
            // 
            // groupBoxVideo
            // 
            this.groupBoxVideo.Controls.Add(this.videoLayout);
            this.groupBoxVideo.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBoxVideo.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.groupBoxVideo.Location = new System.Drawing.Point(6, 396);
            this.groupBoxVideo.Name = "groupBoxVideo";
            this.groupBoxVideo.Size = new System.Drawing.Size(1121, 446);
            this.groupBoxVideo.TabIndex = 60;
            this.groupBoxVideo.TabStop = false;
            this.groupBoxVideo.Text = "Cámara WebRTC";
            // 
            // videoLayout
            // 
            this.videoLayout.ColumnCount = 2;
            this.videoLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.videoLayout.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Absolute, 177F));
            this.videoLayout.Controls.Add(this.webView2Video, 0, 0);
            this.videoLayout.Controls.Add(this.videoBtnPanel, 1, 0);
            this.videoLayout.Dock = System.Windows.Forms.DockStyle.Fill;
            this.videoLayout.Location = new System.Drawing.Point(3, 26);
            this.videoLayout.Name = "videoLayout";
            this.videoLayout.Padding = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.videoLayout.RowCount = 1;
            this.videoLayout.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.videoLayout.Size = new System.Drawing.Size(1115, 417);
            this.videoLayout.TabIndex = 0;
            // 
            // webView2Video
            // 
            this.webView2Video.AllowExternalDrop = true;
            this.webView2Video.CreationProperties = null;
            this.webView2Video.DefaultBackgroundColor = System.Drawing.Color.White;
            this.webView2Video.Dock = System.Windows.Forms.DockStyle.Fill;
            this.webView2Video.Location = new System.Drawing.Point(7, 8);
            this.webView2Video.Name = "webView2Video";
            this.webView2Video.Size = new System.Drawing.Size(924, 401);
            this.webView2Video.TabIndex = 0;
            this.webView2Video.ZoomFactor = 1D;
            // 
            // videoBtnPanel
            // 
            this.videoBtnPanel.ColumnCount = 1;
            this.videoBtnPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.videoBtnPanel.Controls.Add(this.btnVideoConectar, 0, 0);
            this.videoBtnPanel.Controls.Add(this.btnVideoDetener, 0, 1);
            this.videoBtnPanel.Controls.Add(this.btnCapturar, 0, 2);
            this.videoBtnPanel.Controls.Add(this.btnGaleria, 0, 3);
            this.videoBtnPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.videoBtnPanel.Location = new System.Drawing.Point(937, 8);
            this.videoBtnPanel.Name = "videoBtnPanel";
            this.videoBtnPanel.Padding = new System.Windows.Forms.Padding(3, 3, 3, 3);
            this.videoBtnPanel.RowCount = 4;
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 25F));
            this.videoBtnPanel.Size = new System.Drawing.Size(171, 401);
            this.videoBtnPanel.TabIndex = 1;
            // 
            // btnVideoConectar
            // 
            this.btnVideoConectar.BackColor = System.Drawing.Color.SteelBlue;
            this.btnVideoConectar.Dock = System.Windows.Forms.DockStyle.Fill;
            this.btnVideoConectar.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.btnVideoConectar.ForeColor = System.Drawing.Color.White;
            this.btnVideoConectar.Location = new System.Drawing.Point(6, 6);
            this.btnVideoConectar.Name = "btnVideoConectar";
            this.btnVideoConectar.Size = new System.Drawing.Size(159, 92);
            this.btnVideoConectar.TabIndex = 0;
            this.btnVideoConectar.Text = "Conectar video";
            this.btnVideoConectar.UseVisualStyleBackColor = false;
            this.btnVideoConectar.Click += new System.EventHandler(this.btnVideoConectar_Click);
            // 
            // btnVideoDetener
            // 
            this.btnVideoDetener.BackColor = System.Drawing.Color.Firebrick;
            this.btnVideoDetener.Dock = System.Windows.Forms.DockStyle.Fill;
            this.btnVideoDetener.Enabled = false;
            this.btnVideoDetener.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.btnVideoDetener.ForeColor = System.Drawing.Color.White;
            this.btnVideoDetener.Location = new System.Drawing.Point(6, 104);
            this.btnVideoDetener.Name = "btnVideoDetener";
            this.btnVideoDetener.Size = new System.Drawing.Size(159, 92);
            this.btnVideoDetener.TabIndex = 1;
            this.btnVideoDetener.Text = "Detener video";
            this.btnVideoDetener.UseVisualStyleBackColor = false;
            this.btnVideoDetener.Click += new System.EventHandler(this.btnVideoDetener_Click);
            // 
            // btnCapturar
            // 
            this.btnCapturar.BackColor = System.Drawing.Color.DarkGreen;
            this.btnCapturar.Dock = System.Windows.Forms.DockStyle.Fill;
            this.btnCapturar.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.btnCapturar.ForeColor = System.Drawing.Color.White;
            this.btnCapturar.Location = new System.Drawing.Point(6, 202);
            this.btnCapturar.Name = "btnCapturar";
            this.btnCapturar.Size = new System.Drawing.Size(159, 92);
            this.btnCapturar.TabIndex = 2;
            this.btnCapturar.Text = "Capturar foto";
            this.btnCapturar.UseVisualStyleBackColor = false;
            this.btnCapturar.Click += new System.EventHandler(this.btnCapturar_Click);
            // 
            // btnGaleria
            // 
            this.btnGaleria.BackColor = System.Drawing.Color.DarkSlateBlue;
            this.btnGaleria.Dock = System.Windows.Forms.DockStyle.Fill;
            this.btnGaleria.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.btnGaleria.ForeColor = System.Drawing.Color.White;
            this.btnGaleria.Location = new System.Drawing.Point(6, 300);
            this.btnGaleria.Name = "btnGaleria";
            this.btnGaleria.Size = new System.Drawing.Size(159, 95);
            this.btnGaleria.TabIndex = 3;
            this.btnGaleria.Text = "Ver galeria";
            this.btnGaleria.UseVisualStyleBackColor = false;
            this.btnGaleria.Click += new System.EventHandler(this.btnGaleria_Click);
            // 
            // groupBoxCoco
            // 
            this.groupBoxCoco.Controls.Add(this.panelCoco);
            this.groupBoxCoco.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBoxCoco.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Bold);
            this.groupBoxCoco.Location = new System.Drawing.Point(6, 848);
            this.groupBoxCoco.Name = "groupBoxCoco";
            this.groupBoxCoco.Size = new System.Drawing.Size(1121, 180);
            this.groupBoxCoco.TabIndex = 61;
            this.groupBoxCoco.TabStop = false;
            this.groupBoxCoco.Text = "Deteccion de objetos COCO";
            // 
            // panelCoco
            // 
            this.panelCoco.AutoScroll = true;
            this.panelCoco.Dock = System.Windows.Forms.DockStyle.Fill;
            this.panelCoco.Location = new System.Drawing.Point(3, 26);
            this.panelCoco.Name = "panelCoco";
            this.panelCoco.Size = new System.Drawing.Size(1115, 151);
            this.panelCoco.TabIndex = 0;
            // 
            // Form2
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(9F, 20F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(1575, 1050);
            this.Controls.Add(this.mainLayout);
            this.MinimumSize = new System.Drawing.Size(1008, 731);
            this.Name = "Form2";
            this.Text = "Dashboard Dron";
            this.mainLayout.ResumeLayout(false);
            this.leftPanel.ResumeLayout(false);
            this.groupBox1.ResumeLayout(false);
            this.groupBox1.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.altitudebar)).EndInit();
            this.groupBox2.ResumeLayout(false);
            this.groupBox2.PerformLayout();
            this.telemSliderPanel.ResumeLayout(false);
            this.telemSliderPanel.PerformLayout();
            this.groupBox4.ResumeLayout(false);
            this.groupBox4.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.velocidadTrackBar)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.headingTrackBar)).EndInit();
            this.rightPanel.ResumeLayout(false);
            this.groupBoxVideo.ResumeLayout(false);
            this.videoLayout.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)(this.webView2Video)).EndInit();
            this.videoBtnPanel.ResumeLayout(false);
            this.groupBoxCoco.ResumeLayout(false);
            this.ResumeLayout(false);

        }
        #endregion
        // ── declaraciones ─────────────────────────────────────────────────
        private System.Windows.Forms.TableLayoutPanel mainLayout;
        private System.Windows.Forms.TableLayoutPanel leftPanel;
        private System.Windows.Forms.TableLayoutPanel rightPanel;
        private System.Windows.Forms.TableLayoutPanel videoLayout;
        private System.Windows.Forms.TableLayoutPanel videoBtnPanel;
        private System.Windows.Forms.Panel telemSliderPanel;
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