from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QKeyEvent, QPainter
from PyQt5.QtCore import Qt
import sys
from struct import pack

from numpy import arange, r_, c_, array, ones, where
from pathlib import Path
from serial import Serial

image_dir = Path('images/prf').resolve()
onsets = arange(224) * .85
offsets = onsets + .5
onsets *= 1000
offsets *= 1000
val = ones((224 * 2, 2))
val[::2, 0] = onsets
val[::2, 1] = arange(224).astype(int)
val[1::2, 0] = offsets
val[1::2, 1] = 223

COM_PORT = 'COM6'


class PrettyWidget(QtWidgets.QLabel):
    started = False
    timer = None
    serial = None
    current_index = 0

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        print('reading images')
        images = sorted(image_dir.glob('*.png'))
        self.pixmaps = [QtGui.QPixmap(str(x)) for x in images]
        self.current_pixmap = self.pixmaps[-1]
        print('finished reading')
        im = self.pixmaps[0].toImage()
        self.bg_color = QtGui.QColor(im.pixel(0, 0))
        self.setStyleSheet(f"background-color: {self.bg_color.name()};")
        self.show()

        self.time = QtCore.QTime()
        # self.showFullScreen()
        self.setCursor(Qt.BlankCursor)
        self.setGeometry(300, 300, 1000, 1000)
        try:
            self.serial = Serial(COM_PORT, baudrate=11520)
        except:
            print('could not open serial port')
        else:
            self.serial.write(pack('>B', 250))

    def paintEvent(self, event):

        qp = QPainter()
        qp.begin(self)

        rect_x = event.rect().center().x()
        rect_y = event.rect().center().y()
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

        i_im = where(val >= self.time.elapsed())[0][0]
        index_image = int(val[i_im,1])

        if index_image != self.current_index:
            self.current_index = index_image
            self.current_pixmap = self.pixmaps[index_image]
            self.update()
            if self.serial is not None:
                self.serial.write(pack('>B', index_image))

        if self.time.elapsed() > 191000:  # TODO
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


if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = PrettyWidget()

    sys.exit(app.exec_())
