from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
from qttasks.prf import PrettyWidget
from time import sleep
from serial import serial_for_url, SerialException
from pathlib import Path
from struct import unpack

import threading


class SerialThreading(object):
    def __init__(self):
        self.triggers_log = Path('triggers.log').resolve()

        self.port_trigger = serial_for_url('loop://', timeout=0.1)
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):

        with self.triggers_log.open('wb') as f:
            while True:
                out = self.port_trigger.read()
                if out != b'':
                    f.write(out)


def notest_prf_exit(qtbot):

    tr = SerialThreading()

    w = PrettyWidget(port_trigger=tr.port_trigger)
    qtbot.addWidget(w)
    sleep(1)

    qtbot.keyEvent(
        QTest.Click,
        w,
        Qt.Key_Escape,
        )

    with tr.triggers_log.open('rb') as f:
        val = f.read()
    assert unpack('<' + len(val) * 'B', val) == (250, 251)


def notest_prf_exit_after_start(qtbot):

    tr = SerialThreading()

    w = PrettyWidget(port_trigger=tr.port_trigger)
    qtbot.addWidget(w)

    qtbot.keyEvent(
        QTest.Click,
        w,
        Qt.Key_Enter,
        )

    w.start()

    sleep(5)
    w.check_time()
    sleep(5)
    qtbot.keyEvent(
        QTest.Click,
        w,
        Qt.Key_Escape,
        )
    sleep(2)

    with tr.triggers_log.open('rb') as f:
        val = f.read()
    assert unpack('<' + len(val) * 'B', val) == (250, 251)
