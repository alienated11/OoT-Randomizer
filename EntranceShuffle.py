import random
import logging
import struct
from itertools import chain
from Fill import ShuffleError
from collections import OrderedDict
from Search import Search
from Region import TimeOfDay
from Rules import set_entrances_based_rules
from Entrance import Entrance
from State import State
from Item import ItemFactory
from Hints import get_hint_area, HintAreaNotFound
from Rom import Rom
import Mesh
from Mesh import convert_to_unsigned, Mesh, Vertex3d, Face
from SceneList import scene_table


def set_all_entrances_data(world):
    for type, forward_entry, *return_entry in entrance_shuffle_table:
        forward_entrance = world.get_entrance(forward_entry[0])
        forward_entrance.data = forward_entry[1]
        forward_entrance.type = type
        forward_entrance.primary = True
        if type == 'Grotto':
            forward_entrance.data['index'] = 0x1000 + forward_entrance.data['grotto_id']
        if world.settings.decouple_entrances and type not in ('Boss', 'ChildBoss', 'AdultBoss'):
            forward_entrance.decoupled = True
        if return_entry:
            return_entry = return_entry[0]
            return_entrance = world.get_entrance(return_entry[0])
            return_entrance.data = return_entry[1]
            return_entrance.type = type
            forward_entrance.bind_two_way(return_entrance)
            if type == 'Grotto':
                return_entrance.data['index'] = 0x2000 + return_entrance.data['grotto_id']
            if world.settings.decouple_entrances and type not in ('Boss', 'ChildBoss', 'AdultBoss'):
                return_entrance.decoupled = True


def set_grotto_entrances(world):
    grotto_info = open("grottos.txt", "w")
    grotto_info.write("{}\n".format(len(world.get_shufflable_entrances(type='Grotto'))))

    for entrance in world.get_shufflable_entrances(type='Grotto'):
        if entrance.primary:
            if world.settings.shuffle_grotto_location:
                grotto_info.write("{}\n".format(entrance))
                chosen_face = None
                potential_points = []
                safe_points = []
                safe_faces = []
                poly_types = {}
                safe_area = 0
                max_face_area = 0
                scene_mesh = None
                rom = Rom(world.settings.rom)
                for scene_t in scene_table:
                    if scene_t["scene_number"] == entrance.data["scene"]:
                        if scene_t["mesh"] is None:
                            scene_t["mesh"] = Mesh(scene_t["name"])
                            scene_t["mesh"].read_from_rom(rom, scene_t["scene_data"], scene_t["collision_off"])

                        scene_mesh = scene_t["mesh"]
                        for face in scene_mesh.faces:
                            # check face is flat
                            if face.normal.x == 0 and face.normal.z == 0 and face.normal.y == 1:
                                safe_faces.append(face)
                                face_area = face.get_area()
                                safe_area += face_area
                                if face.polytype in poly_types:
                                    poly_types[face.polytype] += 1
                                else:
                                    poly_types[face.polytype] = 0
                                max_face_area = max_face_area if max_face_area > face_area else face_area
                if scene_mesh is not None:
                    grotto_info.write("number of safe faces: {}\n".format(len(safe_faces)))
                    grotto_info.write("number of water: {}\n".format(len(scene_mesh.water)))
                    most_common_poly_type = max(poly_types, key=poly_types.get)
                    grotto_info.write("most common poly type: {}\n".format(most_common_poly_type))
                    if len(safe_faces) > 0:
                        safe_faces_weights = []
                        f = 0
                        for safe_face in safe_faces:
                            if not safe_face.polytype == most_common_poly_type:
                                continue
                            covered = False
                            for face2 in scene_mesh.faces:
                                if safe_face.vertices == face2.vertices or covered:
                                    # grotto_info.write("same face\n")
                                    continue
                                p1 = face2.vertices[0]
                                p2 = face2.vertices[1]
                                p3 = face2.vertices[2]
                                # grotto_info.write("checking against -- {} {} {}\n".format(p1.x, p1.y, p1.z))
                                # grotto_info.write("checking against -- {} {} {}\n".format(p2.x, p2.y, p2.z))
                                # grotto_info.write("checking against -- {} {} {}\n".format(p3.x, p3.y, p3.z))
                                for v in safe_face.vertices:
                                    q1 = Vertex3d(v.x, v.y, v.z)
                                    q2 = Vertex3d(v.x, scene_mesh.bound_y[1], v.z)
                                    # grotto_info.write("checking from -- {} {} {}\n".format(q1.x, q1.y, q1.z))
                                    # grotto_info.write("checking from -- {} {} {}\n".format(q2.x, q2.y, q2.z))
                                    # signed_volume(a,b,c,d) = (1.0/6.0)*dot(cross(b-a,c-a),d-a)
                                    s1 = Face.signed_volume(q1, p1, p2, p3)
                                    s2 = Face.signed_volume(q2, p1, p2, p3)
                                    if ((s1 > 0) - (s1 < 0)) != ((s2 > 0) - (s2 < 0)):
                                        s3 = Face.signed_volume(q1, q2, p1, p2)
                                        s4 = Face.signed_volume(q1, q2, p2, p3)
                                        s5 = Face.signed_volume(q1, q2, p3, p1)
                                        if ((s3 > 0) - (s3 < 0)) == ((s4 > 0) - (s4 < 0)) == ((s5 > 0) - (s5 < 0)):
                                            covered = True
                                    # grotto_info.write("signed vol: {}\n".format(s1))
                                    # grotto_info.write("signed vol: {}\n".format(s2))
                                    # grotto_info.write("signed vol: {}\n".format(s3))
                                    # grotto_info.write("signed vol: {}\n".format(s4))
                                    # grotto_info.write("signed vol: {}\n".format(s5))
                                    # if ((s1 > 0) - (s1 < 0)) != ((s2 > 0) - (s2 < 0)) \
                                    #  and ((s3 > 0) - (s3 < 0)) == ((s4 > 0) - (s4 < 0)) == ((s5 > 0) - (s5 < 0)):
                                    #     covered = True
                            if covered:
                                continue
                            a = safe_face.get_area()
                            safe_faces_weights.append(a/safe_area)
                            # grotto_info.write("face type: {}\n".format(safe_face.polytype))
                            pts_sample = int((safe_area/10000) * (a/safe_area))
                            # pts_sample = int(10*a/max_face_area)
                            f += 1
                            i = 0
                            while i < pts_sample:
                                u = random.random()
                                v = random.random()
                                if u + v > 1:
                                    u = 1 - u
                                    v = 1 - v
                                w = 1 - (u + v)
                                new_point = safe_face.vertices[0] * u + safe_face.vertices[1] * v + safe_face.vertices[2] * w
                                potential_points.append(new_point)
                                i += 1
                                # check point is not underwater
                        for p in potential_points:
                            underwater = False
                            if len(scene_mesh.water) > 0:
                                for water_plane in scene_mesh.water:
                                    if p.y <= water_plane[0].y - 50 \
                                        and water_plane[0].x <= p.x <= water_plane[1].x \
                                            and water_plane[0].z <= p.z <= water_plane[1].z:
                                        underwater = True
                                        break
                            if not underwater:
                                safe_points.append(p)
                        grotto_info.write("number of safe points: {}\n".format(len(safe_points)))
                        chosen_vertex = random.choice(safe_points)
                        grotto_info.write("new pos -- {} {} {}\n".format(chosen_vertex.x, chosen_vertex.y, chosen_vertex.z))
                        exit_position = chosen_vertex - chosen_vertex.unit() * Vertex3d(2, 0, 2)
                        grotto_info.write("exit pos -- {} {} {}\n".format(exit_position.x, exit_position.y, exit_position.z))
                        grotto_x = convert_to_unsigned(int(chosen_vertex.x)) if chosen_vertex.x < 0 else int(chosen_vertex.x)
                        grotto_y = convert_to_unsigned(int(chosen_vertex.y)) if chosen_vertex.y < 0 else int(chosen_vertex.y)
                        grotto_z = convert_to_unsigned(int(chosen_vertex.z)) if chosen_vertex.z < 0 else int(chosen_vertex.z)
                        # grotto_x = struct.unpack('>i', struct.pack('>f', chosen_vertex.x))[0]
                        # grotto_y = struct.unpack('>i', struct.pack('>f', chosen_vertex.y))[0]
                        # grotto_z = struct.unpack('>i', struct.pack('>f', chosen_vertex.z))[0]
                        grotto_info.write("new pos (conv) -- {} {} {}\n".format(grotto_x, grotto_y, grotto_z))
                        exit_position_x = struct.unpack('>i', struct.pack('>f', exit_position.x))[0]
                        exit_position_y = struct.unpack('>i', struct.pack('>f', exit_position.y))[0]
                        exit_position_z = struct.unpack('>i', struct.pack('>f', exit_position.z))[0]
                        grotto_info.write("exit pos (conv) -- {} {} {}\n".format(exit_position_x, exit_position_y, exit_position_z))
                        entrance.data['pos'] = (grotto_x, grotto_y, grotto_z)
                        entrance.reverse.data['pos'] = (exit_position_x, exit_position_y, exit_position_z)
            if world.settings.shuffle_grotto_req != 'off':
                grotto_info.write("Grotto req ({}) \n".format(entrance.name))
                if world.settings.shuffle_grotto_req == 'open':
                    entrance.data['req'] = "open"

                elif world.settings.shuffle_grotto_req == 'hit':
                    entrance.data['req'] = "hit"
                elif world.settings.shuffle_grotto_req == 'storms':
                    entrance.data['req'] = "storms"
                elif world.settings.shuffle_grotto_req == 'random':
                    new_req = random.choice(["open", "hit", "storms"])
                    entrance.data['req'] = new_req
                new_entrance_rule = ""
                if entrance.data['req'] == "open":
                    new_entrance_rule = "True"
                elif entrance.data['req'] == "hit":
                    new_entrance_rule = "can_open_bomb_grotto"
                elif entrance.data['req'] == "storms":
                    new_entrance_rule = "can_open_storm_grotto"
                if "can_blast_or_smash" in entrance.rule_string :
                    new_entrance_rule = entrance.rule_string + " and " + new_entrance_rule
                if "Megaton_Hammer" in entrance.rule_string:
                    if "child" in entrance.rule_string:
                        new_entrance_rule = "(can_use(Megaton_Hammer) or is_child) and " + new_entrance_rule
                    else:
                        new_entrance_rule = "can_use(Megaton_Hammer) and " + new_entrance_rule
                elif "child" in entrance.rule_string:
                    new_entrance_rule = "is_child and " + new_entrance_rule
                if "adult" in entrance.rule_string:
                    new_entrance_rule = "is_adult and " + new_entrance_rule
                grotto_info.write("\told rule: {}\n".format(entrance.rule_string))
                for rule in entrance.access_rules:
                    grotto_info.write("\taccess rule: {}\n".format(rule))
                grotto_info.write("\tnew rule: {}\n".format(new_entrance_rule))
                entrance.rule_string = new_entrance_rule
                world.parser.parse_spot_rule(entrance)
                for rule in entrance.access_rules:
                    grotto_info.write("\taccess rule: {}\n".format(rule))

    grotto_info.close()

def assume_entrance_pool(entrance_pool):
    assumed_pool = []
    for entrance in entrance_pool:
        assumed_forward = entrance.assume_reachable()
        if entrance.reverse != None and not entrance.decoupled:
            assumed_return = entrance.reverse.assume_reachable()
            world = entrance.world
            if not (len(world.settings.mix_entrance_pools) > 1 and (world.settings.shuffle_overworld_entrances or world.shuffle_special_interior_entrances)):
                if (entrance.type in ('Dungeon', 'Grotto', 'Grave') and entrance.reverse.name != 'Spirit Temple Lobby -> Desert Colossus From Spirit Lobby') or \
                   (entrance.type == 'Interior' and world.shuffle_special_interior_entrances):
                    # In most cases, Dungeon, Grotto/Grave and Simple Interior exits shouldn't be assumed able to give access to their parent region
                    assumed_return.set_rule(lambda state, **kwargs: False)
            assumed_forward.bind_two_way(assumed_return)
        assumed_pool.append(assumed_forward)
    return assumed_pool


def build_one_way_targets(world, types_to_include, exclude=(), target_region_names=()):
    one_way_entrances = []
    for pool_type in types_to_include:
        one_way_entrances += world.get_shufflable_entrances(type=pool_type)
    valid_one_way_entrances = list(filter(lambda entrance: entrance.name not in exclude, one_way_entrances))
    if target_region_names:
        return [entrance.get_new_target() for entrance in valid_one_way_entrances
                if entrance.connected_region.name in target_region_names]
    return [entrance.get_new_target() for entrance in valid_one_way_entrances]


#   Abbreviations
#       DMC     Death Mountain Crater
#       DMT     Death Mountain Trail
#       GC      Goron City
#       GF      Gerudo Fortress
#       GS      Gold Skulltula
#       GV      Gerudo Valley
#       HC      Hyrule Castle
#       HF      Hyrule Field
#       KF      Kokiri Forest
#       LH      Lake Hylia
#       LLR     Lon Lon Ranch
#       LW      Lost Woods
#       OGC     Outside Ganon's Castle
#       SFM     Sacred Forest Meadow
#       ToT     Temple of Time
#       ZD      Zora's Domain
#       ZF      Zora's Fountain
#       ZR      Zora's River

entrance_shuffle_table = [
    ('Ganon',           ('Ganons Castle Tower -> Ganons Boss Room',                         {'index':0x041F}),
                        ('Ganons Boss Room -> Ganons Castle Tower',                         {'index':0x534})),
    ('Dungeon',         ('KF Outside Deku Tree -> Deku Tree Lobby',                         { 'index': 0x0000 }),
                        ('Deku Tree Lobby -> KF Outside Deku Tree',                         { 'index': 0x0209, 'blue_warp': 0x0457 })),
    ('Dungeon',         ('Death Mountain -> Dodongos Cavern Beginning',                     { 'index': 0x0004 }),
                        ('Dodongos Cavern Beginning -> Death Mountain',                     { 'index': 0x0242, 'blue_warp': 0x047A })),
    ('Dungeon',         ('Zoras Fountain -> Jabu Jabus Belly Beginning',                    { 'index': 0x0028 }),
                        ('Jabu Jabus Belly Beginning -> Zoras Fountain',                    { 'index': 0x0221, 'blue_warp': 0x010E })),
    ('Dungeon',         ('SFM Forest Temple Entrance Ledge -> Forest Temple Lobby',         { 'index': 0x0169 }),
                        ('Forest Temple Lobby -> SFM Forest Temple Entrance Ledge',         { 'index': 0x0215, 'blue_warp': 0x0608 })),
    ('Dungeon',         ('DMC Fire Temple Entrance -> Fire Temple Lower',                   { 'index': 0x0165 }),
                        ('Fire Temple Lower -> DMC Fire Temple Entrance',                   { 'index': 0x024A, 'blue_warp': 0x0564 })),
    ('Dungeon',         ('Lake Hylia -> Water Temple Lobby',                                { 'index': 0x0010 }),
                        ('Water Temple Lobby -> Lake Hylia',                                { 'index': 0x021D, 'blue_warp': 0x060C })),
    ('Dungeon',         ('Desert Colossus -> Spirit Temple Lobby',                          { 'index': 0x0082 }),
                        ('Spirit Temple Lobby -> Desert Colossus From Spirit Lobby',        { 'index': 0x01E1, 'blue_warp': 0x0610 })),
    ('Dungeon',         ('Graveyard Warp Pad Region -> Shadow Temple Entryway',             { 'index': 0x0037 }),
                        ('Shadow Temple Entryway -> Graveyard Warp Pad Region',             { 'index': 0x0205, 'blue_warp': 0x0580 })),
    ('Dungeon',         ('Kakariko Village -> Bottom of the Well',                          { 'index': 0x0098 }),
                        ('Bottom of the Well -> Kakariko Village',                          { 'index': 0x02A6 })),
    ('Dungeon',         ('ZF Ice Ledge -> Ice Cavern Beginning',                            { 'index': 0x0088 }),
                        ('Ice Cavern Beginning -> ZF Ice Ledge',                            { 'index': 0x03D4 })),
    ('Dungeon',         ('Gerudo Fortress -> Gerudo Training Ground Lobby',                 { 'index': 0x0008 }),
                        ('Gerudo Training Ground Lobby -> Gerudo Fortress',                 { 'index': 0x03A8 })),
    ('Ganon Dungeon',   ('Ganons Castle Grounds -> Ganons Castle Lobby',                    { 'index': 0x0467 }),
                        ('Ganons Castle Lobby -> Ganons Castle Grounds',                    { 'index': 0x023D, 'blue_warp':0x043F }),
                        ('Ganons Castle Lobby -> Castle Grounds',                           { 'index': 0x023F, 'blue_warp':0x023F })),
    ('Ganon Interior',  ('Ganons Castle Lobby -> Ganons Castle Tower',                      { 'index': 0x041B }),
                        ('Ganons Castle Tower -> Ganons Castle Lobby',                      { 'index': 0x0534 })),

    ('Interior',        ('Kokiri Forest -> KF Midos House',                                 { 'index': 0x0433 }),
                        ('KF Midos House -> Kokiri Forest',                                 { 'index': 0x0443 })),
    ('Interior',        ('Kokiri Forest -> KF Sarias House',                                { 'index': 0x0437 }),
                        ('KF Sarias House -> Kokiri Forest',                                { 'index': 0x0447 })),
    ('Interior',        ('Kokiri Forest -> KF House of Twins',                              { 'index': 0x009C }),
                        ('KF House of Twins -> Kokiri Forest',                              { 'index': 0x033C })),
    ('Interior',        ('Kokiri Forest -> KF Know It All House',                           { 'index': 0x00C9 }),
                        ('KF Know It All House -> Kokiri Forest',                           { 'index': 0x026A })),
    ('Interior',        ('Kokiri Forest -> KF Kokiri Shop',                                 { 'index': 0x00C1 }),
                        ('KF Kokiri Shop -> Kokiri Forest',                                 { 'index': 0x0266 })),
    ('Interior',        ('Lake Hylia -> LH Lab',                                            { 'index': 0x0043 }),
                        ('LH Lab -> Lake Hylia',                                            { 'index': 0x03CC })),
    ('Interior',        ('LH Fishing Island -> LH Fishing Hole',                            { 'index': 0x045F }),
                        ('LH Fishing Hole -> LH Fishing Island',                            { 'index': 0x0309 })),
    ('Interior',        ('GV Fortress Side -> GV Carpenter Tent',                           { 'index': 0x03A0 }),
                        ('GV Carpenter Tent -> GV Fortress Side',                           { 'index': 0x03D0 })),
    ('Interior',        ('Market Entrance -> Market Guard House',                           { 'index': 0x007E }),
                        ('Market Guard House -> Market Entrance',                           { 'index': 0x026E })),
    ('Interior',        ('Market -> Market Mask Shop',                                      { 'index': 0x0530 }),
                        ('Market Mask Shop -> Market',                                      { 'index': 0x01D1, 'addresses': [0xC6DA5E] })),
    ('Interior',        ('Market -> Market Bombchu Bowling',                                { 'index': 0x0507 }),
                        ('Market Bombchu Bowling -> Market',                                { 'index': 0x03BC })),
    ('Interior',        ('Market -> Market Potion Shop',                                    { 'index': 0x0388 }),
                        ('Market Potion Shop -> Market',                                    { 'index': 0x02A2 })),
    ('Interior',        ('Market -> Market Treasure Chest Game',                            { 'index': 0x0063 }),
                        ('Market Treasure Chest Game -> Market',                            { 'index': 0x01D5 })),
    ('Interior',        ('Market Back Alley -> Market Bombchu Shop',                        { 'index': 0x0528 }),
                        ('Market Bombchu Shop -> Market Back Alley',                        { 'index': 0x03C0 })),
    ('Interior',        ('Market Back Alley -> Market Man in Green House',                  { 'index': 0x043B }),
                        ('Market Man in Green House -> Market Back Alley',                  { 'index': 0x0067 })),
    ('Interior',        ('Kakariko Village -> Kak Carpenter Boss House',                    { 'index': 0x02FD }),
                        ('Kak Carpenter Boss House -> Kakariko Village',                    { 'index': 0x0349 })),
    ('Interior',        ('Kakariko Village -> Kak House of Skulltula',                      { 'index': 0x0550 }),
                        ('Kak House of Skulltula -> Kakariko Village',                      { 'index': 0x04EE })),
    ('Interior',        ('Kakariko Village -> Kak Impas House',                             { 'index': 0x039C }),
                        ('Kak Impas House -> Kakariko Village',                             { 'index': 0x0345 })),
    ('Interior',        ('Kak Impas Ledge -> Kak Impas House Back',                         { 'index': 0x05C8 }),
                        ('Kak Impas House Back -> Kak Impas Ledge',                         { 'index': 0x05DC })),
    ('Interior',        ('Kak Backyard -> Kak Odd Medicine Building',                       { 'index': 0x0072 }),
                        ('Kak Odd Medicine Building -> Kak Backyard',                       { 'index': 0x034D })),
    ('Interior',        ('Graveyard -> Graveyard Dampes House',                             { 'index': 0x030D }),
                        ('Graveyard Dampes House -> Graveyard',                             { 'index': 0x0355 })),
    ('Interior',        ('Goron City -> GC Shop',                                           { 'index': 0x037C }),
                        ('GC Shop -> Goron City',                                           { 'index': 0x03FC })),
    ('Interior',        ('Zoras Domain -> ZD Shop',                                         { 'index': 0x0380 }),
                        ('ZD Shop -> Zoras Domain',                                         { 'index': 0x03C4 })),
    ('Interior',        ('Lon Lon Ranch -> LLR Talons House',                               { 'index': 0x004F }),
                        ('LLR Talons House -> Lon Lon Ranch',                               { 'index': 0x0378 })),
    ('Interior',        ('Lon Lon Ranch -> LLR Stables',                                    { 'index': 0x02F9 }),
                        ('LLR Stables -> Lon Lon Ranch',                                    { 'index': 0x042F })),
    ('Interior',        ('Lon Lon Ranch -> LLR Tower',                                      { 'index': 0x05D0 }),
                        ('LLR Tower -> Lon Lon Ranch',                                      { 'index': 0x05D4 })),
    ('Interior',        ('Market -> Market Bazaar',                                         { 'index': 0x052C }),
                        ('Market Bazaar -> Market',                                         { 'index': 0x03B8, 'addresses': [0xBEFD74] })),
    ('Interior',        ('Market -> Market Shooting Gallery',                               { 'index': 0x016D }),
                        ('Market Shooting Gallery -> Market',                               { 'index': 0x01CD, 'addresses': [0xBEFD7C] })),
    ('Interior',        ('Kakariko Village -> Kak Bazaar',                                  { 'index': 0x00B7 }),
                        ('Kak Bazaar -> Kakariko Village',                                  { 'index': 0x0201, 'addresses': [0xBEFD72] })),
    ('Interior',        ('Kakariko Village -> Kak Shooting Gallery',                        { 'index': 0x003B }),
                        ('Kak Shooting Gallery -> Kakariko Village',                        { 'index': 0x0463, 'addresses': [0xBEFD7A] })),
    ('Interior',        ('Desert Colossus -> Colossus Great Fairy Fountain',                { 'index': 0x0588 }),
                        ('Colossus Great Fairy Fountain -> Desert Colossus',                { 'index': 0x057C, 'addresses': [0xBEFD82] })),
    ('Interior',        ('Hyrule Castle Grounds -> HC Great Fairy Fountain',                { 'index': 0x0578 }),
                        ('HC Great Fairy Fountain -> Castle Grounds',                       { 'index': 0x0340, 'addresses': [0xBEFD80] })),
    ('Interior',        ('Ganons Castle Grounds -> OGC Great Fairy Fountain',               { 'index': 0x04C2 }),
                        ('OGC Great Fairy Fountain -> Castle Grounds',                      { 'index': 0x0340, 'addresses': [0xBEFD6C] })),
    ('Interior',        ('DMC Lower Nearby -> DMC Great Fairy Fountain',                    { 'index': 0x04BE }),
                        ('DMC Great Fairy Fountain -> DMC Lower Local',                     { 'index': 0x0482, 'addresses': [0xBEFD6A] })),
    ('Interior',        ('Death Mountain Summit -> DMT Great Fairy Fountain',               { 'index': 0x0315 }),
                        ('DMT Great Fairy Fountain -> Death Mountain Summit',               { 'index': 0x045B, 'addresses': [0xBEFD68] })),
    ('Interior',        ('Zoras Fountain -> ZF Great Fairy Fountain',                       { 'index': 0x0371 }),
                        ('ZF Great Fairy Fountain -> Zoras Fountain',                       { 'index': 0x0394, 'addresses': [0xBEFD7E] })),

    ('SpecialInterior', ('Kokiri Forest -> KF Links House',                                 { 'index': 0x0272 }),
                        ('KF Links House -> Kokiri Forest',                                 { 'index': 0x0211 })),
    ('SpecialInterior', ('ToT Entrance -> Temple of Time',                                  { 'index': 0x0053 }),
                        ('Temple of Time -> ToT Entrance',                                  { 'index': 0x0472 })),
    ('SpecialInterior', ('Kakariko Village -> Kak Windmill',                                { 'index': 0x0453 }),
                        ('Kak Windmill -> Kakariko Village',                                { 'index': 0x0351 })),
    ('SpecialInterior', ('Kakariko Village -> Kak Potion Shop Front',                       { 'index': 0x0384 }),
                        ('Kak Potion Shop Front -> Kakariko Village',                       { 'index': 0x044B })),
    ('SpecialInterior', ('Kak Backyard -> Kak Potion Shop Back',                            { 'index': 0x03EC }),
                        ('Kak Potion Shop Back -> Kak Backyard',                            { 'index': 0x04FF })),

    ('Grotto',          ('Desert Colossus -> Colossus Grotto',                              { 'grotto_id': 0x00, "actor_id": 0x00FD, 'entrance': 0x05BC, 'content': 0xFD, 'scene': 0x5C, 'req': 'open'}),
                        ('Colossus Grotto -> Desert Colossus',                              { 'grotto_id': 0x00, "actor_id": 0x00FD, 'entrance': 0x0123, 'room': 0x00, 'angle': 0xA71C, 'pos': (0x427A0800, 0xC2000000, 0xC4A20666) })),
    ('Grotto',          ('Lake Hylia -> LH Grotto',                                         { 'grotto_id': 0x01, "actor_id": 0x00EF, 'entrance': 0x05A4, 'content': 0xEF, 'scene': 0x57, 'req': 'open'}),
                        ('LH Grotto -> Lake Hylia',                                         { 'grotto_id': 0x01, "actor_id": 0x00EF, 'entrance': 0x0102, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC53DF56A, 0xC4812000, 0x45BE05F2) })),
    ('Grotto',          ('Zora River -> ZR Storms Grotto',                                  { 'grotto_id': 0x02, "actor_id": 0x01EB, 'entrance': 0x05BC, 'content': 0xEB, 'scene': 0x54, 'req': 'storms'}),
                        ('ZR Storms Grotto -> Zora River',                                  { 'grotto_id': 0x02, "actor_id": 0x01EB, 'entrance': 0x00EA, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC4CBC1B4, 0x42C80000, 0xC3041ABE) })),
    ('Grotto',          ('Zora River -> ZR Fairy Grotto',                                   { 'grotto_id': 0x03, "actor_id": 0x10E6, 'entrance': 0x036D, 'content': 0xE6, 'scene': 0x54, 'req': 'open'}),
                        ('ZR Fairy Grotto -> Zora River',                                   { 'grotto_id': 0x03, "actor_id": 0x10E6, 'entrance': 0x00EA, 'room': 0x00, 'angle': 0xE000, 'pos': (0x4427A070, 0x440E8000, 0xC3B4ED3B) })),
    ('Grotto',          ('Zora River -> ZR Open Grotto',                                    { 'grotto_id': 0x04, "actor_id": 0x0029, 'entrance': 0x003F, 'content': 0x29, 'scene': 0x54, 'req': 'open'}),
                        ('ZR Open Grotto -> Zora River',                                    { 'grotto_id': 0x04, "actor_id": 0x0029, 'entrance': 0x00EA, 'room': 0x00, 'angle': 0x8000, 'pos': (0x43B52520, 0x440E8000, 0x4309A14F) })),
    ('Grotto',          ('DMC Lower Nearby -> DMC Hammer Grotto',                           { 'grotto_id': 0x05, "actor_id": 0x00F9, 'entrance': 0x05A4, 'content': 0xF9, 'scene': 0x61, 'req': 'open'}),
                        ('DMC Hammer Grotto -> DMC Lower Local',                            { 'grotto_id': 0x05, "actor_id": 0x00F9, 'entrance': 0x0246, 'room': 0x01, 'angle': 0x31C7, 'pos': (0xC4D290C0, 0x44348000, 0xC3ED5557) })),
    ('Grotto',          ('DMC Upper Nearby -> DMC Upper Grotto',                            { 'grotto_id': 0x06, "actor_id": 0x007A, 'entrance': 0x003F, 'content': 0x7A, 'scene': 0x61, 'req': 'open'}),
                        ('DMC Upper Grotto -> DMC Upper Local',                             { 'grotto_id': 0x06, "actor_id": 0x007A, 'entrance': 0x0147, 'room': 0x01, 'angle': 0x238E, 'pos': (0x420F3401, 0x449E2000, 0x44DCD549) })),
    ('Grotto',          ('GC Grotto Platform -> GC Grotto',                                 { 'grotto_id': 0x07, "actor_id": 0x00FB, 'entrance': 0x05A4, 'content': 0xFB, 'scene': 0x62, 'req': 'open'}),
                        ('GC Grotto -> GC Grotto Platform',                                 { 'grotto_id': 0x07, "actor_id": 0x00FB, 'entrance': 0x014D, 'room': 0x03, 'angle': 0x0000, 'pos': (0x448A1754, 0x44110000, 0xC493CCFD) })),
    ('Grotto',          ('Death Mountain -> DMT Storms Grotto',                             { 'grotto_id': 0x08, "actor_id": 0x0157, 'entrance': 0x003F, 'content': 0x57, 'scene': 0x60, 'req': 'storms'}),
                        ('DMT Storms Grotto -> Death Mountain',                             { 'grotto_id': 0x08, "actor_id": 0x0157, 'entrance': 0x01B9, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC3C1CAC1, 0x44AD4000, 0xC497A1BA) })),
    ('Grotto',          ('Death Mountain Summit -> DMT Cow Grotto',                         { 'grotto_id': 0x09, "actor_id": 0x00F8, 'entrance': 0x05FC, 'content': 0xF8, 'scene': 0x60, 'req': 'open'}),
                        ('DMT Cow Grotto -> Death Mountain Summit',                         { 'grotto_id': 0x09, "actor_id": 0x00F8, 'entrance': 0x01B9, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC42CC164, 0x44F34000, 0xC38CFC0C) })),
    ('Grotto',          ('Kak Backyard -> Kak Open Grotto',                                 { 'grotto_id': 0x0A, "actor_id": 0x0028, 'entrance': 0x003F, 'content': 0x28, 'scene': 0x52, 'req': 'open'}),
                        ('Kak Open Grotto -> Kak Backyard',                                 { 'grotto_id': 0x0A, "actor_id": 0x0028, 'entrance': 0x00DB, 'room': 0x00, 'angle': 0x0000, 'pos': (0x4455CF3B, 0x42A00000, 0xC37D1871) })),
    ('Grotto',          ('Kakariko Village -> Kak Redead Grotto',                           { 'grotto_id': 0x0B, "actor_id": 0x02E7, 'entrance': 0x05A0, 'content': 0xE7, 'scene': 0x52, 'req': 'hit'}),
                        ('Kak Redead Grotto -> Kakariko Village',                           { 'grotto_id': 0x0B, "actor_id": 0x02E7, 'entrance': 0x00DB, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC3C8EFCE, 0x00000000, 0x43C96551) })),
    ('Grotto',          ('Hyrule Castle Grounds -> HC Storms Grotto',                       { 'grotto_id': 0x0C, "actor_id": 0x01F6, 'entrance': 0x05B8, 'content': 0xF6, 'scene': 0x5F, 'req': 'storms'}),
                        ('HC Storms Grotto -> Castle Grounds',                              { 'grotto_id': 0x0C, "actor_id": 0x01F6, 'entrance': 0x0138, 'room': 0x00, 'angle': 0x9555, 'pos': (0x447C4104, 0x44C46000, 0x4455E211) })),
    ('Grotto',          ('Hyrule Field -> HF Tektite Grotto',                               { 'grotto_id': 0x0D, "actor_id": 0x02E1, 'entrance': 0x05C0, 'content': 0xE1, 'scene': 0x51, 'req': 'hit'}),
                        ('HF Tektite Grotto -> Hyrule Field',                               { 'grotto_id': 0x0D, "actor_id": 0x02E1, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x1555, 'pos': (0xC59AACA0, 0xC3960000, 0x45315966) })),
    ('Grotto',          ('Hyrule Field -> HF Near Kak Grotto',                              { 'grotto_id': 0x0E, "actor_id": 0x02E5, 'entrance': 0x0598, 'content': 0xE5, 'scene': 0x51, 'req': 'hit'}),
                        ('HF Near Kak Grotto -> Hyrule Field',                              { 'grotto_id': 0x0E, "actor_id": 0x02E5, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0xC000, 'pos': (0x4500299B, 0x41A00000, 0xC32065BD) })),
    ('Grotto',          ('Hyrule Field -> HF Fairy Grotto',                                 { 'grotto_id': 0x0F, "actor_id": 0x10FF, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x51, 'req': 'open'}),
                        ('HF Fairy Grotto -> Hyrule Field',                                 { 'grotto_id': 0x0F, "actor_id": 0x10FF, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC58B2544, 0xC3960000, 0xC3D5186B) })),
    ('Grotto',          ('Hyrule Field -> HF Near Market Grotto',                           { 'grotto_id': 0x10, "actor_id": 0x0000, 'entrance': 0x003F, 'content': 0x00, 'scene': 0x51, 'req': 'open'}),
                        ('HF Near Market Grotto -> Hyrule Field',                           { 'grotto_id': 0x10, "actor_id": 0x0000, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0xE000, 'pos': (0xC4B2B1F3, 0x00000000, 0x444C719D) })),
    ('Grotto',          ('Hyrule Field -> HF Cow Grotto',                                   { 'grotto_id': 0x11, "actor_id": 0x02E4, 'entrance': 0x05A8, 'content': 0xE4, 'scene': 0x51, 'req': 'hit'}),
                        ('HF Cow Grotto -> Hyrule Field',                                   { 'grotto_id': 0x11, "actor_id": 0x02E4, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC5F61086, 0xC3960000, 0x45D84A7E) })),
    ('Grotto',          ('Hyrule Field -> HF Inside Fence Grotto',                          { 'grotto_id': 0x12, "actor_id": 0x02E6, 'entrance': 0x059C, 'content': 0xE6, 'scene': 0x51, 'req': 'hit'}),
                        ('HF Inside Fence Grotto -> Hyrule Field',                          { 'grotto_id': 0x12, "actor_id": 0x02E6, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0xEAAB, 'pos': (0xC59BE902, 0xC42F0000, 0x4657F479) })),
    ('Grotto',          ('Hyrule Field -> HF Open Grotto',                                  { 'grotto_id': 0x13, "actor_id": 0x0022, 'entrance': 0x003F, 'content': 0x03, 'scene': 0x51, 'req': 'open'}),
                        ('HF Open Grotto -> Hyrule Field',                                  { 'grotto_id': 0x13, "actor_id": 0x0022, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC57B69B1, 0xC42F0000, 0x46588DF2) })),
    ('Grotto',          ('Hyrule Field -> HF Southeast Grotto',                             { 'grotto_id': 0x14, "actor_id": 0x0003, 'entrance': 0x003F, 'content': 0x22, 'scene': 0x51, 'req': 'open'}),
                        ('HF Southeast Grotto -> Hyrule Field',                             { 'grotto_id': 0x14, "actor_id": 0x0003, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x9555, 'pos': (0xC384A807, 0xC3FA0000, 0x4640DCC8) })),
    ('Grotto',          ('Lon Lon Ranch -> LLR Grotto',                                     { 'grotto_id': 0x15, "actor_id": 0x00FC, 'entrance': 0x05A4, 'content': 0xFC, 'scene': 0x63, 'req': 'open'}),
                        ('LLR Grotto -> Lon Lon Ranch',                                     { 'grotto_id': 0x15, "actor_id": 0x00FC, 'entrance': 0x0157, 'room': 0x00, 'angle': 0xAAAB, 'pos': (0x44E0FD92, 0x00000000, 0x44BB9A4C) })),
    ('Grotto',          ('SFM Entryway -> SFM Wolfos Grotto',                               { 'grotto_id': 0x16, "actor_id": 0x02ED, 'entrance': 0x05B4, 'content': 0xED, 'scene': 0x56, 'req': 'hit'}),
                        ('SFM Wolfos Grotto -> SFM Entryway',                               { 'grotto_id': 0x16, "actor_id": 0x02ED, 'entrance': 0x00FC, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC33DDC64, 0x00000000, 0x44ED42CE) })),
    ('Grotto',          ('Sacred Forest Meadow -> SFM Storms Grotto',                       { 'grotto_id': 0x17, "actor_id": 0x01EE, 'entrance': 0x05BC, 'content': 0xEE, 'scene': 0x56, 'req': 'storms'}),
                        ('SFM Storms Grotto -> Sacred Forest Meadow',                       { 'grotto_id': 0x17, "actor_id": 0x01EE, 'entrance': 0x00FC, 'room': 0x00, 'angle': 0xAAAB, 'pos': (0x439D6D22, 0x43F00000, 0xC50FC63A) })),
    ('Grotto',          ('Sacred Forest Meadow -> SFM Fairy Grotto',                        { 'grotto_id': 0x18, "actor_id": 0x10FF, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x56, 'req': 'open'}),
                        ('SFM Fairy Grotto -> Sacred Forest Meadow',                        { 'grotto_id': 0x18, "actor_id": 0x10FF, 'entrance': 0x00FC, 'room': 0x00, 'angle': 0x0000, 'pos': (0x425C22D1, 0x00000000, 0x434E9835) })),
    ('Grotto',          ('LW Beyond Mido -> LW Scrubs Grotto',                              { 'grotto_id': 0x19, "actor_id": 0x00F5, 'entrance': 0x05B0, 'content': 0xF5, 'scene': 0x5B, 'req': 'open'}),
                        ('LW Scrubs Grotto -> LW Beyond Mido',                              { 'grotto_id': 0x19, "actor_id": 0x00F5, 'entrance': 0x01A9, 'room': 0x08, 'angle': 0x2000, 'pos': (0x44293FA2, 0x00000000, 0xC51DE32B) })),
    ('Grotto',          ('Lost Woods -> LW Near Shortcuts Grotto',                          { 'grotto_id': 0x1A, "actor_id": 0x0014, 'entrance': 0x003F, 'content': 0x14, 'scene': 0x5B, 'req': 'open'}),
                        ('LW Near Shortcuts Grotto -> Lost Woods',                          { 'grotto_id': 0x1A, "actor_id": 0x0014, 'entrance': 0x011E, 'room': 0x02, 'angle': 0xE000, 'pos': (0x4464B055, 0x00000000, 0xC464DB7D) })),
    ('Grotto',          ('Kokiri Forest -> KF Storms Grotto',                               { 'grotto_id': 0x1B, "actor_id": 0x012C, 'entrance': 0x003F, 'content': 0x2C, 'scene': 0x55, 'req': 'storms'}),
                        ('KF Storms Grotto -> Kokiri Forest',                               { 'grotto_id': 0x1B, "actor_id": 0x012C, 'entrance': 0x0286, 'room': 0x00, 'angle': 0x4000, 'pos': (0xC3FD8856, 0x43BE0000, 0xC4988DA8) })),
    ('Grotto',          ('Zoras Domain -> ZD Storms Grotto',                                { 'grotto_id': 0x1C, "actor_id": 0x11FF, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x58, 'req': 'storms'}),
                        ('ZD Storms Grotto -> Zoras Domain',                                { 'grotto_id': 0x1C, "actor_id": 0x11FF, 'entrance': 0x0108, 'room': 0x01, 'angle': 0xD555, 'pos': (0xC455EB8D, 0x41600000, 0xC3ED3602) })),
    ('Grotto',          ('Gerudo Fortress -> GF Storms Grotto',                             { 'grotto_id': 0x1D, "actor_id": 0x11FF, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x5D, 'req': 'storms'}),
                        ('GF Storms Grotto -> Gerudo Fortress',                             { 'grotto_id': 0x1D, "actor_id": 0x11FF, 'entrance': 0x0129, 'room': 0x00, 'angle': 0x4000, 'pos': (0x43BE42C0, 0x43A68000, 0xC4C317B1) })),
    ('Grotto',          ('GV Fortress Side -> GV Storms Grotto',                            { 'grotto_id': 0x1E, "actor_id": 0x01F0, 'entrance': 0x05BC, 'content': 0xF0, 'scene': 0x5A, 'req': 'storms'}),
                        ('GV Storms Grotto -> GV Fortress Side',                            { 'grotto_id': 0x1E, "actor_id": 0x01F0, 'entrance': 0x022D, 'room': 0x00, 'angle': 0x9555, 'pos': (0xC4A5CAD2, 0x41700000, 0xC475FF9B) })),
    ('Grotto',          ('GV Grotto Ledge -> GV Octorok Grotto',                            { 'grotto_id': 0x1F, "actor_id": 0x00F2, 'entrance': 0x05AC, 'content': 0xF2, 'scene': 0x5A, 'req': 'open'}),
                        ('GV Octorok Grotto -> GV Grotto Ledge',                            { 'grotto_id': 0x1F, "actor_id": 0x00F2, 'entrance': 0x0117, 'room': 0x00, 'angle': 0x8000, 'pos': (0x4391C1A4, 0xC40AC000, 0x44B8CC9B) })),
    ('Grotto',          ('LW Beyond Mido -> Deku Theater',                                  { 'grotto_id': 0x20, "actor_id": 0x00F3, 'entrance': 0x05C4, 'content': 0xF3, 'scene': 0x5B, 'req': 'open'}),
                        ('Deku Theater -> LW Beyond Mido',                                  { 'grotto_id': 0x20, "actor_id": 0x00F3, 'entrance': 0x01A9, 'room': 0x06, 'angle': 0x4000, 'pos': (0x42AA8FDA, 0xC1A00000, 0xC4C82D49) })),

    ('Grave',           ('Graveyard -> Graveyard Shield Grave',                             { 'index': 0x004B }),
                        ('Graveyard Shield Grave -> Graveyard',                             { 'index': 0x035D })),
    ('Grave',           ('Graveyard -> Graveyard Heart Piece Grave',                        { 'index': 0x031C }),
                        ('Graveyard Heart Piece Grave -> Graveyard',                        { 'index': 0x0361 })),
    ('Grave',           ('Graveyard -> Graveyard Royal Familys Tomb',                       { 'index': 0x002D }),
                        ('Graveyard Royal Familys Tomb -> Graveyard',                       { 'index': 0x050B })),
    ('Grave',           ('Graveyard -> Graveyard Dampes Grave',                             { 'index': 0x044F }),
                        ('Graveyard Dampes Grave -> Graveyard',                             { 'index': 0x0359 })),

    ('Overworld',       ('Kokiri Forest -> LW Bridge From Forest',                          { 'index': 0x05E0 }),
                        ('LW Bridge -> Kokiri Forest',                                      { 'index': 0x020D })),
    ('Overworld',       ('Kokiri Forest -> Lost Woods',                                     { 'index': 0x011E }),
                        ('LW Forest Exit -> Kokiri Forest',                                 { 'index': 0x0286 })),
    ('Overworld',       ('Lost Woods -> GC Woods Warp',                                     { 'index': 0x04E2 }),
                        ('GC Woods Warp -> Lost Woods',                                     { 'index': 0x04D6 })),
    ('Overworld',       ('Lost Woods -> Zora River',                                        { 'index': 0x01DD }),
                        ('Zora River -> Lost Woods',                                        { 'index': 0x04DA })),
    ('Overworld',       ('LW Beyond Mido -> SFM Entryway',                                  { 'index': 0x00FC }),
                        ('SFM Entryway -> LW Beyond Mido',                                  { 'index': 0x01A9 })),
    ('Overworld',       ('LW Bridge -> Hyrule Field',                                       { 'index': 0x0185 }),
                        ('Hyrule Field -> LW Bridge',                                       { 'index': 0x04DE })),
    ('Overworld',       ('Hyrule Field -> Lake Hylia',                                      { 'index': 0x0102 }),
                        ('Lake Hylia -> Hyrule Field',                                      { 'index': 0x0189 })),
    ('Overworld',       ('Hyrule Field -> Gerudo Valley',                                   { 'index': 0x0117 }),
                        ('Gerudo Valley -> Hyrule Field',                                   { 'index': 0x018D })),
    ('Overworld',       ('Hyrule Field -> Market Entrance',                                 { 'index': 0x0276 }),
                        ('Market Entrance -> Hyrule Field',                                 { 'index': 0x01FD })),
    ('Overworld',       ('Hyrule Field -> Kakariko Village',                                { 'index': 0x00DB }),
                        ('Kakariko Village -> Hyrule Field',                                { 'index': 0x017D })),
    ('Overworld',       ('Hyrule Field -> ZR Front',                                        { 'index': 0x00EA }),
                        ('ZR Front -> Hyrule Field',                                        { 'index': 0x0181 })),
    ('Overworld',       ('Hyrule Field -> Lon Lon Ranch',                                   { 'index': 0x0157 }),
                        ('Lon Lon Ranch -> Hyrule Field',                                   { 'index': 0x01F9 })),
    ('Overworld',       ('Lake Hylia -> Zoras Domain',                                      { 'index': 0x0328 }),
                        ('Zoras Domain -> Lake Hylia',                                      { 'index': 0x0560 })),
    ('Overworld',       ('GV Fortress Side -> Gerudo Fortress',                             { 'index': 0x0129 }),
                        ('Gerudo Fortress -> GV Fortress Side',                             { 'index': 0x022D })),
    ('Overworld',       ('GF Outside Gate -> Wasteland Near Fortress',                      { 'index': 0x0130 }),
                        ('Wasteland Near Fortress -> GF Outside Gate',                      { 'index': 0x03AC })),
    ('Overworld',       ('Wasteland Near Colossus -> Desert Colossus',                      { 'index': 0x0123 }),
                        ('Desert Colossus -> Wasteland Near Colossus',                      { 'index': 0x0365 })),
    ('Overworld',       ('Market Entrance -> Market',                                       { 'index': 0x00B1 }),
                        ('Market -> Market Entrance',                                       { 'index': 0x0033 })),
    ('Overworld',       ('Market -> Castle Grounds',                                        { 'index': 0x0138 }),
                        ('Castle Grounds -> Market',                                        { 'index': 0x025A })),
    ('Overworld',       ('Market -> ToT Entrance',                                          { 'index': 0x0171 }),
                        ('ToT Entrance -> Market',                                          { 'index': 0x025E })),
    ('Overworld',       ('Kakariko Village -> Graveyard',                                   { 'index': 0x00E4 }),
                        ('Graveyard -> Kakariko Village',                                   { 'index': 0x0195 })),
    ('Overworld',       ('Kak Behind Gate -> Death Mountain',                               { 'index': 0x013D }),
                        ('Death Mountain -> Kak Behind Gate',                               { 'index': 0x0191 })),
    ('Overworld',       ('Death Mountain -> Goron City',                                    { 'index': 0x014D }),
                        ('Goron City -> Death Mountain',                                    { 'index': 0x01B9 })),
    ('Overworld',       ('GC Darunias Chamber -> DMC Lower Local',                          { 'index': 0x0246 }),
                        ('DMC Lower Nearby -> GC Darunias Chamber',                         { 'index': 0x01C1 })),
    ('Overworld',       ('Death Mountain Summit -> DMC Upper Local',                        { 'index': 0x0147 }),
                        ('DMC Upper Nearby -> Death Mountain Summit',                       { 'index': 0x01BD })),
    ('Overworld',       ('ZR Behind Waterfall -> Zoras Domain',                             { 'index': 0x0108 }),
                        ('Zoras Domain -> ZR Behind Waterfall',                             { 'index': 0x019D })),
    ('Overworld',       ('ZD Behind King Zora -> Zoras Fountain',                           { 'index': 0x0225 }),
                        ('Zoras Fountain -> ZD Behind King Zora',                           { 'index': 0x01A1 })),

    ('Overworld',       ('GV Lower Stream -> Lake Hylia',                                   { 'index': 0x0219 })),

    ('OwlDrop',         ('LH Owl Flight -> Hyrule Field',                                   { 'index': 0x027E, 'addresses': [0xAC9F26] })),
    ('OwlDrop',         ('DMT Owl Flight -> Kak Impas Rooftop',                             { 'index': 0x0554, 'addresses': [0xAC9EF2] })),

    ('Spawn',           ('Child Spawn -> KF Links House',                                   { 'index': 0x00BB, 'addresses': [0xB06342] })),
    ('Spawn',           ('Adult Spawn -> Temple of Time',                                   { 'index': 0x05F4, 'addresses': [0xB06332] })),

    ('WarpSong',        ('Minuet of Forest Warp -> Sacred Forest Meadow',                   { 'index': 0x0600, 'addresses': [0xBF023C] })),
    ('WarpSong',        ('Bolero of Fire Warp -> DMC Central Local',                        { 'index': 0x04F6, 'addresses': [0xBF023E] })),
    ('WarpSong',        ('Serenade of Water Warp -> Lake Hylia',                            { 'index': 0x0604, 'addresses': [0xBF0240] })),
    ('WarpSong',        ('Requiem of Spirit Warp -> Desert Colossus',                       { 'index': 0x01F1, 'addresses': [0xBF0242] })),
    ('WarpSong',        ('Nocturne of Shadow Warp -> Graveyard Warp Pad Region',            { 'index': 0x0568, 'addresses': [0xBF0244] })),
    ('WarpSong',        ('Prelude of Light Warp -> Temple of Time',                         { 'index': 0x05F4, 'addresses': [0xBF0246] })),

    ('Extra',           ('ZD Eyeball Frog Timeout -> Zoras Domain',                         { 'index': 0x0153 })),
    ('Extra',           ('ZR Top of Waterfall -> Zora River',                               { 'index': 0x0199 })),
]

def _add_boss_entrances():
    # Compute this at load time to save a lot of duplication
    dungeon_data = {}
    for type, forward, *reverse in entrance_shuffle_table:
        if type != 'Dungeon' and type != 'Ganon Dungeon':
            continue
        if not reverse:
            continue
        name, forward = forward
        reverse = reverse[0][1]
        if 'blue_warp' not in reverse:
            continue
        dungeon_data[name] = {
            'dungeon_index': forward['index'],
            'exit_index': reverse['index'],
            'exit_blue_warp': reverse['blue_warp']
        }

    for type, source, target, boss, dungeon, index, rindex, addresses in [
        (
            'ChildBoss', 'Deku Tree Boss Door', 'Gohma Boss Room', 'Queen Gohma',
            'KF Outside Deku Tree -> Deku Tree Lobby',
            0x040f, 0x0252, [ 0xB06292, 0xBC6162, 0xBC60AE ]
        ),
        (
            'ChildBoss', 'Dodongos Cavern Boss Door', 'King Dodongo Boss Room', 'King Dodongo',
            'Death Mountain -> Dodongos Cavern Beginning',
            0x040b, 0x00c5, [ 0xB062B6, 0xBC616E ]
        ),
        (
            'ChildBoss', 'Jabu Jabus Belly Boss Door', 'Barinade Boss Room', 'Barinade',
            'Zoras Fountain -> Jabu Jabus Belly Beginning',
            0x0301, 0x0407, [ 0xB062C2, 0xBC60C2 ]
        ),
        (
            'AdultBoss', 'Forest Temple Boss Door', 'Phantom Ganon Boss Room', 'Phantom Ganon',
            'SFM Forest Temple Entrance Ledge -> Forest Temple Lobby',
            0x000c, 0x024E, [ 0xB062CE, 0xBC6182 ]
        ),
        (
            'AdultBoss', 'Fire Temple Boss Door', 'Volvagia Boss Room', 'Volvagia',
            'DMC Fire Temple Entrance -> Fire Temple Lower',
            0x0305, 0x0175, [ 0xB062DA, 0xBC60CE ]
        ),
        (
            'AdultBoss', 'Water Temple Boss Door', 'Morpha Boss Room', 'Morpha',
            'Lake Hylia -> Water Temple Lobby',
            0x0417, 0x0423, [ 0xB062E6, 0xBC6196 ]
        ),
        (
            'AdultBoss', 'Spirit Temple Boss Door', 'Twinrova Boss Room', 'Twinrova',
            'Desert Colossus -> Spirit Temple Lobby',
            0x008D, 0x02F5, [ 0xB062F2, 0xBC6122 ]
        ),
        (
            'AdultBoss', 'Shadow Temple Boss Door', 'Bongo Bongo Boss Room', 'Bongo Bongo',
            'Graveyard Warp Pad Region -> Shadow Temple Entryway',
            0x0413, 0x02B2, [ 0xB062FE, 0xBC61AA ]
        ),
        (
            'Ganon', 'Ganons Castle Tower', 'Ganons Boss Room', 'Ganon',
            'Ganons Castle Grounds -> Ganons Castle Lobby',
            0x041F, 0x534, [0xB0626A, 0xB0630A, 0xBC61B6]
        )
    ]:
        d = {'index': index, 'patch_addresses': addresses, 'boss': boss}
        d.update(dungeon_data[dungeon])
        entrance_shuffle_table.append(
            (type, (f"{source} -> {target}", d), (f"{target} -> {source}", {'index': rindex}))
        )
_add_boss_entrances()

# Basically, the entrances in the list above that go to:
# - DMC Central Local (child access for the bean and skull)
# - Desert Colossus (child access to colossus and spirit)
# - Graveyard Warp Pad Region (access to shadow, plus the gossip stone)
# We will always need to pick one from each list to receive a one-way entrance
# if shuffling warp songs (depending on other settings).
# Table maps: short key -> ([target regions], [allowed types])
priority_entrance_table = {
    'Bolero': (['DMC Central Local'], ['OwlDrop', 'WarpSong']),
    'Nocturne': (['Graveyard Warp Pad Region'], ['OwlDrop', 'Spawn', 'WarpSong']),
    'Requiem': (['Desert Colossus', 'Desert Colossus From Spirit Lobby'], ['OwlDrop', 'Spawn', 'WarpSong']),
}


class EntranceShuffleError(ShuffleError):
    pass


# Set entrances of all worlds, first initializing them to their default regions, then potentially shuffling part of them
def set_entrances(worlds):
    for world in worlds:
        world.initialize_entrances()
        # Set entrance data for all entrances, even those we aren't shuffling
        set_all_entrances_data(world)
        set_grotto_entrances(world)

    if worlds[0].entrance_shuffle:
        shuffle_random_entrances(worlds)
    else:
        for world in worlds:
            set_all_entrances_data(world)

    set_entrances_based_rules(worlds)


# Shuffles entrances that need to be shuffled in all worlds
def shuffle_random_entrances(worlds):

    # Store all locations reachable before shuffling to differentiate which locations were already unreachable from those we made unreachable
    complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]
    max_search = Search.max_explore([world.state for world in worlds], complete_itempool)

    non_drop_locations = [location for world in worlds for location in world.get_locations() if location.type not in ('Drop', 'Event')]
    max_search.visit_locations(non_drop_locations)
    locations_to_ensure_reachable = list(filter(max_search.visited, non_drop_locations))

    # Shuffle all entrances within their own worlds
    for world in worlds:

        # Determine entrance pools based on settings, to be shuffled in the order we set them by
        one_way_entrance_pools = OrderedDict()
        entrance_pools = OrderedDict()
        one_way_priorities = {}

        if worlds[0].settings.owl_drops:
            one_way_entrance_pools['OwlDrop'] = world.get_shufflable_entrances(type='OwlDrop')

        if worlds[0].settings.spawn_positions:
            one_way_entrance_pools['Spawn'] = world.get_shufflable_entrances(type='Spawn')

        if worlds[0].settings.warp_songs:
            one_way_entrance_pools['WarpSong'] = world.get_shufflable_entrances(type='WarpSong')
            if worlds[0].settings.reachable_locations != 'beatable' and worlds[0].settings.logic_rules == 'glitchless':
                # In glitchless, there aren't any other ways to access these areas
                one_way_priorities['Bolero'] = priority_entrance_table['Bolero']
                one_way_priorities['Nocturne'] = priority_entrance_table['Nocturne']
                if not worlds[0].shuffle_dungeon_entrances and not worlds[0].settings.shuffle_overworld_entrances:
                    one_way_priorities['Requiem'] = priority_entrance_table['Requiem']

        elif worlds[0].settings.shuffle_dungeon_bosses == 'limited':
            entrance_pools['ChildBoss'] = world.get_shufflable_entrances(type='ChildBoss', only_primary=True)
            entrance_pools['AdultBoss'] = world.get_shufflable_entrances(type='AdultBoss', only_primary=True)
        if worlds[0].settings.shuffle_dungeon_bosses == 'full':
            entrance_pools['Boss'] = world.get_shufflable_entrances(type='ChildBoss', only_primary=True)
            entrance_pools['Boss'] += world.get_shufflable_entrances(type='AdultBoss', only_primary=True)
        if worlds[0].settings.shuffle_dungeon_bosses == "ganon":
            entrance_pools['Boss'] = world.get_shufflable_entrances(type='ChildBoss', only_primary=True)
            entrance_pools['Boss'] += world.get_shufflable_entrances(type='AdultBoss', only_primary=True)
            entrance_pools['Boss'] += world.get_shufflable_entrances(type='Ganon', only_primary=True)
            # entrance_pools['Boss'].append(world.get_entrance('Ganons Boss Room -> Ganons Castle Tower'))

        if worlds[0].shuffle_dungeon_entrances:
            entrance_pools['Dungeon'] = world.get_shufflable_entrances(type='Dungeon', only_primary=True)
            if worlds[0].settings.shuffle_ganon_castle_entrances == 'separate':
                entrance_pools['Dungeon'].append(world.get_entrance('Ganons Castle Grounds -> Ganons Castle Lobby'))
            if worlds[0].settings.shuffle_ganon_castle_entrances == 'together':
                entrance_pools['Dungeon'].append(world.get_entrance('Ganons Castle Grounds -> Ganons Castle Lobby'))
                entrance_pools['Dungeon'].append(world.get_entrance('Ganons Castle Lobby -> Ganons Castle Tower'))
            # The fill algorithm will already make sure gohma is reachable, however it can end up putting
            # a forest escape via the hands of spirit on Deku leading to Deku on spirit in logic. This is
            # not really a closed forest anymore, so specifically remove Deku Tree from closed forest.
            if worlds[0].settings.open_forest == 'closed':
                entrance_pools['Dungeon'].remove(world.get_entrance('KF Outside Deku Tree -> Deku Tree Lobby'))
            if worlds[0].settings.decouple_entrances:
                entrance_pools['DungeonReverse'] = [entrance.reverse for entrance in entrance_pools['Dungeon']]
        if worlds[0].shuffle_interior_entrances:
            entrance_pools['Interior'] = world.get_shufflable_entrances(type='Interior', only_primary=True)
            if worlds[0].shuffle_special_interior_entrances:
                entrance_pools['Interior'] += world.get_shufflable_entrances(type='SpecialInterior', only_primary=True)
            if worlds[0].settings.shuffle_ganon_castle_entrances == 'separate':
                entrance_pools['Interior'].append(world.get_entrance('Ganons Castle Lobby -> Ganons Castle Tower'))
            if worlds[0].settings.decouple_entrances:
                entrance_pools['InteriorReverse'] = [entrance.reverse for entrance in entrance_pools['Interior']]

        if worlds[0].settings.shuffle_grotto_entrances:
            entrance_pools['GrottoGrave'] = world.get_shufflable_entrances(type='Grotto', only_primary=True)
            entrance_pools['GrottoGrave'] += world.get_shufflable_entrances(type='Grave', only_primary=True)
            if worlds[0].settings.decouple_entrances:
                entrance_pools['GrottoGraveReverse'] = [entrance.reverse for entrance in entrance_pools['GrottoGrave']]

        if worlds[0].settings.shuffle_overworld_entrances:
            exclude_overworld_reverse = ('Overworld' in worlds[0].settings.mix_entrance_pools) and not worlds[0].settings.decouple_entrances
            entrance_pools['Overworld'] = world.get_shufflable_entrances(type='Overworld', only_primary=exclude_overworld_reverse)
            if not worlds[0].settings.decouple_entrances:
                entrance_pools['Overworld'].remove(world.get_entrance('GV Lower Stream -> Lake Hylia'))

        # Set shuffled entrances as such
        for entrance in list(chain.from_iterable(one_way_entrance_pools.values())) + list(chain.from_iterable(entrance_pools.values())):
            entrance.shuffled = True
            if entrance.reverse:
                entrance.reverse.shuffled = True

        # Combine all entrance pools into one when mixing entrance pools
        if len(worlds[0].settings.mix_entrance_pools) > 1:
            entrance_pools['Mixed'] = []
            for pool in worlds[0].settings.mix_entrance_pools:
                entrance_pools['Mixed'] += entrance_pools.pop(pool, [])

        # Build target entrance pools and set the assumption for entrances being reachable
        one_way_target_entrance_pools = {}
        for pool_type, entrance_pool in one_way_entrance_pools.items():
            # One way entrances are extra entrances that will be connected to entrance positions from a selection of entrance pools
            if pool_type == 'OwlDrop':
                valid_target_types = ('WarpSong', 'OwlDrop', 'Overworld', 'Extra')
                one_way_target_entrance_pools[pool_type] = build_one_way_targets(world, valid_target_types, exclude=['Prelude of Light Warp -> Temple of Time'])
                for target in one_way_target_entrance_pools[pool_type]:
                    target.set_rule(lambda state, age=None, **kwargs: age == 'child')
            elif pool_type == 'Spawn':
                valid_target_types = ('Spawn', 'WarpSong', 'OwlDrop', 'Overworld', 'Interior', 'SpecialInterior', 'Extra')
                one_way_target_entrance_pools[pool_type] = build_one_way_targets(world, valid_target_types)
            elif pool_type == 'WarpSong':
                valid_target_types = ('Spawn', 'WarpSong', 'OwlDrop', 'Overworld', 'Interior', 'SpecialInterior', 'Extra')
                one_way_target_entrance_pools[pool_type] = build_one_way_targets(world, valid_target_types)
            # Ensure that when trying to place the last entrance of a one way pool, we don't assume the rest of the targets are reachable
            for target in one_way_target_entrance_pools[pool_type]:
                target.add_rule((lambda entrances=entrance_pool: (lambda state, **kwargs: any(entrance.connected_region == None for entrance in entrances)))())
        # Disconnect all one way entrances at this point (they need to be connected during all of the above process)
        for entrance in chain.from_iterable(one_way_entrance_pools.values()):
            entrance.disconnect()

        target_entrance_pools = {}
        for pool_type, entrance_pool in entrance_pools.items():
            target_entrance_pools[pool_type] = assume_entrance_pool(entrance_pool)

        # Set entrances defined in the distribution
        world.distribution.set_shuffled_entrances(worlds, dict(chain(one_way_entrance_pools.items(), entrance_pools.items())), dict(chain(one_way_target_entrance_pools.items(), target_entrance_pools.items())), locations_to_ensure_reachable, complete_itempool)

        # Check placed one way entrances and trim.
        # The placed entrances are already pointing at their new regions.
        placed_entrances = [entrance for entrance in chain.from_iterable(one_way_entrance_pools.values())
                            if entrance.replaces is not None]
        replaced_entrances = [entrance.replaces for entrance in placed_entrances]
        # Remove replaced entrances so we don't place two in one target.
        for remaining_target in chain.from_iterable(one_way_target_entrance_pools.values()):
            if remaining_target.replaces and remaining_target.replaces in replaced_entrances:
                delete_target_entrance(remaining_target)
        # Remove priority targets if any placed entrances point at their region(s).
        for key, (regions, _) in priority_entrance_table.items():
            if key in one_way_priorities:
                for entrance in placed_entrances:
                    if entrance.connected_region and entrance.connected_region.name in regions:
                        del one_way_priorities[key]
                        break

        # Place priority entrances
        placed_one_way_entrances = shuffle_one_way_priority_entrances(worlds, world, one_way_priorities, one_way_entrance_pools, one_way_target_entrance_pools, locations_to_ensure_reachable, complete_itempool, retry_count=2)

        # Delete all targets that we just placed from one way target pools so multiple one way entrances don't use the same target
        replaced_entrances = [entrance.replaces for entrance in chain.from_iterable(one_way_entrance_pools.values())]
        for remaining_target in chain.from_iterable(one_way_target_entrance_pools.values()):
            if remaining_target.replaces in replaced_entrances:
                delete_target_entrance(remaining_target)


        # Shuffle all entrances among the pools to shuffle
        for pool_type, entrance_pool in one_way_entrance_pools.items():
            placed_one_way_entrances += shuffle_entrance_pool(world, worlds, entrance_pool, one_way_target_entrance_pools[pool_type], locations_to_ensure_reachable, check_all=True, placed_one_way_entrances=placed_one_way_entrances)
            # Delete all targets that we just placed from other one way target pools so multiple one way entrances don't use the same target
            replaced_entrances = [entrance.replaces for entrance in entrance_pool]
            for remaining_target in chain.from_iterable(one_way_target_entrance_pools.values()):
                if remaining_target.replaces in replaced_entrances:
                    delete_target_entrance(remaining_target)
            # Delete all unused extra targets after placing a one way pool, since the unused targets won't ever be replaced
            for unused_target in one_way_target_entrance_pools[pool_type]:
                delete_target_entrance(unused_target)

        for pool_type, entrance_pool in entrance_pools.items():
            shuffle_entrance_pool(world, worlds, entrance_pool, target_entrance_pools[pool_type], locations_to_ensure_reachable, placed_one_way_entrances=placed_one_way_entrances)

            if pool_type in ('Boss', 'ChildBoss', 'AdultBoss'):
                for entrance in entrance_pool:
                    entrance.connected_region.change_dungeon(entrance.parent_region.dungeon)


    # Multiple checks after shuffling entrances to make sure everything went fine
    max_search = Search.max_explore([world.state for world in worlds], complete_itempool)

    # Check that all shuffled entrances are properly connected to a region
    for world in worlds:
        for entrance in world.get_shuffled_entrances():
            if entrance.connected_region == None:
                logging.getLogger('').error('%s was shuffled but still isn\'t connected to any region [World %d]', entrance, world.id)
            if entrance.replaces == None:
                logging.getLogger('').error('%s was shuffled but still doesn\'t replace any entrance [World %d]', entrance, world.id)
    if len(world.get_region('Root Exits').exits) > 8:
        for exit in world.get_region('Root Exits').exits:
            logging.getLogger('').error('Root Exit: %s, Connected Region: %s', exit, exit.connected_region)
        raise RuntimeError('Something went wrong, Root has too many entrances left after shuffling entrances [World %d]' % world.id)

    # Check for game beatability in all worlds
    if not max_search.can_beat_game(False):
        raise EntranceShuffleError('Cannot beat game!')

    # Validate the worlds one last time to ensure all special conditions are still valid
    for world in worlds:
        try:
            validate_world(world, worlds, None, locations_to_ensure_reachable, complete_itempool, placed_one_way_entrances=placed_one_way_entrances)
        except EntranceShuffleError as error:
            raise EntranceShuffleError('Worlds are not valid after shuffling entrances, Reason: %s' % error)


def shuffle_one_way_priority_entrances(worlds, world, one_way_priorities, one_way_entrance_pools, one_way_target_entrance_pools, locations_to_ensure_reachable, complete_itempool, retry_count=2):
    while retry_count:
        retry_count -= 1
        rollbacks = []

        try:
            for key, (regions, types) in one_way_priorities.items():
                place_one_way_priority_entrance(worlds, world, key, regions, types, rollbacks, locations_to_ensure_reachable, complete_itempool, one_way_entrance_pools, one_way_target_entrance_pools)

            # If all entrances could be connected without issues, log connections and continue
            for entrance, target in rollbacks:
                confirm_replacement(entrance, target)
            return rollbacks

        except EntranceShuffleError as error:
            for entrance, target in rollbacks:
                restore_connections(entrance, target)
            logging.getLogger('').info('Failed to place all priority one-way entrances for world %d. Will retry %d more times', world.id, retry_count)
            logging.getLogger('').info('\t%s' % error)

    if world.settings.custom_seed:
        raise EntranceShuffleError('Entrance placement attempt count exceeded for world %d. Ensure the \"Seed\" field is empty and retry a few times.' % entrance_pool[0].world.id)
    if world.settings.distribution_file:
        raise EntranceShuffleError('Entrance placement attempt count exceeded for world %d. Some entrances in the Plandomizer File may have to be changed to create a valid seed. Reach out to Support on Discord for help.' % entrance_pool[0].world.id)
    raise EntranceShuffleError('Entrance placement attempt count exceeded for world %d. Retry a few times or reach out to Support on Discord for help.' % entrance_pool[0].world.id)

# Shuffle all entrances within a provided pool
def shuffle_entrance_pool(world, worlds, entrance_pool, target_entrances, locations_to_ensure_reachable, check_all=False, retry_count=20, placed_one_way_entrances=()):

    # Split entrances between those that have requirements (restrictive) and those that do not (soft). These are primarily age or time of day requirements.
    restrictive_entrances, soft_entrances = split_entrances_by_requirements(worlds, entrance_pool, target_entrances)

    while retry_count:
        retry_count -= 1
        rollbacks = []

        try:
            # Shuffle restrictive entrances first while more regions are available in order to heavily reduce the chances of the placement failing.
            shuffle_entrances(worlds, restrictive_entrances, target_entrances, rollbacks, locations_to_ensure_reachable, placed_one_way_entrances=placed_one_way_entrances)

            # Shuffle the rest of the entrances, we don't have to check for beatability/reachability of locations when placing those, unless specified otherwise
            if check_all:
                shuffle_entrances(worlds, soft_entrances, target_entrances, rollbacks, locations_to_ensure_reachable, placed_one_way_entrances=placed_one_way_entrances)
            else:
                shuffle_entrances(worlds, soft_entrances, target_entrances, rollbacks, placed_one_way_entrances=placed_one_way_entrances)

            # Fully validate the resulting world to ensure everything is still fine after shuffling this pool
            complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]
            validate_world(world, worlds, None, locations_to_ensure_reachable, complete_itempool, placed_one_way_entrances=placed_one_way_entrances)

            # If all entrances could be connected without issues, log connections and continue
            for entrance, target in rollbacks:
                confirm_replacement(entrance, target)
            return rollbacks

        except EntranceShuffleError as error:
            for entrance, target in rollbacks:
                restore_connections(entrance, target)
            logging.getLogger('').info('Failed to place all entrances in a pool for world %d. Will retry %d more times', entrance_pool[0].world.id, retry_count)
            logging.getLogger('').info('\t%s' % error)

    if world.settings.custom_seed:
        raise EntranceShuffleError('Entrance placement attempt count exceeded for world %d. Ensure the \"Seed\" field is empty and retry a few times.' % entrance_pool[0].world.id)
    if world.settings.distribution_file:
        raise EntranceShuffleError('Entrance placement attempt count exceeded for world %d. Some entrances in the Plandomizer File may have to be changed to create a valid seed. Reach out to Support on Discord for help.' % entrance_pool[0].world.id)
    raise EntranceShuffleError('Entrance placement attempt count exceeded for world %d. Retry a few times or reach out to Support on Discord for help.' % entrance_pool[0].world.id)


# Split entrances based on their requirements to figure out how each entrance should be handled when shuffling them
def split_entrances_by_requirements(worlds, entrances_to_split, assumed_entrances):

    # First, disconnect all root assumed entrances and save which regions they were originally connected to, so we can reconnect them later
    original_connected_regions = {}
    entrances_to_disconnect = set(assumed_entrances).union(entrance.reverse for entrance in assumed_entrances if entrance.reverse)
    for entrance in entrances_to_disconnect:
        if entrance.connected_region:
            original_connected_regions[entrance] = entrance.disconnect()

    # Generate the states with all assumed entrances disconnected
    # This ensures no assumed entrances corresponding to those we are shuffling are required in order for an entrance to be reachable as some age/tod
    complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]
    max_search = Search.max_explore([world.state for world in worlds], complete_itempool)

    restrictive_entrances = []
    soft_entrances = []

    for entrance in entrances_to_split:
        # Here, we find entrances that may be unreachable under certain conditions
        if not max_search.spot_access(entrance, age='both', tod=TimeOfDay.ALL):
            restrictive_entrances.append(entrance)
            continue
        # If an entrance is reachable as both ages and all times of day with all the other entrances disconnected,
        # then it can always be made accessible in all situations by the Fill algorithm, no matter which combination of entrances we end up with.
        # Thus, those entrances aren't bound to any specific requirements and are very versatile during placement.
        soft_entrances.append(entrance)

    # Reconnect all disconnected entrances afterwards
    for entrance in entrances_to_disconnect:
        if entrance in original_connected_regions:
            entrance.connect(original_connected_regions[entrance])

    return restrictive_entrances, soft_entrances


def replace_entrance(worlds, entrance, target, rollbacks, locations_to_ensure_reachable, itempool, placed_one_way_entrances=()):
    try:
        check_entrances_compatibility(entrance, target, rollbacks, placed_one_way_entrances)
        change_connections(entrance, target)
        validate_world(entrance.world, worlds, entrance, locations_to_ensure_reachable, itempool, placed_one_way_entrances=placed_one_way_entrances)
        rollbacks.append((entrance, target))
        return True
    except EntranceShuffleError as error:
        # If the entrance can't be placed there, log a debug message and change the connections back to what they were previously
        logging.getLogger('').debug('Failed to connect %s To %s (Reason: %s) [World %d]',
                                    entrance, entrance.connected_region or target.connected_region, error, entrance.world.id)
        if entrance.connected_region:
            restore_connections(entrance, target)
    return False


# Connect one random entrance from entrance pools to one random target in the respective target pool.
# Entrance chosen will have one of the allowed types.
# Target chosen will lead to one of the allowed regions.
def place_one_way_priority_entrance(worlds, world, priority_name, allowed_regions, allowed_types, rollbacks, locations_to_ensure_reachable, complete_itempool, one_way_entrance_pools, one_way_target_entrance_pools):
    # Combine the entrances for allowed types in one list.
    # Shuffle this list.
    # Pick the first one not already set, not adult spawn, that has a valid target entrance.
    # Assemble then clear entrances from the pool and target pools as appropriate.
    avail_pool = list(chain.from_iterable(one_way_entrance_pools[t] for t in allowed_types if t in one_way_entrance_pools))
    random.shuffle(avail_pool)
    for entrance in avail_pool:
        if entrance.replaces:
            continue
        # Only allow Adult Spawn as sole Nocturne access if hints != mask.
        # Otherwise, child access is required here (adult access assumed or guaranteed later).
        if entrance.parent_region.name == 'Adult Spawn':
            if priority_name != 'Nocturne' or entrance.world.settings.hints == "mask":
                continue
        # If not shuffling dungeons, Nocturne requires adult access.
        if not entrance.world.shuffle_dungeon_entrances and priority_name == 'Nocturne':
            if entrance.type != 'WarpSong' and entrance.parent_region.name != 'Adult Spawn':
                continue
        for target in one_way_target_entrance_pools[entrance.type]:
            if target.connected_region and target.connected_region.name in allowed_regions:
                if replace_entrance(worlds, entrance, target, rollbacks, locations_to_ensure_reachable, complete_itempool):
                    logging.getLogger('').debug(f'Priority placement for {priority_name}: placing {entrance} as {target}')
                    return
    raise EntranceShuffleError(f'Unable to place priority one-way entrance for {priority_name} [World {world.id}].')


# Shuffle entrances by placing them instead of entrances in the provided target entrances list
# While shuffling entrances, the algorithm will ensure worlds are still valid based on multiple criterias
def shuffle_entrances(worlds, entrances, target_entrances, rollbacks, locations_to_ensure_reachable=(), placed_one_way_entrances=()):

    # Retrieve all items in the itempool, all worlds included
    complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]

    random.shuffle(entrances)

    # Place all entrances in the pool, validating worlds during every placement
    for entrance in entrances:
        if entrance.connected_region != None:
            continue
        random.shuffle(target_entrances)

        for target in target_entrances:
            if target.connected_region == None:
                continue

            if replace_entrance(worlds, entrance, target, rollbacks, locations_to_ensure_reachable, complete_itempool, placed_one_way_entrances=placed_one_way_entrances):
                break

        if entrance.connected_region == None:
            raise EntranceShuffleError('No more valid entrances to replace with %s in world %d' % (entrance, entrance.world.id))


# Check and validate that an entrance is compatible to replace a specific target
def check_entrances_compatibility(entrance, target, rollbacks=(), placed_one_way_entrances=()):
    # An entrance shouldn't be connected to its own scene, so we fail in that situation
    if entrance.parent_region.get_scene() and entrance.parent_region.get_scene() == target.connected_region.get_scene():
        raise EntranceShuffleError('Self scene connections are forbidden')

    # One way entrances shouldn't lead to the same hint area as other already chosen one way entrances
    if entrance.type in ('OwlDrop', 'Spawn', 'WarpSong'):
        try:
            hint_area = get_hint_area(target.connected_region)[0]
        except HintAreaNotFound:
            pass # not connected to a hint area yet, will be checked when shuffling two-way entrances
        else:
            for placed_entrance in (*rollbacks, *placed_one_way_entrances):
                try:
                    if get_hint_area(placed_entrance[0].connected_region)[0] == hint_area:
                        raise EntranceShuffleError(f'Another one-way entrance already leads to {hint_area}')
                except HintAreaNotFound:
                    pass


# Validate the provided worlds' structures, raising an error if it's not valid based on our criterias
def validate_world(world, worlds, entrance_placed, locations_to_ensure_reachable, itempool, placed_one_way_entrances=()):

    if not world.settings.decouple_entrances:
        # Unless entrances are decoupled, we don't want the player to end up through certain entrances as the wrong age
        # This means we need to hard check that none of the relevant entrances are ever reachable as that age
        # This is mostly relevant when mixing entrance pools or shuffling special interiors (such as windmill or kak potion shop)
        # Warp Songs and Overworld Spawns can also end up inside certain indoors so those need to be handled as well
        CHILD_FORBIDDEN = ['OGC Great Fairy Fountain -> Castle Grounds', 'GV Carpenter Tent -> GV Fortress Side']
        ADULT_FORBIDDEN = ['HC Great Fairy Fountain -> Castle Grounds', 'HC Storms Grotto -> Castle Grounds']

        for entrance in world.get_shufflable_entrances():
            if entrance.shuffled:
                if entrance.replaces:
                    if entrance.replaces.name in CHILD_FORBIDDEN and not entrance_unreachable_as(entrance, 'child', already_checked=[entrance.replaces.reverse]):
                        raise EntranceShuffleError('%s is replaced by an entrance with a potential child access' % entrance.replaces.name)
                    elif entrance.replaces.name in ADULT_FORBIDDEN and not entrance_unreachable_as(entrance, 'adult', already_checked=[entrance.replaces.reverse]):
                        raise EntranceShuffleError('%s is replaced by an entrance with a potential adult access' % entrance.replaces.name)
            else:
                if entrance.name in CHILD_FORBIDDEN and not entrance_unreachable_as(entrance, 'child', already_checked=[entrance.reverse]):
                    raise EntranceShuffleError('%s is potentially accessible as child' % entrance.name)
                elif entrance.name in ADULT_FORBIDDEN and not entrance_unreachable_as(entrance, 'adult', already_checked=[entrance.reverse]):
                    raise EntranceShuffleError('%s is potentially accessible as adult' % entrance.name)

    if locations_to_ensure_reachable:
        max_search = Search.max_explore([w.state for w in worlds], itempool)
        # If ALR is enabled, ensure all locations we want to keep reachable are indeed still reachable
        # Otherwise, just continue if the game is still beatable
        if not (world.check_beatable_only and max_search.can_beat_game(False)):
            max_search.visit_locations(locations_to_ensure_reachable)
            for location in locations_to_ensure_reachable:
                if not max_search.visited(location):
                    raise EntranceShuffleError('%s is unreachable' % location.name)

    if world.shuffle_interior_entrances and ('ganondorf' in world.settings.misc_hints or world.settings.hints != 'none') and \
       (entrance_placed == None or entrance_placed.type in ['Interior', 'SpecialInterior']):
        # When cows are shuffled, ensure both Impa's House entrances are in the same hint area because the cow is reachable from both sides
        if world.settings.shuffle_cows:
            impas_front_entrance = get_entrance_replacing(world.get_region('Kak Impas House'), 'Kakariko Village -> Kak Impas House')
            impas_back_entrance = get_entrance_replacing(world.get_region('Kak Impas House Back'), 'Kak Impas Ledge -> Kak Impas House Back')
            if impas_front_entrance is not None and impas_back_entrance is not None and not same_hint_area(impas_front_entrance, impas_back_entrance):
                raise EntranceShuffleError('Kak Impas House entrances are not in the same hint area')

    if (world.shuffle_special_interior_entrances or world.settings.shuffle_overworld_entrances or world.settings.spawn_positions) and \
       (entrance_placed == None or entrance_placed.type in ['SpecialInterior', 'Overworld', 'Spawn', 'WarpSong', 'OwlDrop']):
        # At least one valid starting region with all basic refills should be reachable without using any items at the beginning of the seed
        # Note this creates new empty states rather than reuse the worlds' states (which already have starting items)
        no_items_search = Search([State(w) for w in worlds])

        valid_starting_regions = ['Kokiri Forest', 'Kakariko Village']
        if not any(region for region in valid_starting_regions if no_items_search.can_reach(world.get_region(region))):
            raise EntranceShuffleError('Invalid starting area')

        # Check that a region where time passes is always reachable as both ages without having collected any items
        time_travel_search = Search.with_items([w.state for w in worlds], [ItemFactory('Time Travel', world=w) for w in worlds])

        if not (any(region for region in time_travel_search.reachable_regions('child') if region.time_passes and region.world == world) and
                any(region for region in time_travel_search.reachable_regions('adult') if region.time_passes and region.world == world)):
            raise EntranceShuffleError('Time passing is not guaranteed as both ages')

        # The player should be able to get back to ToT after going through time, without having collected any items
        # This is important to ensure that the player never loses access to the pedestal after going through time
        if world.settings.starting_age == 'child' and not time_travel_search.can_reach(world.get_region('Temple of Time'), age='adult'):
            raise EntranceShuffleError('Path to Temple of Time as adult is not guaranteed')
        elif world.settings.starting_age == 'adult' and not time_travel_search.can_reach(world.get_region('Temple of Time'), age='child'):
            raise EntranceShuffleError('Path to Temple of Time as child is not guaranteed')

    if (world.shuffle_interior_entrances or world.settings.shuffle_overworld_entrances) and \
       (entrance_placed == None or entrance_placed.type in ['Interior', 'SpecialInterior', 'Overworld', 'Spawn', 'WarpSong', 'OwlDrop']):
        # The Big Poe Shop should always be accessible as adult without the need to use any bottles
        # This is important to ensure that players can never lock their only bottles by filling them with Big Poes they can't sell
        # We can use starting items in this check as long as there are no exits requiring the use of a bottle without refills
        time_travel_search = Search.with_items([w.state for w in worlds], [ItemFactory('Time Travel', world=w) for w in worlds])

        if not time_travel_search.can_reach(world.get_region('Market Guard House'), age='adult'):
            raise EntranceShuffleError('Big Poe Shop access is not guaranteed as adult')

    # placing a two-way entrance can connect a one-way entrance to a hint area,
    # so the restriction also needs to be checked here
    for idx1 in range(len(placed_one_way_entrances)):
        try:
            hint_area1 = get_hint_area(placed_one_way_entrances[idx1][0].connected_region)[0]
        except HintAreaNotFound:
            pass
        else:
            for idx2 in range(idx1):
                try:
                    if hint_area1 == get_hint_area(placed_one_way_entrances[idx2][0].connected_region)[0]:
                        raise EntranceShuffleError(f'Multiple one-way entrances lead to {hint_area1}')
                except HintAreaNotFound:
                    pass


# Returns whether or not we can affirm the entrance can never be accessed as the given age
def entrance_unreachable_as(entrance, age, already_checked=None):
    if already_checked == None:
        already_checked = []

    already_checked.append(entrance)

    # The following cases determine when we say an entrance is not safe to affirm unreachable as the given age
    if entrance.type in ('WarpSong', 'Overworld'):
        # Note that we consider all overworld entrances as potentially accessible as both ages, to be completely safe
        return False
    elif entrance.type == 'OwlDrop':
        return age == 'adult'
    elif entrance.name == 'Child Spawn -> KF Links House':
        return age == 'adult'
    elif entrance.name == 'Adult Spawn -> Temple of Time':
        return age == 'child'

    # Other entrances such as Interior, Dungeon or Grotto are fine unless they have a parent which is one of the above cases
    # Recursively check parent entrances to verify that they are also not reachable as the wrong age
    for parent_entrance in entrance.parent_region.entrances:
        if parent_entrance in already_checked: continue
        unreachable = entrance_unreachable_as(parent_entrance, age, already_checked)
        if not unreachable:
            return False

    return True


# Returns whether two entrances are in the same hint area
def same_hint_area(first, second):
    try:
        return get_hint_area(first) == get_hint_area(second)
    except HintAreaNotFound:
        return False


# Shorthand function to find an entrance with the requested name leading to a specific region
def get_entrance_replacing(region, entrance_name):
    original_entrance = region.world.get_entrance(entrance_name)

    if not original_entrance.shuffled:
        return original_entrance

    try:
        return next(filter(lambda entrance: entrance.replaces and entrance.replaces.name == entrance_name and \
                                            entrance.parent_region and entrance.parent_region.name != 'Root Exits' and \
                                            entrance.type not in ('OwlDrop', 'Spawn', 'WarpSong'), region.entrances))
    except StopIteration:
        return None


# Change connections between an entrance and a target assumed entrance, in order to test the connections afterwards if necessary
def change_connections(entrance, target_entrance):
    entrance.connect(target_entrance.disconnect())
    entrance.replaces = target_entrance.replaces
    if entrance.reverse and not entrance.decoupled:
        target_entrance.replaces.reverse.connect(entrance.reverse.assumed.disconnect())
        target_entrance.replaces.reverse.replaces = entrance.reverse


# Restore connections between an entrance and a target assumed entrance
def restore_connections(entrance, target_entrance):
    target_entrance.connect(entrance.disconnect())
    entrance.replaces = None
    if entrance.reverse and not entrance.decoupled:
        entrance.reverse.assumed.connect(target_entrance.replaces.reverse.disconnect())
        target_entrance.replaces.reverse.replaces = None


# Confirm the replacement of a target entrance by a new entrance, logging the new connections and completely deleting the target entrances
def confirm_replacement(entrance, target_entrance):
    delete_target_entrance(target_entrance)
    logging.getLogger('').debug('Connected %s To %s [World %d]', entrance, entrance.connected_region, entrance.world.id)
    if entrance.reverse and not entrance.decoupled:
        replaced_reverse = target_entrance.replaces.reverse
        delete_target_entrance(entrance.reverse.assumed)
        logging.getLogger('').debug('Connected %s To %s [World %d]', replaced_reverse, replaced_reverse.connected_region, replaced_reverse.world.id)


# Delete an assumed target entrance, by disconnecting it if needed and removing it from its parent region
def delete_target_entrance(target_entrance):
    if target_entrance.connected_region != None:
        target_entrance.disconnect()
    if target_entrance.parent_region != None:
        target_entrance.parent_region.exits.remove(target_entrance)
        target_entrance.parent_region = None
