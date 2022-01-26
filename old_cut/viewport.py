from pymol.Qt import QtOpenGL


class ViewPort(QtOpenGL.QGLWidget):
    def __init__(self, parent=None):
        QtOpenGL.QGLWidget.__init__(self, parent)
        self.setMinimumSize(640, 480)

    def paintGL(self):
        QtOpenGL.glClear(QtOpenGL.GL_COLOR_BUFFER_BIT | QtOpenGL.GL_DEPTH_BUFFER_BIT)
        QtOpenGL.glLoadIdentity()
        QtOpenGL.glTranslatef(-2.5, 0.5, -6.0)
        QtOpenGL.glColor3f(1.0, 1.5, 0.0)
        QtOpenGL.glPolygonMode(QtOpenGL.GL_FRONT, QtOpenGL.GL_FILL)
        QtOpenGL.glBegin(QtOpenGL.GL_TRIANGLES)
        QtOpenGL.glVertex3f(2.0, -1.2, 0.0)
        QtOpenGL.glVertex3f(2.6, 0.0, 0.0)
        QtOpenGL.glVertex3f(2.9, -1.2, 0.0)
        QtOpenGL.glEnd()
        QtOpenGL.glFlush()

    def initializeGL(self):
        QtOpenGL.glClearDepth(1.0)
        QtOpenGL.glDepthFunc(QtOpenGL.GL_LESS)
        QtOpenGL.glEnable(QtOpenGL.GL_DEPTH_TEST)
        QtOpenGL.glShadeModel(QtOpenGL.GL_SMOOTH)
        QtOpenGL.glMatrixMode(QtOpenGL.GL_PROJECTION)
        QtOpenGL.glLoadIdentity()
        QtOpenGL.gluPerspective(45.0, 1.33, 0.1, 100.0)
        QtOpenGL.glMatrixMode(QtOpenGL.GL_MODELVIEW)