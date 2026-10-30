"""Offline Mong Kok recreation sites. .venv-geodata/bin/python Tools/import_open_spaces.py.

To extract downloaded iB1000 sheets first: --extract CACHE_DIR TILE_SOURCES_JSON.
Source site/pitch outlines are retained; paths, planting and furniture are authored.
"""
import hashlib
import json
import math
import random
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely import constrained_delaunay_triangles, make_valid, union_all
from shapely.geometry import Polygon, LineString, Point, shape, box
from shapely.ops import nearest_points, polylabel
from import_map import ROOT, ORIGIN, local
from import_buildings import polygons

SOURCE = ROOT/'Data/mong-kok-open-spaces-source.geojson'
TARGET = ROOT/'Data/mong-kok-open-spaces.json'
SITES = {'1503005174':'Anchor Street Playground', '1503005482':'MacPherson Playground',
         '1503005201':'Cherry Street Park', '1503005534':"Diocesan Boys' School grounds",
         '1503005143':'Ivy Street Rest Garden', '1503005266':'Mong Kok Road Playground',
         '1503005193':'Cherry Street Sitting-out Area', '1503005468':'Sai Yee Street Garden',
         '1810041992':'Waterloo Road/Ferry Street Sitting-out Area'}
POCKET_SITES = frozenset(('1503005143','1503005266','1503005193','1503005468','1810041992'))
NS = {'g':'http://www.opengis.net/gml','f':'http://www.safe.com/gml/fme'}
KINDS = {'FOF':'field','BAC':'court','TEC':'court','RAT':'track'}
BOUNDS = box(-1100,-3400,650,-1850)
# Complete iB1000 sheet selection for these nine sites and their surrounding extent.
# Keep this explicit alongside SITES/BOUNDS: presence of a site ID cannot prove all its tile pieces arrived.
TILES = frozenset(('11-NW-14C','11-NW-14D','11-NW-15C','11-NW-19A','11-NW-19B','11-NW-20A',
                   '11-NW-24A','11-NW-24B','11-NW-25A','11-NW-19C','11-NW-19D','11-NW-20C'))


def validate_manifest(metadata):
    rows=metadata.get('tiles',[])
    names=[row.get('tile') for row in rows]
    if len(names)!=len(TILES) or set(names)!=TILES:
        raise ValueError('Incomplete or duplicate Mong Kok sheet selection; expected all twelve iB1000 sheets')


def encoded(data):return json.dumps(data,separators=(',',':'),allow_nan=False).encode('utf-8')


def extract(cache, manifest):
    metadata=json.loads(manifest.read_text())
    validate_manifest(metadata)
    transform=Transformer.from_crs(2326,4326,always_xy=True)
    features=[]
    def ring(element):
        result=[]
        for node in element.findall('.//g:posList',NS):
            values=list(map(float,node.text.split()))
            assert len(values)%3==0 and all(math.isfinite(v) for v in values)
            line=[list(transform.transform(values[i+1],values[i])) for i in range(0,len(values),3)]
            assert not result or math.dist(result[-1],line[0])<1e-8, 'Disconnected source ring'
            result.extend(line if not result else line[1:])
        assert len(result)>=4 and math.dist(result[0],result[-1])<1e-8, 'Open source ring'
        return result
    for row in metadata['tiles']:
        path=cache/(row['tile']+'.zip')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Government ZIP checksum mismatch: '+row['tile'])
        with zipfile.ZipFile(path) as archive:
            for layer in ('Site','BuiltStructurePolygon'):
                name=row['tile']+'/Layers/Buildings/'+layer+'.gml'
                if name not in archive.namelist():raise ValueError('Missing required government layer: '+name)
                doc=ET.fromstring(archive.read(name))
                if doc.tag!='{'+NS['g']+'}FeatureCollection':raise ValueError('Invalid government layer: '+name)
                assert all(e.get('srsName')=='EPSG:2326' for e in doc.iter() if e.get('srsName'))
                # Both layers are populated on every sheet in this fixed regional selection.
                # Empty exports or an unrecognized feature schema must not silently lose a tile piece.
                items=doc.findall('g:featureMember/f:'+layer,NS)
                if not items:raise ValueError('Empty or unrecognized government layer: '+name)
                for item in items:
                    props={e.tag.split('}')[-1]:e.text for e in item if e.tag.startswith('{'+NS['f']+'}')}
                    if props.get('STATUS')!='E':continue
                    if layer=='Site' and props.get('SITEID') not in SITES:continue
                    if layer=='BuiltStructurePolygon' and props.get('USAGETYPE') not in KINDS:continue
                    for patch in item.findall('.//g:PolygonPatch',NS):
                        rings=[ring(patch.find('g:exterior',NS)),*[ring(h) for h in patch.findall('g:interior',NS)]]
                        assert not make_valid(Polygon(rings[0],rings[1:])).is_empty
                        features.append(dict(type='Feature',properties=props|{'tile':row['tile'],'layer':layer},
                                             geometry=dict(type='Polygon',coordinates=rings)))
    sites=union_all([shape(f['geometry']) for f in features if f['properties']['layer']=='Site'])
    features=[f for f in features if f['properties']['layer']=='Site' or shape(f['geometry']).intersects(sites)]
    assert {f['properties']['SITEID'] for f in features if f['properties']['layer']=='Site'}==set(SITES)
    metadata.update(provider='Lands Department, HKSAR Government',origin_wgs84=ORIGIN,
        source='https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0/query',
        source_crs='EPSG:2326',axis_order='GML northing,easting,height; converted to WGS84',
        terms='https://portal.csdi.gov.hk/csdi-webpage/doc/TNC',
        note='Selected existing Site and BuiltStructurePolygon outlines. Feature dates may precede tile revision dates.')
    return encoded(dict(type='FeatureCollection',metadata=metadata,features=features))


def build(source):
    raw=json.loads(source);validate_manifest(raw['metadata']);groups=defaultdict(list);attributes={}
    for feature in raw['features']:
        props=feature['properties'];rings=feature['geometry']['coordinates']
        assert props['STATUS']=='E' and feature['geometry']['type']=='Polygon'
        poly=make_valid(Polygon([local(p) for p in rings[0]],[[local(p) for p in r] for r in rings[1:]]))
        key=(props['layer'],props.get('SITEID',props.get('BUILTSTRUCTUREPOLYGONID')))
        groups[key].append(poly);attributes[key]=props
    merged={key:union_all(parts) for key,parts in groups.items()}
    buildings=[];inputs={}
    for name in ('kowloon-north-layout','west-kowloon-layout'):
        path=ROOT/f'Data/{name}.json';inputs[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        buildings.extend(Polygon(b['rings'][0],b['rings'][1:]) for b in json.loads(path.read_text())['buildings'])
    lots=union_all([p for p in buildings if p.intersects(BOUNDS.buffer(20))])
    roadpath=ROOT/'Data/cross-harbour.json';inputs[str(roadpath.relative_to(ROOT))]=hashlib.sha256(roadpath.read_bytes()).hexdigest()
    roads=[];prop_roads=[]
    for road in json.loads(roadpath.read_text())['roads']:
        if road['tunnel'] and not road.get('ramp',False):continue
        line=LineString([(p[0],p[2]) for p in road['points']])
        if not line.intersects(BOUNDS.buffer(20)):continue
        roads.append(line.buffer(max(12,road['width'])/2+3.5,join_style='mitre'))
        prop_roads.append(line.buffer(max(12,road['width'])/2+8,join_style='mitre'))
    roads=union_all(roads);prop_roads=union_all(prop_roads)
    sites=[];surfaces=[];paving=[];fixtures=[];sports=[];gardens=[];play_areas=[];rng=random.Random(18102026)
    def rings(poly):return [list(poly.exterior.coords)[:-1],*[list(r.coords)[:-1] for r in poly.interiors]]
    def triangles(poly):
        faces=list(constrained_delaunay_triangles(poly).geoms)
        assert abs(sum(t.area for t in faces)-poly.area)<.01
        return [list(t.exterior.coords)[:-1] for t in faces]
    for site_id,name in SITES.items():
        site=merged['Site',site_id]
        assert site.is_valid and site.area>(500 if site_id in POCKET_SITES else 5000) and site.difference(BOUNDS).area<.1
        safe=site.difference(union_all([lots.buffer(4),roads]))
        pitches=[]
        for (layer,source_id),poly in merged.items():
            if layer!='BuiltStructurePolygon' or poly.intersection(site).area<4:continue
            kind=KINDS[attributes[layer,source_id]['USAGETYPE']]
            # LCSD lists these two playgrounds' football pitches as hard surface.
            if kind=='field' and site_id in ('1503005174','1503005482'):kind='court'
            clipped=poly.intersection(safe)
            for part in polygons(clipped):
                sample=part.representative_point()
                surfaces.append(dict(site=site_id,kind=kind,rings=rings(part),triangles=triangles(part),sample=[sample.x,sample.y]))
            pitches.append(poly.intersection(site))
            # Only fit goals/hoops and field markings to intact rectangular playing surfaces.
            rectangle=poly.minimum_rotated_rectangle
            if kind!='track' and clipped.area>poly.area*.98 and poly.area/rectangle.area>.9:
                coords=list(rectangle.exterior.coords)[:-1]
                if math.dist(coords[0],coords[1])>math.dist(coords[1],coords[2]):coords=coords[1:]+coords[:1]
                center=rectangle.centroid;axis=((coords[2][0]-coords[1][0]),(coords[2][1]-coords[1][1]));length=math.hypot(*axis)
                width=math.dist(coords[0],coords[1]);forward=[axis[0]/length,axis[1]/length]
                sports.append(dict(site=site_id,source_id=source_id,kind=kind,usage=attributes[layer,source_id]['USAGETYPE'],
                    center=[center.x,center.y],forward=forward,width=width,length=length))
        if site_id=='1503005266':
            # No sports outline is supplied here. This small play pad and its markings
            # are explicitly authored, kept separate from the sourced sports surfaces.
            center=polylabel(max(polygons(safe),key=lambda p:p.area),tolerance=.1)
            coords=list(site.minimum_rotated_rectangle.exterior.coords)
            dx,dz=coords[1][0]-coords[0][0],coords[1][1]-coords[0][1];length=math.hypot(dx,dz)
            forward=(dx/length,dz/length);right=(forward[1],-forward[0])
            corners=[(center.x+right[0]*x+forward[0]*z,center.y+right[1]*x+forward[1]*z) for x,z in [(-5,-7),(5,-7),(5,7),(-5,7)]]
            pad=Polygon(corners);assert safe.buffer(-1).covers(pad)
            play_areas.append(dict(site=site_id,kind='authored_play',center=[center.x,center.y],forward=forward,width=10,length=14,
                                   rings=rings(pad),triangles=triangles(pad),sample=[center.x,center.y]))
            pitches.append(pad)
        pitches=union_all(pitches)
        paths=union_all([site.boundary.buffer(3),pitches.boundary.buffer(2) if not pitches.is_empty else Polygon()]).intersection(safe).difference(pitches)
        if site_id in POCKET_SITES:
            # An authored circulation loop follows usable ground, including building
            # cutouts. Two crossing paths reach the sourced site edges and nearby paving.
            rect=list(site.minimum_rotated_rectangle.exterior.coords)
            c=site.minimum_rotated_rectangle.centroid
            axes=[((rect[i+1][0]-rect[i][0]),(rect[i+1][1]-rect[i][1])) for i in (0,1)]
            spines=union_all([LineString([(c.x-dx*2,c.y-dz*2),(c.x+dx*2,c.y+dz*2)]).buffer(2) for dx,dz in axes])
            paths=union_all([paths,safe.buffer(-1.8).boundary.buffer(1.8),spines]).intersection(safe).difference(pitches)
            assert paths.area>80
            samples=[[p.x,p.y] for p in (part.representative_point() for part in polygons(paths)) if paths.boundary.distance(p)>.6]
            assert samples
            gardens.append(dict(site=site_id,rings=[rings(p) for p in polygons(site)],paths=[rings(p) for p in polygons(paths)],
                                access=[rings(p) for p in polygons(spines.intersection(safe))],
                                samples=samples,paving_area_m2=round(paths.area,2)))
        for part in polygons(paths):paving.extend(triangles(part))
        pocket=site_id in POCKET_SITES
        radius=2.2 if pocket else 3
        planting=safe.difference(union_all([pitches.buffer(3 if pocket else 5),paths.buffer(radius),prop_roads])).buffer(-radius)
        if pocket:planting=safe.buffer(-radius).difference(union_all([pitches.buffer(3),paths.buffer(radius+.3),prop_roads]))
        props=[]
        xmin,zmin,xmax,zmax=site.bounds
        spacing=10 if pocket else 15;jitter=1.5 if pocket else 3
        for x in range(math.ceil(xmin/spacing)*spacing,math.floor(xmax),spacing):
            for z in range(math.ceil(zmin/spacing)*spacing,math.floor(zmax),spacing):
                p=Point(x+rng.uniform(-jitter,jitter),z+rng.uniform(-jitter,jitter))
                if planting.covers(p):
                    props.append(dict(site=site_id,asset='street-tree' if len(props)%3 else 'banyan',position=[p.x,p.y],yaw=rng.uniform(0,math.tau),radius=radius,scale=(.65 if len(props)%3 else .45) if pocket else (.85 if len(props)%3 else .65)))
        use_planters=pocket and not props
        for part in polygons(safe):
            boundary=part.exterior
            interior=part.buffer(-2)
            if interior.is_empty:continue
            for d in range(10,int(boundary.length),18 if pocket else 35):
                p=boundary.interpolate(d);q=nearest_points(p,interior)[1]
                if q.is_empty or not paths.buffer(1).covers(q) or prop_roads.distance(q)<2 or pitches.distance(q)<2:continue
                if pocket and spines.distance(q)<1.8:continue
                if any(Point(f['position']).distance(q)<f['radius']+2 for f in props):continue
                tangent=boundary.interpolate(min(d+1,boundary.length));yaw=math.atan2(-(tangent.x-p.x),-(tangent.y-p.y))
                planter=use_planters and len(props)%2==1
                props.append(dict(site=site_id,asset='planter' if planter else 'bench',position=[q.x,q.y],yaw=yaw,radius=1.8,scale=1))
        assert all(site.covers(Point(f['position'])) and lots.distance(Point(f['position']))>f['radius'] and roads.distance(Point(f['position']))>f['radius'] for f in props)
        fixtures.extend(props)
        sites.append(dict(id=site_id,name=name,source_area_m2=round(site.area,2),bounds=list(site.bounds),fixtures=len(props)))
    assert len(sites)==9 and len(gardens)==5 and len(play_areas)==1 and len(surfaces)>8 and len(sports)>5 and len(fixtures)>100 and paving
    for surface in surfaces:
        poly=Polygon(surface['rings'][0],surface['rings'][1:])
        assert poly.is_valid and poly.intersection(roads).area<.01 and poly.intersection(lots).area<.01
    meta=dict(provider=raw['metadata']['provider'],source=raw['metadata']['source'],retrieved_utc=raw['metadata']['retrieved_utc'],
        source_sha256=hashlib.sha256(source).hexdigest(),inputs_sha256=inputs,origin_wgs84=ORIGIN,
        note='Nine sourced site boundaries and existing sports surfaces, flattened to game ground and clipped clear of buildings and roads. Paths, planting, benches, planters, the Mong Kok Road play pad, goals, hoops and markings are authored approximations. No eastward expansion or reconstruction of the Sai Yee Street development site.')
    return encoded(dict(metadata=meta,bounds=[-1100,-3400,1750,1550],sites=sites,surfaces=surfaces,paving=paving,fixtures=fixtures,sports=sports,gardens=gardens,play_areas=play_areas))


def replace_outputs(outputs):
    # Validate and stage the entire pair before touching either saved file. Backups on the
    # same filesystem allow rollback if a later replacement fails (including Ctrl-C).
    with tempfile.TemporaryDirectory(prefix='.open-spaces-',dir=TARGET.parent) as directory:
        stage=Path(directory);pending=[];replaced=[]
        try:
            for index,(target,payload) in enumerate(outputs):
                fresh=stage/f'{index}.part';fresh.write_bytes(payload)
                backup=stage/f'{index}.previous'
                if target.exists():backup.write_bytes(target.read_bytes())
                pending.append((target,fresh,backup))
            for target,fresh,backup in pending:
                fresh.replace(target);replaced.append((target,backup))
        except BaseException:
            for target,backup in reversed(replaced):
                if backup.exists():backup.replace(target)
                else:target.unlink(missing_ok=True)
            raise


def refresh(cache=None,manifest=None):
    source=extract(cache,manifest) if cache is not None else SOURCE.read_bytes()
    layout=build(source)
    replace_outputs(([(SOURCE,source)] if cache is not None else [])+[(TARGET,layout)])
    data=json.loads(layout)
    print('ANTILA_OPEN_SPACE_DATA_OK:',len(data['surfaces']),'sports surfaces;',len(data['sports']),'intact courts;',len(data['fixtures']),'fixtures;',len(data['paving']),'paving triangles')
    for site in data['sites']:print(site)


if __name__=='__main__':
    if '--extract' in sys.argv:refresh(Path(sys.argv[2]),Path(sys.argv[3]))
    else:refresh()
