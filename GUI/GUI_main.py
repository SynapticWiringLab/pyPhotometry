# Code which runs on host computer and implements the graphical user interface.
# Copyright (c) Thomas Akam 2018-2020.  Licenced under the GNU General Public License v3.

import os
import sys
import traceback
from pyqtgraph.Qt import QtGui, QtCore
from serial import SerialException
from serial.tools import list_ports

import GUI.config as config
from GUI.acquisition_board import Acquisition_board
from GUI.pyboard import PyboardError
from GUI.plotting import Analog_plot, Digital_plot, Event_triggered_plot, Record_clock

# Utility functions ---------------------------------------------------------------

def set_cbox_item(cbox, item_name):
    '''Set the selected item on a combobox by passing the item name.  If name is not
    valid then selected item is not changed.'''
    index = cbox.findText(item_name, QtCore.Qt.MatchFixedString)
    if index >= 0:
        cbox.setCurrentIndex(index)

# Photometry_GUI ------------------------------------------------------------------

class Photometry_GUI(QtGui.QWidget):

    def __init__(self, parent=None):
        super(QtGui.QWidget, self).__init__(parent)
        self.setWindowTitle('pyPhotometry GUI v{}'.format(config.VERSION))
        self.setGeometry(100, 100, 900, 800) # Left, top, width, height.

        # Variables

        self.board = None
        #self.data_dir = os.path.join(
        #    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.data_dir = 'D:\pupil'
        self.subject_ID = ''
        self.running = False
        self.connected = False
        self.refresh_interval = 1000 # Interval to refresh tasks and ports when not running (ms).
        self.available_ports = None
        self.clipboard = QtGui.QApplication.clipboard() # Used to copy strings to computer clipboard.

        # GUI status groupbox.

        self.status_groupbox = QtGui.QGroupBox('GUI status')

        self.status_text = QtGui.QLineEdit('Not connected')
        self.status_text.setStyleSheet('background-color:rgb(210, 210, 210);')
        self.status_text.setReadOnly(True)
        self.status_text.setFixedWidth(105)

        self.guigroup_layout = QtGui.QHBoxLayout()
        self.guigroup_layout.addWidget(self.status_text)
        self.status_groupbox.setLayout(self.guigroup_layout)  

        # Board groupbox

        self.board_groupbox = QtGui.QGroupBox('Board')

        self.port_label = QtGui.QLabel("Serial port:")
        self.port_select = QtGui.QComboBox()
        self.connect_button = QtGui.QPushButton('Connect')
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.connect_button.setFixedWidth(110)

        self.boardgroup_layout = QtGui.QHBoxLayout()
        self.boardgroup_layout.addWidget(self.port_label)
        self.boardgroup_layout.addWidget(self.port_select)
        self.boardgroup_layout.addWidget(self.connect_button)
        self.board_groupbox.setLayout(self.boardgroup_layout)

        self.connect_button.clicked.connect(
            lambda: self.disconnect() if self.connected else self.connect())

        # Settings groupbox

        self.settings_groupbox = QtGui.QGroupBox('Acquisition settings')        

        self.mode_label = QtGui.QLabel("Mode:")
        self.mode_select = QtGui.QComboBox()
        self.mode_select.addItems(['2 colour continuous', '1 colour time div.', '2 colour time div.', '1site-3colors', '1site-4colors', '2sites-3colors', '2sites-4colors'])
        set_cbox_item(self.mode_select, config.default_acquisition_mode)
        self.rate_label = QtGui.QLabel('Sampling rate (Hz):')
        self.rate_text = QtGui.QLineEdit()
        self.rate_text.setFixedWidth(40)

        self.settingsgroup_layout = QtGui.QHBoxLayout()
        self.settingsgroup_layout.addWidget(self.mode_label)
        self.settingsgroup_layout.addWidget(self.mode_select)
        self.settingsgroup_layout.addWidget(self.rate_label)
        self.settingsgroup_layout.addWidget(self.rate_text)
        self.settings_groupbox.setLayout(self.settingsgroup_layout)

        self.mode_select.activated[str].connect(self.select_mode)
        self.rate_text.textChanged.connect(self.rate_text_change)

        # Current groupbox

        self.current_groupbox = QtGui.QGroupBox('LED current (mA)')

        self.current_label_1 = QtGui.QLabel('CH1:')
        self.current_spinbox_1 = QtGui.QSpinBox()
        self.current_spinbox_1.setFixedWidth(50)

        self.current_label_2 = QtGui.QLabel('CH2:')
        self.current_spinbox_2 = QtGui.QSpinBox()  
        self.current_spinbox_2.setFixedWidth(50)

        self.currentgroup_layout = QtGui.QHBoxLayout()
        self.currentgroup_layout.addWidget(self.current_label_1)
        self.currentgroup_layout.addWidget(self.current_spinbox_1)
        self.currentgroup_layout.addWidget(self.current_label_2)
        self.currentgroup_layout.addWidget(self.current_spinbox_2)
        self.current_groupbox.setLayout(self.currentgroup_layout)

        self.current_spinbox_1.setRange(0,100)
        self.current_spinbox_2.setRange(0,100)
        self.current_spinbox_1.setValue(config.default_LED_current[0])
        self.current_spinbox_2.setValue(config.default_LED_current[1])

        # File groupbox

        self.file_groupbox = QtGui.QGroupBox('Data file')

        self.data_dir_label = QtGui.QLabel("Data dir:")
        self.data_dir_text = QtGui.QLineEdit(self.data_dir)
        self.data_dir_button = QtGui.QPushButton('')
        self.data_dir_button.setIcon(QtGui.QIcon("GUI/icons/folder.svg"))
        self.data_dir_button.setFixedWidth(30)
        self.subject_label = QtGui.QLabel("Subject ID:")
        self.subject_text = QtGui.QLineEdit(self.subject_ID)
        self.subject_text.setFixedWidth(80)
        self.subject_text.setMaxLength(12)
        self.filetype_label = QtGui.QLabel("File type:")
        self.filetype_select = QtGui.QComboBox()
        self.filetype_select.addItems(['ppd','csv'])
        set_cbox_item(self.filetype_select, config.default_filetype)

        self.filegroup_layout = QtGui.QHBoxLayout()
        self.filegroup_layout.addWidget(self.data_dir_label)
        self.filegroup_layout.addWidget(self.data_dir_text)
        self.filegroup_layout.addWidget(self.data_dir_button)
        self.filegroup_layout.addWidget(self.subject_label)
        self.filegroup_layout.addWidget(self.subject_text)
        self.filegroup_layout.addWidget(self.filetype_label)
        self.filegroup_layout.addWidget(self.filetype_select)
        self.file_groupbox.setLayout(self.filegroup_layout)

        self.data_dir_text.textChanged.connect(self.test_data_path)
        self.data_dir_button.clicked.connect(self.select_data_dir)
        self.subject_text.textChanged.connect(self.test_data_path)

        # Acquisition groupbox

        self.acquisition_groupbox = QtGui.QGroupBox('Acquisition')

        self.start_button = QtGui.QPushButton('Start')
        self.start_button.setIcon(QtGui.QIcon("GUI/icons/play.svg"))
        self.record_button = QtGui.QPushButton('Record')
        self.record_button.setIcon(QtGui.QIcon("GUI/icons/record.svg"))
        self.stop_button = QtGui.QPushButton('Stop')
        self.stop_button.setIcon(QtGui.QIcon("GUI/icons/stop.svg"))

        self.acquisitiongroup_layout = QtGui.QHBoxLayout()
        self.acquisitiongroup_layout.addWidget(self.start_button)
        self.acquisitiongroup_layout.addWidget(self.record_button)
        self.acquisitiongroup_layout.addWidget(self.stop_button)
        self.acquisition_groupbox.setLayout(self.acquisitiongroup_layout)

        self.start_button.clicked.connect(self.start)
        self.record_button.clicked.connect(self.record)
        self.stop_button.clicked.connect(self.stop)

        # Plots

        self.analog_plot  = Analog_plot(self)
        self.digital_plot = Digital_plot()
        self.event_triggered_plot = Event_triggered_plot()

        self.record_clock = Record_clock(self.analog_plot.axis)

        # Main layout

        self.vertical_layout     = QtGui.QVBoxLayout()
        self.horizontal_layout_1 = QtGui.QHBoxLayout()
        self.horizontal_layout_2 = QtGui.QHBoxLayout()
        self.plot_splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        self.horizontal_layout_1.addWidget(self.status_groupbox)
        self.horizontal_layout_1.addWidget(self.board_groupbox)
        self.horizontal_layout_1.addWidget(self.settings_groupbox)
        self.horizontal_layout_1.addWidget(self.current_groupbox)
        self.horizontal_layout_2.addWidget(self.file_groupbox)
        self.horizontal_layout_2.addWidget(self.acquisition_groupbox)
        self.plot_splitter.addWidget(self.analog_plot)
        self.plot_splitter.addWidget(self.digital_plot.axis)
        self.plot_splitter.addWidget(self.event_triggered_plot.axis)
        self.plot_splitter.setSizes([300,120,200])

        self.vertical_layout.addLayout(self.horizontal_layout_1)
        self.vertical_layout.addLayout(self.horizontal_layout_2)
        self.vertical_layout.addWidget(self.plot_splitter)

        self.setLayout(self.vertical_layout)

        # Setup Timers.

        self.update_timer = QtCore.QTimer() # Timer to regularly call process_data()
        self.update_timer.timeout.connect(self.process_data)
        self.refresh_timer = QtCore.QTimer() # Timer to regularly call refresh() when not running.
        self.refresh_timer.timeout.connect(self.refresh)

        # Initial setup.

        self.disconnect() # Set initial state as disconnected.
        self.refresh()    # Refresh ports list.
        self.refresh_timer.start(self.refresh_interval) 

    # Button and box functions -------------------------------------------

    def connect(self):
        try:
            self.board = Acquisition_board(self.port_select.currentText())
            self.select_mode(self.mode_select.currentText())
            self.port_select.setEnabled(False)
            self.settings_groupbox.setEnabled(True)
            self.current_groupbox.setEnabled(True)
            self.file_groupbox.setEnabled(True)
            self.acquisition_groupbox.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.connect_button.setText('Disconnect')
            self.connect_button.setIcon(QtGui.QIcon("GUI/icons/disconnect.svg"))
            self.status_text.setText('Connected')
            self.board.set_LED_current(self.current_spinbox_1.value(),self.current_spinbox_2.value())
            self.current_spinbox_1.valueChanged.connect(
                lambda v:self.board.set_LED_current(LED_1_current=int(v)))
            self.current_spinbox_2.valueChanged.connect(
                lambda v:self.board.set_LED_current(LED_2_current=int(v)))
            self.connected = True
        except SerialException:
            self.status_text.setText('Connection failed')
        except PyboardError:
            self.status_text.setText('Connection failed')
            try:
                self.board.close()
            except AttributeError:
                pass

    def disconnect(self):
        # Disconnect from pyboard.
        if self.board: self.board.close()
        self.board = None
        self.settings_groupbox.setEnabled(False)
        self.current_groupbox.setEnabled(False)
        self.file_groupbox.setEnabled(False)
        self.acquisition_groupbox.setEnabled(False)
        self.port_select.setEnabled(True)
        self.connect_button.setText('Connect')
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.status_text.setText('Not connected')
        self.connected = False

    def test_data_path(self):
        # Checks whether data dir and subject ID are valid.
        self.data_dir = self.data_dir_text.text()
        self.subject_ID = self.subject_text.text()
        if (self.running and os.path.isdir(self.data_dir) and str(self.subject_ID)):
                self.record_button.setEnabled(True)

    def select_mode(self, mode):
        self.board.set_mode(mode)
        self.rate_text.setText(str(self.board.sampling_rate))
        self.analog_plot.create_axis(mode)
        self.mode = mode
        if self.mode != '2 colour continuous':
            self.analog_plot.amblightcor_checkbox.setEnabled(True)
            self.analog_plot.amblightcor_checkbox.stateChanged.connect(lambda:
                self.board.set_ambientlightcorrection(
                self.analog_plot.amblightcor_checkbox.isChecked()))
            self.analog_plot.amblightcor_checkbox.setChecked(True)
        else:
            self.analog_plot.amblightcor_checkbox.setChecked(False)
            self.analog_plot.amblightcor_checkbox.setEnabled(False)

    def rate_text_change(self, text):
        if text:
            try:
                sampling_rate = int(text)
            except ValueError:
                self.rate_text.setText(str(self.board.sampling_rate))
                return
            set_rate = self.board.set_sampling_rate(sampling_rate)
            self.rate_text.setText(str(set_rate))

    def select_data_dir(self):
        self.data_dir_text.setText(
            QtGui.QFileDialog.getExistingDirectory(self, 'Select data folder', self.data_dir))

    def start(self):
        # Reset plots.
        self.analog_plot.reset(self.board.sampling_rate)
        self.digital_plot.reset(self.board.sampling_rate)
        self.event_triggered_plot.reset(self.board.sampling_rate)
        # Start acquisition.
        self.board.start()
        self.refresh_timer.stop()
        self.update_timer.start(config.update_interval)
        self.running = True
        # Update UI.
        self.board_groupbox.setEnabled(False)
        self.settings_groupbox.setEnabled(False)
        self.start_button.setEnabled(False)
        self.analog_plot.amblightcor_checkbox.setEnabled(False)
        if self.test_data_path():
            self.record_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_text.setText('Running')

    def record(self):
        if os.path.isdir(self.data_dir):
            filetype = self.filetype_select.currentText()
            file_name = self.board.record(self.data_dir, self.subject_ID, filetype)
            self.clipboard.setText(file_name)
            self.status_text.setText('Recording')
            self.current_groupbox.setEnabled(False)
            self.file_groupbox.setEnabled(False)
            self.record_button.setEnabled(False)
            self.subject_text.setEnabled(False)
            self.data_dir_text.setEnabled(False)
            self.data_dir_button.setEnabled(False)
            self.record_clock.start()
        else:
            self.data_dir_text.setText('Set valid directory')
            self.data_dir_label.setStyleSheet("color: rgb(255, 0, 0);")

    def stop(self):
        self.board.stop()
        self.update_timer.stop()
        self.refresh_timer.start(self.refresh_interval)
        self.running = False
        self.stop_button.setEnabled(False)
        self.board.serial.reset_input_buffer()
        self.board_groupbox.setEnabled(True)
        self.settings_groupbox.setEnabled(True)
        self.current_groupbox.setEnabled(True)
        self.file_groupbox.setEnabled(True)
        self.start_button.setEnabled(True)
        self.record_button.setEnabled(False)
        self.subject_text.setEnabled(True)
        self.data_dir_text.setEnabled(True)
        self.data_dir_button.setEnabled(True)
        self.analog_plot.amblightcor_checkbox.setEnabled(True)
        self.status_text.setText('Connected')
        self.record_clock.stop()

    def serial_connection_lost(self):
        if self.running:
            self.update_timer.stop()
            self.refresh_timer.start(self.refresh_interval)
            self.running = False
            self.board_groupbox.setEnabled(True)
            self.start_button.setEnabled(True)
            self.board.stop_recording()
            self.record_clock.stop()
        self.disconnect()
        QtGui.QMessageBox.question(self, 'Error', 'Serial connection lost.', QtGui.QMessageBox.Ok)

    # Timer callbacks.

    def process_data(self):
        # Called regularly while running, read data from the serial port
        # and update the plot.
        data = self.board.process_data()
        if data:
            if self.mode in ('1site-4colors', '2sites-4colors'):
                new_ADC1_green_ca, new_ADC1_green_iso, new_ADC2_red_ca, new_ADC2_red_iso, new_DI1, new_DI2 = data
                self.analog_plot.update(new_ADC1_green_ca, new_ADC1_green_iso, new_ADC2_red_ca, new_ADC2_red_iso)
                self.digital_plot.update(new_DI1, new_DI2)
                self.event_triggered_plot.update(new_DI1, self.digital_plot, self.analog_plot, self.mode)
            elif self.mode in ('1site-3colors', '2sites-3colors'):
                new_ADC1_green_ca, new_ADC1_green_iso, new_ADC2_red_ca, new_DI1, new_DI2 = data
                self.analog_plot.update(new_ADC1_green_ca, new_ADC1_green_iso, new_ADC2_red_ca, None)
                self.digital_plot.update(new_DI1, new_DI2)
                self.event_triggered_plot.update(new_DI1, self.digital_plot, self.analog_plot, self.mode)
            else:
                new_ADC1, new_ADC2, new_DI1, new_DI2 = data
                self.analog_plot.update(new_ADC1, new_ADC2, None, None)
                self.digital_plot.update(new_DI1, new_DI2)
                self.event_triggered_plot.update(new_DI1, self.digital_plot, self.analog_plot, self.mode)
            self.record_clock.update()

    def refresh(self):
        # Called regularly while not running, scan serial ports for 
        # connected boards and update ports list if changed.
        ports = set([c[0] for c in list_ports.comports()])
        if not ports == self.available_ports:
            self.port_select.clear()
            self.port_select.addItems(sorted(ports))
            self.available_ports = ports

    # Cleanup.

    def closeEvent(self, event):
        # Called when GUI window is closed.
        if self.running: self.stop()
        if self.board: self.board.close()
        event.accept()

    # Exception handling.

    def excepthook(self, ex_type, ex_value, ex_traceback):
        '''Called when an uncaught exception occurs, shows error message and traceback in dialog.'''
        ex_str = '\n'.join(traceback.format_exception(ex_type, ex_value, ex_traceback, chain=False))
        if ex_type == SerialException:
            self.serial_connection_lost()
        elif ex_type == ValueError and 'ViewBoxMenu' in ex_str:
            pass # Bug in pyqtgraph when invalid string entered as axis range limit.
        else:
            message = 'A error occured.  If you are recording and acquisition has not frozen the '     \
                      'error is probably not fatal. Otherwise it is recommended to restart the GUI. '  \
                      'The error traceback has been copied to the clipboard.\n\n'    
            self.clipboard.setText(ex_str)
            QtGui.QMessageBox.question(self, 'Error', message + ex_str, QtGui.QMessageBox.Ok)

# --------------------------------------------------------------------------------
# Launch GUI.
# --------------------------------------------------------------------------------

def launch_GUI():
    '''Launch the pyPhotometry GUI.'''
    app = QtGui.QApplication([])  # Start QT
    photometry_GUI = Photometry_GUI()
    photometry_GUI.show()
    sys.excepthook = photometry_GUI.excepthook
    app.exec_()