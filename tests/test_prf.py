from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
from qttasks.prf import PrettyWidget
from time import sleep


def test_prf(qtbot):

    w = PrettyWidget()
    qtbot.addWidget(w)
    sleep(7)

    qtbot.keyEvent(
        QTest.Click,
        w,
        Qt.Key_Escape,
        )
