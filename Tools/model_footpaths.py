"""Run via Blender MCP. Original tactile paver, pedestrian railing and drain grate; metres."""
import bpy
import math
from pathlib import Path

ROOT = Path('/Users/chanwaichan/workspace/antila')
previous = bpy.context.window.scene
scene = bpy.data.scenes.new('Antila_Footpaths')
bpy.context.window.scene = scene


def material(name, color, metal=0, stone=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    linear = tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in color)+(1,)
    bs.inputs['Base Color'].default_value = linear
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Roughness'].default_value = .85 if stone else .6
    if stone:
        tex = m.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(ROOT/'Assets/Textures/pavement-stone.png'), check_existing=True)
        tex.image.pack()
        tint = m.node_tree.nodes.new('ShaderNodeMix')
        tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'
        tint.inputs[0].default_value = 1; tint.inputs[7].default_value = linear
        m.node_tree.links.new(tex.outputs['Color'], tint.inputs[6])
        m.node_tree.links.new(tint.outputs[2], bs.inputs['Base Color'])
    return m


yellow = material('Antila_tactile_ochre', (1,.79,.28), stone=True)
studs = material('Antila_tactile_studs', (.91,.73,.27))
steel = material('Antila_footpath_steel', (.32,.36,.36), .65)
dark = material('Antila_drain_recess', (.045,.055,.055))


def box(at, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at)
    obj = bpy.context.object; obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)


def cylinder(at, radius, depth, mat, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=depth, location=at, rotation=rotation)
    bpy.context.object.data.materials.append(mat)


def export(name):
    objects = [o for o in scene.objects if not o.hide_get()]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    obj = bpy.context.object; obj.name = name
    scene.cursor.location = (0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    assert obj.data.uv_layers.active is not None
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'Assets/Models'/f'{name}.glb'), export_format='GLB',
                              use_selection=True, use_active_scene=True, export_yup=True, export_apply=True)
    obj.hide_set(True)


box((0,0,.008), (.598,.598,.016), yellow)
for x in range(6):
    for y in range(6):
        cylinder(((x-2.5)*.09,(y-2.5)*.09,.0185), .0175,.007, studs)
export('tactile-paver')

for y in (-.98,.98):
    cylinder((0,y,.52),.035,1.04,steel)
    box((0,y,.015),(.14,.14,.03),steel)
for z in (.18,.98): cylinder((0,0,z),.028,2,steel,(math.pi/2,0,0))
for y in range(-4,5): cylinder((0,y*.2,.58),.012,.8,steel)
export('pedestrian-railing')

box((0,0,.007),(.48,.68,.014),steel)
box((0,0,.015),(.40,.60,.006),dark)
for x in range(-3,4): box((x*.055,0,.021),(.022,.60,.012),steel)
export('drain-grate')

for index,obj in enumerate(sorted(scene.objects,key=lambda o:o.name)):
    obj.hide_set(False)
    obj.location.x=index*2  # Editable source lineup; GLBs were exported at the origin above.
bpy.data.libraries.write(str(ROOT/'Art/footpaths.blend'), {scene})
bpy.context.window.scene = previous
print('ANTILA_FOOTPATH_ASSETS_OK: tactile-paver, pedestrian-railing, drain-grate')
