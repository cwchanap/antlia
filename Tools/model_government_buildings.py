"""Run through Blender MCP after import_buildings.py. One GLB with spatial mesh chunks."""
import bpy
import json
import math
from pathlib import Path

ROOT = Path('/Users/chanwaichan/workspace/antila')


def build():
    global city_scene, previous_scene
    previous_scene = bpy.context.window.scene
    city_scene = bpy.data.scenes.get('CSDI_Kowloon') or bpy.data.scenes.new('CSDI_Kowloon')
    assert all(o.name.startswith(('District','Collision')) for o in city_scene.objects)
    for obj in list(city_scene.objects):
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0: bpy.data.meshes.remove(mesh)
    bpy.context.window.scene = city_scene
    atlas = bpy.data.images.load(str(ROOT / 'Assets/Textures/building-facades.png'), check_existing=True)
    atlas.pack()
    materials = []
    for index, tint in enumerate([(1,1,1),(.82,.88,.88),(1,.91,.79),(.86,.91,.86)]):
        material = bpy.data.materials.get('CSDI_facade_' + str(index)) or bpy.data.materials.new('CSDI_facade_' + str(index))
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        material.node_tree.links.new(bsdf.outputs['BSDF'], nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
        bsdf.inputs['Roughness'].default_value = .87
        texture = nodes.new('ShaderNodeTexImage'); texture.image = atlas
        mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1
        mix.inputs[2].default_value = (*tint, 1)
        material.node_tree.links.new(texture.outputs['Color'], mix.inputs[1])
        material.node_tree.links.new(mix.outputs[0], bsdf.inputs['Base Color'])
        materials.append(material)
    roof = bpy.data.materials.new('CSDI_roof_concrete'); roof.diffuse_color = (.25,.28,.27,1)
    roof.use_nodes = True; roof.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.25,.28,.27,1)
    roof.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95
    materials.append(roof)
    shop = bpy.data.materials.new('CSDI_shopfront'); shop.use_nodes = True
    texture = shop.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(ROOT/'Assets/Textures/cafe-storefront.png'),check_existing=True); texture.image.pack()
    shop.node_tree.links.new(texture.outputs['Color'],shop.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    shop.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .8
    materials.append(shop)
    chunks = {}
    buildings = json.loads((ROOT / 'Data/building-layout.json').read_text())['buildings']
    for b in buildings:
        key = tuple(math.floor(v/128) for v in b['center'])
        if key not in chunks:
            chunks[key] = ([], [], [], [], [], []) # visual vertices/faces/UVs/materials, collision vertices/faces
        vertices, faces, uvs, indices, cv, cf = chunks[key]
        ox, oz = key[0]*128, key[1]*128
        def vertex(p, h): return (p[0]-ox, -p[1]+oz, h)
        def face(points, uv, material):
            start = len(vertices); vertices.extend(points)
            faces.append(tuple(range(start, start+len(points)))); uvs.extend(uv); indices.append(material)
        def collision(points):
            start = len(cv); cv.extend(points); cf.append(tuple(range(start, start+len(points))))
        height = b['height']
        style = b['style']
        u0 = .5 if style in (1,3) else 0
        v0 = .5 if style in (0,1) else 0
        for ring_index, ring in enumerate(b['rings']):
            for edge_index, (a, end) in enumerate(zip(ring, ring[1:]+ring[:1])):
                width = math.dist(a,end)
                if width < .015: continue
                collision([vertex(end,0), vertex(a,0), vertex(a,height), vertex(end,height)])
                base = 3.3 if ring_index==0 and b['frontage'][edge_index] and height>8 and b['id']%3!=1 else 0
                if base:
                    for col in range(max(1,math.ceil(width/10))):
                        start, finish = col*10, min(width,(col+1)*10)
                        p = [a[d]+(end[d]-a[d])*start/width for d in (0,1)]
                        q = [a[d]+(end[d]-a[d])*finish/width for d in (0,1)]
                        span = (finish-start)/10
                        face([vertex(q,0),vertex(p,0),vertex(p,base),vertex(q,base)],[(span,0),(0,0),(0,1),(span,1)],5)
                columns, rows = max(1,math.ceil(width/6)), max(1,math.ceil((height-base)/6.4))
                for col in range(columns):
                    start, finish = col*6, min(width,(col+1)*6)
                    p = [a[d]+(end[d]-a[d])*start/width for d in (0,1)]
                    q = [a[d]+(end[d]-a[d])*finish/width for d in (0,1)]
                    for row in range(rows):
                        lo, hi = base+row*6.4, min(height,base+(row+1)*6.4)
                        u1 = u0+.002+.496*(finish-start)/6
                        v1 = v0+.002+.496*(hi-lo)/6.4
                        assert u0 < u1 <= u0+.5 and v0 < v1 <= v0+.5
                        face([vertex(q,lo),vertex(p,lo),vertex(p,hi),vertex(q,hi)],
                             [(u0+.002,v0+.002),(u1,v0+.002),(u1,v1),(u0+.002,v1)], b['id']%4)
                # Recess-free thin parapet face stays on the legal footprint boundary.
                face([vertex(end,height),vertex(a,height),vertex(a,height+.55),vertex(end,height+.55)], [(0,0)]*4, 4)
                face([vertex(a,height),vertex(end,height),vertex(end,height+.55),vertex(a,height+.55)], [(0,0)]*4, 4)
        for triangle in b['roof']:
            points = [vertex(p,height) for p in reversed(triangle)]
            face(points, [(0,0)]*3, 4); collision(points)
        if b['roof_clearance']>3 and height>12 and b['id']%3==0:
            # Small rooftop plant rooms add depth without changing the surveyed main massing.
            x,z = b['center']
            corners = [[x-1.5,z-1],[x+1.5,z-1],[x+1.5,z+1],[x-1.5,z+1]]
            face([vertex(p,height+1.7) for p in reversed(corners)],[(0,0)]*4,4)
            for a,end in zip(corners,corners[1:]+corners[:1]):
                face([vertex(end,height),vertex(a,height),vertex(a,height+1.7),vertex(end,height+1.7)],[(0,0)]*4,4)
    for key, (vertices, faces, uvs, indices, cv, cf) in chunks.items():
        for prefix, verts, fs in [('District',vertices,faces),('Collision',cv,cf)]:
            mesh = bpy.data.meshes.new(f'{prefix}_{key[0]}_{key[1]}')
            mesh.from_pydata(verts, [], fs); mesh.update()
            obj = bpy.data.objects.new(mesh.name, mesh); city_scene.collection.objects.link(obj)
            obj.location = (key[0]*128, -key[1]*128, 0)
            if prefix == 'District':
                for m in materials: mesh.materials.append(m)
                layer = mesh.uv_layers.new(name='UVMap')
                for loop, uv in zip(layer.data, uvs): loop.uv = uv
                for polygon, index in zip(mesh.polygons,indices): polygon.material_index = index
    print(f'BLENDER_CITY_READY: {len(buildings)} building parts, {len(chunks)} spatial chunks, {sum(len(c[1]) for c in chunks.values())} visual faces')
    bpy.context.window.scene = previous_scene


def export():
    current_scene = bpy.context.window.scene
    try:
        bpy.context.window.scene = city_scene
        bpy.ops.object.select_all(action='DESELECT')
        for obj in city_scene.objects: obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(ROOT/'Assets/Models/kowloon-buildings.glb'),
                                  export_format='GLB', use_selection=True, use_active_scene=True, export_yup=True)
        bpy.data.libraries.write(str(ROOT/'Art/kowloon-buildings.blend'), {city_scene}, fake_user=True)
        print('BLENDER_CITY_EXPORTED: kowloon-buildings.glb and editable blend')
    finally:
        bpy.context.window.scene = current_scene


if __name__ == '__main__':
    build()
    export()
