from PySide6.QtWidgets import QApplication, QTreeView, QFileSystemModel
from PySide6.QtCore import QDir

app = QApplication([])

model = QFileSystemModel()
model.setRootPath(QDir.homePath())

tree = QTreeView()
tree.setModel(model)
tree.setRootIndex(model.index(QDir.homePath()))
tree.setWindowTitle("File Browser")
tree.resize(900, 600)
tree.show()

app.exec()