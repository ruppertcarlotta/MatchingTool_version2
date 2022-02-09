import re
import pandas as pd
import numpy as np
import shutil
import os.path
import os
import sys
import functools
from itertools import groupby

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QPushButton, QVBoxLayout
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

import pydicom
import pydicom.data
from PyQt5.QtWidgets import QWidget, QComboBox, QHBoxLayout, QApplication, QCompleter, QCheckBox, QLabel


def completion(word_list, widget, i=True):
    """ Autocompletion of sender and subject """
    word_set = set(word_list)
    completer = QCompleter(word_set)
    if i:
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
    else:
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
    widget.setCompleter(completer)


class Autocomplete(QtWidgets.QComboBox):
    '''Autocomplete Combobox'''
    def __init__(self, items, parent=None, i=False, allow_duplicates=True):
        super(Autocomplete, self).__init__(parent)
        self.items = items
        self.insensitivity = i
        self.allowDuplicates = allow_duplicates
        self.init()

    def init(self):
        self.setEditable(True)
        self.setDuplicatesEnabled(self.allowDuplicates)
        self.addItems(self.items)
        self.setAutocompletion(self.items, i=self.insensitivity)

    def setAutocompletion(self, items, i):
        completion(items, self, i)


class MplCanvas(QtWidgets.QWidget):
    ''' Canvas Widget holding single DICOM plot and label widgets'''
    def __init__(self, parent=None, dicom_file=None, width=5, height=4, dpi=100):
        super(MplCanvas, self).__init__()
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvas(self.fig)

        self.dicom_file = dicom_file
        self.birads_class = None
        self.checked_dict = {"example": False, "example2": False}
        self.color = "dimgray"
        self.axes = self.fig.add_subplot(111)
        self.selected = False

        self.canvas_layout = QtWidgets.QHBoxLayout()
        self.canvas_layout.addWidget(self.canvas)
        self.setLayout(self.canvas_layout)

        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor.fromRgb(105, 105, 105))
        self.setPalette(p)
        self.fig.patch.set_facecolor(self.color)
        self.canvas.draw()

    def on_button_press_event(self, event):
        # toggle selected
        self.selected = not self.selected
        if self.selected:
            # change color
            self.color = "#FC5A50"

            # create tickbox widget and layout
            self.tickbox_widget = QtWidgets.QWidget()
            self.tickbox_layout = QtWidgets.QVBoxLayout()
            self.tickbox_widget.setLayout(self.tickbox_layout)

            # set widget color
            p = self.tickbox_widget.palette()
            p.setColor(self.backgroundRole(), QColor.fromRgb(252, 90, 80))
            self.tickbox_widget.setPalette(p)

            # # create label
            # self.birads_label = QtWidgets.QLabel("BIRADS class")
            # self.tickbox_layout.addWidget(self.birads_label)

            # create BIRADS Combobox
            self.autocomplete = Autocomplete(['1 - BIRADS 1', '2 - BIRADS 2', '3 - BIRADS 3', '4 - BIRADS 4', '5 - BIRADS 5 ', '6 - BIRADS 6'],
                                             parent=self, i=True, allow_duplicates=False
                                             )
            self.autocomplete.setInsertPolicy(QComboBox.NoInsert)
            self.tickbox_layout.addWidget(self.autocomplete)
            if self.birads_class:
                self.autocomplete.setCurrentIndex(self.birads_class-1)

            # create checkboxes & add them to widget layout
            self.example_tickbox = QtWidgets.QCheckBox("example")
            self.example_tickbox2 = QtWidgets.QCheckBox("example2")
            self.tickbox_layout.addWidget(self.example_tickbox)
            self.tickbox_layout.addWidget(self.example_tickbox2)

            # check current checkbox state
            self.example_tickbox.setChecked(self.checked_dict[self.example_tickbox.text()])
            self.example_tickbox2.setChecked(self.checked_dict[self.example_tickbox2.text()])

            # connect checkboxes and combobox
            self.example_tickbox.stateChanged.connect(lambda: self.state_changed(self.example_tickbox))
            self.example_tickbox2.stateChanged.connect(lambda: self.state_changed(self.example_tickbox2))
            self.autocomplete.currentTextChanged.connect(self.update_birads)

            # add to main canvas layout
            self.canvas_layout.addWidget(self.tickbox_widget)

        else:
            # change color
            self.color = "dimgray"
            # delete tickbox widget
            self.tickbox_widget.setParent(None)

        # draw background color
        self.fig.patch.set_visible(True)
        self.fig.patch.set_facecolor(self.color)
        self.canvas.draw()

    def update_birads(self):
        self.birads_class = int(str(self.autocomplete.currentText())[0])

    def state_changed(self, tickbox):
        key = tickbox.text()
        if tickbox.isChecked():
            self.checked_dict[key] = True
        else:
            self.checked_dict[key] = False


class DicomWindow(QDialog):
    def __init__(self, path, parent=None):
        super(DicomWindow, self).__init__(parent)

        self.init_gui()

        self.result_path = path
        self.selected_files = {'file_names': [], 'birads_class': [], 'session_nb': []}

        self.look_up_excel = pd.read_excel(os.path.join(self.result_path, 'matching.xlsx'), header=None)
        new_header = self.look_up_excel.iloc[0]
        self.look_up_excel = self.look_up_excel[1:]
        self.look_up_excel.columns = new_header

        self.session = 0
        self.birads_class = None
        self.session_plots = []
        self.setWindowTitle("Choose Dicom Files")

    def init_gui(self):

        self.scrolllayout = QtWidgets.QVBoxLayout()

        self.scrollwidget = QtWidgets.QWidget()
        self.scrollwidget.setLayout(self.scrolllayout)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scrollwidget)

        # Just some button connected to `plot` method
        self.button = QPushButton('Start')
        self.button.clicked.connect(self.plot)
        self.save_button = QPushButton('')
        self.save_button.clicked.connect(self.save)


        # set the layout
        layout = QVBoxLayout()

        layout.addWidget(self.scroll)  # group box inside scroll area
        # layout.addWidget(self.group_dicom)
        layout.addWidget(self.button)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def save(self):
        self.update_selected_files()
        write_dict_2_csv(self.selected_files, 'selected', self.result_path)

    def plot(self):

        # Start was pressed
        if self.session == 0:

            if os.path.isfile(os.path.join(self.result_path, 'selected.xlsx')):
                # read file
                saved_file = os.path.join(self.result_path, 'selected.xlsx')
                df = pd.read_excel(saved_file, header=None)
                new_header = df.iloc[0]
                df = df[1:]
                df.columns = new_header
                self.session = df["session_nb"].iloc[-1] + 1
                self.selected_files = df.to_dict('list')

        # delete old plots from widget
        self.update_selected_files()
        for i in reversed(range(self.scrolllayout.count())):
            self.scrolllayout.itemAt(i).widget().setParent(None)

        dicom_files = []
        img_indices = self.look_up_excel['all_img_names'].where(self.look_up_excel['all_sessions'] == self.session)


        for index in img_indices:
            if pd.isnull(index):
                continue
            file_name = str(index + 1) + '.dcm'
            dicom_files.append(file_name)

        self.session_plots = []

        # create plots
        for i, pass_dicom in enumerate(dicom_files):
            sc = MplCanvas(self, pass_dicom, width=14, height=10, dpi=50)
            sc.canvas.mpl_connect('button_press_event', sc.on_button_press_event)
            self.session_plots.append(sc)
            filename = pydicom.data.data_manager.get_files(self.result_path, pass_dicom)[0]
            try:
                ds = pydicom.dcmread(filename)
            except:
                continue
            try:
                data = ds.pixel_array
            except:
                continue

            sc.axes.imshow(data, cmap=plt.cm.bone)
            sc.axes.set_axis_off()
            sc.canvas.setMinimumSize(sc.canvas.size())
            self.scrolllayout.addWidget(sc)

        self.session += 1

        button_update = "Next Session"
        self.button.setText(button_update)

        button_update = "Save"
        self.save_button.setText(button_update)

    def get_selected_files(self):
        return self.selected_files

    def update_selected_files(self):
        for plot in self.session_plots:
            if plot.selected:
                self.selected_files['file_names'].append(plot.dicom_file)
                self.selected_files['birads_class'].append(self.birads_class)
                self.selected_files['session_nb'].append(self.session)



def handle_exceptions(func):
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            with open('errors.log', 'a+') as f:
                f.write('Exception in {}: {}\n'.format(func.__name__, e))
            return None

    return func_wrapper


@handle_exceptions
def all_equal(iterable):
    g = groupby(iterable)
    return next(g, True) and not next(g, False)


@handle_exceptions
def romanToInt(s):
    """
    :type s: str
    :rtype: int
    """
    roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000, 'IV': 4, 'IX': 9, 'XL': 40, 'XC': 90,
             'CD': 400, 'CM': 900}
    i = 0
    num = 0
    while i < len(s):
        if i + 1 < len(s) and s[i:i + 2] in roman:
            num += roman[s[i:i + 2]]
            i += 2
        else:
            # print(i)
            num += roman[s[i]]
            i += 1
    return num


@handle_exceptions
def reports_to_csv(report_file, results_path, unambiguous=False):
    '''

    :return:
    '''
    # report_file = os.path.join(os.getcwd(), 'befunde.txt')
    print("Starting extracting of BIRADS classes...")
    with open(report_file, 'r') as file:
        # read file
        data = file.read().replace('\n', '')

        # reports are divided by dotted line
        search_str = '-------------------------------------------------------------------------------------------------------------------------------------------'
        reports = data.split(search_str)

        # info is structured in the following way:
        # Datum;Name;Vorname;Geburtsdatum;Patienten Fremd ID;

        # loop over reports and fill dict with info
        extracted_dict = {'patient_id': [], 'study_date': [], 'birads': []}
        doubles = 0
        for i, report in enumerate(reports):

            # first report is differently structured
            if i == 0:
                search_str_beg = 'Patienten Fremd ID;'
                index = [l for l in range(len(report)) if data.startswith(search_str_beg, l)]
                start = index[0] + 19
                report = report[start:]

            res = [k for k in range(len(report)) if report.startswith(';', k)]

            info = report.split(';')

            # last report is empty
            if len(info) <= 1:
                continue

            # extract matching information
            study_date = info[0]
            patient_id = info[4]

            # extract BIRADS information from remaining string
            remaining = report[res[4]:]

            # cut end phrase with confusing BIRADS classification
            if "Gerne können Sie bei Bedarf" in report:
                stop_index = [k for k in range(len(remaining)) if
                              remaining.startswith('Gerne können Sie bei Bedarf', k)]
                remaining = remaining[:stop_index[0]]

            birads_index = [k for k in range(len(remaining)) if remaining.startswith('BIRADS', k)]

            # there may be multiple BIRADS in remaining string
            birads_classes = []

            for j, bir in enumerate(birads_index):
                birads_class = remaining[bir + 7]

                if not birads_class.isdigit():

                    # try if there is no spacing
                    birads_class = remaining[bir + 6]

                    if not birads_class.isdigit():

                        # try whether birads class is undefined or not given --> continue
                        if birads_class == '?' or birads_class == '.':
                            continue

                        # try if there is double spacing
                        birads_class = remaining[bir + 8]
                        if not birads_class.isdigit():

                            # try if there are roman numbers
                            rom = remaining[bir + 6:bir + 9]
                            rom = re.sub('[^IV]', '', rom)

                            if len(rom) > 0:
                                birads_class = str(romanToInt(rom))

                            # skip all other cases
                            else:
                                continue
                if birads_class == "0":
                    continue
                birads_classes.append(birads_class)

            # more than once BIRADS in text?
            if len(birads_classes) > 1:
                # all the same?
                if all_equal(birads_classes):

                    extracted_dict['patient_id'].append(patient_id)
                    extracted_dict['study_date'].append(study_date)
                    extracted_dict['birads'].append(birads_classes[0])

                # if ambiguious is True:
                # check whether there are more than 2 different classes in one single report.
                # If there are: continue, if not, keep and add both to dict.
                # For the latter: resulting in 2 lines for same session in the csv file.
                else:
                    if not unambiguous:
                        birads_classes = set(birads_classes)

                        if len(birads_classes) > 2:
                            continue

                        else:
                            doubles += 1
                            for b_class in birads_classes:
                                extracted_dict['patient_id'].append(patient_id)
                                extracted_dict['study_date'].append(study_date)
                                extracted_dict['birads'].append(b_class)

                    else:
                        continue

            # zero valid birads classes ? continue!
            elif len(birads_classes) == 0:
                continue

            # only one birads class? GREAT!
            else:
                extracted_dict['patient_id'].append(patient_id)
                extracted_dict['study_date'].append(study_date)
                extracted_dict['birads'].append(birads_classes[0])

        if not unambiguous:
            print("# of reports with multiple BIRADS classes:", doubles)
        final_dict = {'KIS': [], 'day': [], 'month': [], 'year': [], 'BIRADS': []}
        final_dict['KIS'] = [int(x) for x in extracted_dict['patient_id']]
        final_dict['BIRADS'] = [int(x) for x in extracted_dict['birads']]

        for date in extracted_dict['study_date']:
            date = date.split('.')
            final_dict['day'].append(int(date[0]))
            final_dict['month'].append(int(date[1]))
            final_dict['year'].append(int(date[2]))

        write_dict_2_csv(final_dict, 'report_database', results_path)
        print("Done with BIRADS extraction process!")


def load_dicom_session(session_nb):
    pass


def reformat_date(day, month, year):
    '''
    :param day: int
    :param month: int
    :param year: int
    :return: string of date format yyyymmdd
    '''
    if day < 10:
        day = str(0) + str(day)
    else:
        day = str(day)
    if month < 10:
        month = str(0) + str(month)
    else:
        month = str(month)

    return str(year) + month + day


def copy_dicom_file(file, sub_dir, file_nb, result_path):
    original = os.path.join(os.path.join(os.getcwd(), sub_dir), file)
    target = os.path.join(result_path, str(file_nb) + '.dcm')

    shutil.copyfile(original, target)


def write_dict_2_csv(mydict, name, results_path):
    '''
    Multiple dicom files are matching on single session and birads classification.
    The images are renamed (anonymized) and saved with a corresponding csv / xlsx file containing
    information of the session nb and birads classification.

    :param mydict: dictionary
    :return: None

    Saving xlsx and csv file.
    '''

    # results folder

    df = pd.DataFrame(data=mydict)
    # write to csv
    df.to_csv(os.path.join(results_path, name + '.csv'), index=False)
    df.to_excel(os.path.join(results_path, name + '.xlsx'), index=False)

    print(f'Files successfully saved to {results_path}.')


def matching(dicom_path, result_path, copy=True):
    # read data base reports

    print("Starting matching process...")

    report_xls = os.path.join(result_path, 'report_database.xlsx')
    df = pd.read_excel(report_xls, header=None)
    new_header = df.iloc[0]
    df = df[1:]
    df.columns = new_header

    nb_matches = 0
    nb_session = 0

    matching_dict = {'all_img_names': [], 'all_birads': [], 'all_sessions': []}

    current_id = None
    previous_id = None
    birads_class_balance = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}
    for subdir, dirs, files in os.walk(dicom_path):
        for file in files:

            info = file.split('-')

            # befunde.txt file
            if np.array(info).size == 1:
                continue

            index_KIS = 1
            index_study_date = 3
            KIS = info[index_KIS]
            study_date = info[index_study_date]

            # in case names include '-' (e.g., Jean-Baptiste)
            while not KIS.isnumeric():
                index_KIS += 1
                index_study_date += 1
                KIS = info[index_KIS]
                study_date = info[index_study_date]

            current_id = KIS

            for i, (patient_id, day, month, year, birads) in enumerate(zip(df['KIS'], df['day'],
                                                                           df['month'], df['year'], df['BIRADS'])):
                # if birads == 0:
                #     continue

                # reformat date
                date = reformat_date(day, month, year)

                # check that both patient ID and study date match
                if int(KIS) == patient_id and study_date == date:
                    matching_dict['all_img_names'].append(nb_matches)
                    matching_dict['all_birads'].append(birads)

                    if previous_id:
                        if current_id != previous_id:
                            nb_session += 1

                    matching_dict['all_sessions'].append(nb_session)
                    nb_matches += 1
                    previous_id = current_id
                    birads_class_balance[str(birads)] += 1

                    if copy:
                        print(f"Anonymizing file # {nb_matches}")
                        copy_dicom_file(file, subdir, nb_matches - 1, result_path)

    print(f'\nNumber of matched images: {nb_matches}')
    print(f'Number of entries in the report database: {len(df)}')
    print(f'Number of matched sessions: {nb_session}')
    print(f'Average number of dicom files per matched session: {nb_matches / nb_session}\n')

    class_1 = birads_class_balance['1']
    class_2 = birads_class_balance['2']
    class_3 = birads_class_balance['3']
    class_4 = birads_class_balance['4']
    class_5 = birads_class_balance['5']
    class_6 = birads_class_balance['6']

    print(f'\nClass inbalance:\nBIRADS 1: {class_1}'
          f'\nBIRADS 2: {class_2}\n'
          f'BIRADS 3: {class_3}\n'
          f'BIRADS 4: {class_4}\n'
          f'BIRADS 5: {class_5}\n'
          f'BIRADS 6: {class_6}\n ')

    write_dict_2_csv(matching_dict, 'matching', result_path)
    print("Done with Matching Process!")


class MyWidget(QtWidgets.QWidget):

    @handle_exceptions
    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.dicom_path = None
        self.report_path = None
        self.results_path = None

        self.setWindowTitle("Ultrasound Images")
        self.init_gui()

    def init_gui(self):
        self.report_button = QtWidgets.QPushButton("...")
        self.report_text = QtWidgets.QLabel("Open report.txt file:")
        self.report_text.setAlignment(QtCore.Qt.AlignCenter)
        self.report_line = QLineEdit(self)
        self.report_line.setEnabled(False)
        self.unambiguous = False
        self.cbox = QCheckBox("unambiguous")

        self.dicom_button = QtWidgets.QPushButton("...")
        self.dicom_text = QtWidgets.QLabel("Open dicom folder:")
        self.dicom_text.setAlignment(QtCore.Qt.AlignCenter)
        self.dicom_line = QLineEdit(self)
        self.dicom_line.setEnabled(False)

        self.results_button = QtWidgets.QPushButton("...")
        self.results_text = QtWidgets.QLabel("Choose result folder:")
        self.results_text.setAlignment(QtCore.Qt.AlignCenter)
        self.results_line = QLineEdit(self)
        self.results_line.setEnabled(False)

        self.copy = False
        self.cbox1 = QCheckBox("Copy Dicom Files")

        self.matching_button = QtWidgets.QPushButton("Start Matching and Anonymizing")
        self.pre_labeling_button = QtWidgets.QPushButton("Start Pre-Labeling (Choosing relevant files per US session)")

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.report_text)
        self.hbox_report = QtWidgets.QHBoxLayout()
        self.hbox_report.addWidget(self.report_line)
        self.hbox_report.addWidget(self.report_button)
        self.vbox.addLayout(self.hbox_report)
        self.vbox.addWidget(self.cbox)
        self.vbox.addSpacing(50)
        self.vbox.addWidget(self.dicom_text)
        self.hbox_dicom = QtWidgets.QHBoxLayout()
        self.hbox_dicom.addWidget(self.dicom_line)
        self.hbox_dicom.addWidget(self.dicom_button)
        self.vbox.addLayout(self.hbox_dicom)
        self.vbox.addSpacing(50)
        self.vbox.addWidget(self.results_text)
        self.hbox_results = QtWidgets.QHBoxLayout()
        self.hbox_results.addWidget(self.results_line)
        self.hbox_results.addWidget(self.results_button)
        self.vbox.addLayout(self.hbox_results)
        self.vbox.addWidget(self.cbox1)
        self.vbox.addSpacing(50)
        self.vbox.addWidget(self.matching_button)
        self.vbox.addWidget(self.pre_labeling_button)

        self.setLayout(self.vbox)

        self.report_button.clicked.connect(self.pick_reports)
        self.dicom_button.clicked.connect(self.pick_dicoms)
        self.cbox.toggled.connect(self.onClicked)
        self.cbox1.toggled.connect(self.onClicked1)
        self.results_button.clicked.connect(self.pick_results)
        self.matching_button.clicked.connect(self.start_matching)
        self.pre_labeling_button.clicked.connect(self.start_pre_labeling)

    def start_pre_labeling(self):
        self.labeling_window = DicomWindow(self.results_path)
        self.labeling_window.setGeometry(100, 60, 1000, 800)
        # self.labeling_window.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowType_Mask)
        # self.labeling_window.showFullScreen()

        self.labeling_window.show()

        app.exec()

    def start_matching(self):
        reports_to_csv(self.report_path, self.results_path, unambiguous=self.unambiguous)
        matching(self.dicom_path, self.results_path, self.copy)

    def onClicked(self):
        if self.unambiguous:
            self.unambiguous = False
            print("Unambiguous not selected. In case a patient report contains 2 different "
                  "BIRADS calssifications both will be considered.")
        else:
            self.unambiguous = True
            print("Unambiguous selected. In case a patient report contains 2 different "
                  "BIRADS calssifications the report is omitted.")

    def onClicked1(self):
        if self.copy:
            self.copy = False
            print("Files will not be anonymized and copied.")
        else:
            self.copy = True
            print("Files will be anonymized and copied.")

    def pick_reports(self):
        dialog = QFileDialog()
        folder_path = dialog.getOpenFileName(self)
        self.report_line.setText(str(folder_path[0]))
        self.report_path = folder_path[0]
        print(self.report_path)

    def pick_dicoms(self):
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory(None)
        self.dicom_line.setText(str(folder_path))
        self.dicom_path = folder_path
        print(self.dicom_path)

    def pick_results(self):
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory(None)
        self.results_line.setText(str(folder_path))
        self.results_path = folder_path
        print(self.results_path)


if __name__ == '__main__':
    # show_dicom_file()

    os.chdir('C:\Master Thesis\MT data\datasetUS')

    app = QApplication(sys.argv)

    # Force the style to be the same on all OSs:
    app.setStyle("Fusion")

    # Now use a palette to switch to dark colors:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = MyWidget()
    window.show()

    app.exec()
