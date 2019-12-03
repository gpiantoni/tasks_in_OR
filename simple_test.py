from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtGui import QSurfaceFormat, QOpenGLVersionProfile
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtGui import QSurfaceFormat, QOpenGLVersionProfile, QWindow,QOpenGLWindow
from time import time
from numpy import array, diff

app = QApplication([])


class W(QOpenGLWindow):
    color = False

    def __init__(self):
        super().__init__()
        self.show()

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
            self.paintGL()
            t_1 = time() - t_
            self.c.swapBuffers(self.s)
            t_2 = time() - t_
            print(f'{t_1:10.6f} {t_2:10.6f}')
            a.append(time() - t)

        return a


def main():
    self = W()
    app.processEvents()
    x = self.test()
    print(1/ diff(array(x)).mean() )
    app.exec()


if __name__ == '__main__':

    main()
