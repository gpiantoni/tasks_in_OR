#!/usr/bin/env python3

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QKeyEvent, QPainter
from PyQt5.QtCore import Qt
import sys
from struct import pack

from numpy import arange, r_, c_, array, ones, where, genfromtxt, zeros, dtype
from pathlib import Path
from serial import Serial

IMAGES_DIR = Path('images/prf').resolve()
STIMULI_TSV = '/home/giovanni/tools/tasks/images/template_task-prf.tsv'

COM_PORT = 'COM9'
BAUDRATE = 9600

class PrettyWidget(QtWidgets.QLabel):
    started = False
    timer = None
    serial = None
    current_index = 0
    current_pixmap = None

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        print('reading images')
        self.stimuli = _convert_stimuli()
        print('finished reading')

        # background color
        im = self.stimuli['pixmap'][0].toImage()
        self.bg_color = QtGui.QColor(im.pixel(0, 0))
        self.setStyleSheet(f"background-color: {self.bg_color.name()};")
        self.show()

        self.time = QtCore.QTime()
        # self.showFullScreen()
        self.setCursor(Qt.BlankCursor)
        self.setGeometry(300, 300, 1000, 1000)
        try:
            self.serial = Serial(COM_PORT, baudrate=BAUDRATE)
        except:
            print('could not open serial port')
        else:
            self.serial.write(pack('>B', 250))

    def paintEvent(self, event):

        qp = QPainter()
        qp.begin(self)

        rect_x = event.rect().center().x()
        rect_y = event.rect().center().y()
        if self.current_pixmap is not None:
            img_w = self.current_pixmap.rect().width()
            img_h = self.current_pixmap.rect().height()
            img_origin_x = rect_x - int(img_w / 2)
            img_origin_y = rect_y - int(img_h / 2)
            qp.drawPixmap(img_origin_x, img_origin_y, self.current_pixmap)

        self.drawText(event, qp)
        qp.end()

    def drawText(self, event, qp):

        qp.setPen(QtGui.QColor(168, 34, 3))
        qp.setFont(QtGui.QFont('Decorative', 30))
        qp.drawText(event.rect(), Qt.AlignCenter, '+')

    def check_time(self):

        index_image = where(self.stimuli['onset'] >= self.time.elapsed())[0][0]

        if index_image != self.current_index:
            self.current_index = index_image
            self.current_pixmap = self.stimuli['pixmap'][index_image]
            self.update()

            if self.serial is not None:
                self.serial.write(pack('>B', self.stimuli['trigger'][index_image]))

        if self.time.elapsed() > self.stimuli['onset'][-1]:
            self.stop()

    def start(self):
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.check_time)
        self.timer.start(5)

        self.time.start()

    def stop(self):
        if self.serial is not None:
            self.serial.write(pack('>B', 251))
            self.serial.close()
        if self.timer is not None:
            self.timer.stop()
        self.hide()

    def keyPressEvent(self, event):
        if type(event) == QKeyEvent:
            if not self.started and (
                event.key() == Qt.Key_Enter or
                event.key() == Qt.Key_Return):

                self.started = True
                self.start()

            elif event.key() == Qt.Key_Space:
                pass

            elif event.key() == Qt.Key_Escape:
                self.stop()


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
