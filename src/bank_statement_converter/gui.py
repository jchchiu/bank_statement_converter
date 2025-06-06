import sys, os
from PyQt5.QtCore    import QObject, QThread, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QCheckBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QTabWidget
)
from PyQt5.QtGui     import QDesktopServices

from .cba_converter import convert_cba
from .anz_converter import convert_anz
from .nab_converter import convert_nab
from .wbc_converter import convert_wbc
from .bank_detector import detect_bank
from .csv2qif       import csv_to_qif


# -------------------------------------------------------------------
# Helpers & Workers
# -------------------------------------------------------------------

class EmittingStream:
    """Redirect print() into a Qt signal."""
    def __init__(self, signal):
        self.signal = signal
    def write(self, text):
        text = text.rstrip()
        if text:
            self.signal.emit(text)
    def flush(self):
        pass


class PdfWorker(QObject):
    log      = pyqtSignal(str)
    error    = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, pdf_path, do_qif):
        super().__init__()
        self.pdf_path = pdf_path
        self.do_qif   = do_qif

    @pyqtSlot()
    def run(self):
        # capture print()
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = EmittingStream(self.log)
        sys.stderr = EmittingStream(self.log)
        outputs = []
        try:
            print(f"Detecting bank for “{self.pdf_path}”…")
            bank = detect_bank(self.pdf_path)
            if not bank:
                raise RuntimeError("Bank could not be detected")
            print(f"Detected bank: {bank.upper()}")
            print("-------------------------------------------------")

            print("Converting to CSV…")
            if bank == 'cba':
                csv_path = convert_cba(self.pdf_path)
            elif bank == 'nab':
                csv_path = convert_nab(self.pdf_path)
            elif bank == 'anz':
                csv_path = convert_anz(self.pdf_path)
            elif bank == 'wbc':
                csv_path = convert_wbc(self.pdf_path)
            else:
                raise RuntimeError(f"No converter for bank '{bank}'")
            print(f"Created CSV: {csv_path}")
            outputs.append(csv_path)

            if self.do_qif:
                print("Converting CSV → QIF…")
                qif_path = csv_to_qif(csv_path)
                print(f"Created QIF: {qif_path}")
                outputs.append(qif_path)

            self.finished.emit(outputs)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            sys.stdout, sys.stderr = old_out, old_err


class FolderWorker(QObject):
    """Batch‐convert all PDFs in a folder."""
    log      = pyqtSignal(str)
    error    = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, folder, do_qif):
        super().__init__()
        self.folder = folder
        self.do_qif = do_qif

    @pyqtSlot()
    def run(self):
        # capture print
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = EmittingStream(self.log)
        sys.stderr = EmittingStream(self.log)
        outputs = []
        try:
            pdfs = sorted(
                os.path.join(self.folder, f)
                for f in os.listdir(self.folder)
                if f.lower().endswith('.pdf')
            )
            if not pdfs:
                raise RuntimeError("No PDFs found in folder")

            for pdf in pdfs:
                self.log.emit(f" ")
                self.log.emit(f"--- {os.path.basename(pdf)} ---")
                bank = detect_bank(pdf)
                if not bank:
                    self.log.emit("  ERROR: could not detect bank")
                    continue
                self.log.emit(f"  Detected bank: {bank.upper()}")

                if bank == 'cba':
                    csv_path = convert_cba(pdf)
                elif bank == 'nab':
                    csv_path = convert_nab(pdf)
                elif bank == 'anz':
                    csv_path = convert_anz(pdf)
                elif bank == 'wbc':
                    csv_path = convert_wbc(pdf)
                else:
                    self.log.emit(f"  ERROR: no converter for '{bank}'")
                    continue

                self.log.emit(f"  → CSV: {csv_path}")
                outputs.append(csv_path)

                if self.do_qif:
                    self.log.emit("  Converting CSV → QIF…")
                    qif_path = csv_to_qif(csv_path)
                    self.log.emit(f"  → QIF: {qif_path}")
                    outputs.append(qif_path)

            self.finished.emit(outputs)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            sys.stdout, sys.stderr = old_out, old_err


class CsvWorker(QObject):
    log      = pyqtSignal(str)
    error    = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, csv_path):
        super().__init__()
        self.csv_path = csv_path

    @pyqtSlot()
    def run(self):
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = EmittingStream(self.log)
        sys.stderr = EmittingStream(self.log)
        try:
            print(f"Converting {self.csv_path} → QIF…")
            qif = csv_to_qif(self.csv_path)
            print(f"Created QIF: {qif}")
            self.finished.emit([qif])
        except Exception as e:
            self.error.emit(str(e))
        finally:
            sys.stdout, sys.stderr = old_out, old_err


class CsvFolderWorker(QObject):
    """Batch‐convert all CSVs in a folder → QIF."""
    log      = pyqtSignal(str)
    error    = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

    @pyqtSlot()
    def run(self):
        outputs = []
        try:
            csvs = sorted(
                os.path.join(self.folder, f)
                for f in os.listdir(self.folder)
                if f.lower().endswith('.csv')
            )
            if not csvs:
                raise RuntimeError("No CSVs found in folder")

            for csv_path in csvs:
                self.log.emit(f"--- {os.path.basename(csv_path)} ---")
                self.log.emit("Converting → QIF…")
                qif = csv_to_qif(csv_path)
                self.log.emit(f"  → QIF: {qif}")
                outputs.append(qif)

            self.finished.emit(outputs)
        except Exception as e:
            self.error.emit(str(e))


# -------------------------------------------------------------------
# UI Tabs
# -------------------------------------------------------------------

class PdfTab(QWidget):
    def __init__(self):
        super().__init__()
        # Widgets
        self.le_pdf           = QLineEdit()
        self.btn_browse_pdf   = QPushButton("Browse PDF…")
        self.btn_conv_pdf     = QPushButton("Convert PDF")

        self.le_folder_pdf    = QLineEdit()
        self.btn_browse_fld   = QPushButton("Browse Folder…")   
        self.btn_conv_folder  = QPushButton("Convert Folder")
        
        self.chk_qif          = QCheckBox("Also generate QIF")
        self.chk_qif.setChecked(True)
        self.btn_reset        = QPushButton("Reset")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.on_reset)

        self.txt_log          = QTextEdit(readOnly=True)
        self.lst_out          = QListWidget()

        # Layout
        v = QVBoxLayout(self)

        # Single‐PDF row: [PDF] [Browse] [Convert] [QIF?]
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("PDF:"))
        h1.addWidget(self.le_pdf)
        h1.addWidget(self.btn_browse_pdf)
        h1.addWidget(self.btn_conv_pdf)
        v.addLayout(h1)

        # Folder row: [Folder] [Browse] [Convert]
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Folder:"))
        h2.addWidget(self.le_folder_pdf)
        h2.addWidget(self.btn_browse_fld)
        h2.addWidget(self.btn_conv_folder)
        v.addLayout(h2)
        
        # Options
        opts = QHBoxLayout()
        opts.addWidget(QLabel("Options:"))
        opts.addWidget(self.chk_qif)
        opts.addStretch()
        opts.addWidget(self.btn_reset)
        v.addLayout(opts)

        # Log & outputs
        v.addWidget(QLabel("Log:"))
        v.addWidget(self.txt_log, 1)
        v.addWidget(QLabel("Outputs (double-click to open):"))
        v.addWidget(self.lst_out, 1)

        # Signals
        self.btn_browse_pdf.clicked.connect(self.on_browse_pdf)
        self.btn_conv_pdf.clicked.connect(self.on_convert_pdf)
        self.btn_browse_fld.clicked.connect(self.on_browse_folder)
        self.btn_conv_folder.clicked.connect(self.on_convert_folder)
        self.lst_out.itemDoubleClicked.connect(self.open_file)

    def on_reset(self):
        # clear all inputs
        self.le_pdf.clear()
        self.le_folder_pdf.clear()
        self.chk_qif.setChecked(False)

        # clear results
        self.txt_log.clear()
        self.lst_out.clear()

        # re-enable convert buttons
        self.btn_conv_pdf.setEnabled(True)
        self.btn_conv_folder.setEnabled(True)

        # disable reset until next run
        self.btn_reset.setEnabled(False)

    def on_browse_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf)"
        )
        if path:
            self.le_pdf.setText(path)

    def on_browse_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select folder of PDFs", ""
        )
        if path:
            self.le_folder_pdf.setText(path)

    def on_convert_pdf(self):
        pdf = self.le_pdf.text().strip()
        if not pdf or not os.path.isfile(pdf):
            QMessageBox.warning(self, "No PDF", "Please select a valid PDF.")
            return
        self._reset_ui_single()
        # start worker
        self._start_pdf_worker(pdf, self.chk_qif.isChecked())

    def on_convert_folder(self):
        fld = self.le_folder_pdf.text().strip()
        if not fld or not os.path.isdir(fld):
            QMessageBox.warning(self, "No folder", "Please select a valid folder.")
            return
        self._reset_ui_single()
        # start folder worker
        self._start_folder_worker(fld, self.chk_qif.isChecked())

    def _reset_ui_single(self):
        self.txt_log.clear()
        self.lst_out.clear()
        self.btn_conv_pdf.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)

    def _start_pdf_worker(self, pdf, do_qif):
        self.thread = QThread()
        self.worker = PdfWorker(pdf, do_qif)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.txt_log.append)
        self.worker.error.connect(self._on_error_pdf)
        self.worker.finished.connect(self._on_finished_pdf)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _start_folder_worker(self, fld, do_qif):
        self.thread = QThread()
        self.worker = FolderWorker(fld, do_qif)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.txt_log.append)
        self.worker.error.connect(self._on_error_folder)
        self.worker.finished.connect(self._on_finished_folder)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_finished_pdf(self, outputs):
        self.txt_log.append("<b>Done.</b>")
        for f in outputs:
            self.lst_out.addItem(QListWidgetItem(f))
        # disable convert until user hits Reset
        self.btn_conv_pdf.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)

    def _on_finished_folder(self, outputs):
        self.txt_log.append("<b>Batch Done.</b>")
        for f in outputs:
            self.lst_out.addItem(QListWidgetItem(f))
        self.btn_conv_pdf.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)

    def _on_error_pdf(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.txt_log.append(f"<span style='color:red'>ERROR: {msg}</span>")
        # allow Retry or Reset
        self.btn_conv_pdf.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)

    def _on_error_folder(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.txt_log.append(f"<span style='color:red'>ERROR: {msg}</span>")
        self.btn_conv_pdf.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)


    def open_file(self, item):
        path = item.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Not found", f"{path} does not exist.")


class CsvTab(QWidget):
    def __init__(self):
        super().__init__()
        # Inputs
        self.le_csv           = QLineEdit()
        self.btn_browse_csv   = QPushButton("Browse CSV…")
        self.btn_conv_csv     = QPushButton("Convert CSV")
        self.le_folder_csv    = QLineEdit()
        self.btn_browse_fld   = QPushButton("Browse Folder…")
        self.btn_conv_folder  = QPushButton("Convert Folder")
        
        self.btn_reset        = QPushButton("Reset")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.on_reset)
        # Log & Outputs
        self.txt_log          = QTextEdit(readOnly=True)
        self.lst_out          = QListWidget()
        

        # Layout
        v = QVBoxLayout(self)
        # CSV row
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("CSV:"))
        h1.addWidget(self.le_csv)
        h1.addWidget(self.btn_browse_csv)
        h1.addWidget(self.btn_conv_csv)
        v.addLayout(h1)
        
        # Folder row
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Folder:"))
        h2.addWidget(self.le_folder_csv)
        h2.addWidget(self.btn_browse_fld)
        h2.addWidget(self.btn_conv_folder)
        v.addLayout(h2)
        
        # Options
        opts = QHBoxLayout()
        opts.addWidget(QLabel("Options:"))
        opts.addStretch()
        opts.addWidget(self.btn_reset)
        v.addLayout(opts)
        
        # Log & Outputs
        v.addWidget(QLabel("Log:"))
        v.addWidget(self.txt_log, 1)
        v.addWidget(QLabel("Outputs (double-click to open):"))
        v.addWidget(self.lst_out, 1)

        # Signals
        self.btn_browse_csv.clicked.connect(self.on_browse_csv)
        self.btn_browse_fld.clicked.connect(self.on_browse_folder)
        self.btn_conv_csv.clicked.connect(self.on_convert_csv)
        self.btn_conv_folder.clicked.connect(self.on_convert_folder)
        self.lst_out.itemDoubleClicked.connect(self.open_file)

    def on_browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV file", "", "CSV Files (*.csv)"
        )
        if path:
            self.le_csv.setText(path)

    def on_browse_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select folder of CSVs", ""
        )
        if path:
            self.le_folder_csv.setText(path)

    def on_convert_csv(self):
        csv = self.le_csv.text().strip()
        if not csv or not os.path.isfile(csv):
            QMessageBox.warning(self, "No CSV", "Please select a valid CSV.")
            return
        self._reset_ui_single()
        self._start_csv_worker(csv)

    def on_convert_folder(self):
        fld = self.le_folder_csv.text().strip()
        if not fld or not os.path.isdir(fld):
            QMessageBox.warning(self, "No folder", "Please select a valid folder.")
            return
        self._reset_ui_single()
        self._start_csv_folder_worker(fld)

    def _reset_ui_single(self):
        self.txt_log.clear()
        self.lst_out.clear()
        self.btn_conv_csv.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
    
    def on_reset(self):
        self.le_csv.clear()
        self.le_folder_csv.clear()
        self.txt_log.clear()
        self.lst_out.clear()
        self.btn_conv_csv.setEnabled(True)
        self.btn_conv_folder.setEnabled(True)
        self.btn_reset.setEnabled(False)


    def _start_csv_worker(self, csv):
        self.thread = QThread()
        self.worker = CsvWorker(csv)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.txt_log.append)
        self.worker.error.connect(self._on_error_csv)
        self.worker.finished.connect(self._on_finished_csv)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _start_csv_folder_worker(self, fld):
        self.thread = QThread()
        self.worker = CsvFolderWorker(fld)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.txt_log.append)
        self.worker.error.connect(self._on_error_folder)
        self.worker.finished.connect(self._on_finished_folder)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_error_csv(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.txt_log.append(f"<span style='color:red'>ERROR: {msg}</span>")
        self.btn_conv_csv.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)

    def _on_finished_csv(self, outputs):
        self.txt_log.append("<b>Done.</b>")
        for f in outputs:
            self.lst_out.addItem(QListWidgetItem(f))
        self.btn_conv_csv.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)

    def _on_error_folder(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.txt_log.append(f"<span style='color:red'>ERROR: {msg}</span>")
        self.btn_conv_csv.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)

    def _on_finished_folder(self, outputs):
        self.txt_log.append("<b>Batch Done.</b>")
        for f in outputs:
            self.lst_out.addItem(QListWidgetItem(f))
        self.btn_conv_csv.setEnabled(False)
        self.btn_conv_folder.setEnabled(False)
        self.btn_reset.setEnabled(True)

    def open_file(self, item):
        path = item.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Not found", f"{path} does not exist.")


# -------------------------------------------------------------------
# Main Application
# -------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bank Converter GUI")
        tabs = QTabWidget()
        tabs.addTab(PdfTab(), "PDF → CSV/QIF")
        tabs.addTab(CsvTab(), "CSV → QIF")
        self.setCentralWidget(tabs)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
