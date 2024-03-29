#!/usr/bin/env python3

from struct import pack, unpack
import sys
import logging
from argparse import ArgumentParser
from random import random
from pprint import pformat
from json import load
from numpy import where
from datetime import datetime
from time import sleep
from pathlib import Path

try:
    from psutil import Process, HIGH_PRIORITY_CLASS  # only windows
except ImportError:
    Process = None

from PyQt5.QtCore import (
    Qt,
    QObject,
    QThread,
    QTime,
    QTimer,
    pyqtSignal,
    pyqtSlot,
    )
from PyQt5.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    )
from PyQt5.QtMultimedia import QSound
from PyQt5.QtWidgets import (
    QApplication,
    QOpenGLWidget,
    )

from serial import Serial
from serial import SerialException
from serial.tools.list_ports import comports

from .dataglove import FiveDTGlove
from .paths import LOG_DIR, SOUNDS_DIR, DEFAULTS_JSON, TASKS_DIR, update, CONFIG_DIR
from .read_tsv import read_stimuli, read_fast_stimuli

TASKS = sorted([x.stem for x in TASKS_DIR.iterdir()])
CONFIGURATIONS = sorted([x.stem for x in CONFIG_DIR.glob('*.json')])

lg = logging.getLogger('qttask')
lg.addHandler(logging.StreamHandler())


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    lg.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

app = QApplication([])


class PrettyWidget(QOpenGLWidget):
    started = False
    finished = False
    timer = None
    port_trigger = None
    current_index = None
    presenting = None
    paused = False
    delay = 0  # used when pausing
    cross_delay = 2
    cross_color = 'green'
    sound = {'start': None, 'end': None}
    fast_tsv = None
    fast_i = None
    fast_t = None

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
        self.start_serial_input()

        lg.info('Reading images')
        self.stimuli = read_stimuli(self.P)
        lg.info('Reading images: finished')

        # background color
        self.bg_color = QColor(self.P['BACKGROUND'])

        self.show()

        self.time = QTime()
        self.timer = QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.check_time)

        self.setCursor(Qt.BlankCursor)
        self.setGeometry(200, 200, 1000, 1000)
        if self.P['FULLSCREEN']:
            self.showFullScreen()
        else:
            self.showNormal()
        self.serial(250)
        if self.P['DATAGLOVE']:
            self.open_dataglove()

    def open_dataglove(self):

        lg.info('Opening dataglove')
        self.glove = []
        if FiveDTGlove.gloveDLL is None:  # could not initialize DLL
            return

        for i in range(2):  # TODO: we should use scan_USB but I get error
            logname = self.P['logname']
            DATAGLOVE_LOG = logname.parent / (logname.stem + f'_dataglove{i}.txt')
            new_glove = FiveDTGlove(DATAGLOVE_LOG)
            try:
                new_glove.open(f'USB{i}'.encode())
            except IOError:
                pass
            else:
                self.glove.append(new_glove)

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
            lg.debug(f'Sending trigger {trigger:03d}')
            if self.port_trigger is not None:
                try:
                    self.port_trigger.write(pack('>B', trigger))
                except Exception:
                    lg.warning('could not write to serial port')
                    self.open_serial()

    def paintGL(self):

        window_rect = self.rect()
        rect_x = window_rect.center().x() + self.P['SCREEN']['RIGHTWARDS']
        rect_y = window_rect.center().y() + self.P['SCREEN']['DOWNWARDS']

        qp = QPainter()
        qp.begin(self)

        qp.fillRect(window_rect, self.bg_color)

        if self.paused:
            self.draw_text(qp, 'PAUSED')

        elif self.current_index is None:
            self.draw_text(qp, 'READY')

        else:

            if self.fast_tsv is not None:
                i_pixmap = where(self.fast_tsv['onset'] <= self.fast_i)[0][-1]

                if self.fast_i == self.fast_tsv['onset'][-1]:
                    self.fast_tsv = None
                    self.fast_i = None
                    self.frameSwapped.disconnect()

                else:
                    if self.fast_tsv['stim_file'][i_pixmap] is not None:
                        current_pixmap = self.fast_tsv['stim_file'][i_pixmap]
                        image_rect = current_pixmap.rect()
                        size = image_rect.size().scaled(window_rect.size(), Qt.KeepAspectRatio)
                        img_origin_x = rect_x - int(size.width() / 2)
                        img_origin_y = rect_y - int(size.height() / 2)

                        qp.beginNativePainting()
                        qp.drawPixmap(
                            img_origin_x,
                            img_origin_y,
                            size.width(),
                            size.height(),
                            current_pixmap)
                        qp.endNativePainting()

                    lg.debug(f'FAST IMAGE #{self.fast_i}')
                    self.fast_i += 1

            else:
                current_pixmap = self.stimuli['stim_file'][self.current_index]
                if isinstance(current_pixmap, Path):
                    self.fast_tsv = read_fast_stimuli(current_pixmap)
                    self.fast_i = 0

                elif isinstance(current_pixmap, str):
                    self.draw_text(qp, current_pixmap)
                    if current_pixmap == 'END':
                        if not self.finished:
                            self.draw_text(qp, 'END')
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

                self.drawText(qp)

        qp.end()

        if self.presenting is not None:  # send triggers and log info right after the image was presented
            trial = self.stimuli[self.presenting]
            lg.info('Presenting ' + str(trial['trial_name']))
            self.serial(trial['trial_type'])
            self.presenting = None

        if self.fast_i == 0:
            self.input_thread.msleep(1000)
            self.frameSwapped.connect(self.update)
            self.update()

    def drawText(self, qp):

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

        color = QColor(self.cross_color)
        qp.setPen(color)
        qp.setFont(QFont('SansSerif', 50))
        qp.drawText(*self.center_rect(), Qt.AlignCenter, '+')

    def draw_text(self, qp, text):

        qp.setPen(QColor(40, 40, 255))
        qp.setFont(QFont('Decorative', 50))
        qp.drawText(*self.center_rect(), Qt.AlignCenter, text)

    def center_rect(self):
        window_rect = self.rect()
        width = window_rect.width()
        height = window_rect.height()
        img_origin_x = window_rect.center().x() - int(width / 2) + self.P['SCREEN']['RIGHTWARDS']
        img_origin_y = window_rect.center().y() - int(height / 2) + self.P['SCREEN']['DOWNWARDS']

        return (img_origin_x, img_origin_y, width, height)

    def check_time(self):

        elapsed = self.time.elapsed() + self.delay

        if self.P['DATAGLOVE']:
            for glove in self.glove:
                if glove.new_data:
                    glove_data = glove.get_sensor_raw_all()
                    glove.f.write(datetime.now().strftime('%H:%M:%S.%f') + '\t' + '\t'.join([f'{x}' for x in glove_data]) + '\n')

        index_image = where((self.stimuli['onset'] * 1e3) <= elapsed)[0]
        if len(index_image) == len(self.stimuli):
            self.stop()

        elif len(index_image) > 0:
            index_image = index_image[-1]

            if index_image != self.current_index:
                self.current_index = index_image

                if index_image is not None:
                    self.presenting = index_image

        self.update()

    def start(self):
        if self.started:
            return

        lg.warning('Starting')
        self.started = True
        self.current_index = -1
        self.time.start()
        self.timer.start(self.P['QTIMER_INTERVAL'])
        if self.sound['start'] is not None:
            self.sound['start'].play()

    def start_serial_input(self):
        self.input_worker = SerialInputWorker()
        self.input_worker.port_input = self.port_input
        self.input_thread = QThread(parent=self)
        self.input_thread.started.connect(self.input_worker.start_reading)
        self.input_worker.signal_to_main.connect(self.read_serial_input)
        self.input_worker.moveToThread(self.input_thread)
        self.input_thread.start()
        self.input_thread.setPriority(QThread.LowestPriority)

    def read_serial_input(self, number):
        lg.info(f'Received input trigger {number}')

        if self.P['COM']['INPUT']['START_TRIGGER'] == number:
            self.start()

        self.serial(254)

    def stop(self):
        lg.info('Stopping task')

        if self.timer is not None:
            self.timer.stop()

        # nice wayt to stop the worker
        self.input_worker.running = False
        self.input_thread.terminate()

        sleep(1)
        app.exit(0)

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
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self.start()

            elif event.key() == Qt.Key_Space:
                self.pause()

            elif event.key() == Qt.Key_Escape:
                lg.info('Pressed Escape')
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

    def closeEvent(self, event):
        self.stop()
        event.accept()


class SerialInputWorker(QObject):
    signal_to_main = pyqtSignal(int)
    running = True

    def __init__(self):
        super().__init__()

    @pyqtSlot()
    def start_reading(self):
        while self.running:
            if self.port_input is not None:
                serial_input = self.port_input.read()
                if serial_input != b'' and serial_input != b'\x00':
                    self.signal_to_main.emit(unpack('>B', serial_input)[0])


def _warn_about_ports():
    port_names = sorted([x.device for x in comports()])
    if len(port_names) > 0:
        ports = ', '.join(port_names)
        lg.warning(f'Available ports are {ports}')
    else:
        lg.warning('No available ports')


def main():

    parser = ArgumentParser(prog='presentation')
    parser.add_argument(
        'task',
        nargs='?',
        help='one of [{}]'.format(', '.join(TASKS)))
    parser.add_argument(
        'configuration',
        nargs='?',
        default=None,
        help='empty or one of [{}]'.format(', '.join(CONFIGURATIONS)))
    args = parser.parse_args()
    print(args)

    with DEFAULTS_JSON.open() as f:
        PARAMETERS = load(f)

    task_dir = TASKS_DIR / args.task
    parameter_json = task_dir / 'parameters.json'
    with parameter_json.open() as f:
        CHANGES = load(f)
    PARAMETERS = update(PARAMETERS, CHANGES)

    if args.configuration is not None:
        parameter_json = CONFIG_DIR / f'{args.configuration}.json'
        with parameter_json.open() as f:
            CHANGES = load(f)
        PARAMETERS = update(PARAMETERS, CHANGES)

    PARAMETERS['task'] = args.task
    PARAMETERS['configuration'] = args.configuration

    now = datetime.now()
    logname = LOG_DIR / f'log_{now:%Y%m%d_%H%M%S}.txt'

    logging.basicConfig(
        filename=logname,
        filemode='w',
        format='%(asctime)s.%(msecs)03d\t%(name)s\t%(levelname)s\t%(message)s',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)
    logging.info(str(now))
    PARAMETERS['logname'] = logname

    if Process is not None:
        ps = Process()
        ps.nice(HIGH_PRIORITY_CLASS)

    task_tsv = (task_dir / PARAMETERS['TASK_TSV']).resolve()
    if task_tsv.exists():
        PARAMETERS['TASK_TSV'] = task_tsv
    else:
        lg.debug(f'Cannot find {task_tsv}, using default "timing.tsv"')
        PARAMETERS['TASK_TSV'] = (task_dir / 'timing.tsv').resolve()

    lg.debug(pformat(PARAMETERS))
    w = PrettyWidget(PARAMETERS)
    app.exec()


if __name__ == '__main__':

    main()
