import sys
import os

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QListWidget,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QLineEdit,
    QMenuBar, QMenu, QStyle, QToolButton
)
from PyQt5.QtCore import Qt, QTimer, QRunnable, QThreadPool, QObject, pyqtSignal


class SignalProxy(QObject):
    finished = pyqtSignal(list)


class ListLoaderWorker(QRunnable):
    def __init__(self, source_dir, current_entries, signal_proxy):
        super().__init__()
        self.source_dir = source_dir
        self.current_entries = current_entries
        self.signal_proxy = signal_proxy

    def run(self):
        try:
            all_files = sorted([
                f for f in os.listdir(self.source_dir)
                if os.path.isfile(os.path.join(self.source_dir, f))
            ], key=str.lower)
            available = sorted(set(all_files) - self.current_entries, key=str.lower)
        except Exception:
            available = []
        self.signal_proxy.finished.emit(available)


class ListManager(QWidget):
    def closeEvent(self, event):
        if hasattr(self, 'list_file') and self.list_file:
            current_list = sorted(self.current_entries, key=str.lower)
            try:
                with open(self.list_file, 'r') as f:
                    lines = f.readlines()[1:]
                    original_list = sorted([line.strip() for line in lines if line.strip()], key=str.lower)
            except Exception:
                original_list = []

            if current_list != original_list or self.source_dir_edit.text().strip() != self.orig_source_dir:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "You have unsaved changes. Save before exiting?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Cancel
                )
                if reply == QMessageBox.Cancel:
                    event.ignore()
                    return
                elif reply == QMessageBox.Yes:
                    self.save_list_file()
                    event.accept()
                    return
        event.accept()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(".list File Manager")
        self.resize(1280, 720)

        self.list_file = None
        self.source_dir = None
        self.current_entries = set()
        self.all_available = []
        self.all_in_list = []

        menu_bar = QMenuBar(self)
        file_menu = menu_bar.addMenu("File")

        load_action = file_menu.addAction("Load List File")
        load_action.triggered.connect(self.load_list_file)

        new_action = file_menu.addAction("New List File")
        new_action.triggered.connect(self.create_new_list_file)

        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_list_file)

        self.source_dir_edit = QLineEdit()
        self.source_dir_edit.setPlaceholderText("Source directory from first line of file")
        self.source_dir_edit.textChanged.connect(self.update_source_dir)

        self.change_source_button = QToolButton()
        self.change_source_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.change_source_button.setToolTip("Change Source Directory")
        self.change_source_button.clicked.connect(self.change_source_directory)

        source_layout = QHBoxLayout()
        source_layout.addWidget(self.source_dir_edit)
        source_layout.addWidget(self.change_source_button)

        self.status = QLabel("No file loaded")
        self.counts = QLabel("0 available, 0 in list")

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Type 4+ characters to search...")
        self.search_bar.textChanged.connect(self.filter_lists)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_filter)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.clear_button)

        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.MultiSelection)

        self.in_list = QListWidget()
        self.in_list.setSelectionMode(QListWidget.MultiSelection)

        self.add_button = QPushButton("Add >>")
        self.add_button.clicked.connect(self.add_selected)

        self.remove_button = QPushButton("<< Remove")
        self.remove_button.clicked.connect(self.remove_selected)

        button_layout = QVBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()

        lists_layout = QHBoxLayout()
        lists_layout.addWidget(self.available_list)
        lists_layout.addLayout(button_layout)
        lists_layout.addWidget(self.in_list)

        top_layout = QVBoxLayout()
        top_layout.setMenuBar(menu_bar)
        top_layout.addWidget(self.save_button)
        top_layout.addWidget(QLabel("Source Directory:"))
        top_layout.addLayout(source_layout)
        top_layout.addLayout(search_layout)
        top_layout.addWidget(self.status)
        top_layout.addWidget(self.counts)
        top_layout.addLayout(lists_layout)

        self.setLayout(top_layout)
        self.threadpool = QThreadPool()

    def update_source_dir(self, text):
        self.orig_source_dir = text.strip()
        self.source_dir = os.path.normpath(self.orig_source_dir.replace("/mnt/user/Stuff/", "Y:/"))

    def change_source_directory(self):
        start_dir = ""
        if os.path.isdir(self.source_dir):
            start_dir = self.source_dir
        folder = QFileDialog.getExistingDirectory(self, "Select New Source Folder", start_dir)
        if folder:
            linux_style_path = folder.replace("\\", "/").replace("Y:/", "/mnt/user/Stuff/")
            self.source_dir_edit.setText(linux_style_path)

    def create_new_list_file(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if not folder:
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Create .list File", "", "List Files (*.list)")
        if not save_path:
            return
        linux_style_path = folder.replace("\\", "/").replace("Y:/", "/mnt/user/Stuff/")
        try:
            with open(save_path, 'w', newline='\n') as f:
                f.write(linux_style_path + '\n')
            QMessageBox.information(self, "Created", f"New .list file created:\n{save_path}")
            self.list_file = save_path
            self.orig_source_dir = linux_style_path
            self.source_dir = folder
            self.source_dir_edit.setText(linux_style_path)
            self.current_entries = set()
            self.all_available = []
            self.all_in_list = []
            self.status.setText("Loading")
            self.loading_dots = 0
            self.loading_timer = QTimer(self)
            self.loading_timer.timeout.connect(self.animate_loading)
            self.loading_timer.start(300)
            QTimer.singleShot(50, self.start_background_worker)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create file:\n{e}")

    def load_list_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select .list File", "", "List Files (*.list)")
        if not path:
            return
        self.list_file = path
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read list file:\n{e}")
            return
        if not lines:
            QMessageBox.critical(self, "Error", "List file is empty.")
            return
        self.orig_source_dir = lines[0].strip()
        self.source_dir_edit.setText(self.orig_source_dir)
        self.source_dir = os.path.normpath(self.orig_source_dir.replace("/mnt/user/Stuff/", "Y:/"))
        if not os.path.isdir(self.source_dir):
            QMessageBox.critical(self, "Error", f"Source directory does not exist:\n{self.source_dir}")
            return
        self.loading_dots = 0
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.animate_loading)
        self.loading_timer.start(300)
        self.status.setText("Loading")
        QApplication.processEvents()
        self.current_entries = set(line.strip() for line in lines[1:] if line.strip())
        QTimer.singleShot(50, self.start_background_worker)

    def start_background_worker(self):
        self.signal_proxy = SignalProxy(self)
        self.signal_proxy.finished.connect(self.finish_list_update)
        worker = ListLoaderWorker(self.source_dir, self.current_entries, self.signal_proxy)
        self.threadpool.start(worker)
        self.worker = worker

    def finish_list_update(self, available):
        if hasattr(self, 'loading_timer') and self.loading_timer.isActive():
            self.loading_timer.stop()
        self.all_available = available
        self.all_in_list = sorted(self.current_entries, key=str.lower)
        self.filter_lists()
        self.status.setText(f"Loaded: {os.path.basename(self.list_file)}")

    def save_list_file(self):
        if not self.list_file:
            return
        try:
            with open(self.list_file, 'w', newline='\n') as f:
                f.write(self.orig_source_dir + '\n')
                for entry in sorted(self.current_entries, key=str.lower):
                    f.write(entry + '\n')
            QMessageBox.information(self, "Saved", "List file saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save list file:\n{e}")

    def filter_lists(self):
        term = self.search_bar.text().lower()
        self.available_list.clear()
        self.in_list.clear()
        if len(term) >= 4:
            filtered_available = [f for f in self.all_available if term in f.lower()]
            filtered_in_list = [f for f in self.all_in_list if term in f.lower()]
        else:
            filtered_available = self.all_available
            filtered_in_list = self.all_in_list
        self.available_list.addItems(filtered_available)
        self.in_list.addItems(filtered_in_list)
        self.update_counts()

    def clear_filter(self):
        self.search_bar.clear()
        self.filter_lists()

    def add_selected(self):
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            return
        added = []
        for item in selected_items:
            text = item.text()
            if text not in self.current_entries:
                self.current_entries.add(text)
                added.append(text)
        if added:
            self.all_available = [f for f in self.all_available if f not in added]
            self.all_in_list = sorted(self.current_entries, key=str.lower)
            self.filter_lists()

    def remove_selected(self):
        selected_items = self.in_list.selectedItems()
        if not selected_items:
            return
        removed = []
        for item in selected_items:
            text = item.text()
            if text in self.current_entries:
                self.current_entries.remove(text)
                removed.append(text)
        if removed:
            self.all_in_list = sorted(self.current_entries, key=str.lower)
            self.all_available += removed
            self.all_available = sorted(self.all_available, key=str.lower)
            self.filter_lists()

    def animate_loading(self):
        self.loading_dots = (self.loading_dots + 1) % 4
        self.status.setText("Loading" + "." * self.loading_dots)

    def update_counts(self):
        self.counts.setText(f"{self.available_list.count()} available, {self.in_list.count()} in list")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ListManager()
    window.show()
    sys.exit(app.exec_())
