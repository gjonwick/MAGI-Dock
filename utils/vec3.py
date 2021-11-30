class vec3:

    RSMALL4 = 0.0001

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, v) -> 'vec3':
        return vec3(self.x + v.x, self.y + v.y, self.z + v.z)

    def __sub__(self, v) -> 'vec3':
        return vec3(self.x - v.x, self.y - v.y, self.z - v.z)

    def __mul__(self, c) -> 'vec3':
        return vec3(self.x * c, self.y * c, self.z * c)

    def dot(self, v: 'vec3') -> float:
        return self.x * v.x + self.y * v.y + self.z * v.z

    def cross(self, v: 'vec3') -> 'vec3':
        return vec3(self.y * v.z - self.z * v.y, self.z * v.x - self.x * v.z, self.x * v.y - self.y * v.x)
    
    def normalize(self) -> 'vec3':
        return vec3(self.x / self.length(), self.y / self.length(), self.z / self.length())
    
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def __truediv__(self, c) -> 'vec3':
        return vec3(self.x / c, self.y / c, self.z / c)

    def __str__(self):
        return f'({str(self.x)}, {str(self.y)}, {str(self.z)})'

    def cube(self, x: float) -> float:
        return x * x * x

    def unpack(self):
        return self.x, self.y, self.z