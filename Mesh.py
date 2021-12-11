from Rom import Rom


def convert_to_signed(value):        
    if value >= 0x8000:
        value -= 0x10000
    return value

class Mesh():
    def __init__(self,name=None):
        self.vertices = []
        self.faces = []
        self.bound_x = [0,0]
        self.bound_y = [0,0]
        self.bound_z = [0,0]
        self.name = name
    def read_from_rom(self,rom, scene_offset, collision_offset):
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

        #read vertices
        rom.seek_address(scene_offset + vertex_segment_offset)
        i = 0
        vertices = []
        while i < number_of_vertices:
            x = convert_to_signed(rom.read_int16())
            y = convert_to_signed(rom.read_int16())
            z = convert_to_signed(rom.read_int16())
            self.vertices.append(Vertex3d(x,y,z,i))
            i+=1

        #read polygons
        rom.seek_address(scene_offset + polygon_segment_offset)
        i = 0
        polygons = []
        while i < number_of_polygons:
            type = rom.read_int16()
            a = rom.read_int16() & 0x1FFF
            b = rom.read_int16() & 0x1FFF
            c = rom.read_int16() & 0x1FFF
            n_x = convert_to_signed(rom.read_int16())
            n_y = convert_to_signed(rom.read_int16())
            n_z = convert_to_signed(rom.read_int16())
            normal = Vertex3d(n_x,n_y,n_z)
            distance = rom.read_int16()
            self.faces.append(Face([a,b,c],normal,i))
            i+=1

        polygon_type_segment_offset = rom.read_int32() & 0x00FFFFFF
        camera_data_segment_offset = rom.read_int32() & 0x00FFFFFF
       
        number_of_water_boxes = rom.read_int16()
        rom.seek_address(delta=2)
        water_box_segment_offset = rom.read_int32() & 0x00FFFFFF

    def write_mesh(self):
        file_name = self.name if self.name != None else "mesh"
        m = open("{}.obj".format(file_name),"w")
        m.write("#{}\n".format(self.name))
        for v in self.vertices:
            m.write("v {} {} {}\n".format(v.x, v.y, v.z))
        for f in self.faces:
            m.write("f {} {} {}\n".format(f.vertices[0]+1, f.vertices[1]+1, f.vertices[2]+1))
        m.close()

class Vertex3d():
    def __init__(self,x,y,z,index=None):
        self.x = x
        self.y = y
        self.z = z
        self.faces = {}
        self.index = index
    def add_face(face):
        self.faces[len(self.faces)] = face
    def set_index(index):
        self.index = index

class Face():
    def __init__(self,vertices=None,normal=None,index=None):
        self.vertices = vertices
        self.normal = normal
        self.index = index
    def add_vertex(vertex_index):
        self.vertices.append(vertex_index)
    def set_index(index):
        self.index = index



scene_table = [
    {"scene_number":0x51, "name":"Hyrule Field",            "scene_data": 0x01FB8000, "collision_off":0x00008464, "mesh":Mesh("Hyrule Field")},
    {"scene_number":0x52, "name":"Kakariko Village",        "scene_data": 0x01FF9000, "collision_off":0x00004A1C, "mesh":Mesh("Kakariko Village")},
    {"scene_number":0x54, "name":"Zora's River",            "scene_data": 0x0204D000, "collision_off":0x00006580, "mesh":Mesh("Zora's River")},
    {"scene_number":0x55, "name":"Kokiri Forest",           "scene_data": 0x0206F000, "collision_off":0x00008918, "mesh":Mesh("Kokiri Forest")},
    {"scene_number":0x56, "name":"Sacred Forest Meadow",    "scene_data": 0x020AC000, "collision_off":0x00003F4C, "mesh":Mesh("Sacred Forest Meadow")},
    {"scene_number":0x57, "name":"Lake Hylia",              "scene_data": 0x020CB000, "collision_off":0x000055AC, "mesh":Mesh("Lake Hylia")},
    {"scene_number":0x58, "name":"Zora's Domain",           "scene_data": 0x020F2000, "collision_off":0x00003824, "mesh":Mesh("Zora's Domain")},
    {"scene_number":0x5A, "name":"Gerudo Valley",           "scene_data": 0x0212B000, "collision_off":0x00002128, "mesh":Mesh("Gerudo Valley")},
    {"scene_number":0x5B, "name":"Lost Woods",              "scene_data": 0x02146000, "collision_off":0x000001A8, "mesh":Mesh("Lost Woods")},
    {"scene_number":0x5C, "name":"Desert Colossus",         "scene_data": 0x02186000, "collision_off":0x00004EE4, "mesh":Mesh("Desert Colossus")},
    {"scene_number":0x5D, "name":"Gerudo Fortress",         "scene_data": 0x021AD000, "collision_off":0x00005030, "mesh":Mesh("Gerudo Fortress")},
    {"scene_number":0x5F, "name":"Hyrule Castle Grounds",   "scene_data": 0x021F6000, "collision_off":0x00003CE8, "mesh":Mesh("Hyrule Castle Grounds")},
    {"scene_number":0x60, "name":"Death Mountain Trail",    "scene_data": 0x0221D000, "collision_off":0x00003D10, "mesh":Mesh("Death Mountain Trail")},
    {"scene_number":0x61, "name":"Death Mountain Crater",   "scene_data": 0x02247000, "collision_off":0x000045A4, "mesh":Mesh("Death Mountain Crater")},
    {"scene_number":0x62, "name":"Goron City",              "scene_data": 0x02271000, "collision_off":0x000059AC, "mesh":Mesh("Goron City")},
    {"scene_number":0x63, "name":"Lon Lon Ranch",           "scene_data": 0x029BC000, "collision_off":0x00002948, "mesh":Mesh("Lon Lon Ranch")}
]

rom = Rom("")
for scene in scene_table:
    scene["mesh"].read_from_rom(rom, scene["scene_data"], scene["collision_off"])
    scene["mesh"].write_mesh()