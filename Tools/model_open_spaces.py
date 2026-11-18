"""Run through Blender MCP. Authored fittings on the retained iB1000 sports outlines.

Ground colours use the terrain mask; this GLB contains only markings and furniture.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
MARKING_WIDTH=.11
BASKETBALL_CIRCLE_RADIUS=1.8
BASKETBALL_KEY_DEPTH=5.8
BASKETBALL_MARKING_GAP=.1
GATEBALL_IDS={'1500001863','1500001864'}


def basketball_marking_parameters(length):
    half_length=length/2-.3
    line_clearance=MARKING_WIDTH+BASKETBALL_MARKING_GAP
    radius=min(BASKETBALL_CIRCLE_RADIUS,max(0,(half_length-2*line_clearance)/3))
    free_throw_offset=max(half_length-BASKETBALL_KEY_DEPTH,2*radius+line_clearance)
    return half_length,radius,free_throw_offset


def validate_basketball_markings(sports):
    parameters={}
    adjusted=[]
    for court in sports:
        if court['usage']!='BAC':continue
        half_length,radius,offset=basketball_marking_parameters(court['length'])
        legacy_offset=half_length-BASKETBALL_KEY_DEPTH
        legacy_circle_gap=legacy_offset-2*BASKETBALL_CIRCLE_RADIUS-MARKING_WIDTH
        legacy_baseline_gap=half_length-legacy_offset-BASKETBALL_CIRCLE_RADIUS-MARKING_WIDTH
        legacy_clear=(legacy_offset>0 and legacy_circle_gap>=BASKETBALL_MARKING_GAP and
                      legacy_baseline_gap>=BASKETBALL_MARKING_GAP)
        circle_gap=offset-2*radius-MARKING_WIDTH
        baseline_gap=half_length-offset-radius-MARKING_WIDTH
        assert offset>0 and offset<half_length,\
            f'{court["source_id"]}: basketball key crosses midcourt or court baseline'
        assert circle_gap>=BASKETBALL_MARKING_GAP-1e-8,\
            f'{court["source_id"]}: basketball circle strokes overlap'
        assert baseline_gap>=BASKETBALL_MARKING_GAP-1e-8,\
            f'{court["source_id"]}: basketball free-throw circle approaches the baseline stroke'
        if legacy_clear:
            assert radius==BASKETBALL_CIRCLE_RADIUS and offset==legacy_offset,\
                f'{court["source_id"]}: standard basketball markings changed unnecessarily'
        else:
            adjusted.append(court['source_id'])
        parameters[court['source_id']]=(radius,offset)
    return parameters,adjusted


def build(region='mong-kok'):
    defaults={
        'mong-kok':(ROOT/'Data/mong-kok-open-spaces.json',ROOT/'Assets/Models/mong-kok-recreation.glb',ROOT/'Art/mong-kok-recreation.blend'),
        'east-kowloon':(ROOT/'Data/east-kowloon-open-spaces.json',ROOT/'Assets/Models/east-kowloon-recreation.glb',ROOT/'Art/east-kowloon-recreation.blend')}
    if region not in defaults:raise ValueError('Unknown recreation region: '+region)
    data_path,asset_path,blend_path=defaults[region]
    previous=bpy.context.window.scene
    scene=bpy.data.scenes.new('Antila_'+region.replace('-','_')+'Recreation')
    bpy.context.window.scene=scene
    try:
        materials=[]
        for name,color in [('Court chalk',(.84,.85,.77)),('Painted dark green steel',(.045,.12,.10)),
                           ('Goal and backboard',(.72,.75,.70)),('Hoop orange',(.8,.23,.035)),('Net cord',(.37,.43,.39))]:
            mat=bpy.data.materials.new(name);mat.use_nodes=True
            bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.85
            materials.append(mat)
        data=json.loads(data_path.read_text())
        basketball_markings,adjusted_basketball_ids=validate_basketball_markings(data['sports'])
        if region=='east-kowloon':
            assert len(basketball_markings)==30 and len(adjusted_basketball_ids)==2,\
                'Reviewed east-Kowloon BAC inventory or dimension-adjusted count changed'
        checked_marking_vertices=0
        for court in data['sports']:
            vertices=[];faces=[];indices=[];cv=[];cf=[]
            forward=Vector(court['forward']);right=Vector((forward.y,-forward.x))
            source_forward=forward.copy();source_right=right.copy()
            center=Vector(court['center']);shift=Vector((0,0))
            def point(p):
                q=shift+right*p[0]+forward*p[1]
                return (q.x,-q.y,p[2])
            def face(points,mat,solid=False):
                if mat==0:points=list(reversed(points))  # Blender +Z faces upward after converting game -Z north.
                start=len(vertices);vertices.extend(point(p) for p in points)
                faces.append(tuple(range(start,start+len(points))));indices.append(mat)
                if solid:
                    start=len(cv);cv.extend(point(p) for p in points);cf.append(tuple(range(start,start+len(points))))
            def beam(a,b,radius=.04,mat=1,solid=True):
                a,b=Vector(a),Vector(b);axis=(b-a).normalized()
                tangent=axis.cross(Vector((0,0,1)))
                if tangent.length<.1:tangent=axis.cross(Vector((1,0,0)))
                tangent.normalize();normal=axis.cross(tangent)
                ring=[(tangent*math.cos(i*math.tau/8)+normal*math.sin(i*math.tau/8))*radius for i in range(8)]
                face([a+p for p in reversed(ring)],mat,solid);face([b+p for p in ring],mat,solid)
                for i,p in enumerate(ring):
                    q=ring[(i+1)%8];face([a+p,a+q,b+q,b+p],mat,solid)
            def stripe(a,b,width=MARKING_WIDTH):
                a,b=Vector(a),Vector(b);d=b-a
                if d.length<.001:return
                n=Vector((-d.y,d.x)).normalized()*width/2
                face([(p.x,p.y,.045) for p in (a+n,a-n,b-n,b+n)],0)
            def loop(points):
                for a,b in zip(points,points[1:]+points[:1]):stripe(a,b)
            def rectangle(x0,y0,x1,y1):loop([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])
            def circle(x,y,r):loop([(x+math.cos(i*math.tau/48)*r,y+math.sin(i*math.tau/48)*r) for i in range(48)])
            def net(x0,x1,y,height):
                for x in range(math.ceil(x0*3),math.floor(x1*3)+1):beam((x/3,y,.1),(x/3,y,height),.008,4,False)
                for h in range(1,math.ceil(height*3)+1):beam((x0,y,h/3),(x1,y,h/3),.008,4,False)
            def football(width,length,goal_width=None):
                w=width/2-1.4;l=length/2-1.4
                assert length>width, 'Football goal lines must lie on the shorter sides'
                rectangle(-w,-l,w,l);stripe((-w,0),(w,0));circle(0,0,min(5,w*.28))
                goal=goal_width if goal_width is not None else 3 if length<40 else min(6,w*.4)
                for end in (-1,1):
                    y=end*l;back=y+end*1
                    rectangle(-goal,y,goal,y-end*min(9,l*.32))
                    for x in (-goal/2,goal/2):
                        beam((x,y,0),(x,y,2.1),.055,2);beam((x,y,2.1),(x,back,.1),.025,2)
                    beam((-goal/2,y,2.1),(goal/2,y,2.1),.055,2)
                    net(-goal/2,goal/2,back,1.8)
            w=court['width']/2-.3;l=court['length']/2-.3
            if court['usage']=='FOF':
                if court['source_id'] in GATEBALL_IDS:
                    # Gate and centre-pole fittings are sized from the WGU rules.
                    rectangle(-w,-l,w,l)
                    for x,y,dx,dy in ((-w+4,l-2,0,.115),(w-2,l-12,.115,0),(-w+2,0,.115,0)):
                        for side in (-1,1):
                            leg=(x+side*dx,y+side*dy)
                            beam((*leg,0),(*leg,.195),.005,2)
                        beam((x-dx,y-dy,.195),(x+dx,y+dy,.195),.005,2)
                    beam((0,0,0),(0,0,.2),.01,2)
                elif court['site']=='1503005174':
                    # Split the combined source outline, then run each pitch across it.
                    # Keep five-a-side goals even though the corrected length exceeds 40 m.
                    split_axis=forward.copy();forward,right=right,-forward
                    for offset in (-court['length']/4,court['length']/4):
                        shift=split_axis*offset
                        start=len(vertices)
                        football(court['length']/2,court['width'],goal_width=3)
                        for x,y,z in vertices[start:]:
                            p=Vector((x,-y));along=p.dot(split_axis);across=p.dot(forward)
                            assert abs(along-offset)<court['length']/4 and abs(across)<court['width']/2, 'Split pitch fitting leaves its source half'
                else:football(court['width'],court['length'])
            else:
                rectangle(-w,-l,w,l);stripe((-w,0),(w,0))
                if court['usage']=='TEC':
                    for x in (-w*.75,w*.75):stripe((x,-l),(x,l))
                    for y in (-l*.55,l*.55):stripe((-w*.75,y),(w*.75,y))
                    stripe((0,-l*.55),(0,l*.55))
                    for x in (-w,w):beam((x,0,0),(x,0,1.08),.05)
                    beam((-w,0,.96),(w,0,.96),.022,2,False);net(-w,w,0,.9)
                else:
                    circle_radius,free_throw_offset=basketball_markings[court['source_id']]
                    circle(0,0,circle_radius)
                    # Keep the penalty box and its stroke inside the fitted rectangle on narrow courts.
                    penalty_half_width=min(2.45,max(0,w-MARKING_WIDTH/2))
                    assert penalty_half_width+MARKING_WIDTH/2<=w+1e-8, 'Narrow court penalty marking exceeds the safe fit'
                    for end in (-1,1):
                        y=end*(l-.8);free_throw_y=end*free_throw_offset
                        rectangle(-penalty_half_width,end*l,penalty_half_width,free_throw_y)
                        circle(0,free_throw_y,circle_radius)
                        beam((0,end*(l-.15),0),(0,end*(l-.15),3.8),.09)
                        beam((0,end*(l-.15),3.5),(0,y,3.5),.07)
                        face([(-.9,y,2.9),(.9,y,2.9),(.9,y,4),(-.9,y,4)],2,True)
                        hoop=y-end*.43
                        for i in range(20):
                            a=i*math.tau/20;b=(i+1)*math.tau/20
                            beam((.23*math.cos(a),hoop+.23*math.sin(a),3.05),(.23*math.cos(b),hoop+.23*math.sin(b),3.05),.018,3,False)
            for face_indices,material_index in zip(faces,indices):
                if material_index!=0:continue
                for vertex_index in face_indices:
                    x,y,_=vertices[vertex_index];local=Vector((x,-y))
                    across=abs(local.dot(source_right));along=abs(local.dot(source_forward))
                    assert across<=court['width']/2+1e-5 and along<=court['length']/2+1e-5, \
                        f'{court["source_id"]}: court paint leaves its fitted source rectangle'
                    checked_marking_vertices+=1
            for name,vs,fs,mi in [('Court',vertices,faces,indices),('Collision',cv,cf,None)]:
                mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update()
                bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
                if mi is not None:
                    for mat in materials:mesh.materials.append(mat)
                    for poly,index in zip(mesh.polygons,mi):poly.material_index=index
                obj=bpy.data.objects.new(name+'_'+court['source_id'],mesh);scene.collection.objects.link(obj)
                obj.location=(center.x,-center.y,0)
        # Authored pavement games; separate from the government sports outlines.
        # Paint has no raised collision geometry and cannot obstruct the garden paths.
        for play in data.get('play_areas',[]):
            center=Vector(play['center']);forward=Vector(play['forward']);right=Vector((forward.y,-forward.x))
            vertices=[];faces=[]
            def stripe(a,b,width=.08):
                a,b=Vector(a),Vector(b);n=Vector((-(b-a).y,(b-a).x)).normalized()*width/2
                points=[]
                for p in (a+n,b+n,b-n,a-n):
                    q=right*p.x+forward*p.y;points.append((q.x,-q.y,.045))
                start=len(vertices);vertices.extend(points);faces.append(tuple(range(start,start+4)))
            def loop(points):
                for a,b in zip(points,points[1:]+points[:1]):stripe(a,b)
            for row in range(7):
                for x in ([-1,0] if row in (2,4,6) else [-.5]):
                    z=-5+row
                    loop([(x,z),(x+1,z),(x+1,z+.95),(x,z+.95)])
            for radius in (1,2):
                loop([(math.cos(i*math.tau/48)*radius,4+math.sin(i*math.tau/48)*radius) for i in range(48)])
            assert all(abs(Vector((x,-y)).dot(right))<play['width']/2 and
                       abs(Vector((x,-y)).dot(forward))<play['length']/2 for x,y,z in vertices)
            mesh=bpy.data.meshes.new('Play markings');mesh.from_pydata(vertices,[],faces);mesh.materials.append(materials[0])
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();mesh.update()
            obj=bpy.data.objects.new('Play_'+play['site'],mesh);scene.collection.objects.link(obj);obj.location=(center.x,-center.y,0)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in scene.objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=next(iter(scene.objects))
        print('ANTILA_RECREATION_PAINT_BOUNDS_OK:',region,checked_marking_vertices,'marking vertices within fitted source rectangles')
        print('ANTILA_RECREATION_BASKETBALL_MARKINGS_OK:',region,len(basketball_markings),'BAC courts;',
              len(adjusted_basketball_ids),'dimension-adjusted:',','.join(adjusted_basketball_ids) or 'none')
        bpy.ops.export_scene.gltf(filepath=str(asset_path),export_format='GLB',
            use_selection=True,use_active_scene=True,export_yup=True,export_apply=True)
        bpy.data.libraries.write(str(blend_path),{scene})
        print('ANTILA_RECREATION_MODEL_OK:',region,len(data['sports']),'courts;',len(data.get('play_areas',[])),'authored play markings;',len(scene.objects),'objects')
    finally:bpy.context.window.scene=previous


if __name__=='__main__':build()
