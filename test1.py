import sys
import re
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QFileSystemModel, QVBoxLayout, QWidget, QLabel, QSplitter
from PyQt5.QtCore import QSortFilterProxyModel, QRegExp, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap

class ImageFileFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        if self.sourceModel().isDir(index):
            return True
        file_name = self.sourceModel().fileName(index)
        return bool(QRegExp.match(r".*\.(jpg|jpeg|png)$", file_name, QRegExp.IGNORECASE))

class FileExplorerWidget(QWidget):
    # Define a custom signal that emits the file path as a string
    fileDoubleClicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.splitter = QSplitter(self)
        self.layout.addWidget(self.splitter)

        self.model = QFileSystemModel()
        self.model.setRootPath('')

        self.proxyModel = ImageFileFilterProxyModel()
        self.proxyModel.setSourceModel(self.model)
        self.proxyModel.setFilterKeyColumn(0)  # Apply filter on the file names

        self.tree = QTreeView()
        self.tree.setModel(self.proxyModel)
        self.tree.setRootIndex(self.proxyModel.mapFromSource(self.model.index('')))
        self.tree.setColumnWidth(0, 400)

        # Hide other columns except the first one (name)
        for i in range(1, self.model.columnCount()):
            self.tree.hideColumn(i)

        self.tree.doubleClicked.connect(self.onDoubleClick)

        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setMinimumSize(1, 1)

        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.imageLabel)

    def onDoubleClick(self, index):
        # Map the proxy index to the source index
        source_index = self.proxyModel.mapToSource(index)
        file_path = self.model.filePath(source_index)
        self.fileDoubleClicked.emit(file_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("File Explorer")
        self.setGeometry(100, 100, 1000, 600)

        self.fileExplorerWidget = FileExplorerWidget()
        self.setCentralWidget(self.fileExplorerWidget)

        # Connect the custom signal to a slot in the main window
        self.fileExplorerWidget.fileDoubleClicked.connect(self.showImage)

    def showImage(self, file_path):
        pixmap = QPixmap(file_path)
        self.fileExplorerWidget.imageLabel.setPixmap(pixmap.scaled(
            self.fileExplorerWidget.imageLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

def main():
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
