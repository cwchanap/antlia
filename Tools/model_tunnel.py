"""Execute through Blender MCP. Government XY geometry, authored tunnel structure, metres."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path('/Users/chanwaichan/workspace/antila')
data = json.loads((ROOT/'Data/cross-harbour.json').read_text())
previous = bpy.context.window.scene
if previous.name.startswith('Antila_CrossHarbour'):
    previous=bpy.data.scenes.get(previous.get('antila_previous_scene','')) or next(s for s in bpy.data.scenes if not s.name.startswith('Antila_CrossHarbour'))
    bpy.context.window.scene=previous
try:
    for old in list(bpy.data.scenes):
        if old.name.startswith('Antila_CrossHarbour') and old != previous:
            for obj in list(old.objects): bpy.data.objects.remove(obj,do_unlink=True)
            bpy.data.scenes.remove(old)
    scene = bpy.data.scenes.new('Antila_CrossHarbour')
    scene['antila_previous_scene']=previous.name
    bpy.context.window.scene = scene


    def material(name, color, texture=None, emission=0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (*color,1)
        bs.inputs['Roughness'].default_value = .8
        if texture:
            tex = m.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(str(ROOT/'Assets/Textures'/texture),check_existing=True)
            tex.image.pack()
            m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        if emission:
            bs.inputs['Emission Color'].default_value = (*color,1)
            bs.inputs['Emission Strength'].default_value = emission
        return m


    asphalt = material('CHT_asphalt',(.09,.10,.10),'asphalt.png')
    tiles = material('CHT_ceramic',(.65,.63,.54),'tunnel-tiles.png')
    concrete = material('CHT_concrete',(.19,.21,.20))
    white = material('CHT_lane_white',(.82,.81,.67))
    lamp = material('CHT_lamp',(.85,.96,1),emission=3)
    amber = material('CHT_reflector',(.94,.57,.08),emission=.7)


    def mesh(name, vertices, faces, mat, uvs=None):
        m = bpy.data.meshes.new(name)
        m.from_pydata([(p[0],-p[2],p[1]) for p in vertices],[],faces)
        m.materials.append(mat)
        uv = m.uv_layers.new()
        for f in m.polygons:
            for li in f.loop_indices:
                vi = m.loops[li].vertex_index
                p = vertices[vi]
                uv.data[li].uv = uvs[vi] if uvs else (p[0]/2,p[2]/2)
        obj = bpy.data.objects.new(name,m)
        scene.collection.objects.link(obj)
        return obj


    # One triangulated surface with portal openings, used for both visible ground and physics.
    ground = [Vector((p[0],0,p[1])) for tri in data['ground_triangles'] for p in tri]
    faces = []
    for i in range(0,len(ground),3):
        a,b,c = ground[i:i+3]
        faces.append((i,i+1,i+2) if (b-a).cross(c-a).y>0 else (i,i+2,i+1))
    mesh('HarbourGround',ground,faces,concrete)
    water = material('CHT_water',(.045,.16,.20))
    water.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .3
    vertices = [Vector((p[0],-2,p[1])) for tri in data['water_triangles'] for p in tri]
    water_faces=[]
    for i in range(0,len(vertices),3):
        a,b,c=vertices[i:i+3]
        water_faces.append((i,i+1,i+2) if (b-a).cross(c-a).y>0 else (i,i+2,i+1))
    mesh('HarbourWater',vertices,water_faces,water)
    vertices = [Vector((p[0],.035,p[1])) for tri in data['surface_triangles'] for p in tri]
    faces=[]
    for i in range(0,len(vertices),3):
        a,b,c=vertices[i:i+3]
        faces.append((i,i+1,i+2) if (b-a).cross(c-a).y>0 else (i,i+2,i+1))
    mesh('RoadSurface',vertices,faces,asphalt)

    model_roads = [r for r in data['roads'] if not r['tunnel']]
    for tube in data['tubes']:
        parts = [next(r for r in data['roads'] if r['id']==ident) for ident in tube['model_source_ids']]
        model_roads.append(dict(parts[0],points=[p for i,r in enumerate(parts) for p in r['points'][0 if i==0 else 1:]]))
    for road in model_roads:
        points = [Vector(p) for p in road['points']]
        if road['tunnel']:
            # Resample across source joins: a tiny final source segment can fold a wide road quad.
            import bisect
            arc=[0]
            for a,b in zip(points,points[1:]):arc.append(arc[-1]+(b-a).length)
            sampled=[]
            for d in [min(i*4,arc[-1]) for i in range(math.ceil(arc[-1]/4)+1)]:
                j=min(len(points)-2,max(0,bisect.bisect_right(arc,d)-1))
                sampled.append(points[j].lerp(points[j+1],(d-arc[j])/(arc[j+1]-arc[j])))
            points=sampled
        half = road['width']/2
        rights = []
        for i,p in enumerate(points):
            direction = points[min(i+1,len(points)-1)]-points[max(0,i-1)]
            rights.append(Vector((-direction.z,0,direction.x)).normalized())
        distance = [0]
        for a,b in zip(points,points[1:]): distance.append(distance[-1]+(b-a).length)

        def strip(name, offsets, mat, reverse=False):
            vs,fs,uvs = [],[],[]
            for i,(p,r) in enumerate(zip(points,rights)):
                for x,y in offsets:
                    vs.append(p+r*x+Vector((0,y,0)))
                    uvs.append((distance[i]/2,(y if 'Wall' in name else x)/2))
            for i in range(len(points)-1):
                face=(2*i,2*i+1,2*i+3,2*i+2)
                fs.append(tuple(reversed(face)) if reverse else face)
            if name=='Road' and road['tunnel']:
                for a,b,c,d in fs:
                    for i,j,k in [(a,b,c),(a,c,d)]:
                        normal=(vs[j]-vs[i]).cross(vs[k]-vs[i])
                        assert normal.y > normal.length*.97, (road['id'],'folded or steep floor triangle',i)
            mesh(name+'_'+road['id'],vs,fs,mat,uvs)

        if road['tunnel']:strip('Road',[(-half,.035),(half,.035)],asphalt)
        if road['tunnel']:
            strip('WallLeft',[(-half,5.6),(-half,.035)],tiles)
            strip('WallRight',[(half,.035),(half,5.6)],tiles)
            strip('Ceiling',[(-half,5.6),(half,5.6)],concrete,True)
            # Continuous raised service ledges leave a 7.3 m carriageway inside each tube.
            strip('KerbLeft',[(-half,.28),(-3.95,.28)],concrete)
            strip('KerbRight',[(3.95,.28),(half,.28)],concrete)
        # Repeating paint and fixtures are joined per source section, not individual nodes.
        for tag,mat in [('Paint',white),('Lamps',lamp),('Reflectors',amber)]:
            vs,fs = [],[]
            for i in range(len(points)-1):
                if tag=='Paint':
                    # Solid lane divider inside the tunnel, broken lines on approaches.
                    if not road['tunnel'] and i%3:continue
                    specs=[(-.065,.065,.055)]
                    if road['tunnel']:specs += [(-3.78,-3.66,.055),(3.66,3.78,.055)]
                    for left,right,y in specs:
                        a=points[i];b=points[i+1]
                        q=[a+rights[i]*left,a+rights[i]*right,b+rights[i+1]*right,b+rights[i+1]*left]
                        k=len(vs);vs.extend(p+Vector((0,y,0)) for p in q);fs.append((k,k+1,k+2,k+3))
                elif road['tunnel'] and i%(3 if tag=='Lamps' else 5)==0:
                    for side in [-1,1]:
                        p=points[i];r=rights[i];f=(points[i+1]-p).normalized()
                        y=4.8 if tag=='Lamps' else .7
                        length=1.2 if tag=='Lamps' else .13
                        height=.09 if tag=='Lamps' else .08
                        c=p+r*(half-.025)*side+Vector((0,y,0))
                        k=len(vs);vs.extend([c-f*length,c+f*length,c+f*length+Vector((0,height,0)),c-f*length+Vector((0,height,0))]);fs.append((k,k+1,k+2,k+3))
            if vs:mesh(tag+'_'+road['id'],vs,fs,mat)

    # Portal frames are authored in the scene using the same world-space endpoints.
    for tube in data['tubes']:
        section = next(r for r in data['roads'] if r['id']==tube['model_source_ids'][0])
        p=Vector(section['points'][0]);f=(Vector(section['points'][1])-p).normalized()
        yaw=math.atan2(f.x,-f.z)
        for side in [-1,1]:
            r=Vector((-f.z,0,f.x)).normalized()
            at=p+r*side*5.15+Vector((0,3.05,0))
            bpy.ops.mesh.primitive_cube_add(size=1,location=(at.x,-at.z,at.y))
            obj=bpy.context.object;obj.name='PortalPillar';obj.dimensions=(1.2,3.5,6.1);obj.rotation_euler.z=-yaw
            obj.data.materials.append(concrete)
        bpy.ops.mesh.primitive_cube_add(size=1,location=(p.x,-p.z,6.1))
        obj=bpy.context.object;obj.name='PortalLintel';obj.dimensions=(11.5,3.5,1);obj.rotation_euler.z=-yaw;obj.data.materials.append(concrete)

    objects=list(scene.objects)
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'Assets/Models/cross-harbour.glb'),export_format='GLB',
        use_selection=True,use_active_scene=True,export_yup=True,export_apply=True)
    bpy.data.libraries.write(str(ROOT/'Art/cross-harbour.blend'),{scene})
    print('ANTILA_TUNNEL_MODEL_OK:',len(objects),'isolated objects; government alignment, two tubes, ceramic walls and lamps')
finally:
    bpy.context.window.scene=previous
