"""Run through Blender MCP after downloading the free Renderpeople sources.
See docs/PASSENGER_ASSETS.md for source URLs and usage restrictions.
Creates an isolated scene; never modifies the user's existing Blender scenes.
"""
import bpy
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path('/Users/chanwaichan/workspace/antila')
SOURCES = ROOT/'Art/Passengers'
scene = bpy.data.scenes.new('Antila_Passengers')
bpy.context.window.scene = scene

models = [
    ('mei', 'rp_mei_posed_001', 'rp_mei_posed_001_30k.obj'),
    ('dennis', 'rp_dennis_posed_004', 'rp_dennis_posed_004_30k.obj'),
    ('family', 'rp_fabienne_percy_posed_001', 'rp_fabienne_percy_posed_001_60k.obj'),
    ('headphones', 'rp_posed_00178_29', 'rp_posed_00178_29.glb'),
]

for name, source, filename in models:
    for obj in scene.objects:
        obj.hide_set(True)
    before = set(scene.objects)
    path = SOURCES/source/filename
    if path.suffix == '.obj':
        bpy.ops.wm.obj_import(filepath=str(path),forward_axis='NEGATIVE_Z',up_axis='Y')
    else:
        bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [o for o in scene.objects if o not in before and o.type == 'MESH']
    assert imported, f'No meshes imported from {path}'
    for obj in imported:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
    bpy.ops.object.select_all(action='DESELECT')
    for obj in imported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    if len(imported)>1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = 'Passenger_'+name
    if path.suffix == '.obj':
        obj.scale *= .01  # Source OBJ coordinates are centimetres.
    else:
        obj.scale *= 10  # This supplied GLB is 0.1725 m tall after its node scale.
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    low = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    obj.location -= Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    assert 1.5 < obj.dimensions.z < 2.1, f'Incorrect passenger height: {obj.dimensions.z}'
    assert obj.data.uv_layers.active is not None
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(math.isfinite(c) for item in obj.data.uv_layers.active.data for c in item.uv)

    # A single supplied diffuse texture contains the scan's skin, hair and clothes.
    material = bpy.data.materials.new('Antila_passenger_'+name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .85
    texture = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture_path = SOURCES/source/'tex'/(source+('_dif_2k.jpg' if path.suffix=='.obj' else '_basecolor.jpg'))
    texture.image = bpy.data.images.load(str(texture_path),check_existing=True)
    texture.image.pack()
    material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.material_index = 0
        face.use_smooth = True
    obj.data.calc_loop_triangles()
    assert len(obj.data.loop_triangles) <= 125000
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'Assets/Models'/('passenger_'+name+'.glb')),
        export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True)
    print('PASSENGER_EXPORTED',name,'height',round(obj.dimensions.z,3),'triangles',len(obj.data.loop_triangles))

# A source lineup makes each imported passenger easy to inspect in Blender.
for index, obj in enumerate(scene.objects):
    obj.hide_set(False)
    obj.location.x = index*1.5
bpy.data.libraries.write(str(ROOT/'Art/passengers.blend'),{scene})
print('ANTILA_PASSENGERS_OK')
