# Code which runs on host computer and implements the GUI plot panels.
# Copyright (c) Thomas Akam 2018-2020.  Licenced under the GNU General Public License v3.

import numpy as np
import pyqtgraph as pg
from datetime import datetime
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets

from GUI.config import history_dur, triggered_dur

# Analog_plot ------------------------------------------------------

class Analog_plot(QtGui.QWidget):

    def __init__(self, parent=None):
        super(QtGui.QWidget, self).__init__(parent)

        self.axis = pg.PlotWidget(title="Analog signal", labels={'left': 'Volts'})

        # Create controls
        self.demean_checkbox = QtWidgets.QCheckBox('De-mean plotted signals')
        self.demean_checkbox.stateChanged.connect(self.enable_disable_demean_mode)
        self.offset_label = QtGui.QLabel('Offset channels (mV):')
        self.offset_spinbox = QtGui.QSpinBox()
        self.offset_spinbox.setSingleStep(10)
        self.offset_spinbox.setMaximum(500)
        self.offset_spinbox.setFixedWidth(50)
        self.enable_disable_demean_mode()
        self.controls_layout = QtGui.QHBoxLayout()
        self.controls_layout.addWidget(self.demean_checkbox)
        self.controls_layout.addWidget(self.offset_label)
        self.controls_layout.addWidget(self.offset_spinbox)
        self.controls_layout.addStretch()
        self.amblightcor_checkbox = QtWidgets.QCheckBox('Ambient light correction')
        self.controls_layout.addWidget(self.amblightcor_checkbox)
        self.amblightcor_checkbox.setEnabled(False)

        # Main layout
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.addLayout(self.controls_layout)
        self.vertical_layout.addWidget(self.axis)
        self.setLayout(self.vertical_layout)

    def create_axis(self, mode):
        self.axis.clear()
        self.legend = self.axis.addLegend(offset=(10, 10))
        self.axis.setYRange(0, 3.3, padding=0)
        self.axis.setXRange(-history_dur, history_dur*0.02, padding=0)
        self.mode = mode
        if self.mode == '2 colour continuous':
            self.plot_1 = self.axis.plot(pen=pg.mkPen(color=(102,204,000)),
                                         name='analog 1 (green calcium, 470nm excitation)')
            self.plot_2 = self.axis.plot(pen=pg.mkPen(color=(204,000,000)),
                                         name='analog 2 (red calcium, 550nm excitation)')
        elif self.mode == '1 colour time div.':
            self.plot_1 = self.axis.plot(pen=pg.mkPen(color=(102,204,000)),
                                         name='analog 1 (green calcium, 470nm excitation)')
            self.plot_2 = self.axis.plot(pen=pg.mkPen(color=(204,255,153)),
                                         name='analog 2 (green isosbestic, 405nm excitation)')
        elif self.mode == '2 colour time div.':
            self.plot_1 = self.axis.plot(pen=pg.mkPen(color=(102,204,000)),
                                         name='analog 1 (green calcium, 470nm excitation)')
            self.plot_2 = self.axis.plot(pen=pg.mkPen(color=(204,000,000)),
                                         name='analog 2 (red calcium, 550nm excitation)')
        elif self.mode == '4 colour time div.':
            self.plot_1 = self.axis.plot(pen=pg.mkPen(color=(102,204,000)),
                                         name='analog 1 (green calcium, 470nm excitation)')
            self.plot_2 = self.axis.plot(pen=pg.mkPen(color=(204,255,153)),
                                         name='analog 1 (green isosbestic, 405nm excitation)')
            self.plot_3 = self.axis.plot(pen=pg.mkPen(color=(204,000,000)),
                                         name='analog 2 (red calcium, 550nm excitation)')
            self.plot_4 = self.axis.plot(pen=pg.mkPen(color=(255,153,153)),
                                         name='analog 2 (red isosbestic, 470nm excitation)')

    def reset(self, sampling_rate):
        history_length = int(sampling_rate * history_dur)
        if self.mode == '4 colour time div.':
            self.ADC1_green_ca  = Signal_history(history_length)
            self.ADC1_green_iso = Signal_history(history_length)
            self.ADC2_red_ca    = Signal_history(history_length)
            self.ADC2_red_iso   = Signal_history(history_length)
        else:
            self.ADC1 = Signal_history(history_length)
            self.ADC2 = Signal_history(history_length)
        self.x = np.linspace(-history_dur, 0, history_length) # X axis for timeseries plots.

    def update(self, input1, input2, input3, input4):
        if self.mode == '4 colour time div.':
            new_ADC1_green_ca  = input1
            new_ADC1_green_iso = input2
            new_ADC2_red_ca    = input3
            new_ADC2_red_iso   = input4
            new_ADC1_green_ca  = 3.3 * new_ADC1_green_ca / (1 << 15) # Convert to Volts.
            new_ADC1_green_iso = 3.3 * new_ADC1_green_iso / (1 << 15)
            new_ADC2_red_ca    = 3.3 * new_ADC2_red_ca / (1 << 15)
            new_ADC2_red_iso   = 3.3 * new_ADC2_red_iso / (1 << 15)
            self.ADC1_green_ca.update(new_ADC1_green_ca)
            self.ADC1_green_iso.update(new_ADC1_green_iso)
            self.ADC2_red_ca.update(new_ADC2_red_ca)
            self.ADC2_red_iso.update(new_ADC2_red_iso)
            if self.AC_mode: 
                # Plot signals with mean removed.
                y1 = self.ADC1_green_ca.history - np.mean(self.ADC1_green_ca.history) \
                    + 1.5*self.offset_spinbox.value()/1000
                y2 = self.ADC1_green_iso.history - np.mean(self.ADC1_green_iso.history) \
                    + 0.5*self.offset_spinbox.value()/1000
                y3 = self.ADC2_red_ca.history - np.mean(self.ADC2_red_ca.history) \
                    - 0.5*self.offset_spinbox.value()/1000
                y4 = self.ADC2_red_iso.history - np.mean(self.ADC2_red_iso.history) \
                    - 1.5*self.offset_spinbox.value()/1000
                self.plot_1.setData(self.x, y1)
                self.plot_2.setData(self.x, y2)
                self.plot_3.setData(self.x, y3)
                self.plot_4.setData(self.x, y4)
            else:
                self.plot_1.setData(self.x, self.ADC1_green_ca.history)
                self.plot_2.setData(self.x, self.ADC1_green_iso.history)
                self.plot_3.setData(self.x, self.ADC2_red_ca.history)
                self.plot_4.setData(self.x, self.ADC2_red_iso.history)   
        else:
            new_ADC1 = input1
            new_ADC2 = input2
            new_ADC1 = 3.3 * new_ADC1 / (1 << 15) # Convert to Volts.
            new_ADC2 = 3.3 * new_ADC2 / (1 << 15)
            self.ADC1.update(new_ADC1)
            self.ADC2.update(new_ADC2)
            if self.AC_mode: 
                # Plot signals with mean removed.
                y1 = self.ADC1.history - np.mean(self.ADC1.history) \
                     + self.offset_spinbox.value()/1000
                y2 = self.ADC2.history - np.mean(self.ADC2.history)
                self.plot_1.setData(self.x, y1)
                self.plot_2.setData(self.x, y2)
            else:
                self.plot_1.setData(self.x, self.ADC1.history)
                self.plot_2.setData(self.x, self.ADC2.history)

    def enable_disable_demean_mode(self):
        if self.demean_checkbox.isChecked():
            self.AC_mode = True
            self.offset_spinbox.setEnabled(True)
            self.offset_label.setStyleSheet('color : black')
            self.axis.enableAutoRange(axis='y')
        else:
            self.AC_mode = False
            self.offset_spinbox.setEnabled(False)
            self.offset_label.setStyleSheet('color : gray')

# Digital_plot ------------------------------------------------------

class Digital_plot():

    def __init__(self):
        self.axis = pg.PlotWidget(title="Digital signal", labels={'left': 'Level', 'bottom':'Time (seconds)'})
        self.axis.addLegend(offset=(10, 10))
        self.plot_1 = self.axis.plot(pen=pg.mkPen('b'), name='digital 1')
        self.plot_2 = self.axis.plot(pen=pg.mkPen('y'), name='digital 2')
        self.axis.setYRange(-0.1, 1.1, padding=0)
        self.axis.setXRange(-history_dur, history_dur*0.02, padding=0)

    def reset(self, sampling_rate):
        history_length = int(sampling_rate*history_dur)
        self.DI1 = Signal_history(history_length, int) 
        self.DI2 = Signal_history(history_length, int)
        self.x = np.linspace(-history_dur, 0, history_length) # X axis for timeseries plots.

    def update(self, new_DI1, new_DI2):
        self.DI1.update(new_DI1)
        self.DI2.update(new_DI2)
        self.plot_1.setData(self.x, self.DI1.history)
        self.plot_2.setData(self.x, self.DI2.history)
 
# Event triggered plot -------------------------------------------------

class Event_triggered_plot():

    def __init__(self, tau=5):
        self.axis = pg.PlotWidget(title="Event triggered", labels={'left': 'Volts', 'bottom':'Time (seconds)'})
        self.axis.addLegend(offset=(-10, 10))
        self.prev_plot = self.axis.plot(pen=pg.mkPen(pg.hsvColor(0.6, sat=0, alpha=0.3)), name='latest')
        self.ave_plot  = self.axis.plot(pen=pg.mkPen(pg.hsvColor(0.6)), name='average')
        self.axis.addItem(pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(style=QtCore.Qt.DotLine)))
        self.axis.setXRange(triggered_dur[0], triggered_dur[1], padding=0)
        self.alpha = 1 - np.exp(-1./tau) # Learning rate for update of average trace, tau is time constant.

    def reset(self, sampling_rate):
        self.window = (np.array(triggered_dur)*sampling_rate).astype(int)   # Window for event triggered signals (samples [pre, post])
        self.x = np.linspace(*triggered_dur, self.window[1]-self.window[0]) # X axis for event triggered plots.
        self.average = None
        self.prev_plot.clear()
        self.ave_plot.clear()

    def update(self, new_DI1, digital, analog, mode):
        # Update event triggered average plot.
        new_data_len = len(new_DI1)
        trig_section = digital.DI1.history[-self.window[1]-new_data_len-1:-self.window[1]]
        rising_edges = np.where(np.diff(trig_section)==1)[0]
        for i, edge in enumerate(rising_edges):
            edge_ind = -self.window[1]-new_data_len-1+edge # Position of edge in signal history.
            if mode == '4 colour time div.':
                ev_trig_sig = analog.ADC1_green_ca.history[edge_ind + self.window[0]:edge_ind + self.window[1]]
            else:
                ev_trig_sig = analog.ADC1.history[edge_ind+self.window[0]:edge_ind+self.window[1]]
            if self.average is None: # First acquisition
                self.average = ev_trig_sig
            else: # Update averaged trace.
                self.average = (1-self.alpha)*self.average + self.alpha*ev_trig_sig
            if i+1 == len(rising_edges): 
                self.prev_plot.setData(self.x, ev_trig_sig)
                self.ave_plot.setData(self.x, self.average)

# Signal_history ------------------------------------------------------------

class Signal_history():
    # Buffer to store the recent history of a signal.

    def __init__(self, history_length, dtype=float):
        self.history = np.zeros(history_length, dtype)

    def update(self, new_data):
        # Move old data along buffer, store new data samples.
        data_len = len(new_data)
        self.history = np.roll(self.history, -data_len)
        if len(new_data) > 0:
            self.history[-data_len:] = new_data

# Record_clock ----------------------------------------------------

class Record_clock():
    # Class for displaying the run time.

    def __init__(self, axis):
        self.clock_text = pg.TextItem(text='')
        self.clock_text.setFont(QtGui.QFont('arial',12, QtGui.QFont.Bold))
        axis.getViewBox().addItem(self.clock_text, ignoreBounds=True)
        self.clock_text.setParentItem(axis.getViewBox())
        self.clock_text.setPos(740,10)
        self.recording_text = pg.TextItem(text='', color=(255,255,255))
        self.recording_text.setFont(QtGui.QFont('arial',12,QtGui.QFont.Bold))
        axis.getViewBox().addItem(self.recording_text, ignoreBounds=True)
        self.recording_text.setParentItem(axis.getViewBox())
        self.recording_text.setPos(650,10)
        self.warning_text = pg.TextItem(text='!!! NOT RECORDING !!!', color=(255,000,000))
        self.warning_text.setFont(QtGui.QFont('arial',30,QtGui.QFont.Bold))
        axis.getViewBox().addItem(self.warning_text, ignoreBounds=True)
        self.warning_text.setParentItem(axis.getViewBox())
        self.warning_text.setPos(200,125)
        self.start_time = None

    def start(self):
        self.start_time = datetime.now()
        self.recording_text.setText('Recording')
        self.warning_text.setText('')

    def update(self):
        if self.start_time:
            self.clock_text.setText(str(datetime.now()-self.start_time)[:7])

    def stop(self):
        self.clock_text.setText('')
        self.recording_text.setText('')
        self.warning_text.setText('!!! NOT RECORDING !!!')
        self.start_time = None