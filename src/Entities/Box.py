from src.utils.vec3 import vec3
from pymol.cgo import *
from pymol import cmd
from pymol.vfont import plain


# NOTE: Rendering includes communication with pymol (cmd, etc.). May be decoupled from the Box class
# because it is better to let the plugin handle the rendering and the communication with PyMol
# we can let the box just return CGO objects maybe?
class Box:
    class __Box:
        def __init__(self) -> None:
            self.center = None
            self.dim = None
            self.fill = False
            self.hidden = False

        def __str__(self):
            return f'Center {str(self.center)}); Dim {str(self.dim)}'

        def set_fill(self, state):
            self.fill = state

        def set_hidden(self, state):
            self.hidden = state

        def set_config(self, center: 'vec3', dim: 'vec3') -> None:
            self.center = center
            self.dim = dim

        def translate(self, v: 'vec3') -> None:
            self.center = self.center + v

        def extend(self, v: 'vec3') -> None:
            self.dim = self.dim + v

        def set_center(self, v: 'vec3') -> None:
            self.center = v

        def get_center(self) -> 'vec3':
            return self.center

        def set_dim(self, v: 'vec3') -> None:
            self.dim = v

        def get_dim(self) -> 'vec3':
            return self.dim

        def __showaxes(self, minX: float, minY: float, minZ: float) -> None:
            cmd.delete('axes')
            w = 0.15  # cylinder width
            l = 5.0  # cylinder length

            obj = [
                CYLINDER, minX, minY, minZ, minX + l, minY, minZ, w, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                CYLINDER, minX, minY, minZ, minX, minY + l, minZ, w, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0,
                CYLINDER, minX, minY, minZ, minX, minY, minZ + l, w, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0,
                CONE, minX + l, minY, minZ, minX + 1 + l, minY, minZ, w * 1.5, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0,
                1.0,
                CONE, minX, minY + l, minZ, minX, minY + 1 + l, minZ, w * 1.5, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0,
                1.0,
                CONE, minX, minY, minZ + l, minX, minY, minZ + 1 + l, w * 1.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0,
                1.0
            ]

            cyl_text(obj, plain, [minX + l + 1 + 0.2, minY, minZ - w], 'X', 0.1, axes=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            cyl_text(obj, plain, [minX - w, minY + l + 1 + 0.2, minZ], 'Y', 0.1, axes=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            cyl_text(obj, plain, [minX - w, minY, minZ + l + 1 + 0.2], 'Z', 0.1, axes=[[0, 0, 1], [0, 1, 0], [1, 0, 0]])

            cmd.load_cgo(obj, 'axes')

        # TODO: fix repeated code

        def __draw_normals(self, normal, color):
            w = 0.15  # cylinder width
            l = 5.0  # cylinder length
            n = normal[1]

            obj = [
                CYLINDER, self.center.x, self.center.y, self.center.z, self.center.x + n.x, self.center.y + n.y,
                                                                       self.center.z + n.z, w, color[0], color[1],
                color[2], color[0], color[1], color[2],
                # CONE,   minX + l, minY, minZ, minX + 1 + l, minY, minZ, w * 1.5, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0,
            ]

            cyl_text(obj, plain, [self.center.x + n.x, self.center.y + n.y, self.center.z + n.z], str(normal[0]), 0.1,
                     axes=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])

            cmd.load_cgo(obj, 'normal')

        def __refresh_unfilled(self) -> None:
            center = self.center
            dim = self.dim

            # get extremes
            (minX, minY, minZ) = (center - dim / 2).unpack()
            (maxX, maxY, maxZ) = (center + dim / 2).unpack()

            box_cgo = [
                LINEWIDTH, float(2.0),

                BEGIN, LINES,
                COLOR, float(0.5), float(0.8), float(1.0),

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, minX, minY, maxZ,  # 2

                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, minX, maxY, maxZ,  # 4

                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, maxX, minY, maxZ,  # 6

                VERTEX, maxX, maxY, minZ,  # 7
                VERTEX, maxX, maxY, maxZ,  # 8

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, maxX, minY, minZ,  # 5

                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, maxX, maxY, minZ,  # 7

                VERTEX, minX, maxY, maxZ,  # 4
                VERTEX, maxX, maxY, maxZ,  # 8

                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, maxX, minY, maxZ,  # 6

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, minX, maxY, minZ,  # 3

                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, maxX, maxY, minZ,  # 7

                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, minX, maxY, maxZ,  # 4

                VERTEX, maxX, minY, maxZ,  # 6
                VERTEX, maxX, maxY, maxZ,  # 8

                END
            ]

            self.__showaxes(minX, minY, minZ)
            cmd.delete('box')
            cmd.load_cgo(box_cgo, 'box')

        # TODO: normals are hardcoded, do not work if the cube is rotated
        def __refresh_filled(self, settings={}):
            # c1 = self.center - self.dim / 2
            # c2 = c1 + vec3(self.dim.x, 0, 0)
            # c3 = c2 + vec3(0, 0, self.dim.z)
            # c4 = c3 + vec3(-self.dim.x, 0, 0)
            # normal = (c2 - c1).cross((c4 - c1))
            # normal = normal.normalize()

            center = self.center
            dim = self.dim

            # get extremes
            (minX, minY, minZ) = (center - dim / 2).unpack()
            (maxX, maxY, maxZ) = (center + dim / 2).unpack()

            c1 = vec3(minX, minY, minZ)
            c2 = vec3(minX, minY, maxZ)
            c3 = vec3(minX, maxY, minZ)
            c4 = vec3(minX, maxY, maxZ)

            c5 = vec3(maxX, minY, minZ)
            c6 = vec3(maxX, minY, maxZ)
            c7 = vec3(maxX, maxY, minZ)
            c8 = vec3(maxX, maxY, maxZ)

            # normal1 = (c1.normalize() - c2.normalize()).cross(c1.normalize() - c3.normalize())
            normal1 = vec3(-1.0, 0.0, 0.0)

            # normal2 = (c5.normalize() - c6.normalize()).cross(c5.normalize() - c7.normalize())
            normal2 = vec3(1.0, 0.0, 0.0)

            # normal2 = vec3(0.0, 0.0, 1.0)
            # normal3 = (c1.normalize() - c5.normalize()).cross(c1.normalize() - c3.normalize())
            normal3 = vec3(0.0, 0.0, -1.0)

            # normal4 = (c2.normalize() - c6.normalize()).cross(c2.normalize() - c4.normalize())
            normal4 = vec3(0.0, 0.0, 1.0)
            # normal5 = (c3.normalize() - c7.normalize()).cross(c3.normalize() - c4.normalize())
            normal5 = vec3(0.0, 1.0, 0.0)
            # normal6 = (c1.normalize() - c5.normalize()).cross(c1.normalize() - c2.normalize())
            normal6 = vec3(0.0, -1.0, 0.0)

            # Render the normals
            '''
            self.__draw_normals(['n3', normal3], [0.0, 0.0, 1.0])
            self.__draw_normals(['n4', normal4], [1.0, 0.5, 0.0])
            self.__draw_normals(['n6', normal6], [1.0, 0.0, 0.0])
            self.__draw_normals(['n5', normal5], [0.2, 0.6, 0.2])
            self.__draw_normals(['n1', normal1], [0.55, 0.1, 0.6])
            self.__draw_normals(['n2', normal2], [1.0, 1.0, 1.0])
            '''

            alpha = 0.8

            box_cgo = [
                LINEWIDTH, float(2.0),

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal1.x, normal1.y, normal1.z,
                ALPHA, float(alpha),
                COLOR, float(0.55), float(0.1), float(0.60),  # purple

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, minX, maxY, maxZ,  # 4
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal2.x, normal2.y, normal2.z,
                ALPHA, float(alpha),
                COLOR, float(1.0), float(1.0), float(0.0),  # yellow

                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, maxX, minY, maxZ,  # 6
                VERTEX, maxX, maxY, minZ,  # 7
                VERTEX, maxX, maxY, maxZ,  # 8
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal3.x, normal3.y, normal3.z,
                ALPHA, float(alpha),
                COLOR, float(0.0), float(0.0), float(1.0),  # blue

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, maxX, maxY, minZ,  # 7
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal4.x, normal4.y, normal4.z,
                ALPHA, float(alpha),
                COLOR, float(1.0), float(0.5), float(0.0),  # orange

                VERTEX, minX, maxY, maxZ,  # 4
                VERTEX, maxX, maxY, maxZ,  # 8
                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, maxX, minY, maxZ,  # 6
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal5.x, normal5.y, normal5.z,
                ALPHA, float(alpha),
                COLOR, float(0.2), float(0.6), float(0.2),  # green

                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, maxX, maxY, minZ,  # 7
                VERTEX, minX, maxY, maxZ,  # 4
                VERTEX, maxX, maxY, maxZ,  # 8
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal6.x, normal6.y, normal6.z,
                ALPHA, float(alpha),
                COLOR, float(1.0), float(0.0), float(0.0),  # red
                VERTEX, minX, minY, minZ,  # 1
                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, maxX, minY, maxZ,  # 6

                END
            ]

            self.__showaxes(minX, minY, minZ)
            cmd.delete('box')
            cmd.load_cgo(box_cgo, 'box')

        def render(self) -> None:
            if self.hidden is False and self.center is not None and self.dim is not None:
                if self.fill:
                    self.__refresh_filled()
                else:
                    self.__refresh_unfilled()

    _instance = None

    def __init__(self):
        if not Box._instance:
            Box._instance = Box.__Box()

            # Delegate Calls to the inner private class

    def __getattr__(self, name):
        return getattr(self._instance, name)
