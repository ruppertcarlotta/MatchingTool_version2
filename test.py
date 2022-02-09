import sys
from PyQt5 import QtWidgets, QtCore

class MyDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MyDialog, self).__init__(parent)

        scrolllayout = QtWidgets.QVBoxLayout()

        scrollwidget = QtWidgets.QWidget()
        scrollwidget.setLayout(scrolllayout)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)  # Set to make the inner widget resize with scroll area
        scroll.setWidget(scrollwidget)

        self.groupboxes = []  # Keep a reference to groupboxes for later use
        for i in range(8):    # 8 groupboxes with textedit in them
            groupbox = QtWidgets.QGroupBox('%d' % i)
            grouplayout = QtWidgets.QHBoxLayout()
            grouptext = QtWidgets.QTextEdit()
            grouplayout.addWidget(grouptext)
            groupbox.setLayout(grouplayout)
            scrolllayout.addWidget(groupbox)
            self.groupboxes.append(groupbox)

        self.buttonbox = QtWidgets.QDialogButtonBox()
        self.buttonbox.setOrientation(QtCore.Qt.Vertical)
        self.buttonbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(scroll)
        layout.addWidget(self.buttonbox)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    dialog = MyDialog()
    dialog.show()
    sys.exit(app.exec_())