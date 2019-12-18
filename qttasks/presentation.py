#!/usr/bin/env python3

from PyQt5.QtWidgets import QApplication
from PyQt5.QtMultimedia import QSound
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QKeyEvent, QPainter, QMouseEvent
from PyQt5.QtCore import Qt
import sys
from struct import pack, unpack
import logging

from argparse import ArgumentParser
from random import random
from pprint import pformat
from json import load
from numpy import where, genfromtxt, zeros, dtype
from pathlib import Path
from serial import Serial
from serial import SerialException
from serial.tools.list_ports import comports
from datetime import datetime

app = QApplication([])

SCRIPT_DIR = Path(__file__).resolve().parent
IMAGES_DIR = SCRIPT_DIR / 'images'
SOUNDS_DIR = SCRIPT_DIR / 'sounds'
LOG_DIR = SCRIPT_DIR / 'log'
	
logname = LOG_DIR / f'log_{datetime.now():%Y%m%d_%H%M%S}.txt'

logging.basicConfig(
    filename=logname,
    filemode='w',
    format='%(asctime)s.%(msecs)03d\t%(name)s\t%(levelname)s\t%(message)s',
    datefmt='%H:%M:%S',
    level=logging.DEBUG)
logging.info("Log File")

lg = logging.getLogger('qttask')
lg.addHandler(logging.StreamHandler())


def read_mic():
    from PyQt5.QtMultimedia import QAudioRecorder, QAudioEncoderSettings, QMultimedia
    from PyQt5.QtCore import QUrl

    audioRecorder = QAudioRecorder()

    audioSettings = QAudioEncoderSettings()
    audioSettings.setCodec("audio/amr")  #  check codec
    audioSettings.setQuality(QMultimedia.HighQuality);
    audioRecorder.setEncodingSettings(audioSettings);

    audioRecorder.setOutputLocation(QUrl.fromLocalFile(r"C:\Users\gpianton\Programs\Github\tasks_in_OR\qttasks\sounds"))

    audioRecorder.record()
    # wait
    audioRecorder.stop()

class PrettyWidget(QtWidgets.QLabel):
    started = False
    finished = False
    timer = None
    port_trigger = None
    current_index = None
    paused = False
    delay = 0  # used when pausing
    cross_delay = 2
    cross_color = 'green'
    sound = {'start': None, 'end': None}

    def __init__(self, parameters):
        super().__init__()
        self.P = parameters

        if self.P['SOUND']['PLAY']:
            self.sound = {
                'start': QSound(str(SOUNDS_DIR / self.P['SOUND']['START'])),
                'end': QSound(str(SOUNDS_DIR / self.P['SOUND']['END'])),
                }
        self.open_serial()

        try:
            port_input = Serial(
                self.P['COM']['INPUT']['PORT'], 
                baudrate=self.P['COM']['INPUT']['BAUDRATE'])
        except SerialException:
            port_input = None
            lg.warning('could not open serial port to read input')
            _warn_about_ports()
        self.port_input = port_input

        lg.info('Reading images')
        self.stimuli = _convert_stimuli(self.P)
        lg.info('Reading images: finished')

        # background color
        im = self.stimuli['pixmap'][1].toImage()
        self.bg_color = QtGui.QColor(im.pixel(0, 0))
        self.setStyleSheet(f"background-color: {self.bg_color.name()};")
        self.show()

        self.time = QtCore.QTime()
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.check_time)

        self.setCursor(Qt.BlankCursor)
        self.setGeometry(200, 200, 1000, 1000)
        if self.P['FULLSCREEN']:
            self.showFullScreen()
        else:
            self.showNormal()
        self.serial(250)

    def open_serial(self):
        try:
            self.port_trigger = Serial(
                self.P['COM']['TRIGGER']['PORT'], 
                baudrate=self.P['COM']['TRIGGER']['BAUDRATE'])
        except SerialException:
            lg.warning('could not open serial port for triggers')
            _warn_about_ports()

    def serial(self, trigger):
        """trigger needs to be between 0 and 255. If none, then it closes the
        serial port"""
        if trigger is None:
            if self.port_trigger is not None:
                self.port_trigger.close()
        else:
            lg.info(f'Sending trigger {trigger:03d}')
            if self.port_trigger is not None:
                try:
                    self.port_trigger.write(pack('>B', trigger))
                except:
                    lg.warning('could not write to serial port')
                    self.open_serial()

    def paintEvent(self, event):

        qp = QPainter()
        qp.begin(self)

        if self.paused:
            self.draw_text(event, qp, 'PAUSED')

        elif self.current_index is None:
            self.draw_text(event, qp, 'READY')
			
        else:

            window_rect = event.rect()
            rect_x = window_rect.center().x()
            rect_y = window_rect.center().y()
            
            current_pixmap = self.stimuli['pixmap'][self.current_index]
            if self.current_index == -1 or isinstance(current_pixmap, str):
                self.draw_text(event, qp, current_pixmap)
                
                if current_pixmap == 'DONE':
                    if not self.finished:
                        self.finished = True
                        self.serial(None)
                        if self.sound['end'] is not None:
                            self.sound['end'].play()

            else:
                image_rect = current_pixmap.rect()

                size = image_rect.size().scaled(window_rect.size(), Qt.KeepAspectRatio)
                img_origin_x = rect_x - int(size.width() / 2)
                img_origin_y = rect_y - int(size.height() / 2)
                qp.drawPixmap(
                    img_origin_x,
                    img_origin_y,
                    size.width(),
                    size.height(),
                    current_pixmap)

        self.drawText(event, qp)

        qp.end()

    def drawText(self, event, qp):

        if not self.P['FIXATION']['ACTIVE']:
            return

        elapsed = self.time.elapsed() + self.delay
        if elapsed > self.cross_delay:
            if self.cross_color == 'green':
                self.cross_color = 'red'
                self.serial(240)
            else:
                self.cross_color = 'green'
                self.serial(241)
            self.cross_delay += random() * 5000 + 2000

        color = QtGui.QColor(self.cross_color)
        qp.setPen(color)
        qp.setFont(QtGui.QFont('Decorative', 80))
        qp.drawText(event.rect(), Qt.AlignCenter, '+')

    def draw_text(self, event, qp, text):

        qp.setPen(QtGui.QColor(40, 40, 255 ))
        qp.setFont(QtGui.QFont('Decorative', 50))
        qp.drawText(event.rect(), Qt.AlignCenter, text)

    def check_time(self):

        elapsed = self.time.elapsed() + self.delay

        index_image = where(self.stimuli['onset'] <= elapsed)[0]
        if len(index_image) == len(self.stimuli):
            self.stop()

        elif len(index_image) > 0:
            index_image = index_image[-1]

            if index_image != self.current_index:
                self.current_index = index_image

                if index_image is not None:
                    i_trigger = self.stimuli['trigger'][index_image]
                    self.serial(i_trigger)

        self.update()

    def start(self):
        self.started = True
        self.current_index = -1
        self.time.start()
        self.timer.start(self.P['QTIMER_INTERVAL'])
        # self.start_serial_input()
        # HERE: start recording from mic
        if self.sound['start'] is not None:
            self.sound['start'].play()

    def start_serial_input(self):
        self.input_worker = SerialInputWorker()
        self.input_worker.port_input = self.port_input
        self.input_thread = QtCore.QThread()
        self.input_thread.started.connect(self.input_worker.start_reading)
        self.input_worker.signal_to_main.connect(self.read_serial_input)
        self.input_worker.moveToThread(self.input_thread)
        self.input_thread.start()

    def read_serial_input(self, number):
        lg.input(f'Received input trigger {number}')
        self.serial(254)

    def stop(self):
        lg.info('Stopping task')
        # HERE: stop recording from mic

        if self.timer is not None:
            self.timer.stop()

        self.close()

    def pause(self):
        if not self.paused:
            self.paused = True
            self.delay += self.time.elapsed()
            self.timer.stop()
            self.serial(253)
            lg.info('Pausing the task')

        else:
            self.paused = False
            self.time.restart()
            self.serial(254)
            lg.info('Pause finished: restarting the task')
            self.timer.start(self.P['QTIMER_INTERVAL'])
        self.update()

    def keyPressEvent(self, event):
        if isinstance(event, QKeyEvent):
            if (not self.started
                and (
                    event.key() == Qt.Key_Enter
                    or event.key() == Qt.Key_Return)):

                self.start()

            elif event.key() == Qt.Key_Space:
                self.pause()

            elif event.key() == Qt.Key_Escape:
                self.serial(255)
                self.stop()

            elif event.key() == Qt.Key_PageUp:
                self.showFullScreen()
                
            elif event.key() == Qt.Key_PageDown:
                self.showNormal()
                
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if isinstance(event, QMouseEvent):
            if event.pos().x() > self.rect().center().x():

                if not self.started:
                    self.start()
                else:
                    self.pause()

            else:
                if self.isFullScreen():
                    self.showNormal()
                else:
                    self.showFullScreen()

        else:
            super().mouseDoubleClickEvent(event)


class SerialInputWorker(QtCore.QObject):
    signal_to_main = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()

    @QtCore.pyqtSlot()
    def start_reading(self):
        while True:
            if self.port_input is not None:
                serial_input = self.port_input.read()
                if serial_input != b'':
                    self.signal_to_main.emit(unpack('>B', serial_input))


def _convert_stimuli(P):

    STIMULI_TSV = str(IMAGES_DIR / P['TASK_TSV'])
    tsv = genfromtxt(
        fname=STIMULI_TSV,
        delimiter='\t',
        names=True,
        dtype=None,  # forces it to read strings
        deletechars='',
        encoding='utf-8')
    n_stims = tsv.shape[0] * 2 + 3  # onsets and offsets

    stimuli = zeros(n_stims, dtype([
        ('onset', '<f8'),
        ('pixmap', 'O'),
        ('trigger', 'uint8'),
        ]))
    stimuli['onset'][1:-2:2] = tsv['onset']
    stimuli['onset'][2:-2:2] = tsv['onset'] + tsv['duration']
    stimuli['onset'][-2] = stimuli['onset'][-3] + P['OUTRO']
    stimuli['onset'][-1] = stimuli['onset'][-2] + 1
    stimuli['onset'] *= 1000  # s -> ms
    
    # read images only once
    stimuli['pixmap'] = None
    stimuli['pixmap'][1:-2:2] = tsv['stim_file']
    d_images = {png: QtGui.QPixmap(str(IMAGES_DIR / png)) for png in set(tsv['stim_file'])}
    for png, pixmap in d_images.items():
        stimuli['pixmap'][stimuli['pixmap'] == png] = pixmap
    stimuli['pixmap'][::2] = P['BASELINE']
    stimuli['pixmap'][-2] = 'DONE'
    
    stimuli['trigger'][1:-2:2] = tsv['trial_type']
    stimuli['trigger'][-2] = 251
    
    return stimuli


def _warn_about_ports():
    port_names = sorted([x.device for x in comports()])
    if len(port_names) > 0:
        ports = ', '.join(port_names)
        lg.warning(f'Available ports are {ports}')
    else:
        lg.warning(f'No available ports')


def main():

    parser = ArgumentParser(prog='presentation')
    parser.add_argument(
        'parameters', 
        nargs='?',
        help='json file with the parameters')
    args = parser.parse_args()
    
    defaults_json = SCRIPT_DIR / 'default.json'
    with defaults_json.open() as f:
        PARAMETERS = load(f)
    
    parameter_json = SCRIPT_DIR / args.parameters
    parameter_json = parameter_json.with_suffix('.json')
    with parameter_json.open() as f:
        CHANGES = load(f)
        
    PARAMETERS.update(CHANGES)
 
    lg.debug(pformat(PARAMETERS))
    w = PrettyWidget(PARAMETERS)
    app.exec()


if __name__ == '__main__':

    main()
