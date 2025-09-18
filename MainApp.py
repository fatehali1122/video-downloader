import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QProgressBar, QMessageBox, QDesktopWidget,QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from downloader import get_available_formats, download_with_format, pick_nearest_format

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, url, fmt, output_dir):
        super().__init__()
        self.url = url
        self.fmt = fmt
        self.output_dir = output_dir
        self._is_running = True

    def run(self):
        try:
            
            def progress_hook(d):
                if not self._is_running:
                    raise Exception("Download cancelled by user")
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    if total:
                        percent = int(downloaded / total * 100)
                        self.progress.emit(percent)
                        self.status.emit(f"Downloading... {percent}%")
                elif d.get("status") == "finished":
                    self.progress.emit(100)
                    self.status.emit("Download completed!")

            download_with_format(self.url, self.fmt, self.output_dir, progress_hook)
        except Exception as e:
            self.status.emit(f"Error: {str(e)}")

    def stop(self):
        self._is_running = False

def patched_download_with_format(url, format_string, output_dir="downloads", progress_hook=None):
    os.makedirs(output_dir, exist_ok=True)
    from yt_dlp import YoutubeDL
    ydl_opts = {
        "format": format_string,
        "outtmpl": os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s"),
        "merge_output_format": None,
        "noplaylist": True,
    }
    if progress_hook:
        ydl_opts["progress_hooks"] = [progress_hook]
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

import downloader
downloader.download_with_format = patched_download_with_format


class MainWindow(QWidget):
    def center(self):
        qr = self.frameGeometry()                  
        cp = QDesktopWidget().availableGeometry().center()  
        qr.moveCenter(cp)                         
        self.move(qr.topLeft()) 
    
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.save_path.setText(folder)
    
    def __init__(self,parent = None):
        super().__init__(parent)

        self.setWindowTitle("Video Downloader")
        self.setFixedSize(1000, 600)
        self.center()

        layout = QVBoxLayout()
        layout.setSpacing(25)  
        layout.setContentsMargins(30,30,30,30)

        urlLayout = QHBoxLayout()
        self.url_label = QLabel("🔗 Video URL ")
        self.url_label.setFixedWidth(170)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste the link here")

        urlLayout.addWidget(self.url_label)
        urlLayout.addWidget(self.url_input,3)

        self.fetch_button = QPushButton("Fetch Formats")
        self.fetch_button.setObjectName("fetch")
        self.fetch_button.clicked.connect(self.fetch_formats)

        urlLayout.addWidget(self.fetch_button,1)

        format_Layout = QHBoxLayout()
        self.format_label = QLabel("⬇️ Select Format:")
        self.format_label.setFixedWidth(170)
        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(500)
        self.format_combo.setFixedHeight(36)


        format_Layout.addWidget(self.format_label)
        format_Layout.addWidget(self.format_combo,2)

        save_layout = QHBoxLayout()
        self.save_label = QLabel("📂 Save Location:")
        self.save_label.setFixedWidth(170)
        self.save_button = QPushButton("Choose Folder")
        self.save_button.setFixedHeight(36)
        self.save_button.setObjectName("save")
        self.save_path = QLabel("No folder selected")
        self.save_button.clicked.connect(self.choose_folder)

        save_layout.addWidget(self.save_label)
        save_layout.addWidget(self.save_button,1)
        save_layout.addWidget(self.save_path,3)

        button_layout = QHBoxLayout()
        self.download_button = QPushButton("⬇️ Download")
        self.cancel_button = QPushButton("✖️ Cancel")
        self.download_button.setObjectName("download")
        self.cancel_button.setObjectName("cancel")

        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(urlLayout)
        layout.addLayout(format_Layout)
        layout.addLayout(save_layout)
        layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(36)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self.download_button.clicked.connect(self.start_download)
        self.cancel_button.clicked.connect(self.cancel_download)

        self.thread = None
    
    def fetch_formats(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a video URL!")
            return
        try:
            self.formats_dict = get_available_formats(url)
            self.format_combo.clear()
            self.format_combo.addItems(self.formats_dict.keys())

            self.status_label.setText(f"Status: Found {len(self.formats_dict)} formats")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not fetch formats:\n{str(e)}")

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a video URL!")
            return
        if self.save_path.text() == "No folder selected":
            QMessageBox.warning(self, "Error", "Please select a save folder!")
            return
        selected_format = self.format_combo.currentText()
        if not selected_format:
            QMessageBox.warning(self, "Error", "Please select a format!")
            return

        formats_dict = self.formats_dict
        selected_format = self.format_combo.currentText()
        if not selected_format:
            QMessageBox.warning(self, "Error", "Please select a format!")
            return
        fmt_string = pick_nearest_format(selected_format, formats_dict)

        self.thread = DownloadThread(url, fmt_string, self.save_path.text())
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.status.connect(lambda msg: self.status_label.setText(f"Status: {msg}"))
        self.thread.start()

    def cancel_download(self):
        if self.thread:
            self.thread.stop()



if __name__ == "__main__":
    app = QApplication(sys.argv)

    with open("dark_theme.qss", "r") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
