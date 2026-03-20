/*
 * FormGallery.cs — Galería de fotos capturadas desde el stream WebRTC
 *
 * Se abre desde Form2 al pulsar "Ver galería".
 * Muestra las fotos en una cuadrícula con navegación y opción de guardar/abrir carpeta.
 */

using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace Formulario
{
    public partial class FormGallery : Form
    {
        private readonly List<string> _files;

        // Controles principales
        private FlowLayoutPanel _flow;
        private PictureBox _preview;
        private Label _lblInfo;
        private Button _btnFolder;
        private Button _btnDelete;
        private Button _btnSaveAs;

        private string _selectedFile;

        public FormGallery(List<string> photoFiles)
        {
            _files = new List<string>(photoFiles); // copia defensiva
            BuildUI();
            LoadThumbnails();
        }

        // ═════════════════════════════════════════════════════════════════
        //  CONSTRUCCIÓN DE LA UI
        // ═════════════════════════════════════════════════════════════════

        private void BuildUI()
        {
            this.Text = "Galería de fotos del dron";
            this.Size = new Size(1100, 720);
            this.MinimumSize = new Size(800, 500);
            this.BackColor = Color.FromArgb(10, 12, 16);
            this.ForeColor = Color.FromArgb(200, 216, 240);
            this.Font = new Font("Segoe UI", 9);
            this.StartPosition = FormStartPosition.CenterParent;

            // ── Layout principal: panel izquierdo (thumbnails) + panel derecho (preview)
            var split = new SplitContainer
            {
                Dock = DockStyle.Fill,
                Orientation = Orientation.Vertical,
                SplitterWidth = 5,
                BackColor = Color.FromArgb(22, 27, 40),
            };
            split.SplitterDistance = 380;
            this.Controls.Add(split);

            // ── Panel izquierdo: barra de título + scroll de thumbnails
            var leftHeader = new Label
            {
                Text = $"FOTOS CAPTURADAS ({_files.Count})",
                Dock = DockStyle.Top,
                Height = 32,
                TextAlign = ContentAlignment.MiddleLeft,
                Padding = new Padding(10, 0, 0, 0),
                Font = new Font("Courier New", 9, FontStyle.Bold),
                ForeColor = Color.FromArgb(0, 212, 255),
                BackColor = Color.FromArgb(17, 21, 32),
            };

            _flow = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                BackColor = Color.FromArgb(13, 18, 28),
                Padding = new Padding(8),
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = true,
            };

            split.Panel1.Controls.Add(_flow);
            split.Panel1.Controls.Add(leftHeader);

            // ── Panel derecho: preview grande + info + botones
            var rightPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 3,
                ColumnCount = 1,
                BackColor = Color.FromArgb(17, 21, 32),
                Padding = new Padding(10),
            };
            rightPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            rightPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 28));
            rightPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 44));
            split.Panel2.Controls.Add(rightPanel);

            _preview = new PictureBox
            {
                Dock = DockStyle.Fill,
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = Color.Black,
                BorderStyle = BorderStyle.None,
            };
            rightPanel.Controls.Add(_preview, 0, 0);

            _lblInfo = new Label
            {
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleLeft,
                Font = new Font("Courier New", 8),
                ForeColor = Color.FromArgb(100, 130, 170),
            };
            rightPanel.Controls.Add(_lblInfo, 0, 1);

            var btnPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                FlowDirection = FlowDirection.LeftToRight,
                BackColor = Color.Transparent,
            };
            rightPanel.Controls.Add(btnPanel, 0, 2);

            _btnFolder = MakeBtn("📁  Abrir carpeta", Color.FromArgb(37, 94, 178));
            _btnSaveAs = MakeBtn("💾  Guardar como…", Color.FromArgb(34, 139, 34));
            _btnDelete = MakeBtn("🗑  Eliminar", Color.Firebrick);

            _btnFolder.Click += (_, __) =>
                System.Diagnostics.Process.Start("explorer.exe",
                    Path.GetDirectoryName(_selectedFile ?? _files[0]));

            _btnSaveAs.Click += BtnSaveAs_Click;
            _btnDelete.Click += BtnDelete_Click;

            btnPanel.Controls.AddRange(new Control[] { _btnFolder, _btnSaveAs, _btnDelete });
        }

        private static Button MakeBtn(string text, Color bg) => new Button
        {
            Text = text,
            BackColor = bg,
            ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat,
            Height = 34,
            AutoSize = true,
            Margin = new Padding(0, 0, 8, 0),
            Font = new Font("Segoe UI", 9),
        };

        // ═════════════════════════════════════════════════════════════════
        //  THUMBNAILS
        // ═════════════════════════════════════════════════════════════════

        private void LoadThumbnails()
        {
            _flow.Controls.Clear();
            foreach (string file in _files)
                AddThumbnail(file);
        }

        private void AddThumbnail(string file)
        {
            if (!File.Exists(file)) return;

            const int THUMB = 120;

            var panel = new Panel
            {
                Size = new Size(THUMB + 4, THUMB + 24),
                BackColor = Color.FromArgb(22, 33, 52),
                Cursor = Cursors.Hand,
                Margin = new Padding(4),
                Tag = file,
            };

            var pb = new PictureBox
            {
                Size = new Size(THUMB, THUMB),
                Location = new Point(2, 2),
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = Color.Black,
                Tag = file,
            };
            try
            {
                // Cargar sin bloquear el handle del archivo
                using (var ms = new MemoryStream(File.ReadAllBytes(file)))
                    pb.Image = Image.FromStream(ms);
            }
            catch { pb.BackColor = Color.DarkSlateGray; }

            var lbl = new Label
            {
                Text = Path.GetFileName(file).Substring(5, 15), // "yyyyMMdd_HHmmss"
                Size = new Size(THUMB, 20),
                Location = new Point(2, THUMB + 4),
                ForeColor = Color.FromArgb(130, 160, 200),
                Font = new Font("Courier New", 7),
                TextAlign = ContentAlignment.MiddleCenter,
                Tag = file,
            };

            panel.Controls.Add(pb);
            panel.Controls.Add(lbl);

            EventHandler onClick = (_, __) => SelectPhoto(file, panel);
            panel.Click += onClick;
            pb.Click += onClick;
            lbl.Click += onClick;

            _flow.Controls.Add(panel);
        }

        // ═════════════════════════════════════════════════════════════════
        //  SELECCIÓN Y PREVIEW
        // ═════════════════════════════════════════════════════════════════

        private Panel _selectedPanel;

        private void SelectPhoto(string file, Panel panel)
        {
            // Quitar resaltado anterior
            if (_selectedPanel != null)
                _selectedPanel.BackColor = Color.FromArgb(22, 33, 52);

            _selectedFile = file;
            _selectedPanel = panel;
            panel.BackColor = Color.FromArgb(0, 80, 130);

            // Preview
            try
            {
                using (var ms = new MemoryStream(File.ReadAllBytes(file)))
                    _preview.Image = Image.FromStream(ms);
            }
            catch { _preview.Image = null; }

            // Info
            var fi = new FileInfo(file);
            _lblInfo.Text = $"{fi.Name}   |   {fi.Length / 1024} KB   |   {fi.CreationTime:dd/MM/yyyy HH:mm:ss}";
        }

        // ═════════════════════════════════════════════════════════════════
        //  ACCIONES
        // ═════════════════════════════════════════════════════════════════

        private void BtnSaveAs_Click(object sender, EventArgs e)
        {
            if (_selectedFile == null) { MessageBox.Show("Selecciona una foto primero."); return; }

            using (var dlg = new SaveFileDialog())
            {
                dlg.Title = "Guardar foto como…";
                dlg.Filter = "PNG (*.png)|*.png|JPEG (*.jpg)|*.jpg|Todos (*.*)|*.*";
                dlg.FileName = Path.GetFileNameWithoutExtension(_selectedFile);
                dlg.DefaultExt = "png";

                if (dlg.ShowDialog() != DialogResult.OK) return;

                try
                {
                    if (dlg.FilterIndex == 2) // JPEG
                    {
                        using (var img = Image.FromFile(_selectedFile))
                        using (var bmp = new System.Drawing.Bitmap(img))
                            bmp.Save(dlg.FileName, System.Drawing.Imaging.ImageFormat.Jpeg);
                    }
                    else
                    {
                        File.Copy(_selectedFile, dlg.FileName, overwrite: true);
                    }
                    MessageBox.Show("Foto guardada correctamente.");
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Error guardando: {ex.Message}");
                }
            }
        }

        private void BtnDelete_Click(object sender, EventArgs e)
        {
            if (_selectedFile == null) { MessageBox.Show("Selecciona una foto primero."); return; }

            if (MessageBox.Show($"¿Eliminar {Path.GetFileName(_selectedFile)}?",
                    "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes)
                return;

            try
            {
                File.Delete(_selectedFile);
                _files.Remove(_selectedFile);
                if (_selectedPanel != null)
                {
                    _flow.Controls.Remove(_selectedPanel);
                    _selectedPanel.Dispose();
                    _selectedPanel = null;
                }
                _preview.Image = null;
                _lblInfo.Text = "";
                _selectedFile = null;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error eliminando: {ex.Message}");
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            // Liberar imágenes cargadas
            foreach (Control c in _flow.Controls)
                foreach (Control child in c.Controls)
                    if (child is PictureBox pb && pb.Image != null)
                    {
                        pb.Image.Dispose();
                        pb.Image = null;
                    }
            _preview.Image?.Dispose();
            base.OnFormClosed(e);
        }
    }
}