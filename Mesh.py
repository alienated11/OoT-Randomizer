from Rom import Rom
from SceneList import scene_table


def convert_to_signed(value):        
    if value >= 0x8000:
        value -= 0x10000
    return value


def convert_to_unsigned(value):
    return value + 0x10000


class Mesh:
    def __init__(self, name=None):
        self.vertices = []
        self.faces = []
        self.bound_x = [0, 0]
        self.bound_y = [0, 0]
        self.bound_z = [0, 0]
        self.name = name

    def read_from_rom(self, rom, scene_offset, collision_offset):
        rom.seek_address(scene_offset + collision_offset)
        self.bound_x[0] = convert_to_signed(rom.read_int16())
        self.bound_y[0] = convert_to_signed(rom.read_int16())
        self.bound_z[0] = convert_to_signed(rom.read_int16())
        self.bound_x[1] = convert_to_signed(rom.read_int16())
        self.bound_y[1] = convert_to_signed(rom.read_int16())
        self.bound_z[1] = convert_to_signed(rom.read_int16())
        number_of_vertices = rom.read_int16()
        rom.seek_address(delta=2)
        vertex_segment_offset = rom.read_int32() & 0x00FFFFFF
        number_of_polygons = rom.read_int16()
        rom.seek_address(delta=2)
        polygon_segment_offset = rom.read_int32() & 0x00FFFFFF

        # read vertices
        rom.seek_address(scene_offset + vertex_segment_offset)
        i = 0
        vertices = []
        while i < number_of_vertices:
            x = convert_to_signed(rom.read_int16())
            y = convert_to_signed(rom.read_int16())
            z = convert_to_signed(rom.read_int16())
            self.vertices.append(Vertex3d(x, y, z, i))
            i += 1

        # read polygons
        rom.seek_address(scene_offset + polygon_segment_offset)
        i = 0
        polygons = []
        while i < number_of_polygons:
            poly_type = rom.read_int16()
            a = rom.read_int16() & 0x1FFF
            b = rom.read_int16() & 0x1FFF
            c = rom.read_int16() & 0x1FFF
            n_x = convert_to_signed(rom.read_int16())/0x7FFF
            n_y = convert_to_signed(rom.read_int16())/0x7FFF
            n_z = convert_to_signed(rom.read_int16())/0x7FFF
            normal = Vertex3d(n_x,n_y,n_z)
            distance = rom.read_int16()
            self.faces.append(Face([self.vertices[a], self.vertices[b], self.vertices[c]], normal, i))
            # if n_x == 0 and n_z == 0 and n_y == 1:
            # print("{} ({}) -- Normal: {} {} {}".format(self.name, i, n_x, n_y, n_z))
            i += 1

        polygon_type_segment_offset = rom.read_int32() & 0x00FFFFFF
        camera_data_segment_offset = rom.read_int32() & 0x00FFFFFF
       
        number_of_water_boxes = rom.read_int16()
        rom.seek_address(delta=2)
        water_box_segment_offset = rom.read_int32() & 0x00FFFFFF

    def write_mesh(self):
        file_name = self.name if self.name != "" else "mesh"
        m = open("{}.obj".format(file_name),"w")
        m.write("#{}\n".format(self.name))
        for v in self.vertices:
            m.write("v {} {} {}\n".format(v.x, v.y, v.z))
        for f in self.faces:
            m.write("vn {} {} {}\n".format(f.normal.x, f.normal.y, f.normal.z))
            # m.write("f {0}/{3} {1}/{3} {2}/{3}\n".format(f.vertices[0]+1, f.vertices[1]+1, f.vertices[2]+1,f.index+1))
            m.write("f {0} {1} {2}\n".format(f.vertices[0].index+1, f.vertices[1].index+1, f.vertices[2].index+1))
        m.close()


class Vertex3d:
    def __init__(self, x, y, z, index=None):
        self.x = x
        self.y = y
        self.z = z
        self.faces = {}
        self.index = index

    def __sub__(self, other):
        return Vertex3d(self.x-other.x, self.y-other.y, self.z-other.z)

    def __add__(self, other):
        return Vertex3d(self.x+other.x, self.y+other.y, self.z+other.z)

    def __mul__(self, other):
        if isinstance(other, Vertex3d):
            return Vertex3d(self.x*other.x, self.y*other.y, self.z*other.z)
        else:
            return Vertex3d(self.x * other, self.y * other, self.z * other)

    def __truediv__(self, scalar):
        return Vertex3d(self.x/scalar, self.y/scalar, self.z/scalar)

    def cross(self, other):
        return Vertex3d((self.y*other.z - self.z*other.y), -1*(self.x*other.z-self.z*other.x), (self.x*other.y-self.y*other.x))

    def mag(self):
        return (self.x**2 + self.y**2 + self.z**2)**(1/2)

    def unit(self):
        m = self.mag()
        return self/m

    def add_face(self, face):
        self.faces[len(self.faces)] = face

    def set_index(self, index):
        self.index = index


class Face:
    def __init__(self, vertices=None, normal=None, index=None):
        self.vertices = vertices
        self.normal = normal
        self.index = index
        self.area = 0

    def add_vertex(self, vertex_index):
        self.vertices.append(vertex_index)

    def set_index(self, index):
        self.index = index

    def get_area(self):
        if len(self.vertices) == 3 and self.area <= 0:
            self.area = 0.5*(self.vertices[1] - self.vertices[0]).cross((self.vertices[2] - self.vertices[0])).mag()
        return self.area







# rom = Rom("")
# for scene in scene_table:
#     scene["mesh"] = Mesh(scene["name"])
#     scene["mesh"].read_from_rom(rom, scene["scene_data"], scene["collision_off"])
#     scene["mesh"].write_mesh()