"""
TODO
----
how to handle 2 datagloves
"""
import time
from pathlib import Path

from ctypes import cdll, create_string_buffer, byref, c_ushort, c_int, pointer, c_bool, c_float

SCRIPT_DIR = Path(__file__).resolve().parent


GLOVE_HAND = {
    0: 'Left',
    1: 'Right',
    }

GLOVE_TYPE = {
    0: 'GLOVENONE',
    1: 'GLOVE5U',
    2: 'GLOVE5UW',
    3: 'GLOVE5U_USB',
    4: 'GLOVE7',
    5: 'GLOVE7W',
    6: 'GLOVE16',
    7: 'GLOVE16W',
    8: 'GLOVE14U',
    9: 'GLOVE14UW',
    10: 'GLOVE14U_USB',
    }


def func(f, glove):

    done = time.time()
    elapsed = done - glove.start
    data = glove.get_sensor_raw_all()
    v = ', '.join(map(str, data))
    glove.f.write(f'{elapsed: 16.3f}\t{v}\n')


class FiveDTGlove:
    """
    glove = FiveDTGlove(Path('logfile.txt'))
    glove.open(b'USB0')

    CMPFUNC = CFUNCTYPE(None, c_int)
    c_func = CMPFUNC(partial(func, glove=glove))
    glove.callback(c_func)
    """
    gloveDLL = cdll.LoadLibrary(str(SCRIPT_DIR / "include/fglove.dll"))

    def __init__(self, logfile):
       
        if self.gloveDLL is None:
            raise IOError("Could not open fglove.dll")
        self.start = time.time()
        self.f = logfile.open('w+')

    @classmethod
    def scan_USB(cls):
        """I get access violation writing ..."""
        if cls.gloveDLL is not None:
            return cls.gloveDLL.fdScanUSB('')

    def open(self, port):
        """port should be a binary file, like b'USB0'
        """
        self.glovePntr = 0
        self.glovePntr = self.gloveDLL.fdOpen(port)
        if self.glovePntr == 0:
            raise IOError("Could not connect to 5DT glove.")
        self.num_sensors = self.get_num_sensors()

    def close(self):
        self.f.close()
        self.gloveDLL.fdClose(self.glovePntr)

    def get_glove_hand(self):
        return GLOVE_HAND[self.gloveDLL.fdGetGloveHand(self.glovePntr)]

    def get_glove_type(self):
        return GLOVE_TYPE[self.gloveDLL.fdGetGloveType(self.glovePntr)]

    def get_num_sensors(self):
        return self.gloveDLL.fdGetNumSensors(self.glovePntr)

    def get_sensor_raw(self, index):
        return self.gloveDLL.fdGetSensorRaw(self.glovePntr, index)

    def get_sensor_raw_all(self):
        data = (c_ushort * self.num_sensors)()
        self.gloveDLL.fdGetSensorRawAll(self.glovePntr, data)
        DATA_GLOVE_INDEX = [0, 3, 6, 9, 12]
        return [data[i] for i in DATA_GLOVE_INDEX]

    def get_sensor_scaled_all(self):
        data = (c_float * self.num_sensors)()
        self.gloveDLL.fdGetSensorRawAll(self.glovePntr, data)

        DATA_GLOVE_INDEX = [0, 3, 6, 9, 12]
        return [data[i] for i in DATA_GLOVE_INDEX]

    def get_calibration(self, index):
        calibrationUpper = c_ushort(0)
        calibrationLower = c_ushort(0)
        self.gloveDLL.fdGetCalibration(self.glovePntr, 1, pointer(calibrationUpper), pointer(calibrationLower))
        return [calibrationUpper.value, calibrationLower.value]

    def get_calibration_all(self):
        arrTypeUShortArray20 = c_ushort * 20
        calibrationUpper = arrTypeUShortArray20()
        calibrationLower = arrTypeUShortArray20()
        self.gloveDLL.fdGetCalibrationAll(self.glovePntr, calibrationUpper, calibrationLower)
        return [list(calibrationUpper), list(calibrationLower)]

    def reset_calibration_all(self):
        self.gloveDLL.fdResetCalibrationAll(self.glovePntr)

    def get_glove_info(self):
        charBuffer = create_string_buffer(256)
        self.gloveDLL.fdGetGloveInfo(self.glovePntr, byref(charBuffer))
        return charBuffer.value.decode()

    def get_drive_info(self):
        charBuffer = create_string_buffer(256)
        self.gloveDLL.fdGetDriverInfo(self.glovePntr, byref(charBuffer))
        return charBuffer.value.decode()

    def callback(self, func):
        self.f.write('started\n')
        self.gloveDLL.fdSetCallback(self.glovePntr, func, c_int(1))

    def remove_callback(self, func):
        self.gloveDLL.fdRemoveCallback(self.glovePntr)
        self.f.write('finished\n')

    def get_packet_rate(self):
        return self.gloveDLL.fdGetPacketRate(self.glovePntr)

    def new_data(self):
        self.gloveDLL.fdNewData.restype = c_bool
        return self.gloveDLL.fdNewData(self.glovePntr)

    def get_FW_version_major(self):
        return self.gloveDLL.fdGetFWVersionMajor(self.glovePntr)

    def get_FW_version_minor(self):
        return self.gloveDLL.fdGetFWVersionMinor(self.glovePntr)

    def get_autocalibrate(self):
        self.gloveDLL.fdGetAutoCalibrate.restype = c_bool
        return self.gloveDLL.fdGetAutoCalibrate(self.glovePntr)

    def set_autocalibrate(self, value):
        self.gloveDLL.fdSetAutoCalibrate(self.glovePntr, c_bool(value))

