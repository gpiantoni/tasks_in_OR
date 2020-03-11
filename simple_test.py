from PyQt5.QtGui import QSurfaceFormat, QOpenGLVersionProfile, QPixmap
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtGui import QOpenGLWindow, QPainter
from time import time
from numpy import array, diff
from pathlib import Path
from numpy import genfromtxt, zeros, dtype, where


app = QApplication([])

pixmap0 = QPixmap('/home/gio/tools/tasks_in_OR/qttasks/images/jip/allemaal.jpg')
pixmap1 = QPixmap('/home/gio/tools/tasks_in_OR/qttasks/images/fingermapping_right/stim_009.png')


def _convert_stimuli(STIMULI_TSV):
    IMAGES_DIR = Path('/home/gio/tools/tasks_in_OR/opengl/')

    tsv = genfromtxt(
        fname=STIMULI_TSV,
        delimiter='\t',
        names=True,
        dtype=None,  # forces it to read strings
        deletechars='',
        encoding='utf-8')
    n_stims = tsv.shape[0] + 1

    stimuli = zeros(n_stims, dtype([
        ('onset', 'int32'),
        ('pixmap', 'O'),
        ]))
    stimuli['onset'][:-1] = tsv['onset']
    stimuli['onset'][1:] = tsv['onset'] + tsv['duration']

    # read images only once
    stimuli['pixmap'] = None
    stimuli['pixmap'][:-1] = tsv['stim_file']
    d_images = {png: QPixmap(str(IMAGES_DIR / png)) for png in set(tsv['stim_file'])}
    for png, pixmap in d_images.items():
        stimuli['pixmap'][stimuli['pixmap'] == png] = pixmap

    return stimuli


class Pres(QOpenGLWindow):
    info = []
    t = time()
    color = True
    stim = _convert_stimuli('/home/gio/tools/tasks_in_OR/opengl/stim1.tsv')
    i = 0

    def __init__(self):
        super().__init__()
        self.show()
        self.showFullScreen()

    def start(self):
        self.i = 0
        self.frameSwapped.connect(self.update)
        self.update()

    def paintGL(self):
        print(self.i)
        if self.i is not None:

            i_pixmap = where(self.stim['onset'] <= self.i)[0][-1]
            if self.stim['pixmap'][i_pixmap] is None:
                self.close()
                return

            qp = QPainter()
            qp.begin(self)
            qp.beginNativePainting()
            qp.drawPixmap(0, 0, self.stim['pixmap'][i_pixmap])
            qp.endNativePainting()
            qp.end()
            self.i += 1
            self.info.append(time() - self.t)
            print(time() - self.t)


class W(QOpenGLWindow):
    color = False

    def __init__(self):
        super().__init__()
        self.show()
        self.showFullScreen()

    def initializeGL(self):
        self.c = self.context()
        self.s = self.c.surface()
        self.f = QSurfaceFormat()            # The default
        self.f.setSwapInterval(1)
        self.p = QOpenGLVersionProfile(self.f)
        print(self.p.version())
        self.gl = self.c.versionFunctions(self.p)
        self.gl.initializeOpenGLFunctions()
        super().initializeGL()

    def paintGL(self):
        qp = QPainter()
        qp.begin(self)
        if self.color:
            current_pixmap = pixmap0
        else:
            current_pixmap = pixmap1

        qp.drawPixmap(0, 0, current_pixmap)

        qp.end()

    def paintGLx(self):
        self.gl.glClear(self.gl.GL_COLOR_BUFFER_BIT | self.gl.GL_DEPTH_BUFFER_BIT)
        if self.color:
            self.gl.glColor3f(0.5, 0.0, 1.0)
        else:
            self.gl.glColor3f(0.5, 1.0, 0.0)

        self.gl.glBegin(self.gl.GL_QUADS)
        self.gl.glVertex2d(0, 0)
        self.gl.glVertex2d(50, 0)
        self.gl.glVertex2d(50, 50)
        self.gl.glVertex2d(0, 50)
        self.gl.glEnd()

        self.gl.glFinish()

    def test(self):
        t = time()

        a = []
        for i in range(300):
            self.color = not self.color
            t_ = time()
            self.paint()
            t_1 = time() - t_
            self.c.swapBuffers(self.s)
            t_2 = time() - t_
            print(f'{t_1:10.6f} {t_2:10.6f}')
            a.append(time() - t)

        return a


def main_x():
    self = W()
    app.processEvents()
    x = self.test()
    print(1 / diff(array(x)).mean())
    app.exec()


def main():
    self = Pres()
    self.raise_()
    app.processEvents()
    self.start()
    app.exec()


if __name__ == '__main__':

    main()
