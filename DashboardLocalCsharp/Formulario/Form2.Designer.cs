namespace Formulario
{
    partial class Form2
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.ir_al_punto = new System.Windows.Forms.Button();
            this.label4 = new System.Windows.Forms.Label();
            this.headingTrackBar = new System.Windows.Forms.TrackBar();
            this.headingLbl = new System.Windows.Forms.Label();
            this.label9 = new System.Windows.Forms.Label();
            this.velocidadLbl = new System.Windows.Forms.Label();
            this.velocidadTrackBar = new System.Windows.Forms.TrackBar();
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
            this.groupBox2 = new System.Windows.Forms.GroupBox();
            this.label11 = new System.Windows.Forms.Label();
            this.label10 = new System.Windows.Forms.Label();
            this.label8 = new System.Windows.Forms.Label();
            this.altitudeBox = new System.Windows.Forms.TextBox();
            this.LonBox = new System.Windows.Forms.TextBox();
            this.LatBox = new System.Windows.Forms.TextBox();
            this.label6 = new System.Windows.Forms.Label();
            this.button17 = new System.Windows.Forms.Button();
            this.button16 = new System.Windows.Forms.Button();
            this.button15 = new System.Windows.Forms.Button();
            this.button14 = new System.Windows.Forms.Button();
            this.button13 = new System.Windows.Forms.Button();
            this.button12 = new System.Windows.Forms.Button();
            this.button11 = new System.Windows.Forms.Button();
            this.button10 = new System.Windows.Forms.Button();
            this.button9 = new System.Windows.Forms.Button();
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.altitudebar = new System.Windows.Forms.TrackBar();
            this.label1 = new System.Windows.Forms.Label();
            this.alturaBox = new System.Windows.Forms.TextBox();
            this.but_connect = new System.Windows.Forms.Button();
            this.landBtn = new System.Windows.Forms.Button();
            this.despegarBtn = new System.Windows.Forms.Button();
            this.RTLBtn = new System.Windows.Forms.Button();
            ((System.ComponentModel.ISupportInitialize)(this.headingTrackBar)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.velocidadTrackBar)).BeginInit();
            this.groupBox4.SuspendLayout();
            this.groupBox2.SuspendLayout();
            this.groupBox1.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.altitudebar)).BeginInit();
            this.SuspendLayout();
            // 
            // ir_al_punto
            // 
            this.ir_al_punto.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.ir_al_punto.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.ir_al_punto.Location = new System.Drawing.Point(357, 720);
            this.ir_al_punto.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.ir_al_punto.Name = "ir_al_punto";
            this.ir_al_punto.Size = new System.Drawing.Size(147, 48);
            this.ir_al_punto.TabIndex = 50;
            this.ir_al_punto.Text = "ir al punto";
            this.ir_al_punto.UseVisualStyleBackColor = false;
            this.ir_al_punto.Click += new System.EventHandler(this.ir_al_punto_Click);
            // 
            // label4
            // 
            this.label4.AutoSize = true;
            this.label4.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.label4.Location = new System.Drawing.Point(492, 183);
            this.label4.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label4.Name = "label4";
            this.label4.Size = new System.Drawing.Size(85, 25);
            this.label4.TabIndex = 49;
            this.label4.Text = "Heading";
            // 
            // headingTrackBar
            // 
            this.headingTrackBar.Location = new System.Drawing.Point(422, 240);
            this.headingTrackBar.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.headingTrackBar.Maximum = 360;
            this.headingTrackBar.Name = "headingTrackBar";
            this.headingTrackBar.Size = new System.Drawing.Size(272, 69);
            this.headingTrackBar.TabIndex = 44;
            this.headingTrackBar.Scroll += new System.EventHandler(this.headingTrackBar_Scroll);
            this.headingTrackBar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.headingTrackBar_MouseUp);
            // 
            // headingLbl
            // 
            this.headingLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.headingLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.headingLbl.ForeColor = System.Drawing.Color.Red;
            this.headingLbl.Location = new System.Drawing.Point(408, 184);
            this.headingLbl.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.headingLbl.Name = "headingLbl";
            this.headingLbl.Size = new System.Drawing.Size(72, 30);
            this.headingLbl.TabIndex = 45;
            this.headingLbl.Text = "0";
            this.headingLbl.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            // 
            // label9
            // 
            this.label9.AutoSize = true;
            this.label9.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.label9.Location = new System.Drawing.Point(492, 72);
            this.label9.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label9.Name = "label9";
            this.label9.Size = new System.Drawing.Size(99, 25);
            this.label9.TabIndex = 48;
            this.label9.Text = "Velocidad";
            // 
            // velocidadLbl
            // 
            this.velocidadLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.velocidadLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.velocidadLbl.ForeColor = System.Drawing.Color.Red;
            this.velocidadLbl.Location = new System.Drawing.Point(405, 64);
            this.velocidadLbl.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.velocidadLbl.Name = "velocidadLbl";
            this.velocidadLbl.Size = new System.Drawing.Size(72, 36);
            this.velocidadLbl.TabIndex = 47;
            this.velocidadLbl.Text = "0";
            this.velocidadLbl.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            // 
            // velocidadTrackBar
            // 
            this.velocidadTrackBar.Location = new System.Drawing.Point(422, 113);
            this.velocidadTrackBar.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.velocidadTrackBar.Name = "velocidadTrackBar";
            this.velocidadTrackBar.Size = new System.Drawing.Size(272, 69);
            this.velocidadTrackBar.TabIndex = 46;
            this.velocidadTrackBar.Scroll += new System.EventHandler(this.velocidadTrackBar_Scroll);
            this.velocidadTrackBar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.velocidadTrackBar_MouseUp);
            // 
            // groupBox4
            // 
            this.groupBox4.Controls.Add(this.label7);
            this.groupBox4.Controls.Add(this.headLbl);
            this.groupBox4.Controls.Add(this.longitudLbl);
            this.groupBox4.Controls.Add(this.latitudLbl);
            this.groupBox4.Controls.Add(this.altitudLbl);
            this.groupBox4.Controls.Add(this.label2);
            this.groupBox4.Controls.Add(this.label3);
            this.groupBox4.Controls.Add(this.label5);
            this.groupBox4.Controls.Add(this.button22);
            this.groupBox4.Controls.Add(this.button23);
            this.groupBox4.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox4.Location = new System.Drawing.Point(369, 327);
            this.groupBox4.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.groupBox4.Name = "groupBox4";
            this.groupBox4.Padding = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.groupBox4.Size = new System.Drawing.Size(416, 320);
            this.groupBox4.TabIndex = 41;
            this.groupBox4.TabStop = false;
            this.groupBox4.Text = "Telemetría";
            // 
            // label7
            // 
            this.label7.AutoSize = true;
            this.label7.Location = new System.Drawing.Point(202, 195);
            this.label7.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label7.Name = "label7";
            this.label7.Size = new System.Drawing.Size(104, 29);
            this.label7.TabIndex = 11;
            this.label7.Text = "Heading";
            // 
            // headLbl
            // 
            this.headLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.headLbl.Location = new System.Drawing.Point(315, 194);
            this.headLbl.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.headLbl.Name = "headLbl";
            this.headLbl.Size = new System.Drawing.Size(94, 45);
            this.headLbl.TabIndex = 10;
            // 
            // longitudLbl
            // 
            this.longitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.longitudLbl.Location = new System.Drawing.Point(117, 192);
            this.longitudLbl.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.longitudLbl.Name = "longitudLbl";
            this.longitudLbl.Size = new System.Drawing.Size(83, 47);
            this.longitudLbl.TabIndex = 8;
            // 
            // latitudLbl
            // 
            this.latitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.latitudLbl.Location = new System.Drawing.Point(117, 131);
            this.latitudLbl.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.latitudLbl.Name = "latitudLbl";
            this.latitudLbl.Size = new System.Drawing.Size(83, 47);
            this.latitudLbl.TabIndex = 7;
            // 
            // altitudLbl
            // 
            this.altitudLbl.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.altitudLbl.Location = new System.Drawing.Point(315, 132);
            this.altitudLbl.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.altitudLbl.Name = "altitudLbl";
            this.altitudLbl.Size = new System.Drawing.Size(94, 45);
            this.altitudLbl.TabIndex = 6;
            // 
            // label2
            // 
            this.label2.AutoSize = true;
            this.label2.Location = new System.Drawing.Point(218, 134);
            this.label2.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(79, 29);
            this.label2.TabIndex = 4;
            this.label2.Text = "Altitud";
            // 
            // label3
            // 
            this.label3.AutoSize = true;
            this.label3.Location = new System.Drawing.Point(9, 132);
            this.label3.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(84, 29);
            this.label3.TabIndex = 3;
            this.label3.Text = "Latitud";
            // 
            // label5
            // 
            this.label5.AutoSize = true;
            this.label5.Location = new System.Drawing.Point(0, 192);
            this.label5.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label5.Name = "label5";
            this.label5.Size = new System.Drawing.Size(106, 29);
            this.label5.TabIndex = 2;
            this.label5.Text = "Longitud";
            // 
            // button22
            // 
            this.button22.Location = new System.Drawing.Point(224, 58);
            this.button22.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button22.Name = "button22";
            this.button22.Size = new System.Drawing.Size(164, 40);
            this.button22.TabIndex = 1;
            this.button22.Text = "Parar";
            this.button22.UseVisualStyleBackColor = true;
            this.button22.Click += new System.EventHandler(this.detenerTelemetriaBtn_Click);
            // 
            // button23
            // 
            this.button23.Location = new System.Drawing.Point(26, 58);
            this.button23.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button23.Name = "button23";
            this.button23.Size = new System.Drawing.Size(176, 40);
            this.button23.TabIndex = 0;
            this.button23.Text = "Iniciar";
            this.button23.UseVisualStyleBackColor = true;
            this.button23.Click += new System.EventHandler(this.enviarTelemetriaBtn_Click);
            // 
            // groupBox2
            // 
            this.groupBox2.Controls.Add(this.label11);
            this.groupBox2.Controls.Add(this.label10);
            this.groupBox2.Controls.Add(this.label8);
            this.groupBox2.Controls.Add(this.altitudeBox);
            this.groupBox2.Controls.Add(this.LonBox);
            this.groupBox2.Controls.Add(this.LatBox);
            this.groupBox2.Controls.Add(this.label6);
            this.groupBox2.Controls.Add(this.button17);
            this.groupBox2.Controls.Add(this.button16);
            this.groupBox2.Controls.Add(this.button15);
            this.groupBox2.Controls.Add(this.button14);
            this.groupBox2.Controls.Add(this.button13);
            this.groupBox2.Controls.Add(this.button12);
            this.groupBox2.Controls.Add(this.button11);
            this.groupBox2.Controls.Add(this.button10);
            this.groupBox2.Controls.Add(this.button9);
            this.groupBox2.Font = new System.Drawing.Font("Microsoft Sans Serif", 15.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox2.Location = new System.Drawing.Point(16, 367);
            this.groupBox2.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.groupBox2.Name = "groupBox2";
            this.groupBox2.Padding = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.groupBox2.Size = new System.Drawing.Size(332, 400);
            this.groupBox2.TabIndex = 43;
            this.groupBox2.TabStop = false;
            this.groupBox2.Text = "Movimiento";
            // 
            // label11
            // 
            this.label11.AutoSize = true;
            this.label11.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.label11.Location = new System.Drawing.Point(226, 317);
            this.label11.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label11.Name = "label11";
            this.label11.Size = new System.Drawing.Size(40, 29);
            this.label11.TabIndex = 41;
            this.label11.Text = "Alt";
            // 
            // label10
            // 
            this.label10.AutoSize = true;
            this.label10.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.label10.Location = new System.Drawing.Point(130, 317);
            this.label10.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label10.Name = "label10";
            this.label10.Size = new System.Drawing.Size(53, 29);
            this.label10.TabIndex = 41;
            this.label10.Text = "Lon";
            // 
            // label8
            // 
            this.label8.AutoSize = true;
            this.label8.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.label8.Location = new System.Drawing.Point(42, 317);
            this.label8.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label8.Name = "label8";
            this.label8.Size = new System.Drawing.Size(45, 29);
            this.label8.TabIndex = 41;
            this.label8.Text = "Lat";
            // 
            // altitudeBox
            // 
            this.altitudeBox.Location = new System.Drawing.Point(206, 352);
            this.altitudeBox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.altitudeBox.Name = "altitudeBox";
            this.altitudeBox.Size = new System.Drawing.Size(80, 43);
            this.altitudeBox.TabIndex = 41;
            // 
            // LonBox
            // 
            this.LonBox.Location = new System.Drawing.Point(114, 352);
            this.LonBox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.LonBox.Name = "LonBox";
            this.LonBox.Size = new System.Drawing.Size(80, 43);
            this.LonBox.TabIndex = 41;
            // 
            // LatBox
            // 
            this.LatBox.Location = new System.Drawing.Point(26, 352);
            this.LatBox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.LatBox.Name = "LatBox";
            this.LatBox.Size = new System.Drawing.Size(80, 43);
            this.LatBox.TabIndex = 41;
            // 
            // label6
            // 
            this.label6.AutoSize = true;
            this.label6.Location = new System.Drawing.Point(172, 75);
            this.label6.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label6.Name = "label6";
            this.label6.Size = new System.Drawing.Size(0, 37);
            this.label6.TabIndex = 18;
            // 
            // button17
            // 
            this.button17.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button17.Location = new System.Drawing.Point(206, 235);
            this.button17.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button17.Name = "button17";
            this.button17.Size = new System.Drawing.Size(82, 74);
            this.button17.TabIndex = 8;
            this.button17.Tag = "SouthEast";
            this.button17.Text = "SE";
            this.button17.UseVisualStyleBackColor = false;
            // 
            // button16
            // 
            this.button16.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button16.Location = new System.Drawing.Point(117, 235);
            this.button16.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button16.Name = "button16";
            this.button16.Size = new System.Drawing.Size(80, 74);
            this.button16.TabIndex = 7;
            this.button16.Tag = "South";
            this.button16.Text = "S";
            this.button16.UseVisualStyleBackColor = false;
            // 
            // button15
            // 
            this.button15.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button15.Location = new System.Drawing.Point(26, 235);
            this.button15.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button15.Name = "button15";
            this.button15.Size = new System.Drawing.Size(82, 74);
            this.button15.TabIndex = 6;
            this.button15.Tag = "SouthWest";
            this.button15.Text = "SW";
            this.button15.UseVisualStyleBackColor = false;
            // 
            // button14
            // 
            this.button14.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button14.Location = new System.Drawing.Point(208, 157);
            this.button14.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button14.Name = "button14";
            this.button14.Size = new System.Drawing.Size(80, 69);
            this.button14.TabIndex = 5;
            this.button14.Tag = "East";
            this.button14.Text = "E";
            this.button14.UseVisualStyleBackColor = false;
            // 
            // button13
            // 
            this.button13.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button13.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.button13.Location = new System.Drawing.Point(117, 155);
            this.button13.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button13.Name = "button13";
            this.button13.Size = new System.Drawing.Size(82, 71);
            this.button13.TabIndex = 4;
            this.button13.Tag = "Stop";
            this.button13.Text = "Stop";
            this.button13.UseVisualStyleBackColor = false;
            // 
            // button12
            // 
            this.button12.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button12.Location = new System.Drawing.Point(26, 155);
            this.button12.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button12.Name = "button12";
            this.button12.Size = new System.Drawing.Size(82, 71);
            this.button12.TabIndex = 3;
            this.button12.Tag = "West";
            this.button12.Text = "W";
            this.button12.UseVisualStyleBackColor = false;
            // 
            // button11
            // 
            this.button11.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button11.Location = new System.Drawing.Point(208, 71);
            this.button11.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button11.Name = "button11";
            this.button11.Size = new System.Drawing.Size(80, 75);
            this.button11.TabIndex = 2;
            this.button11.Tag = "NorthEast";
            this.button11.Text = "NE";
            this.button11.UseVisualStyleBackColor = false;
            // 
            // button10
            // 
            this.button10.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button10.Location = new System.Drawing.Point(117, 71);
            this.button10.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button10.Name = "button10";
            this.button10.Size = new System.Drawing.Size(82, 75);
            this.button10.TabIndex = 1;
            this.button10.Tag = "North";
            this.button10.Text = "N";
            this.button10.UseVisualStyleBackColor = false;
            // 
            // button9
            // 
            this.button9.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.button9.Font = new System.Drawing.Font("Microsoft Sans Serif", 10F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.button9.Location = new System.Drawing.Point(26, 71);
            this.button9.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.button9.Name = "button9";
            this.button9.Size = new System.Drawing.Size(82, 74);
            this.button9.TabIndex = 0;
            this.button9.Tag = "NorthWest";
            this.button9.Text = "NW";
            this.button9.UseVisualStyleBackColor = false;
            // 
            // groupBox1
            // 
            this.groupBox1.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Stretch;
            this.groupBox1.Controls.Add(this.altitudebar);
            this.groupBox1.Controls.Add(this.label1);
            this.groupBox1.Controls.Add(this.alturaBox);
            this.groupBox1.Controls.Add(this.but_connect);
            this.groupBox1.Controls.Add(this.landBtn);
            this.groupBox1.Controls.Add(this.despegarBtn);
            this.groupBox1.Controls.Add(this.RTLBtn);
            this.groupBox1.Font = new System.Drawing.Font("Microsoft Sans Serif", 15.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox1.Location = new System.Drawing.Point(16, 38);
            this.groupBox1.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.Padding = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.groupBox1.Size = new System.Drawing.Size(332, 320);
            this.groupBox1.TabIndex = 42;
            this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Control";
            // 
            // altitudebar
            // 
            this.altitudebar.Location = new System.Drawing.Point(16, 165);
            this.altitudebar.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.altitudebar.Maximum = 100;
            this.altitudebar.Name = "altitudebar";
            this.altitudebar.Size = new System.Drawing.Size(272, 69);
            this.altitudebar.TabIndex = 40;
            this.altitudebar.Scroll += new System.EventHandler(this.altitudebar_Scroll);
            this.altitudebar.MouseUp += new System.Windows.Forms.MouseEventHandler(this.altitudebar_MouseUp);
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.label1.Location = new System.Drawing.Point(98, 122);
            this.label1.Margin = new System.Windows.Forms.Padding(4, 0, 4, 0);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(87, 29);
            this.label1.TabIndex = 7;
            this.label1.Text = "metros";
            // 
            // alturaBox
            // 
            this.alturaBox.Location = new System.Drawing.Point(8, 108);
            this.alturaBox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.alturaBox.Name = "alturaBox";
            this.alturaBox.Size = new System.Drawing.Size(80, 43);
            this.alturaBox.TabIndex = 6;
            // 
            // but_connect
            // 
            this.but_connect.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.but_connect.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.but_connect.Location = new System.Drawing.Point(9, 46);
            this.but_connect.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.but_connect.Name = "but_connect";
            this.but_connect.Size = new System.Drawing.Size(304, 45);
            this.but_connect.TabIndex = 2;
            this.but_connect.Text = "Connectar";
            this.but_connect.UseVisualStyleBackColor = false;
            this.but_connect.Click += new System.EventHandler(this.but_connect_Click);
            // 
            // landBtn
            // 
            this.landBtn.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.landBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.landBtn.Location = new System.Drawing.Point(9, 251);
            this.landBtn.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.landBtn.Name = "landBtn";
            this.landBtn.Size = new System.Drawing.Size(147, 48);
            this.landBtn.TabIndex = 13;
            this.landBtn.Text = "Aterrizar";
            this.landBtn.UseVisualStyleBackColor = false;
            this.landBtn.Click += new System.EventHandler(this.aterrizarBtn_Click);
            // 
            // despegarBtn
            // 
            this.despegarBtn.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.despegarBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.despegarBtn.Location = new System.Drawing.Point(182, 108);
            this.despegarBtn.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.despegarBtn.Name = "despegarBtn";
            this.despegarBtn.Size = new System.Drawing.Size(132, 48);
            this.despegarBtn.TabIndex = 5;
            this.despegarBtn.Text = "Despegar";
            this.despegarBtn.UseVisualStyleBackColor = false;
            this.despegarBtn.Click += new System.EventHandler(this.but_takeoff_Click);
            // 
            // RTLBtn
            // 
            this.RTLBtn.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(255)))), ((int)(((byte)(192)))), ((int)(((byte)(128)))));
            this.RTLBtn.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.RTLBtn.Location = new System.Drawing.Point(165, 251);
            this.RTLBtn.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.RTLBtn.Name = "RTLBtn";
            this.RTLBtn.Size = new System.Drawing.Size(148, 48);
            this.RTLBtn.TabIndex = 10;
            this.RTLBtn.Text = "RTL";
            this.RTLBtn.UseVisualStyleBackColor = false;
            this.RTLBtn.Click += new System.EventHandler(this.RTLBtn_Click);
            // 
            // Form2
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(9F, 20F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(800, 807);
            this.Controls.Add(this.ir_al_punto);
            this.Controls.Add(this.label4);
            this.Controls.Add(this.headingTrackBar);
            this.Controls.Add(this.headingLbl);
            this.Controls.Add(this.label9);
            this.Controls.Add(this.velocidadLbl);
            this.Controls.Add(this.velocidadTrackBar);
            this.Controls.Add(this.groupBox4);
            this.Controls.Add(this.groupBox2);
            this.Controls.Add(this.groupBox1);
            this.Name = "Form2";
            this.Text = "Form2";
            ((System.ComponentModel.ISupportInitialize)(this.headingTrackBar)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.velocidadTrackBar)).EndInit();
            this.groupBox4.ResumeLayout(false);
            this.groupBox4.PerformLayout();
            this.groupBox2.ResumeLayout(false);
            this.groupBox2.PerformLayout();
            this.groupBox1.ResumeLayout(false);
            this.groupBox1.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.altitudebar)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

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
    }
}