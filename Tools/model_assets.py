"""Run in Blender via MCP. Creates an isolated scene and exports original GLBs.
Blender +Y is vehicle forward; glTF exports it as Godot -Z. Units are metres.
"""
import bpy
import math
import random
from pathlib import Path
from mathutils import Vector, Euler

ROOT = Path('/Users/chanwaichan/workspace/antila')
previous_scene = bpy.context.window.scene
only_buildings = globals().get('ONLY_BUILDINGS', False)
scene = bpy.data.scenes.new('Antila_Buildings' if only_buildings else 'Antila_Kowloon_Assets')
bpy.context.window.scene = scene


def mat(name, color, metal=0, rough=.55, emission=0):
    color = tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in color)
    m = bpy.data.materials.new('Antila_' + name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Emission Color'].default_value = (*color, 1)
    bs.inputs['Emission Strength'].default_value = emission
    return m


cream = mat('ivory enamel', (.88,.81,.63), .25,.3)
red = mat('vermilion enamel', (.66,.09,.045), .3,.3)
glass = mat('blue smoked glazing', (.035,.105,.13), .5,.18)
black = mat('rubber', (.018,.025,.028), 0,.75)
steel = mat('brushed steel', (.39,.45,.46), .75,.28)
white = mat('warm white', (.89,.88,.76))
amber = mat('amber LEDs', (1,.48,.035), 0,.35,1.3)
lamp = mat('headlamp', (1,.9,.66), .3,.2,1.3)
concrete = [mat('facade '+str(i), c) for i,c in enumerate([
    (.65,.59,.46),(.68,.70,.64),(.48,.61,.60),(.71,.49,.38)])]
teal = mat('shop teal', (.025,.25,.25))


def photo_material(name, filename, metres=None):
    material = mat(name, (1,1,1), rough=.9)
    texture = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(ROOT/'Assets/Textures'/filename), check_existing=True)
    texture.image.pack()
    material.node_tree.links.new(texture.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    material['texture_metres'] = metres or 0
    return material


tiled_wall = photo_material('weathered ceramic tiles', 'weathered-tiles.png', 2)
storefront = photo_material('photographic cafe storefront', 'cafe-storefront.png')
bark = photo_material('banyan bark', 'banyan-bark.png', 1)
leaf = photo_material('banyan leaf cutout', 'banyan-leaves.png')
leaf.use_backface_culling = False
leaf.surface_render_method = 'DITHERED'
leaf_nodes = leaf.node_tree.nodes
leaf_image = next(n for n in leaf_nodes if n.type == 'TEX_IMAGE').image
assert leaf_image.channels == 4 and min(leaf_image.pixels[3::4]) < .01 and max(leaf_image.pixels[3::4]) > .99, 'Leaf cutouts require real transparent and opaque pixels'
leaf_alpha = leaf_nodes.new('ShaderNodeMath')
leaf_alpha.operation = 'ROUND'  # glTF exports this as alphaMode MASK, cutoff 0.5.
leaf.node_tree.links.new(next(n for n in leaf_nodes if n.type == 'TEX_IMAGE').outputs['Alpha'], leaf_alpha.inputs[0])
leaf.node_tree.links.new(leaf_alpha.outputs[0], leaf_nodes.get('Principled BSDF').inputs['Alpha'])
wood = mat('weathered bench slats', (.30,.19,.11), rough=.9)
orange = mat('street bin orange', (.85,.32,.045), rough=.65)
soil = mat('planter soil', (.12,.10,.065), rough=1)


def box(name, pos, size, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    o = bpy.context.object
    o.name = name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if 'texture_metres' in material:
        # Project by physical size; do not stretch one tile across an entire tower.
        metres = material['texture_metres']
        for face in o.data.polygons:
            for loop in face.loop_indices:
                co = o.data.vertices[o.data.loops[loop].vertex_index].co
                if metres:
                    world = o.matrix_world @ co
                    uv = (world.y,world.z) if abs(face.normal.x)>.5 else (world.x,world.y) if abs(face.normal.z)>.5 else (world.x,world.z)
                    uv = (uv[0]/metres,uv[1]/metres)
                else:
                    uv = (co.x/size[0]+.5,co.z/size[2]+.5)
                o.data.uv_layers.active.data[loop].uv = uv
    if bevel:
        m = o.modifiers.new('Soft manufactured edges', 'BEVEL')
        m.width = bevel
        m.segments = 2
        bpy.ops.object.modifier_apply(modifier=m.name)
        o.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return o


def cyl(name, pos, radius, depth, material, rotation=(0,0,0), vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=pos, rotation=rotation)
    o=bpy.context.object
    o.name=name
    o.data.materials.append(material)
    return o


def text(name, body, pos, size, material, rotation=(math.pi/2,0,math.pi)):
    data=bpy.data.curves.new(name, 'FONT')
    data.body=body
    data.size=size
    data.align_x='CENTER'
    data.align_y='CENTER'
    data.extrude=.001
    o=bpy.data.objects.new(name,data)
    scene.collection.objects.link(o)
    o.location=pos
    o.rotation_euler=rotation
    o.data.materials.append(material)
    return o


def begin(name):
    global group
    group=bpy.data.collections.new(name)
    scene.collection.children.link(group)
    for o in list(scene.objects):
        o.hide_set(True)


def export(name):
    objects=[o for o in scene.objects if not o.hide_get()]
    # Merge static parts by material; preserve the wheel origins for runtime rotation.
    for o in objects:
        for collection in list(o.users_collection):
            collection.objects.unlink(o)
        group.objects.link(o)
    static=[o for o in objects if not o.name.startswith(('Wheel_', 'Door_'))]
    bpy.ops.object.select_all(action='DESELECT')
    for o in static:
        o.select_set(True)
    bpy.context.view_layer.objects.active=static[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    body=bpy.context.object
    body.name=name+'_Body'
    assert body.data.uv_layers.active is not None
    assert all(math.isfinite(c) for item in body.data.uv_layers.active.data for c in item.uv)
    scene.cursor.location=(0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.select_all(action='DESELECT')
    for o in group.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'Assets/Models'/f'{name}.glb'), export_format='GLB', use_selection=True, use_active_scene=True, export_yup=True, export_apply=True)
    print('EXPORTED', name, len(group.objects))


def bus():
    begin('DoubleDecker')
    box('lower body',(0,0,.92),(2.5,10.7,.95),cream,.16)
    box('red skirt',(0,0,.58),(2.52,10.55,.34),red,.08)
    box('roof',(0,0,4.13),(2.5,10.7,.30),cream,.14)
    box('upper floor',(0,0,2.55),(2.5,10.65,.40),red,.06)
    box('top deck windows',(0,0,3.34),(2.45,10.42,1.12),glass,.09)
    box('lower deck windows',(0,0,1.89),(2.44,10.4,.91),glass,.06)
    for side in (-1,1):
        for y in [-5,-3.7,-2.2,-.7,.8,2.3,3.8,5]:
            box('upper pillar',(side*1.24,y,3.35),(.06,.085,1.25),cream)
            box('lower pillar',(side*1.24,y,1.9),(.06,.07,1.07),cream)
        box('window trim',(side*1.253,0,2.88),(.045,10.4,.035),steel)
        box('route banner',(side*1.269,-.7,2.56),(.025,5.0,.3),cream)
    # Three axles. Separate tyres keep origins at axle height for animation.
    for y in (3.25,-2.5,-3.85):
        for side in (-1,1):
            cyl('Wheel_'+str(side)+'_'+str(y),(side*1.21,y,.55),.54,.27,black,(0,math.pi/2,0),24)
            cyl('hub',(side*1.355,y,.55),.29,.026,steel,(0,math.pi/2,0),16)
    for index,y in enumerate((3.95,.45)):
        box('left doors',(-1.273,y,1.36),(.035,1.14,1.85),black,.015)
        for side,yy in [('L',-.28),('R',.28)]:
            panel=box('door panel',(-1.31,y+yy,1.36),(.04,.55,1.85),cream,.015)
            pane=box('door glazing',(-1.34,y+yy,1.55),(.02,.47,1.33),glass)
            bpy.ops.object.select_all(action='DESELECT')
            panel.select_set(True)
            pane.select_set(True)
            bpy.context.view_layer.objects.active=panel
            bpy.ops.object.join()
            panel.name='Door_'+str(index)+'_'+side
    box('front destination',(0,5.365,2.59),(2.19,.04,.37),black,.025)
    text('destination','H1  JORDAN',(0,5.4,2.59),.24,amber)
    box('rear destination',(0,-5.365,3.70),(.72,.025,.32),black)
    text('rear route','H1',(0,-5.39,3.7),.23,amber,(math.pi/2,0,0))
    text('rear name','KOWLOON',(0,-5.395,2.61),.15,cream,(math.pi/2,0,0))
    box('rear engine grille',(0,-5.375,1.0),(1.35,.025,.5),black)
    for z in [.8,.9,1,1.1,1.2]:
        box('grille fin',(0,-5.398,z),(1.3,.018,.025),steel)
    for side in (-1,1):
        box('headlamp',(side*.93,5.33,.99),(.36,.05,.18),lamp,.05)
        box('taillamp',(side*1.05,-5.35,1.14),(.13,.04,.32),red,.025)
        box('mirror arm',(side*1.47,4.91,2.1),(.45,.05,.05),black)
        box('mirror',(side*1.68,4.9,1.91),(.15,.18,.43),black,.06)
    box('bumper',(0,5.36,.56),(2.2,.12,.17),black,.04)
    box('plate',(0,5.43,.83),(.55,.025,.14),white)
    text('license','HK 1024',(0,5.452,.83),.086,black)
    export('bus')


def building(index):
    begin('ShopHouse'+str(index))
    floors=7+index*2
    height=4+floors*2.9
    width=13+index*2
    wall=tiled_wall.copy()
    wall.name='Antila_facade_tiles_'+str(index)
    tint=wall.node_tree.nodes.new('ShaderNodeMix')
    tint.data_type='RGBA'
    tint.blend_type='MULTIPLY'
    tint.inputs[0].default_value=1
    palette=[(.86,.81,.69),(.64,.75,.70),(.72,.77,.81)][index]
    tint.inputs[7].default_value=tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in palette)+(1,)
    texture=next(n for n in wall.node_tree.nodes if n.type=='TEX_IMAGE')
    wall.node_tree.links.new(texture.outputs['Color'],tint.inputs[6])
    wall.node_tree.links.new(tint.outputs[2],wall.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    curtains=mat('closed curtains '+str(index),(.31,.34,.32),rough=.8)
    box('concrete',(0,0,height/2),(width,15,height),wall)
    box('shop glazing',(0,7.53,1.65),(width-.6,.08,2.8),storefront)
    for x in (-width/2+.3,width/2-.3):
        box('shop pier',(x,7.7,1.8),(.3,.5,3.6),cream)
    box('canopy',(0,8.05,3.6),(width+.5,2.2,.23),cream)
    box('shop fascia',(0,8.95,3.1),(width-.3,.1,.76),red if index%2==0 else teal)
    text('shop name',['KOWLOON CAFE','GOLDEN DRAGON','NATHAN CAMERA'][index],(0,9.015,3.11),.55,cream)
    for floor in range(floors):
        z=5.5+floor*2.9
        box('floor sill',(0,7.6,z-1.08),(width+.1,.55,.13),cream)
        for x in [-width/2+1.7+i*2.7 for i in range(int(width/2.7))]:
            box('window frame',(x,7.58,z),(1.85,.16,1.92),cream)
            pane=curtains if (floor+int(x)+index)%7==0 else glass
            box('window',(x,7.7,z),(1.59,.05,1.7),pane)
            box('window mullion',(x,7.75,z),(.045,.035,1.7),steel)
            if (floor+int(x))%3==0:
                box('air conditioner',(x+.35,8.03,z-1.1),(.8,.7,.49),concrete[1],.04)
                box('AC grille',(x+.35,8.39,z-1.1),(.63,.025,.3),steel)
    for side in (-1,1):
        for floor in range(floors):
            for y in (-4,0,4):
                z=5.5+floor*2.9
                pane=curtains if (floor+y+index)%5==0 else glass
                box('side frame',(side*(width/2+.06),y,z),(.15,1.9,1.98),cream)
                box('side window',(side*(width/2+.15),y,z),(.035,1.65,1.72),pane)
                box('side mullion',(side*(width/2+.18),y,z),(.035,.05,1.72),steel)
                box('side sill',(side*(width/2+.12),y,z-1.06),(.25,2.05,.13),cream)
        box('roof parapet',(side*width/2,0,height+.5),(.3,15,1),wall)
    # Exposed rear walls need their own elevation when blocks are viewed from side streets.
    for floor in range(floors):
        z=5.5+floor*2.9
        for column,x in enumerate((-width/2+2,0,width/2-2)):
            pane=curtains if (floor+column+index)%4==0 else glass
            box('rear frame',(x,-7.56,z),(1.85,.15,1.98),cream)
            box('rear window',(x,-7.66,z),(1.61,.035,1.72),pane)
            box('rear mullion',(x,-7.69,z),(.05,.035,1.72),steel)
            box('rear sill',(x,-7.63,z-1.06),(2.0,.30,.13),cream)
            if (floor+column)%3==0:
                box('rear AC',(x+.35,-7.8,z-1.15),(.74,.48,.42),concrete[1],.025)
                box('rear AC grille',(x+.35,-8.05,z-1.15),(.6,.025,.27),steel)
    cyl('rear drainpipe',(-width/2+.55,-7.73,height/2),.065,height,steel,vertices=10)
    box('service door',(width/2-1.8,-7.54,1.25),(1.1,.08,2.5),teal)
    for y in (-7.4,7.4):
        box('roof parapet end',(0,y,height+.5),(width,.3,1),wall)
    box('rooftop plant',(2,-2,height+.8),(3,4,1.6),concrete[1])
    cyl('water tank',(-3,-3,height+1.4),1.35,2.8,steel)
    box('projecting shop sign',(-width/2+.4,10.1,7.5),(.2,3.4,5.4),teal if index%2==0 else red)
    export('shop_'+str(index))


def shelter():
    begin('Shelter')
    for x in (-3,3):
        box('pillar',(x,.65,1.3),(.13,.13,2.6),steel)
    box('roof',(0,0,2.65),(6.7,2.5,.18),red,.05)
    box('roof edge',(0,-1.25,2.62),(6.7,.07,.23),cream)
    box('glass back',(0,.78,1.4),(6,.06,2.3),glass)
    box('bench',(0,.34,.5),(3.5,.53,.15),steel,.04)
    for x in (-1.4,1.4):
        box('bench leg',(x,.35,.24),(.12,.4,.5),steel)
    box('poster panel',(2,.71,1.4),(1.27,.15,1.96),cream)
    cyl('stop pole',(-4,-.2,1.8),.055,3.6,steel)
    cyl('stop disc',(-4,-.2,3.25),.40,.10,red,(math.pi/2,0,0),32)
    text('stop route','H1',(-4,-.265,3.25),.29,cream,(math.pi/2,0,0))
    export('shelter')


def taxi():
    begin('Taxi')
    box('taxi body',(0,0,.7),(1.8,4.5,.8),red,.18)
    box('cabin',(0,-.15,1.22),(1.65,2.5,.72),glass,.16)
    box('silver roof',(0,-.15,1.62),(1.66,2.35,.12),steel,.07)
    box('taxi sign',(0,-.1,1.81),(.62,.25,.24),lamp,.03)
    for side in (-1,1):
        for y in (-1.3,1.35):
            cyl('tyre',(side*.85,y,.36),.35,.22,black,(0,math.pi/2,0),16)
        box('door post',(side*.83,-.2,1.23),(.04,.12,.7),red)
        box('headlight',(side*.59,2.245,.82),(.44,.03,.2),lamp)
    export('taxi')


def branch(points, radii):
    """A tapered tube with bark UVs following its length."""
    assert len(points) == len(radii) and len(points) >= 2
    points = [Vector(p) for p in points]
    verts, faces, lengths = [], [], [0.0]
    sides = 10
    for i, p in enumerate(points):
        direction = points[min(i+1,len(points)-1)] - points[max(0,i-1)]
        rotation = direction.to_track_quat('Z','Y')
        if i:
            lengths.append(lengths[-1] + (p-points[i-1]).length)
        for j in range(sides+1):
            a = j*math.tau/sides
            verts.append(p + rotation @ Vector((radii[i]*math.cos(a),radii[i]*math.sin(a),0)))
        if i:
            for j in range(sides):
                k = i*(sides+1)+j
                faces.append((k-sides-1,k-sides,k+1,k))
    mesh = bpy.data.meshes.new('banyan branch')
    mesh.from_pydata(verts,[],faces)
    uv = mesh.uv_layers.new()
    for face in mesh.polygons:
        face.use_smooth = True
        for loop in face.loop_indices:
            ring, j = divmod(mesh.loops[loop].vertex_index,sides+1)
            uv.data[loop].uv = (j/sides*math.tau*radii[0],lengths[ring])
    obj = bpy.data.objects.new('banyan branch',mesh)
    scene.collection.objects.link(obj)
    mesh.materials.append(bark)


def foliage(rng, count, center, spread, card_size):
    # ponytail: static leaf cards; add wind/LODs only when the scene needs them.
    verts, faces = [], []
    for i in range(count):
        a = rng.uniform(0,math.tau)
        z = rng.uniform(-1,1)
        radius = rng.random()**(1/3)
        radial = math.sqrt(1-z*z)*radius
        at = Vector((center[0]+math.cos(a)*radial*spread[0], center[1]+math.sin(a)*radial*spread[1], center[2]+z*radius*spread[2]))
        rotation = Euler((rng.uniform(-1.2,1.2),rng.uniform(-1.2,1.2),rng.uniform(0,math.tau))).to_matrix()
        size = card_size*rng.uniform(.8,1.15)/2
        first = len(verts)
        for x,y in ((-1,-1),(1,-1),(1,1),(-1,1)):
            verts.append(at + rotation @ Vector((x*size,y*size,0)))
        faces.append(tuple(first+j for j in range(4)))
    mesh = bpy.data.meshes.new('leaf sprays')
    mesh.from_pydata(verts,[],faces)
    uv = mesh.uv_layers.new()
    for face in mesh.polygons:
        for loop, coord in zip(face.loop_indices,((0,0),(1,0),(1,1),(0,1))):
            uv.data[loop].uv = coord
    obj = bpy.data.objects.new('leaf sprays',mesh)
    scene.collection.objects.link(obj)
    mesh.materials.append(leaf)


def tree():
    begin('Banyan')
    rng = random.Random(104)
    branch([(0,0,0),(.12,-.07,.65),(-.08,.12,1.6),(.12,.1,2.8),(0,0,4.5)],[.60,.38,.32,.27,.11])
    for i in range(9):
        a = i*math.tau/9 + rng.uniform(-.15,.15)
        x,y = math.cos(a),math.sin(a)
        height = rng.uniform(4.9,6.2)
        branch([(.05,0,2.1+i*.13),(x*.9,y*.9,3.8),(x*2.2,y*2.2,height-.7),(x*3.2,y*3.2,height)],[.23,.15,.085,.025])
        branch([(x*1.7,y*1.7,height-1),(x*2.6-y*.7,y*2.6+x*.7,height+.15),(x*3.4-y*.9,y*3.4+x*.9,height+.4)],[.09,.045,.012])
        branch([(x*.3,y*.3,.65),(x*.7,y*.7,.16),(x*1.4,y*1.4,.025)],[.17,.10,.025])
        # Slender aerial roots hang from older lateral branches.
        branch([(x*1.25,y*1.25,4.1),(x*1.3+.07,y*1.3,2.5),(x*1.4,y*1.4,rng.uniform(.1,1.3))],[.045,.027,.012])
    foliage(rng,112,(0,0,5.9),(3.6,3.4,1.5),2.15)
    export('banyan')


def street_furniture():
    begin('ParkBench')
    for x in (-.85,.85):
        box('bench leg',(x,0,.26),(.10,.55,.50),steel,.025)
        box('back support',(x,.23,.69),(.08,.08,.95),steel,.025)
        box('armrest',(x,0,.70),(.09,.60,.06),steel,.025)
    for y in (-.22,-.075,.075,.22):
        box('seat slat',(0,y,.50),(2.1,.13,.075),wood,.015)
    for z in (.73,.90,1.07):
        box('back slat',(0,.28,z),(2.1,.065,.14),wood,.015)
    export('bench')
    begin('StreetBin')
    cyl('bin foot',(0,0,.065),.27,.13,black,vertices=24)
    cyl('orange bin',(0,0,.53),.29,.90,orange,vertices=32)
    cyl('dark opening',(0,0,.95),.295,.19,black,vertices=32)
    cyl('bin lid',(0,0,1.065),.32,.09,orange,vertices=32)
    for x in (-.235,.235):
        box('lid bridge',(x,0,.98),(.07,.38,.17),orange,.025)
    box('bin label',(0,-.291,.62),(.20,.012,.20),white,.01)
    export('bin')
    begin('RoadsidePlanter')
    box('planter',(0,0,.28),(1.55,.85,.56),concrete[1],.055)
    box('earth',(0,0,.57),(1.40,.70,.025),soil)
    foliage(random.Random(57),18,(0,0,.91),(.53,.20,.20),.67)
    export('planter')


if only_buildings:
    for i in range(3):
        building(i)
    for o in scene.objects:
        o.hide_set(False)
    bpy.data.libraries.write(str(ROOT/'Art/buildings.blend'), {scene})
else:
    bus()
    for i in range(3):
        building(i)
    shelter()
    taxi()
    tree()
    street_furniture()
    for o in scene.objects:
        o.hide_set(not o.name.startswith(('bus_', 'Wheel_', 'Door_')))
    # Save only this scene and its dependencies; do not capture the user's other scenes.
    bpy.data.libraries.write(str(ROOT/'Art/antila-assets.blend'), {scene})
bpy.context.window.scene = previous_scene
print('ANTILA_ASSETS_OK')
