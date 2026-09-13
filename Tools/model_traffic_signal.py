"""Run through Blender MCP; preserves existing scenes and exports only this asset."""
import bpy
import math
from pathlib import Path

ROOT = Path('/Users/chanwaichan/workspace/antila')
previous = bpy.context.window.scene
scene = bpy.data.scenes.new('Antila_Traffic_Signal')
bpy.context.window.scene = scene

def material(name, color, metal=0):
    m = bpy.data.materials.new('Signal_' + name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Roughness'].default_value = .55
    return m

black = material('Housing', (.012, .018, .019))
grey = material('Galvanized', (.37, .40, .39), .65)
white = material('Border', (.76, .77, .70))
dark = material('Unlit', (.025, .032, .029))

def box(name, position, size, mat, bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    mod = obj.modifiers.new('Rounded edges', 'BEVEL')
    mod.width = bevel
    mod.segments = 3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj

def cylinder(name, position, radius, depth, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth,
        location=position, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj

cylinder('Pole', (0, .10, 1.78), .065, 3.56, grey)
cylinder('Foot', (0, .10, .22), .11, .44, black)
box('Access cover', (0, .025, .70), (.12, .035, .27), grey)
box('Pale backing border', (0, .015, 3.38), (.54, .10, 1.34), white, .075)
box('Black signal housing', (0, -.075, 3.38), (.46, .23, 1.25), black, .06)
for name, height in [('Red', 3.78), ('Amber', 3.38), ('Green', 2.98)]:
    cylinder('Lamp' + name, (0, -.20, height), .145, .018, dark, (math.pi / 2, 0, 0))
    # Open-bottom sun hood: curved metal shell, with no cap hiding the lens.
    vertices = []
    for y in [-.195, -.40]:
        for i in range(25):
            angle = math.pi * i / 24
            vertices.append((.16 * math.cos(angle), y, height + .16 * math.sin(angle)))
    faces = [(i, i + 1, i + 26, i + 25) for i in range(24)]
    mesh = bpy.data.meshes.new('Hood mesh')
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new('Hood_' + name, mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(black)
    mod = obj.modifiers.new('Metal thickness', 'SOLIDIFY')
    mod.thickness = .012

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(ROOT / 'Assets/Models/traffic-signal.glb'),
    export_format='GLB', use_selection=True, use_active_scene=True, export_yup=True, export_apply=True)
bpy.data.libraries.write(str(ROOT / 'Art/traffic-signal.blend'), {scene})
bpy.context.window.scene = previous
print('ANTILA_SIGNAL_ASSET_OK: 4 m pole, three separate lenses, open sun hoods; preserved previous scene')
