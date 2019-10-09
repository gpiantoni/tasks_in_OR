#!/usr/bin/env python3

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QKeyEvent, QPainter
from PyQt5.QtCore import Qt
import sys
from struct import pack, unpack
import logging

from numpy import where, genfromtxt, zeros, dtype
from pathlib import Path
from serial import Serial
from serial import SerialException

IMAGES_DIR = Path('images/prf').resolve()
STIMULI_TSV = str(Path('images/template_task-prf.tsv').resolve())

COM_PORT_TRIGGER = 'COM9'
COM_PORT_INPUT = 'COM8'
BAUDRATE = 9600
QTIMER_INTERVAL = 1

logname = Path('log.txt').resolve()  # use time in logfile name

logging.basicConfig(
    filename=logname,
    filemode='w',
    format='%(asctime)s.%(msecs)d\t%(name)s\t%(levelname)s\t%(message)s',
    datefmt='%H:%M:%S',
    level=logging.DEBUG)
logging.info("Log File")

lg = logging.getLogger('task')
lg.addHandler(logging.StreamHandler())

try:
    port_trigger = Serial(COM_PORT_TRIGGER, baudrate=BAUDRATE)
except SerialException:
    port_trigger = None
    lg.warning('could not open serial port for triggers')

try:
    port_input = Serial(COM_PORT_INPUT, baudrate=BAUDRATE)
except SerialException:
    port_input = None
    lg.warning('could not open serial port to read input')


class PrettyWidget(QtWidgets.QLabel):
    started = False
    timer = None
    current_index = 0
    current_pixmap = None
    paused = False
    delay = 0  # used when pausing

    def __init__(self):
        super().__init__()

        lg.info('Reading images')
        self.stimuli = _convert_stimuli()
        lg.info('Reading images: finished')

        # background color
        im = self.stimuli['pixmap'][0].toImage()
        self.bg_color = QtGui.QColor(im.pixel(0, 0))
        self.setStyleSheet(f"background-color: {self.bg_color.name()};")
        self.show()

        self.time = QtCore.QTime()
        # self.showFullScreen()
        self.setCursor(Qt.BlankCursor)
        self.setGeometry(300, 300, 1000, 1000)
        self.serial(250)

    def serial(self, trigger):
        """trigger needs to be between 0 and 255. If none, then it closes the
        serial port"""
        if trigger is None:
            if port_trigger is not None:
                port_trigger.close()
        else:
            lg.info(f'Sending trigger {trigger:03d}')
            if port_trigger is not None:
                port_trigger.write(pack('>B', trigger))

    def paintEvent(self, event):

        qp = QPainter()
        qp.begin(self)

        if self.paused:
            self.draw_pause(event, qp)

        else:
            window_rect = event.rect()
            rect_x = window_rect.center().x()
            rect_y = window_rect.center().y()
            if self.current_pixmap is not None:
                image_rect = self.current_pixmap.rect()

                size = image_rect.size().scaled(window_rect.size(), Qt.KeepAspectRatio)
                img_origin_x = rect_x - int(size.width() / 2)
                img_origin_y = rect_y - int(size.height() / 2)
                qp.drawPixmap(
                    img_origin_x,
                    img_origin_y,
                    window_rect.width(),
                    window_rect.height(),
                    self.current_pixmap)

            self.drawText(event, qp)

        qp.end()

    def drawText(self, event, qp):

        qp.setPen(QtGui.QColor(168, 34, 3))
        qp.setFont(QtGui.QFont('Decorative', 30))
        qp.drawText(event.rect(), Qt.AlignCenter, '+')

    def draw_pause(self, event, qp):

        qp.setPen(QtGui.QColor(168, 34, 3))
        qp.setFont(QtGui.QFont('Decorative', 60))
        qp.drawText(event.rect(), Qt.AlignCenter, 'PAUSED')

    def check_time(self):

        elapsed = self.time.elapsed() + self.delay

        index_image = where(self.stimuli['onset'] >= elapsed)[0]
        if len(index_image) == 0:
            self.stop()
        else:
            index_image = index_image[0]

            if index_image != self.current_index:
                self.current_index = index_image
                self.current_pixmap = self.stimuli['pixmap'][index_image]
                self.update()

                i_trigger = self.stimuli['trigger'][index_image]
                self.serial(i_trigger)

    def start(self):
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.check_time)
        self.timer.start(QTIMER_INTERVAL)
        self.start_serial_input()

        self.time.start()

    def start_serial_input(self):
        self.input_worker = SerialInputWorker()
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

        self.serial(251)
        self.serial(None)

        if self.timer is not None:
            self.timer.stop()

        QApplication.quit()

    def pause(self):
        if not self.paused:
            self.paused = True
            self.delay += self.time.elapsed()
            self.timer.stop()
            self.serial(253)
            lg.info('Pausing the task')
            self.update()

        else:
            self.paused = False
            self.time.restart()
            self.serial(254)
            lg.info('Pause finished: restarting the task')
            self.timer.start(QTIMER_INTERVAL)

    def keyPressEvent(self, event):
        if type(event) == QKeyEvent:
            if (not self.started
                and (
                    event.key() == Qt.Key_Enter
                    or event.key() == Qt.Key_Return)):

                self.started = True
                self.start()

            elif event.key() == Qt.Key_Space:
                self.pause()

            elif event.key() == Qt.Key_Escape:
                self.stop()


class SerialInputWorker(QtCore.QObject):
    signal_to_main = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()

    @QtCore.pyqtSlot()
    def start_reading(self):
        while True:
            if port_input is not None:
                serial_input = port_input.read()
                if serial_input != b'':
                    self.signal_to_main.emit(unpack('>B', serial_input))

def _convert_stimuli():

    tsv = genfromtxt(
        fname=STIMULI_TSV,
        delimiter='\t',
        names=True,
        dtype=None,  # forces it to read strings
        deletechars='',
        encoding='utf-8')
    n_stims = tsv.shape[0] * 2  # onsets and offsets

    stimuli = zeros(n_stims, dtype([
        ('onset', '<f8'),
        ('pixmap', 'O'),
        ('trigger', 'uint8'),
        ]))
    stimuli['onset'][::2] = tsv['onset']
    stimuli['onset'][1::2] = tsv['onset'] + tsv['duration']
    stimuli['onset'] *= 1000  # s -> ms
    stimuli['trigger'][::2] = tsv['trial_type']
    stimuli['pixmap'][::2] = [QtGui.QPixmap(str(IMAGES_DIR / png)) for png in tsv['stim_file']]
    stimuli['pixmap'][1::2] = stimuli['pixmap'][-2]

    return stimuli


if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = PrettyWidget()

    sys.exit(app.exec_())
