from Models.Box import Box
from utils.vec3 import vec3
from utils.util import dotdict
from pymol import cmd


class BoxAPI:

    def __init__(self) -> None:
        self.boxInstance = Box()

    def fill(self):
        self.boxInstance.set_fill(True)
        self.boxInstance.render()
        # logging.info(f'BoxAPI here ...')

    def unfill(self):
        self.boxInstance.set_fill(False)
        self.boxInstance.render()

    def extend(self, x, y, z):
        self.boxInstance.extend(vec3(x, y, z))
        self.boxInstance.render()

    def move(self, x, y, z):
        self.boxInstance.translate(vec3(x, y, z))
        self.boxInstance.render()

    def set_center(self, x, y, z):
        self.boxInstance.set_center(vec3(x, y, z))
        self.boxInstance.render()
        print(self.boxInstance)

    def set_dim(self, x, y, z):
        self.boxInstance.set_dim(vec3(x, y, z))
        self.boxInstance.render()
        print(self.boxInstance)

    # TODO: Decouple generation from returning the data?

    def gen_box(self, selection="(sele)", padding=2.0) -> 'dotdict':
        ([minX, minY, minZ], [maxX, maxY, maxZ]) = cmd.get_extent(selection)
        # cmd.iterate(selector.process(selection, 'stored.residues.add(resv'))
        # for residue in stored.residues:
        #     print(str(residue))
        center = vec3((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2)
        dim = vec3((maxX - minX + 2 * padding), (maxY - minY + 2 * padding), (maxZ - minZ + 2 * padding))
        self.boxInstance.set_config(center, dim)
        print(self.boxInstance)
        self.boxInstance.render()
        return self.box_data()

    def read_box(self, filename) -> 'dotdict':
        with open(filename, 'r') as f:
            lines = f.readlines()

            centerX = float(lines[0].split('=')[1].strip())
            centerY = float(lines[1].split('=')[1].strip())
            centerZ = float(lines[2].split('=')[1].strip())

            dimX = float(lines[3].split('=')[1].strip())
            dimY = float(lines[4].split('=')[1].strip())
            dimZ = float(lines[5].split('=')[1].strip())

            center = vec3(centerX, centerY, centerZ)
            dim = vec3(dimX, dimY, dimZ)

        self.boxInstance.set_config(center, dim)
        print(self.boxInstance)
        self.boxInstance.render()
        return self.box_data()

    def save_box(self, filename, vinaOutput):
        box = self.boxInstance
        with open(filename, 'w') as f:
            f.write("center_x = " + str(box.center.x) + '\n')
            f.write("center_y = " + str(box.center.y) + '\n')
            f.write("center_z = " + str(box.center.z) + '\n')

            f.write("size_x = " + str(box.dim.x) + '\n')
            f.write("size_y = " + str(box.dim.y) + '\n')
            f.write("size_z = " + str(box.dim.z) + '\n')

            if vinaOutput != '':
                f.write("out = " + vinaOutput + '\n')

    # TODO: handle the case when the name changes
    # Explicit function to render and hide the box (why not?)
    def render_box(self):
        self.boxInstance.render()

    def hide_box(self):
        self.boxInstance.set_hidden(True)
        cmd.delete('box')
        cmd.delete('axes')

    def show_box(self):
        self.boxInstance.set_hidden(False)
        self.boxInstance.render()

    def box_data(self) -> 'dotdict':
        box = self.boxInstance

        if not self.box_exists():
            raise Exception("No box config yet!")

        return dotdict({
            "center": dotdict({
                "x": box.center.x,
                "y": box.center.y,
                "z": box.center.z
            }),
            "dim": dotdict({
                "x": box.dim.x,
                "y": box.dim.y,
                "z": box.dim.z
            })
        })

    def box_exists(self) -> bool:
        return self.boxInstance.center is not None and self.boxInstance.dim is not None

    def is_hidden(self):
        return self.boxInstance.hidden

    def is_filled(self):
        return self.boxInstance.fill
