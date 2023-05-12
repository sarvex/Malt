import collections

import OpenGL
#OpenGL.ERROR_LOGGING = False
#OpenGL.FULL_LOGGING = False
#OpenGL.ERROR_ON_COPY = False
from OpenGL.GL import *
from OpenGL.extensions import hasGLExtension

#For some reason PyOpenGL doesnt support the most common depth/stencil buffer by default ???
#https://sourceforge.net/p/pyopengl/bugs/223/
from OpenGL import images
images.TYPE_TO_ARRAYTYPE[GL_UNSIGNED_INT_24_8] = GL_UNSIGNED_INT
images.TIGHT_PACK_FORMATS[GL_UNSIGNED_INT_24_8] = 4
images.TYPE_TO_ARRAYTYPE[GL_HALF_FLOAT] = GL_HALF_FLOAT
from OpenGL import arrays
if arrays.ADT:
    arrays.GL_CONSTANT_TO_ARRAY_TYPE[GL_HALF_FLOAT] = arrays.ADT(GL_HALF_FLOAT, GLhalfARB)
else:
    class GLhalfFloatArray(ArrayDatatype, ctypes.POINTER(GLhalfARB)):
        baseType = GLhalfARB
        typeConstant = GL_HALF_FLOAT
    arrays.GL_CONSTANT_TO_ARRAY_TYPE[GL_HALF_FLOAT] = GLhalfFloatArray

NULL = None
GL_ENUMS = {}
GL_NAMES = {}

from OpenGL import GL
for e in dir(GL):
    if e.startswith('GL_'):
        GL_ENUMS[getattr(GL, e)] = e
        GL_NAMES[e] = getattr(GL, e)

class DrawQuery():

    def __init__(self, query_type=GL_ANY_SAMPLES_PASSED):
        self.query = None
        self.query_type = query_type
    
    def begin_query(self):
        if self.query:
            glDeleteQueries(1, self.query)
        self.query = gl_buffer(GL_UNSIGNED_INT, 1)
        glGenQueries(1, self.query)
        glBeginQuery(self.query_type, self.query[0])

    def end_query(self):        
        glEndQuery(self.query_type)

    def begin_conditional_draw(self, wait_mode=GL_QUERY_WAIT):
        glBeginConditionalRender(self.query[0], wait_mode)
    
    def end_conditional_draw(self):
        glEndConditionalRender()
    

def gl_buffer(type, size, data=None):
    types = {
        GL_BYTE : GLbyte,
        GL_UNSIGNED_BYTE : GLubyte,
        GL_SHORT : GLshort,
        GL_UNSIGNED_SHORT : GLushort,
        GL_INT : GLint,
        GL_UNSIGNED_INT : GLuint,
        #GL_HALF_FLOAT : GLhalfARB,
        GL_HALF_FLOAT : GLfloat,
        GL_FLOAT : GLfloat,
        GL_DOUBLE : GLdouble,
        GL_BOOL : GLboolean,
    }
    gl_type = (types[type] * size)
    if not data:
        return gl_type()
    try:
        return gl_type(*data)
    except:
        return gl_type(data)


def buffer_to_string(buffer):
    chars = []
    for char in list(buffer):
        if chr(char) == '\0':
            break
        chars.append(chr(char))
    return ''.join(chars)
