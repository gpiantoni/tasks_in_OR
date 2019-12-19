#!/usr/bin/env python3

from PyQt5.QtMultimedia import QAudioRecorder, QAudioEncoderSettings, QMultimedia
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtMultimedia import QSound
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QKeyEvent, QPainter, QMouseEvent
from PyQt5.QtCore import Qt
import logging

from argparse import ArgumentParser
from pprint import pformat
from json import load
from numpy import where, genfromtxt, zeros, dtype
from pathlib import Path
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

micname = logname.with_suffix('.wav')


class PrettyWidget(QtWidgets.QLabel):
    started = False
    finished = False
    timer = None
    current_index = None
    sound = {'start': None, 'end': None}

    def __init__(self, parameters):
        super().__init__()
        self.P = parameters

        if self.P['SOUND']['PLAY']:
            self.sound = {
                'start': QSound(str(SOUNDS_DIR / self.P['SOUND']['START'])),
                'end': QSound(str(SOUNDS_DIR / self.P['SOUND']['END'])),
                }

        lg.info('Reading images')
        self.stimuli = _convert_stimuli(self.P)
        lg.info('Reading images: finished')

        mic_settings = QAudioEncoderSettings()
        mic_settings.setCodec(self.P['MICROPHONE']['CODEC'])
        mic_settings.setQuality(QMultimedia.VeryHighQuality)

        self.mic = QAudioRecorder()
        self.mic.setEncodingSettings(mic_settings)
        self.mic.setOutputLocation(QUrl.fromLocalFile(str(micname)))

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

    def paintEvent(self, event):

        qp = QPainter()
        qp.begin(self)

        if self.current_index is None:
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
                        if self.sound['end'] is not None:
                            self.sound['end'].play()
                            lg.info('Playing END sound')

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

        color = QtGui.QColor(self.cross_color)
        qp.setPen(color)
        qp.setFont(QtGui.QFont('Decorative', 80))
        qp.drawText(event.rect(), Qt.AlignCenter, '+')

    def draw_text(self, event, qp, text):

        qp.setPen(QtGui.QColor(40, 40, 255))
        qp.setFont(QtGui.QFont('Decorative', 50))
        qp.drawText(event.rect(), Qt.AlignCenter, text)

    def check_time(self):

        elapsed = self.time.elapsed()

        index_image = where(self.stimuli['onset'] <= elapsed)[0]
        if len(index_image) == len(self.stimuli):
            self.stop()

        elif len(index_image) > 0:
            index_image = index_image[-1]

            if index_image != self.current_index:
                self.current_index = index_image

                if index_image is not None:
                    i_trigger = self.stimuli['trigger'][index_image]
                    lg.info(f'Presenting stim_file  {i_trigger:03d}')

            self.update()

    def start(self):
        self.started = True
        self.current_index = -1
        self.time.start()
        self.timer.start(self.P['QTIMER_INTERVAL'])
        lg.info('Start Recording Microphone')
        self.mic.record()
        if self.sound['start'] is not None:
            lg.info('Playing START sound')
            self.sound['start'].play()

    def stop(self):
        lg.info('Stopping task')
        lg.info('Stop Recording Microphone')
        self.mic.stop()

        if self.timer is not None:
            self.timer.stop()

        self.close()

    def keyPressEvent(self, event):
        if isinstance(event, QKeyEvent):
            if (not self.started
                and (
                    event.key() == Qt.Key_Enter
                    or event.key() == Qt.Key_Return)):

                self.start()

            elif event.key() == Qt.Key_Escape:
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
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        else:
            super().mouseDoubleClickEvent(event)


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
