"""Offline CSDI building massing. Run with .venv-geodata/bin/python Tools/import_buildings.py.

Survey heights are datums: each touching building group shares its lowest base across regional extracts.
The flat game terrain preserves relative roof heights, not surveyed ground levels.
"""
import hashlib
import json
import math
import datetime
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from shapely import constrained_delaunay_triangles, make_valid, STRtree, union_all
from shapely.geometry import Polygon, LineString, Point, box, shape
from shapely.geometry.polygon import orient
from shapely.ops import polylabel
from pyproj import Transformer
from import_map import local, BBOX, ORIGIN

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0/query"
PARK = Polygon([(-26,-368),(-193,-361),(-378,-570),(-415,-903),(-63,-920)])
PARK_FACILITIES = {336429, 336430}  # Kowloon Park Sports Centre and Administration Building.
RAISED_CULLINAN_WEST = {54076,149593,203401,228383,260821,268148,268379}
V_WALK_PODIUM_ID = 262652
BUS_ENVELOPE_HEIGHT = 4.2
BUS_CLEARANCE_MARGIN = 1.8
WIDE = {"CANTON ROAD", "CHATHAM ROAD SOUTH", "KOWLOON PARK DRIVE", "AUSTIN ROAD",
        "AUSTIN ROAD WEST", "JORDAN ROAD", "SALISBURY ROAD", "SCIENCE MUSEUM ROAD", "MODY ROAD"}
LANDMARK_TILE = '11-SW-4D'
LANDMARK_TILE_SHA256 = '9732121d37c72455d457d0ee380bbc861812041b132c560db1cdd1d11e67a6e6'
LANDMARK_GML_URL = 'https://open.hkmapservice.gov.hk/OpenData/directDownload?productName=iB1000&sheetName=T11-SW-4D&productFormat=GML'
LANDMARK_SITES = {'1503005422':'Hong Kong Cultural Centre', '1810047563':'Hong Kong Museum of Art',
                  '1502005204':'Hong Kong Space Museum'}
CLOCK_TOWER_ID = '1108244403'
CLOCK_TOWER_NAME = 'Former Kowloon-Canton Railway Clock Tower'
IB1000_NS = {'g':'http://www.opengis.net/gml','f':'http://www.safe.com/gml/fme'}
LANDMARK_LAYOUT_IDS = {1108244351,1108244353,1108244354,1108244358,1108244367,1108244369,
                       1108244370,1108244383,1108244393,1108244397,1108244403,1108247477,1810141373}


def extract_southwest_landmarks(tile_path):
    """Create a small WGS84 source supplement from the pinned LandsD iB1000 tile."""
    tile_path=Path(tile_path)
    payload=tile_path.read_bytes()
    tile_sha256=hashlib.sha256(payload).hexdigest()
    if tile_sha256!=LANDMARK_TILE_SHA256:raise ValueError('Unexpected iB1000 landmark tile checksum')
    with zipfile.ZipFile(tile_path) as archive:
        if archive.testzip() is not None:raise ValueError('Corrupt iB1000 landmark tile')
        def document(layer):
            name=f'{LANDMARK_TILE}/Layers/Buildings/{layer}.gml'
            if name not in archive.namelist():raise ValueError('Missing iB1000 landmark layer: '+name)
            root=ET.fromstring(archive.read(name))
            if root.tag!='{'+IB1000_NS['g']+'}FeatureCollection':raise ValueError('Invalid iB1000 landmark layer')
            return root
        transform=Transformer.from_crs(2326,4326,always_xy=True)

        def properties(item):
            return {child.tag.split('}')[-1]:child.text for child in item
                    if child.tag.startswith('{'+IB1000_NS['f']+'}')}

        def read_ring(element):
            points=[]
            for node in element.findall('.//g:posList',IB1000_NS):
                values=list(map(float,node.text.split()))
                if len(values)%3 or not all(math.isfinite(value) for value in values):
                    raise ValueError('Invalid iB1000 landmark ring coordinates')
                line=[]
                for i in range(0,len(values),3):
                    lon,lat=transform.transform(values[i+1],values[i])
                    line.append([lon,lat])
                if points and math.dist(points[-1],line[0])>1e-8:
                    raise ValueError('Disconnected iB1000 landmark ring')
                points.extend(line if not points else line[1:])
            if len(points)<4 or math.dist(points[0],points[-1])>1e-8:
                raise ValueError('Open iB1000 landmark ring')
            points[-1]=points[0]
            return points

        def geometry(item):
            parts=[]
            for patch in item.findall('.//g:PolygonPatch',IB1000_NS):
                exterior=patch.find('g:exterior',IB1000_NS)
                if exterior is None:raise ValueError('Missing iB1000 landmark exterior')
                rings=[read_ring(exterior),*[read_ring(hole) for hole in patch.findall('g:interior',IB1000_NS)]]
                parts.append(rings)
            if not parts:raise ValueError('Missing iB1000 landmark building geometry')
            return {'type':'Polygon','coordinates':parts[0]} if len(parts)==1 else {'type':'MultiPolygon','coordinates':parts}

        sites={}
        for item in document('Site').findall('g:featureMember/f:Site',IB1000_NS):
            props=properties(item);site_id=props.get('SITEID')
            if site_id in LANDMARK_SITES:
                sites.setdefault(site_id,[]).append(local_geometry(geometry(item)))
        sites={site_id:union_all(parts) for site_id,parts in sites.items()}
        if set(sites)!=set(LANDMARK_SITES):raise ValueError('Incomplete landmark Sites in iB1000 tile')

        records=[]
        for item in document('Building').findall('g:featureMember/f:Building',IB1000_NS):
            source=properties(item);ident=source.get('BUILDINGID')
            if source.get('BUILDINGSTATUS')!='E':continue
            geo=geometry(item);poly=local_geometry(geo)
            overlaps={site_id:poly.intersection(site).area for site_id,site in sites.items()}
            site_id=max(overlaps,key=overlaps.get) if overlaps else None
            if ident==CLOCK_TOWER_ID:
                site_id='AMO-M0043'
            elif site_id is None or overlaps[site_id]<4:
                continue
            block=source.get('TYPEOFBUILDINGBLOCK')
            base=float(source['BASELEVEL']) if source.get('BASELEVEL') not in (None,'') else None
            top=float(source['ROOFLEVEL']) if source.get('ROOFLEVEL') not in (None,'') else None
            name=CLOCK_TOWER_NAME if ident==CLOCK_TOWER_ID else LANDMARK_SITES[site_id]
            records.append({'type':'Feature','properties':{
                'OBJECTID':int(ident),'BuildingCSUID':'iB1000:'+ident,
                'BuildingBlockType':{'P':'Podium','T':'Tower','OS':'Open-sided'}.get(block,block or 'Building'),
                'BaseHeight':base,'TopHeight':top,'Storeys':None,'BuildingNameEN':name,
                'SourceProvider':'Lands Department, HKSAR Government','SourceProduct':'iB1000',
                'SourceTile':LANDMARK_TILE,'SourceBuildingID':ident,'SourceSiteID':site_id,
                'TYPEOFBUILDINGBLOCK':block,'BASELEVEL':base,'ROOFLEVEL':top,
                'BASELEVELDATASOURCE':source.get('BASELEVELDATASOURCE'),
                'ROOFLEVELDATASOURCE':source.get('ROOFLEVELDATASOURCE'),
                'BUILDINGSTATUS':source.get('BUILDINGSTATUS'),'CERTAINTY':source.get('CERTAINTY'),
                'LASTUPDATEDATE':source.get('LASTUPDATEDATE')},'geometry':geo})
        records.sort(key=lambda feature:feature['properties']['OBJECTID'])
        if sum(f['properties']['SourceBuildingID']==CLOCK_TOWER_ID for f in records)!=1:
            raise ValueError('The iB1000 Clock Tower candidate is missing')
        if not set(LANDMARK_SITES).issubset({f['properties']['SourceSiteID'] for f in records}):
            raise ValueError('An iB1000 landmark Site has no selected building footprints')

    local_bounds=union_all([local_geometry(feature['geometry']) for feature in records]).bounds
    west=ORIGIN[0]+local_bounds[0]/(111320*math.cos(math.radians(ORIGIN[1])))
    east=ORIGIN[0]+local_bounds[2]/(111320*math.cos(math.radians(ORIGIN[1])))
    south=ORIGIN[1]-local_bounds[3]/111320
    north=ORIGIN[1]-local_bounds[1]/111320
    metadata={
        'provider':'Lands Department, HKSAR Government','product':'Digital Topographic Map iB1000',
        'source':LANDMARK_GML_URL,'source_tile':LANDMARK_TILE,'source_tile_sha256':tile_sha256,
        'source_crs':'EPSG:2326','axis_order':'GML northing,easting,height; converted to WGS84',
        'bbox_wgs84':[west,south,east,north],'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'tile_revision_date':'2026-10-23','terms':'https://portal.csdi.gov.hk/csdi-webpage/doc/TNC',
        'clock_tower_name_reference':'https://www.amo.gov.hk/en/historic-buildings/monuments/kowloon/monuments_43/index.html',
        'features':len(records),'note':'Original iB1000 Building polygons and level attributes for the Cultural Centre, Museum of Art, Space Museum and the monument-matched Clock Tower. Clock Tower identity is a spatial match to the AMO monument location; OS features without source levels remain in this source but are omitted from derived massing.'}
    return json.dumps({'type':'FeatureCollection','metadata':metadata,'features':records},ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


def polygons(geometry):
    if geometry.geom_type == "Polygon":
        if geometry.area >= 4:
            yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from polygons(part)


def local_geometry(geometry):
    geometry_type=geometry.get('type')
    coordinates=geometry.get('coordinates')
    members=[coordinates] if geometry_type=='Polygon' else coordinates if geometry_type=='MultiPolygon' else None
    if not isinstance(members,list) or not members:raise ValueError('Expected a non-empty building Polygon or MultiPolygon')
    parts=[]
    for rings in members:
        if not isinstance(rings,list) or not rings:raise ValueError('Missing building polygon rings')
        for ring in rings:
            if not isinstance(ring,list) or len(ring)<4 or ring[0]!=ring[-1]:raise ValueError('Invalid building polygon ring')
            for point in ring:
                if not isinstance(point,list) or len(point) not in (2,3) or any(type(v) not in (int,float) or not math.isfinite(v) for v in point):
                    raise ValueError('Invalid building polygon coordinate')
                if not (-180<=point[0]<=180 and -90<=point[1]<=90):raise ValueError('Expected WGS84 building coordinates')
        part=make_valid(Polygon([local(p) for p in rings[0]],[[local(p) for p in ring] for ring in rings[1:]]))
        if part.is_empty or part.area<=0:raise ValueError('Empty building footprint')
        parts.append(part)
    polygon=make_valid(union_all(parts))
    if polygon.is_empty or polygon.area<=0:raise ValueError('Empty building footprint')
    return polygon


from import_tunnel import CHI_MAN_STREET_ID, ISLAND_BOUNDS, KOWLOON_BOUNDS, WEST_BOUNDS, NORTHWEST_BOUNDS, KWAI_CHUNG_BOUNDS, TSUEN_WAN_BOUNDS, WEST_COAST_BOUNDS, EAST_KOWLOON_BOUNDS
ISLAND_BBOX = (ORIGIN[0]+ISLAND_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-ISLAND_BOUNDS[3]/111320,
               ORIGIN[0]+ISLAND_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-ISLAND_BOUNDS[1]/111320)

KOWLOON_BBOX = (ORIGIN[0]+KOWLOON_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KOWLOON_BOUNDS[3]/111320,
                ORIGIN[0]+KOWLOON_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KOWLOON_BOUNDS[1]/111320)
WEST_BBOX = (ORIGIN[0]+WEST_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_BOUNDS[3]/111320,
             ORIGIN[0]+WEST_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_BOUNDS[1]/111320)
NORTHWEST_BBOX = (ORIGIN[0]+NORTHWEST_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-NORTHWEST_BOUNDS[3]/111320,
                 ORIGIN[0]+NORTHWEST_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-NORTHWEST_BOUNDS[1]/111320)
NORTHWEST_LEGACY_BOUNDS = (-4600,-6000,0,-3900)
NORTHWEST_EXTENSION_BOUNDS = (0,-6000,550,-4800)
NORTHWEST_BUILDING_REGION = union_all([box(*NORTHWEST_LEGACY_BOUNDS),box(*NORTHWEST_EXTENSION_BOUNDS)])
KOWLOON_TONG_SOURCE = 'Data/kowloon-tong-buildings-source.geojson'
KOWLOON_TONG_SOURCE_RESPONSE_SHA256 = '5150f9580d44047875b13a0614c78631462435d390b7bd550e4376d72ce7c0ee'
KOWLOON_TONG_RAW_FEATURE_COUNT = 222
KOWLOON_TONG_SELECTED_FEATURE_COUNT = 145
KOWLOON_TONG_SELECTED_CSUIDS_SHA256 = '9eef70f180fc85aa3d7a1ecdc025bfbb128da01b9293df8b44ff816a00f298ca'
KOWLOON_TONG_SELECTED_UNION_AREA_M2 = 58082.88613457147
KOWLOON_CITY_BOUNDARY = 'Data/kowloon-city-district-boundary.geojson'
CHI_MAN_BUILDING_NOTE = ' Chi Man Street (TD_105191) uses a 0.1 m setback beyond its 5 m carriageway to preserve the surveyed SPCA footprint.'

KWAI_CHUNG_BBOX = (ORIGIN[0]+KWAI_CHUNG_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KWAI_CHUNG_BOUNDS[3]/111320,
                   ORIGIN[0]+KWAI_CHUNG_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KWAI_CHUNG_BOUNDS[1]/111320)

TSUEN_WAN_BBOX = (ORIGIN[0]+TSUEN_WAN_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-TSUEN_WAN_BOUNDS[3]/111320,
                   ORIGIN[0]+TSUEN_WAN_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-TSUEN_WAN_BOUNDS[1]/111320)

WEST_COAST_BBOX = (ORIGIN[0]+WEST_COAST_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_COAST_BOUNDS[3]/111320,
                   ORIGIN[0]+WEST_COAST_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_COAST_BOUNDS[1]/111320)

EAST_KOWLOON_BBOX = (ORIGIN[0]+EAST_KOWLOON_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-EAST_KOWLOON_BOUNDS[3]/111320,
                     ORIGIN[0]+EAST_KOWLOON_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-EAST_KOWLOON_BOUNDS[1]/111320)


def kowloon_city_boundary():
    boundary=json.loads((ROOT/KOWLOON_CITY_BOUNDARY).read_text())
    feature,=boundary['features']
    encoded=json.dumps(feature,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    feature_sha256=hashlib.sha256(encoded.encode()).hexdigest()
    if feature['properties']['District']!='Kowloon City District' or feature_sha256!=boundary['metadata']['feature_sha256']:
        raise ValueError('Kowloon City District boundary does not match its recorded feature identity')
    return local_geometry(feature['geometry']),feature_sha256


def building_road_clearance(road):
    # The surveyed Chi Man Street centreline clears the SPCA wall by 2.646 m.
    if road['id']==CHI_MAN_STREET_ID and road['width']==5:
        return road['width']/2+.1
    return max(12,road['width'])/2+3.5


def download_island(north=False, west=False, northwest=False, kwai_chung=False, tsuen_wan=False, west_coast=False, east_kowloon=False):
    bbox = EAST_KOWLOON_BBOX if east_kowloon else WEST_COAST_BBOX if west_coast else TSUEN_WAN_BBOX if tsuen_wan else KWAI_CHUNG_BBOX if kwai_chung else NORTHWEST_BBOX if northwest else WEST_BBOX if west else KOWLOON_BBOX if north else ISLAND_BBOX
    target=ROOT/('Data/east-kowloon-buildings.geojson' if east_kowloon else 'Data/west-coast-buildings.geojson' if west_coast else 'Data/tsuen-wan-buildings.geojson' if tsuen_wan else 'Data/kwai-chung-buildings.geojson' if kwai_chung else 'Data/lai-chi-kok-buildings.geojson' if northwest else 'Data/west-kowloon-buildings.geojson' if west else 'Data/kowloon-north-buildings.geojson' if north else 'Data/island-buildings.geojson')
    if east_kowloon and not target.exists():
        raise FileNotFoundError('Restore the bundled East Kowloon building source before refreshing its pinned records')
    previous_bytes=target.read_bytes() if east_kowloon else None
    previous=json.loads(previous_bytes) if previous_bytes is not None else None
    if east_kowloon and not isinstance(previous,dict):raise ValueError('Invalid saved east-Kowloon building source')
    previous_features=previous.get('features') if previous else []
    previous_metadata=previous.get('metadata') if previous else {}
    if previous is not None:
        if previous.get('type')!='FeatureCollection' or not isinstance(previous_features,list) or not isinstance(previous_metadata,dict):
            raise ValueError('Invalid saved east-Kowloon building source')
        if any(not isinstance(f,dict) or not isinstance(f.get('properties'),dict) for f in previous_features):
            raise ValueError('Invalid saved east-Kowloon building feature')
        previous_ids=[f['properties'].get('OBJECTID') for f in previous_features]
        if any(type(i) is not int for i in previous_ids) or len(set(previous_ids))!=len(previous_ids):
            raise ValueError('Invalid or duplicate saved east-Kowloon building OBJECTID')
        previous_csuids=[f['properties'].get('BuildingCSUID') for f in previous_features]
        if any(not isinstance(uid,str) or not uid.strip() for uid in previous_csuids) or len(set(previous_csuids))!=len(previous_csuids):
            raise ValueError('Invalid or duplicate saved east-Kowloon BuildingCSUID')
        previous_provenance=previous_metadata.get('merge_provenance',{})
        original_metadata=previous_provenance.get('preserved_source_metadata',previous_metadata) if isinstance(previous_provenance,dict) else previous_metadata
        previous_bbox=original_metadata.get('bbox_wgs84') if isinstance(original_metadata,dict) else None
        if not isinstance(previous_bbox,list) or len(previous_bbox)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in previous_bbox):
            raise ValueError('Missing previous east-Kowloon query bounds')
        previous_ids=set(previous_ids);previous_csuids=set(previous_csuids)
        previous_east,previous_north=local([previous_bbox[2],previous_bbox[3]])
    query = dict(geometry=','.join(map(str,bbox)),geometryType='esriGeometryEnvelope',
                 inSR=4326,spatialRel='esriSpatialRelIntersects',where="Status='Active'" if east_kowloon else '1=1')
    def request(**params):
        with urllib.request.urlopen(SOURCE+'?'+urllib.parse.urlencode(query | params),timeout=60) as response:
            result=json.load(response)
        if not isinstance(result,dict): raise ValueError('Invalid building service response')
        if 'error' in result: raise ValueError(result['error'])
        return result
    count=request(f='json',returnCountOnly='true').get('count')
    if type(count) is not int or count<=0: raise ValueError('Expected a positive building count')
    features=[]
    while len(features)<count:
        page=request(f='geojson',outSR=4326,outFields='*',orderByFields='OBJECTID',resultOffset=len(features),resultRecordCount=3000)
        if page.get('type')!='FeatureCollection' or not isinstance(page.get('features'),list) or not page['features']:
            raise ValueError('Invalid or empty building page before count reached')
        features.extend(page['features'])
    ids=set();csuids=set();local_polygons=[]
    for feature in features:
        if not isinstance(feature,dict) or feature.get('type')!='Feature': raise ValueError('Invalid building feature')
        props=feature.get('properties');geometry=feature.get('geometry')
        if not isinstance(props,dict) or type(props.get('OBJECTID')) is not int:
            raise ValueError('Missing or invalid building OBJECTID')
        for field in ('BuildingCSUID','BuildingBlockType'):
            if not isinstance(props.get(field),str) or not props[field].strip(): raise ValueError(f'Missing building {field}')
        for field in ('BaseHeight','TopHeight','Storeys'):
            value=props.get(field)
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
                raise ValueError(f'Invalid building {field}')
        if props.get('BuildingNameEN') is not None and not isinstance(props['BuildingNameEN'],str):
            raise ValueError('Invalid building name')
        if not isinstance(geometry,dict):raise ValueError('Missing building geometry')
        # Match the builder's repair step; source polygons need not already be valid.
        polygon=local_geometry(geometry)
        ids.add(props['OBJECTID']);csuids.add(props['BuildingCSUID']);local_polygons.append(polygon)
    if len(features)!=count or len(ids)!=count or len(csuids)!=count: raise ValueError('Incomplete or duplicate building extract')
    retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    query_features_sha256=hashlib.sha256(json.dumps(features,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    merged_features=features;merge_provenance=None
    if previous is not None:
        west_south=local([bbox[0],bbox[1]]);east_north=local([bbox[2],bbox[3]])
        expanded_bounds=[west_south[0],east_north[1],east_north[0],west_south[1]]
        west,north_edge,east,south=expanded_bounds
        east_extension=east>previous_east+.01
        # An eastward refresh must not replace the established northern strip or
        # admit newer records there unless the query also extends farther north.
        donor_bbox=previous_metadata['bbox_wgs84']
        retained_north=local([donor_bbox[2],donor_bbox[3]])[1] if east_extension else previous_north
        retained_east=previous_east if east_extension else east
        addition_region=box(west,north_edge,east,south).difference(box(west,retained_north,retained_east,south))
        if east_extension:
            district,district_sha256=kowloon_city_boundary()
            addition_region=addition_region.intersection(district)
        additions=[];occupied_ids=set(previous_ids);next_internal_id=max(previous_ids|ids,default=0)+1;id_remaps=[]
        for feature,polygon in zip(features,local_polygons):
            props=feature['properties'];source_id=props['OBJECTID'];uid=props['BuildingCSUID']
            if uid in previous_csuids or props.get('Status')!='Active' or polygon.intersection(addition_region).area<=.01:continue
            if source_id in occupied_ids:
                internal_id=next_internal_id;next_internal_id+=1
                feature={**feature,'properties':{**props,'source_OBJECTID':source_id,'OBJECTID':internal_id}}
                id_remaps.append({'BuildingCSUID':uid,'source_OBJECTID':source_id,'internal_OBJECTID':internal_id})
            internal_id=feature['properties']['OBJECTID']
            if internal_id in occupied_ids:raise ValueError(f'Duplicate merged east-Kowloon OBJECTID {internal_id}')
            occupied_ids.add(internal_id);additions.append(feature)
        merged_features=previous_features+additions
        original_provenance=previous_metadata.get('merge_provenance',{})
        original_provenance=original_provenance if isinstance(original_provenance,dict) else {}
        original_source_sha256=original_provenance.get('preserved_source_sha256') if isinstance(original_provenance,dict) else None
        original_source_metadata=original_provenance.get('preserved_source_metadata') if isinstance(original_provenance,dict) else None
        original_feature_count=original_provenance.get('preserved_feature_count') if isinstance(original_provenance,dict) else None
        previous_added_csuids=original_provenance.get('added_csuids')
        if previous_added_csuids is None:
            base_count=original_feature_count if type(original_feature_count) is int else len(previous_features)
            if not 0<=base_count<=len(previous_features):raise ValueError('Invalid preserved east-Kowloon feature count')
            previous_added_csuids=[f['properties']['BuildingCSUID'] for f in previous_features[base_count:]]
        previous_remaps=original_provenance.get('objectid_remaps',[])
        if not isinstance(previous_added_csuids,list) or any(not isinstance(uid,str) for uid in previous_added_csuids) or not isinstance(previous_remaps,list):
            raise ValueError('Invalid previous east-Kowloon merge provenance')
        missing_csuids=sorted(previous_csuids-csuids)
        remaps=previous_remaps+id_remaps
        merged_ids=[f['properties']['OBJECTID'] for f in merged_features]
        merged_csuids=[f['properties']['BuildingCSUID'] for f in merged_features]
        if len(set(merged_ids))!=len(merged_ids) or len(set(merged_csuids))!=len(merged_csuids):
            raise ValueError('Duplicate identity in merged east-Kowloon source')
        added_csuids=sorted(set(previous_added_csuids)|{f['properties']['BuildingCSUID'] for f in additions})
        if not set(added_csuids).issubset(set(merged_csuids)):raise ValueError('Missing previously merged east-Kowloon addition')
        added_features={f['properties']['BuildingCSUID']:f for f in merged_features if f['properties']['BuildingCSUID'] in set(added_csuids)}
        added_objectids=sorted(f['properties'].get('source_OBJECTID',f['properties']['OBJECTID']) for f in added_features.values())
        if len(added_features)!=len(added_csuids):raise ValueError('Duplicate east-Kowloon addition identity')
        total_added=len(added_csuids)
        selection='the expansion within the official Kowloon City District boundary' if east_extension else 'the expanded northern strip'
        merge_provenance=dict(strategy=f'preserve saved eastern features verbatim; append only unseen active records intersecting {selection}',
            preserved_source_sha256=original_source_sha256 or hashlib.sha256(previous_bytes).hexdigest(),
            preserved_source_metadata=original_source_metadata or previous_metadata,
            preserved_feature_count=original_feature_count or len(previous_features),
            donor_source_sha256=hashlib.sha256(previous_bytes).hexdigest(),
            donor_source_metadata={key:previous_metadata.get(key) for key in ('source','bbox_wgs84','retrieved_utc','query_retrieved_utc','query_feature_count','query_features_sha256')},
            query_feature_count=count,query_features_sha256=query_features_sha256,
            objectid_semantics='OBJECTID is the unique layout/cache key; source_OBJECTID records the upstream ID when a new feature ID collides with a preserved feature',
            added_feature_count=total_added,cumulative_added_feature_count=total_added,incremental_added_feature_count=len(additions),added_csuids=added_csuids,
            added_csuids_sha256=hashlib.sha256(json.dumps(added_csuids,separators=(',',':')).encode()).hexdigest(),
            added_objectids_sha256=hashlib.sha256(json.dumps(added_objectids,separators=(',',':')).encode()).hexdigest(),
            objectid_remaps=remaps,missing_service_csuids=missing_csuids,
            geometry_vintage_semantics='preserved features retain their original source geometry and attributes; appended features use the recorded current query',
            shared_height_ordering='The file-level retrieved_utc remains pinned to the preserved source snapshot so historical east-Kowloon heights keep their prior precedence',
            expanded_bounds_local=expanded_bounds,previous_north_boundary_local_z=previous_north)
        if east_extension:
            merge_provenance['previous_east_boundary_local_x']=previous_east
            merge_provenance['district_boundary_feature_sha256']=district_sha256
            if original_provenance:
                merge_provenance['northern_strip_provenance']=original_provenance.get('northern_strip_provenance',original_provenance)
    metadata=dict(source=SOURCE,bbox_wgs84=list(bbox),retrieved_utc=previous_metadata.get('retrieved_utc',retrieved_utc) if east_kowloon and previous is not None else retrieved_utc,
                  query_feature_count=count,query_features_sha256=query_features_sha256)
    if east_kowloon and previous is not None:metadata['query_retrieved_utc']=retrieved_utc
    if merge_provenance is not None:metadata['merge_provenance']=merge_provenance
    contents=json.dumps(dict(type='FeatureCollection',metadata=metadata,features=merged_features),ensure_ascii=False,separators=(',',':'),allow_nan=False)
    with tempfile.NamedTemporaryFile(dir=target.parent,prefix=target.name+'.',suffix='.part',delete=False) as staged:
        pending=Path(staged.name)
    try:
        pending.write_text(contents,encoding='utf-8')
        pending.replace(target)
    finally:pending.unlink(missing_ok=True)
    print('EAST_KOWLOON_BUILDINGS_DOWNLOADED:' if east_kowloon else 'WEST_COAST_BUILDINGS_DOWNLOADED:' if west_coast else 'TSUEN_WAN_BUILDINGS_DOWNLOADED:' if tsuen_wan else 'KWAI_CHUNG_BUILDINGS_DOWNLOADED:' if kwai_chung else 'NORTHWEST_BUILDINGS_DOWNLOADED:' if northwest else 'WEST_BUILDINGS_DOWNLOADED:' if west else 'NORTH_BUILDINGS_DOWNLOADED:' if north else 'ISLAND_BUILDINGS_DOWNLOADED:',count,flush=True)


def build(island=False, north=False, west=False, northwest=False, kwai_chung=False, tsuen_wan=False, west_coast=False, east_kowloon=False, landmarks=False, include_landmarks=True, write=True):
    raw = ROOT / ("Data/southwest-landmarks-source.geojson" if landmarks else "Data/east-kowloon-buildings.geojson" if east_kowloon else "Data/west-coast-buildings.geojson" if west_coast else "Data/tsuen-wan-buildings.geojson" if tsuen_wan else "Data/kwai-chung-buildings.geojson" if kwai_chung else "Data/lai-chi-kok-buildings.geojson" if northwest else "Data/west-kowloon-buildings.geojson" if west else "Data/kowloon-north-buildings.geojson" if north else "Data/island-buildings.geojson" if island else "Data/buildings.geojson")
    raw_data = json.loads(raw.read_text())
    features = raw_data["features"]
    roads = json.loads((ROOT / "Data/nathan-road.json").read_text())
    boundary = box(*(KOWLOON_BOUNDS if north else ISLAND_BOUNDS if island else roads['bounds']))
    if island:boundary=shape(json.loads((ROOT/'Data/island-coast.json').read_text())['land'])
    if west:
        coast=json.loads((ROOT/'Data/west-kowloon-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if northwest:
        coast=json.loads((ROOT/'Data/lai-chi-kok-coast.json').read_text())
        # Preserve legacy NW ownership; only the former-water strip east of x=0 extends the building region.
        boundary=shape(coast['land']).intersection(NORTHWEST_BUILDING_REGION).difference(union_all([box(*WEST_BOUNDS),box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if kwai_chung:
        coast=json.loads((ROOT/'Data/kwai-chung-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*WEST_BOUNDS),NORTHWEST_BUILDING_REGION,box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if tsuen_wan:
        coast=json.loads((ROOT/'Data/tsuen-wan-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*KWAI_CHUNG_BOUNDS),box(*WEST_BOUNDS),NORTHWEST_BUILDING_REGION,box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if west_coast:
        coast=json.loads((ROOT/'Data/west-coast-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*TSUEN_WAN_BOUNDS),box(*KWAI_CHUNG_BOUNDS),box(*WEST_BOUNDS),NORTHWEST_BUILDING_REGION,box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if east_kowloon:
        coast=json.loads((ROOT/'Data/east-kowloon-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*WEST_COAST_BOUNDS),box(*TSUEN_WAN_BOUNDS),box(*KWAI_CHUNG_BOUNDS),box(*WEST_BOUNDS),NORTHWEST_BUILDING_REGION,box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    buffers = [LineString(roads["road_points"]).buffer(13.5, quad_segs=2, join_style="mitre")]
    for road in roads["side_roads"]:
        width = 18 if road["name"] in WIDE else 12
        buffers.append(LineString(road["points"]).buffer(width/2+3.5, quad_segs=2, join_style="mitre"))
    harbour = json.loads((ROOT/'Data/cross-harbour.json').read_text())
    for road in harbour['roads']:
        if not road['tunnel'] or road.get('ramp',False):
            buffers.append(LineString([(p[0],p[2]) for p in road['points']]).buffer(building_road_clearance(road),quad_segs=2,join_style='mitre').intersection(boundary))
    road_zone = union_all(buffers)
    # The prototype permits a bus turn into Granville: protect the long nose through that tight corner.
    turning_zone = LineString(roads["points"]).interpolate(503).buffer(32, quad_segs=8)
    turn_clearance = road_zone.buffer(2, quad_segs=2, join_style="mitre").intersection(turning_zone)
    street_exclusion = union_all([road_zone, turn_clearance])
    exclusion = union_all([PARK, road_zone, turn_clearance])
    source_polys = [local_geometry(f["geometry"]) for f in features]
    northwest_supplement_ids=[]
    kowloon_tong_source_ids=[]
    kowloon_tong_source_internal_ids=[]
    kowloon_tong_source_csuids=[]
    kowloon_tong_source_id_remaps=[]
    kowloon_tong_source_area=0.0
    kowloon_tong_union_area=0.0
    regional_sources = [ROOT/'Data'/name for name in
        ('buildings.geojson','kowloon-north-buildings.geojson','west-kowloon-buildings.geojson','lai-chi-kok-buildings.geojson','kwai-chung-buildings.geojson','tsuen-wan-buildings.geojson','west-coast-buildings.geojson','east-kowloon-buildings.geojson')]
    kowloon_tong_source_path=ROOT/KOWLOON_TONG_SOURCE
    base_sources = ([raw]+regional_sources) if landmarks else [raw] if island else regional_sources+([kowloon_tong_source_path] if northwest else [])
    snapshot_pairs=[(path,json.loads(path.read_text())) for path in base_sources]
    snapshot_pairs.sort(key=lambda pair: datetime.datetime.fromisoformat(pair[1].get('metadata',{}).get('retrieved_utc','2026-09-13T00:00:00+00:00')))
    snapshots=[snapshot for _,snapshot in snapshot_pairs]
    base_features = [f for snapshot in snapshots for f in snapshot['features']]
    if northwest:
        extension=box(*NORTHWEST_EXTENSION_BOUNDS)
        by_csuid={f['properties']['BuildingCSUID']:i for i,f in enumerate(features)}
        for source_path in (ROOT/'Data/west-kowloon-buildings.geojson',ROOT/'Data/east-kowloon-buildings.geojson'):
            supplement=json.loads(source_path.read_text())
            for feature in supplement['features']:
                polygon=local_geometry(feature['geometry'])
                fragment=polygon.intersection(extension)
                if fragment.area<=4:
                    continue
                props=feature['properties'];csuid=props['BuildingCSUID'];object_id=props['OBJECTID']
                if csuid in by_csuid:
                    existing=source_polys[by_csuid[csuid]]
                    if fragment.difference(existing).area>.1:
                        raise ValueError(f'Northwest source supplement {object_id} disagrees with its cached BuildingCSUID geometry')
                    continue
                by_csuid[csuid]=len(features)
                features.append(feature);source_polys.append(polygon);northwest_supplement_ids.append(object_id)
        supplement=next(snapshot for path,snapshot in snapshot_pairs if path==kowloon_tong_source_path)
        supplement_metadata=supplement.get('metadata',{})
        expected_bbox=[ORIGIN[0]+NORTHWEST_EXTENSION_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))),
                       ORIGIN[1]-NORTHWEST_EXTENSION_BOUNDS[3]/111320,
                       ORIGIN[0]+NORTHWEST_EXTENSION_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))),
                       ORIGIN[1]-NORTHWEST_EXTENSION_BOUNDS[1]/111320]
        if supplement.get('type')!='FeatureCollection' or supplement_metadata.get('source')!=SOURCE:
            raise ValueError('Missing official Kowloon Tong CSDI Building source')
        if supplement_metadata.get('query_response_sha256')!=KOWLOON_TONG_SOURCE_RESPONSE_SHA256:
            raise ValueError('Kowloon Tong source response provenance changed')
        if supplement_metadata.get('query_local_bounds_m')!=list(NORTHWEST_EXTENSION_BOUNDS) or len(supplement_metadata.get('bbox_wgs84',[]))!=4 or any(abs(a-b)>1e-12 for a,b in zip(supplement_metadata['bbox_wgs84'],expected_bbox)):
            raise ValueError('Kowloon Tong source query no longer matches the owned fill bounds')
        source_features=supplement.get('features')
        if not isinstance(source_features,list) or len(source_features)!=KOWLOON_TONG_RAW_FEATURE_COUNT or supplement_metadata.get('query_feature_count')!=KOWLOON_TONG_RAW_FEATURE_COUNT:
            raise ValueError('Incomplete official Kowloon Tong source response')
        source_ids=[f.get('properties',{}).get('OBJECTID') for f in source_features]
        source_csuids=[f.get('properties',{}).get('BuildingCSUID') for f in source_features]
        if any(type(ident) is not int for ident in source_ids) or len(set(source_ids))!=len(source_ids) or any(not isinstance(uid,str) or not uid for uid in source_csuids) or len(set(source_csuids))!=len(source_csuids):
            raise ValueError('Duplicate or invalid identity in the Kowloon Tong source response')
        if any(f.get('properties',{}).get('Status')!='Active' for f in source_features):
            raise ValueError('Kowloon Tong source response includes a non-active record')
        existing_source_csuids={f['properties']['BuildingCSUID'] for path,snapshot in snapshot_pairs if path!=kowloon_tong_source_path for f in snapshot['features']}
        eligible=[]
        for feature in source_features:
            props=feature['properties'];polygon=local_geometry(feature['geometry'])
            fragment=polygon.intersection(extension)
            if props.get('BuildingBlockType') not in {'Tower','Podium','Temporary Structure'} or fragment.area<20 or props['BuildingCSUID'] in existing_source_csuids:
                continue
            eligible.append((feature,polygon,fragment))
        selected_csuids=sorted(feature['properties']['BuildingCSUID'] for feature,_,_ in eligible)
        selected_csuids_sha256=hashlib.sha256(json.dumps(selected_csuids,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        if len(eligible)!=KOWLOON_TONG_SELECTED_FEATURE_COUNT or selected_csuids_sha256!=KOWLOON_TONG_SELECTED_CSUIDS_SHA256:
            raise ValueError('Kowloon Tong source selection changed; review the source identities')
        kowloon_tong_source_area=sum(fragment.area for _,_,fragment in eligible)
        kowloon_tong_union_area=union_all([fragment for _,_,fragment in eligible]).area
        if abs(kowloon_tong_union_area-KOWLOON_TONG_SELECTED_UNION_AREA_M2)>.1:
            raise ValueError('Kowloon Tong source footprint union changed')
        occupied_ids={feature['properties']['OBJECTID'] for feature in features}
        next_internal_id=max(occupied_ids|set(source_ids),default=0)+1
        for feature,polygon,_ in eligible:
            props=feature['properties'];source_id=props['OBJECTID'];uid=props['BuildingCSUID']
            if source_id in occupied_ids:
                internal_id=next_internal_id;next_internal_id+=1
                feature={**feature,'properties':{**props,'source_OBJECTID':source_id,'OBJECTID':internal_id}}
                kowloon_tong_source_id_remaps.append({'BuildingCSUID':uid,'source_OBJECTID':source_id,'internal_OBJECTID':internal_id})
            occupied_ids.add(feature['properties']['OBJECTID'])
            by_csuid[uid]=len(features)
            features.append(feature);source_polys.append(polygon)
            kowloon_tong_source_ids.append(source_id);kowloon_tong_source_internal_ids.append(feature['properties']['OBJECTID']);kowloon_tong_source_csuids.append(uid)
    if landmarks:boundary=union_all(source_polys)
    base_polys = source_polys if island else [local_geometry(f['geometry']) for f in base_features]
    tree = STRtree(base_polys)
    parent = list(range(len(base_features)))

    def group(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_csuid = {}
    for i, f in enumerate(base_features):
        csuid = f['properties']['BuildingCSUID']
        assert isinstance(csuid,str) and csuid, 'Missing persistent building identity'
        if csuid in by_csuid:parent[group(i)] = group(by_csuid[csuid])
        by_csuid[csuid] = i
    for i, poly in enumerate(base_polys):
        for j in tree.query(poly, predicate="dwithin", distance=.25):
            parent[group(int(j))] = group(i)
    ground = {}
    for i, f in enumerate(base_features):
        base = f["properties"].get("BaseHeight")
        if isinstance(base, (float, int)) and math.isfinite(base):
            root = group(i)
            ground[root] = min(ground.get(root, base), base)
    roots = [group(by_csuid[f['properties']['BuildingCSUID']]) for f in features]

    raised_bases = {}
    raised_source_polygons = {}
    raised_podium_polygon = Polygon()
    raised_podium_base = None
    if west:
        podium_feature = next((f for f in features if f['properties']['OBJECTID']==V_WALK_PODIUM_ID),None)
        if podium_feature is None:raise ValueError('Cullinan West towers require the source-backed V Walk podium')
        podium_props=podium_feature['properties']
        podium_base=podium_props.get('BaseHeight')
        podium_top=podium_props.get('TopHeight')
        if podium_props.get('BuildingNameEN')!='V Walk' or podium_props.get('BuildingBlockType')!='Podium' or (podium_base,podium_top)!=(3.9,28.2):
            raise ValueError('V Walk podium height datum changed; recheck the Cullinan West supports')
        podium_polygon=local_geometry(podium_feature['geometry'])
        target_features={f['properties']['OBJECTID']: (i,f,poly) for i,(f,poly) in enumerate(zip(features,source_polys))
                         if f['properties']['OBJECTID'] in RAISED_CULLINAN_WEST}
        if set(target_features)!=RAISED_CULLINAN_WEST:
            raise ValueError('The seven surveyed Cullinan West Sky Mansions changed')
        for ident,(i,feature,polygon) in target_features.items():
            props=feature['properties']
            if props.get('BuildingBlockType')!='Tower' or props.get('BaseHeight')!=26.9:
                raise ValueError(f'Cullinan West tower {ident} changed its surveyed base')
            if polygon.difference(podium_polygon).area>.1:
                raise ValueError(f'Cullinan West tower {ident} is no longer supported by V Walk')
            if abs(ground[roots[i]]-podium_base)>.05:
                raise ValueError(f'Cullinan West tower {ident} changed the local podium datum')
            raised_bases[ident]=podium_top-podium_base
            raised_source_polygons[ident]=polygon

        crossing_roads=[]
        for road in harbour['roads']:
            if road['tunnel'] and not road.get('ramp',False):continue
            carriageway=LineString([(p[0],p[2]) for p in road['points']]).buffer(max(12,road['width'])/2+3.5,quad_segs=2,join_style='mitre')
            if carriageway.intersects(podium_polygon.intersection(boundary).intersection(street_exclusion)):
                crossing_roads.append(road)
        if not crossing_roads:
            raise ValueError('Expected source roads beneath the V Walk upper podium')
        highest_road=max(max(p[1] for p in road['points']) for road in crossing_roads)
        raised_podium_base=max(6.0,highest_road+BUS_ENVELOPE_HEIGHT+BUS_CLEARANCE_MARGIN)
        if raised_podium_base>=podium_top-podium_base:
            raise ValueError('V Walk podium has insufficient structural depth above its road clearance')
        if highest_road+BUS_ENVELOPE_HEIGHT+BUS_CLEARANCE_MARGIN>raised_podium_base+1e-6:
            raise ValueError('Raised V Walk podium does not preserve the low-bus envelope')
        crossing_road_ids={road['id'] for road in crossing_roads}
        if not {'TD_107160','TD_107055'}.issubset(crossing_road_ids):
            raise ValueError('The V Walk podium must account for roads TD_107160 and TD_107055')
        tower_footprints=union_all(list(raised_source_polygons.values()))
        supported_tower_polygon=tower_footprints.intersection(podium_polygon).intersection(boundary)
        raised_podium_polygon=(podium_polygon.intersection(boundary).intersection(street_exclusion)
                               .difference(PARK).difference(tower_footprints))
        flat_podium_polygon=(podium_polygon.intersection(boundary).difference(exclusion)
                             .difference(tower_footprints))
        tower_support_flat=supported_tower_polygon.difference(exclusion)
        tower_support_raised=supported_tower_polygon.intersection(street_exclusion).difference(PARK)
        supported_area=union_all([flat_podium_polygon,raised_podium_polygon,tower_support_flat,tower_support_raised])
        expected_area=podium_polygon.intersection(boundary).difference(PARK)
        if expected_area.symmetric_difference(supported_area).area>.1:
            raise ValueError('V Walk podium surfaces and open-top tower supports must cover its retained source outline')
        for ident,polygon in raised_source_polygons.items():
            if polygon.difference(flat_podium_polygon.union(raised_podium_polygon).union(tower_support_flat).union(tower_support_raised)).area>.1:
                raise ValueError(f'Cullinan West tower {ident} has an unsupported footprint gap')
            if polygon.distance(raised_podium_polygon.union(flat_podium_polygon).union(tower_support_flat).union(tower_support_raised))>.1:
                raise ValueError(f'Cullinan West tower {ident} does not contact the source V Walk podium')
        if not raised_podium_polygon.boundary.intersection(flat_podium_polygon.boundary).length>0:
            raise ValueError('Raised V Walk podium must connect to the retained source podium sides')
        for road in harbour['roads']:
            if road['id'] not in crossing_road_ids:continue
            carriageway=LineString([(p[0],p[2]) for p in road['points']]).buffer(max(12,road['width'])/2+3.5,quad_segs=2,join_style='mitre')
            if carriageway.intersection(raised_podium_polygon).area>.1 and max(p[1] for p in road['points'])+BUS_ENVELOPE_HEIGHT>raised_podium_base+1e-6:
                raise ValueError(f'Source road {road["id"]} lacks low-bus clearance below the raised V Walk podium')

    candidates = []
    missing = clipped = 0
    for i, (f, poly) in enumerate(zip(features, source_polys)):
        # The newest extract owns height inputs; regional footprints and IDs stay local.
        props = base_features[by_csuid[f['properties']['BuildingCSUID']]]["properties"]
        top = props.get("TopHeight")
        base = props.get("BaseHeight")
        if landmarks and (not isinstance(top,(int,float)) or not isinstance(base,(int,float)) or top<=base):
            continue
        if not isinstance(top, (int, float)) or top <= ground.get(roots[i], 4):
            missing += 1
            height = max(3.2, (props.get("Storeys") or 3)*3.2)
        else:
            height = top - ground.get(roots[i], props.get("BaseHeight") or 4)
        source_id=f["properties"]["OBJECTID"]
        clearance = Polygon() if landmarks or source_id in raised_bases else street_exclusion if source_id in PARK_FACILITIES else exclusion
        playable = poly.intersection(boundary).difference(clearance)
        if source_id==V_WALK_PODIUM_ID and west:
            playable=playable.difference(tower_footprints)
        if poly.area - playable.area > .1:
            clipped += 1
        # Upper envelope removes duplicate/internal podium surfaces and overlapping collisions.
        candidates.append((round(height, 3), i, playable, raised_bases.get(source_id,0.0), False))
        if source_id==V_WALK_PODIUM_ID and not raised_podium_polygon.is_empty:
            candidates.append((round(height,3),i,raised_podium_polygon,raised_podium_base,False))
            if not tower_support_flat.is_empty:
                candidates.append((round(height,3),i,tower_support_flat,0.0,True))
            if not tower_support_raised.is_empty:
                candidates.append((round(height,3),i,tower_support_raised,raised_podium_base,True))
    candidates.sort(key=lambda candidate:(candidate[0],candidate[1],candidate[3],candidate[4]),reverse=True)
    occupied = {}
    output = []
    for height, i, playable, base_height, support_only in candidates:
        root = roots[i]
        visible = playable if support_only else playable.difference(occupied[root]) if root in occupied else playable
        if not support_only:
            occupied[root] = union_all([occupied[root], playable]) if root in occupied else playable
        props = features[i]["properties"]
        source_id = props["OBJECTID"]
        style = 1 if height > 75 else 2 if props["BuildingBlockType"] == "Podium" else source_id % 3
        if style == 1 and height <= 75:
            style = 3
        # Clipping can leave a valid polygon plus a zero-area point or tiny fragment.
        simplified = (poly if source_id in raised_bases or (west and source_id==V_WALK_PODIUM_ID)
                      else poly.simplify(.08, preserve_topology=True).intersection(visible) for poly in polygons(visible))
        for poly in (part for geometry in simplified for part in polygons(geometry)):
            poly = orient(poly, sign=1)
            triangles = list(constrained_delaunay_triangles(poly).geoms)
            assert abs(sum(t.area for t in triangles)-poly.area) < .01
            point = poly.representative_point()
            # Difference operations can leave a narrow spur whose midpoint rounds outside the roof.
            if point.distance(poly.boundary)<.1:point=polylabel(poly,tolerance=.1)
            assert poly.contains(Point(round(point.x,4),round(point.y,4))), 'Rounded roof probe must remain inside its footprint'
            def coords(ring):
                return [[x, z] for x, z in list(ring.coords)[:-1]]
            building={"id": source_id, "name": props.get("BuildingNameEN") or "",
                           "type": props["BuildingBlockType"], "height": height, "style": style,
                           "center": [round(point.x, 4), round(point.y, 4)],
                           "roof_clearance": point.distance(poly.boundary),
                           "frontage": [LineString([a,b]).distance(road_zone)<1 for a,b in zip(list(poly.exterior.coords),list(poly.exterior.coords)[1:])],
                           "rings": [coords(poly.exterior), *[coords(r) for r in poly.interiors]],
                           "roof": [coords(orient(t, sign=1).exterior) for t in triangles]}
            if base_height>0:
                building["base_height"]=base_height
            if support_only:
                building["open_top_support"]=True
            output.append(building)

    actual = [Polygon(b["rings"][0], b["rings"][1:]) for b in output]
    for footprint, building in zip(actual, output):
        podium_support = building['id']==V_WALK_PODIUM_ID and (building.get('base_height',0)>0 or building.get('open_top_support'))
        clearance = Polygon() if building["id"] in raised_bases or podium_support else street_exclusion if building["id"] in PARK_FACILITIES else exclusion
        assert footprint.is_valid and footprint.difference(boundary).area < .1 and footprint.intersection(clearance).area < .1, "Invalid or obstructing footprint"
    if west:
        for ident,source_polygon in raised_source_polygons.items():
            footprint=union_all([poly for poly,building in zip(actual,output) if building['id']==ident])
            assert source_polygon.symmetric_difference(footprint).area<.1, f'Raised tower {ident} must retain its surveyed footprint'
            entries=[building for building in output if building['id']==ident]
            assert entries and all(abs(building['base_height']-raised_bases[ident])<.001 for building in entries)
        podium_parts=[(Polygon(building['rings'][0],building['rings'][1:]),building)
                      for building in output if building['id']==V_WALK_PODIUM_ID]
        upper_podium=union_all([poly for poly,building in podium_parts if building.get('base_height',0)>0 and not building.get('open_top_support')])
        if upper_podium.symmetric_difference(raised_podium_polygon).area>.1:
            raise ValueError('Raised V Walk podium output must retain its clipped source-backed support polygon')
        if any(abs(building['base_height']-raised_podium_base)>.001 or abs(building['height']-(podium_top-podium_base))>.001
               for poly,building in podium_parts if building.get('base_height',0)>0):
            raise ValueError('Raised V Walk podium output has an inconsistent base or surveyed roof height')
        if not upper_podium.boundary.intersection(union_all([poly for poly,building in podium_parts if not building.get('base_height',0)]).boundary).length>0:
            raise ValueError('Raised V Walk podium output lost contact with the retained podium sides')
        open_support=union_all([poly for poly,building in podium_parts if building.get('open_top_support')])
        expected_open_support=union_all([tower_support_flat,tower_support_raised])
        if open_support.symmetric_difference(expected_open_support).area>.1:
            raise ValueError('Open-top V Walk support pads must match the seven surveyed tower footprints')
        for ident,source_polygon in raised_source_polygons.items():
            entries=[(poly,building) for poly,building in podium_parts if building.get('open_top_support') and poly.intersects(source_polygon)]
            tower_base=raised_bases[ident]
            support_area=union_all([poly.intersection(source_polygon) for poly,building in entries])
            if source_polygon.difference(support_area).area>.1:
                raise ValueError(f'Cullinan West tower {ident} lacks continuous source podium support below its base slab')
            if any(abs(building['height']-tower_base)>.001 for poly,building in entries):
                raise ValueError(f'Cullinan West tower {ident} support does not meet its lower collision face')
    actual_tree = STRtree(actual)
    for i, poly in enumerate(actual):
        for j in actual_tree.query(poly):
            j=int(j)
            if j>=i:continue
            overlap=poly.intersection(actual[j]).area
            if overlap<.1:continue
            a,b=output[i],output[j]
            support,tower=(a,b) if a.get('open_top_support') else (b,a)
            if (support.get('open_top_support') and support['id']==V_WALK_PODIUM_ID
                    and tower['id'] in RAISED_CULLINAN_WEST and abs(support['height']-tower.get('base_height',-1))<.001):
                continue
            assert overlap<.1, 'Unexpected overlapping building footprints'
    area = union_all(actual).area
    # Close only small enclosed paving gaps; keep the park and larger open spaces intact.
    paved = union_all([road_zone.buffer(-.5), *[Polygon(p.exterior).buffer(3, join_style="bevel") for p in actual]])
    pavement_patches = []
    for part in polygons(paved):
        for ring in part.interiors:
            hole = Polygon(ring)
            if hole.area > 40 or hole.intersects(PARK):
                continue
            patch = hole.buffer(.4).intersection(boundary)
            if patch.geom_type != "Polygon" or patch.is_empty or patch.intersects(PARK):
                continue
            point = patch.representative_point()
            pavement_patches.append({"center": [point.x,point.y], "polygon": list(patch.exterior.coords)[:-1]})
    assert (landmarks or east_kowloon or west_coast or tsuen_wan or kwai_chung or northwest or west or north or island or pavement_patches) and all(Polygon(p["polygon"]).is_valid for p in pavement_patches)
    names = {b["name"] for b in output}
    if landmarks:
        assert {b["id"] for b in output}==LANDMARK_LAYOUT_IDS and len(output)>=13, 'Landmark layout lost a height-backed iB1000 source building'
        assert all(b['height']>0 for b in output) and area>15000, 'Southwest landmark massing is unexpectedly sparse'
    elif not (island or north or west or northwest or kwai_chung or tsuen_wan or west_coast or east_kowloon):
        assert len(features) == 1718 and len(output) > 900 and area > 650000
        assert PARK_FACILITIES <= {b["id"] for b in output}, "Kowloon Park facility footprints missing"
        assert any("MASTERPIECE" in n.upper() for n in names)
        assert max(b["height"] for b in output) > 240
    else:
        assert len(output)>20 and area>10000, 'Island district extract is unexpectedly sparse'
    assert min(b["height"] for b in output) > 0
    meta = {"provider": raw_data.get('metadata',{}).get('provider','Lands Department, HKSAR Government / CSDI Portal') if landmarks else "Lands Department, HKSAR Government / CSDI Portal", "source": raw_data.get('metadata',{}).get('source',SOURCE) if landmarks else SOURCE,
            "terms": "https://portal.csdi.gov.hk/csdi-webpage/doc/TNC", "retrieved_utc": raw_data.get('metadata',{}).get('retrieved_utc','2026-09-13'),
            "source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "bbox_wgs84": raw_data.get('metadata',{}).get('bbox_wgs84') if landmarks else EAST_KOWLOON_BBOX if east_kowloon else WEST_COAST_BBOX if west_coast else TSUEN_WAN_BBOX if tsuen_wan else KWAI_CHUNG_BBOX if kwai_chung else NORTHWEST_BBOX if northwest else WEST_BBOX if west else KOWLOON_BBOX if north else ISLAND_BBOX if island else BBOX, "origin_wgs84": ORIGIN,
            "source_parts": len(features), "rendered_parts": len(output), "source_parts_retained": len({b["id"] for b in output}),
            "source_parts_clipped": clipped, "fallback_height_parts": missing, "footprint_area_m2": round(area),
            "volume_m3": round(sum(p.area*b["height"] for p,b in zip(actual,output))),
            "styles": dict(Counter(b["style"] for b in output)),
            "note": "Derived game massing, not survey-grade reconstruction. Flat ground; connected-part minimum base datum; upper-envelope podium/tower silhouettes. Road clearance 3.5m beyond authored carriageways including the Cross-Harbour surface approaches, plus 2m within 32m of the Nathan/Granville bus turn; authored park reserved except for the sourced sports centre and administration building. Missing heights use storeys x 3.2m or 9.6m. Facades are generated artwork, not surveyed photographs."}
    meta["small_pavement_gaps_filled"] = len(pavement_patches)
    if island or north or west or northwest or kwai_chung or tsuen_wan or west_coast or east_kowloon:
        meta['note'] = 'Derived expansion corridor massing on the authored land apron, not survey-grade reconstruction. Original WGS84 footprints and relative roof heights; flat ground; connected-part minimum base datum and upper-envelope podium/tower silhouettes. Buildings clipped to the land boundary and 3.5m beyond the surface carriageways. Missing heights use storeys x 3.2m or 9.6m. Facades, paving and vegetation are authored; selected street centrelines come from the Transport Department; the coastline remains authored.'
    if (north or east_kowloon) and any(road['id']==CHI_MAN_STREET_ID and road['width']==5 for road in harbour['roads']):
        meta['note'] += CHI_MAN_BUILDING_NOTE
    if east_kowloon or west or northwest or kwai_chung or tsuen_wan or west_coast:meta['note']=meta['note'].replace('authored land apron','government-derived land boundary').replace('the coastline remains authored','the western coastline comes from LandsD iB1000 Shoreline and CartoHydroLine seawall/high-water features, with recorded short gap repairs; prior building regions are excluded to avoid duplicate geometry')
    if west:
        meta['raised_podium_support']={'source_site':'V Walk','source_OBJECTID':V_WALK_PODIUM_ID,'source_base_mPD':podium_base,
                                       'source_top_mPD':podium_top,'local_base_m':round(podium_top-podium_base,3),
                                       'raised_support_underside_m':raised_podium_base,
                                       'low_bus_envelope_m':BUS_ENVELOPE_HEIGHT,
                                       'clearance_margin_m':BUS_CLEARANCE_MARGIN,
                                       'tower_source_OBJECTIDs':sorted(RAISED_CULLINAN_WEST)}
    if northwest:
        meta['building_region']={'legacy_bounds_m':list(NORTHWEST_LEGACY_BOUNDS),
                                 'former_water_extension_bounds_m':list(NORTHWEST_EXTENSION_BOUNDS),
                                 'east_region_retained_from_x_m':550}
        meta['source_supplement']={'sources':['Data/west-kowloon-buildings.geojson','Data/east-kowloon-buildings.geojson'],
                                   'clipped_to_former_water_extension':True,
                                   'source_OBJECTIDs':sorted(northwest_supplement_ids)}
        if northwest_supplement_ids:
            meta['note']+=' The northwest land-fill extension uses West Kowloon/East Kowloon source building footprints clipped to x=0..550m and z=-6000..-4800m; legacy northwest footprints retain their prior area ownership, while the east region retains x=550..650m.'
        meta['source_supplement']['official_gap_source']={
            'path':KOWLOON_TONG_SOURCE,'source':supplement_metadata['source'],
            'source_response_sha256':supplement_metadata['query_response_sha256'],
            'query_bbox_wgs84':supplement_metadata['bbox_wgs84'],
            'query_bounds_local_m':supplement_metadata['query_local_bounds_m'],
            'query_feature_count':KOWLOON_TONG_RAW_FEATURE_COUNT,
            'existing_source_csuids_excluded':len([f for f in source_features if f['properties']['BuildingBlockType'] in {'Tower','Podium','Temporary Structure'} and local_geometry(f['geometry']).intersection(box(*NORTHWEST_EXTENSION_BOUNDS)).area>=20 and f['properties']['BuildingCSUID'] in existing_source_csuids]),
            'selected_feature_count':len(kowloon_tong_source_ids),
            'selected_source_OBJECTIDs':sorted(kowloon_tong_source_ids),
            'selected_csuids_sha256':selected_csuids_sha256,
            'selected_source_objectid_remaps':sorted(kowloon_tong_source_id_remaps,key=lambda row:row['source_OBJECTID']),
            'minimum_clipped_source_area_m2':20,
            'selected_clipped_area_sum_m2':round(kowloon_tong_source_area,3),
            'selected_clipped_union_area_m2':round(kowloon_tong_union_area,3),
            'selection':'Active Tower, Podium and Temporary Structure source records not already present by BuildingCSUID in the bundled Kowloon building sources; source footprint intersection with the former-water extension must be at least 20 m2.'}
        rendered_ids={building['id'] for building in output}
        rendered_source_ids=sorted(source_id for source_id,internal_id in zip(kowloon_tong_source_ids,kowloon_tong_source_internal_ids) if internal_id in rendered_ids)
        meta['source_supplement']['official_gap_source']['rendered_source_record_count']=len(rendered_source_ids)
        meta['source_supplement']['official_gap_source']['rendered_layout_part_count']=sum(building['id'] in set(kowloon_tong_source_internal_ids) for building in output)
        meta['source_supplement']['official_gap_source']['source_OBJECTIDs_pruned_after_clearance']=sorted(set(kowloon_tong_source_ids)-set(rendered_source_ids))
        if len(kowloon_tong_source_ids)!=KOWLOON_TONG_SELECTED_FEATURE_COUNT:
            raise ValueError('Kowloon Tong layout source manifest is incomplete')
        if len(rendered_source_ids)!=144 or meta['source_supplement']['official_gap_source']['source_OBJECTIDs_pruned_after_clearance']!=[110069]:
            raise ValueError('Kowloon Tong road-clearance footprint accounting changed')
        meta['note']+=' A pinned official CSDI query adds 145 previously absent Tower, Podium and Temporary Structure records within the former-water extension; 144 contribute rendered parts after clearance. Source identities and its 58,082.886 m2 dissolved footprint are recorded in source_supplement. The final 1.967 m2 remnant of source OBJECTID 110069 falls below the existing 4 m2 render cutoff after Cornwall Street clearance.'
    if east_kowloon:meta['note']=meta['note'].replace('western coastline','eastern coastline')
    if west_coast:meta['note']=meta['note'].replace('with recorded short gap repairs','plus connected CartoLandCoverLine rock outlines and pier outlines, with recorded authored gap repairs up to 115.34 m')
    if island:
        meta['note']=meta['note'].replace('authored land apron','government-derived land boundary').replace('the coastline remains authored','the island shoreline comes from LandsD iB1000 with recorded authored ferry-terminal and tunnel-mouth joins')
        meta['coast_sha256']=hashlib.sha256((ROOT/'Data/island-coast.json').read_bytes()).hexdigest()
    else:
        meta['base_sources_sha256'] = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in base_sources}
        if landmarks:
            meta['note']='Height-backed southwest landmark polygons from official iB1000 Building records; source base/roof levels are retained, touching podium/tower parts follow the established upper-envelope layout rule, and no road clearance or unsupported height fallback alters these named footprints.'
        else:
            meta['note'] += f' Base datums are reconciled across all {len(base_sources)} bundled Kowloon building sources before regional clipping; duplicate BuildingCSUID records share one group. TopHeight and fallback Storeys use the newest retrieved_utc record per BuildingCSUID (original undated extract: 2026-09-13 UTC; ties prefer east Kowloon, west coast, Tsuen Wan, Kwai Chung, northwest, west, north, original). Each region retains its own source footprint and OBJECTID.'
    result={"metadata":meta,"buildings":output,"pavement_patches":pavement_patches}
    normal_layout=not (landmarks or island or north or west or northwest or kwai_chung or tsuen_wan or west_coast or east_kowloon)
    if normal_layout and include_landmarks:
        supplement_path=ROOT/'Data/southwest-landmarks-source.geojson'
        if not supplement_path.exists():raise FileNotFoundError('Missing cached southwest iB1000 landmark source')
        supplement=build(landmarks=True,include_landmarks=False,write=False)
        result['buildings'].extend(supplement['buildings'])
        result['metadata']['southwest_landmark_supplement']={
            'source':json.loads(supplement_path.read_text())['metadata'],
            'derived':supplement['metadata']}
        result['metadata']['source_parts']+=supplement['metadata']['source_parts']
        result['metadata']['rendered_parts']=len(result['buildings'])
        result['metadata']['source_parts_retained']=len({b['id'] for b in result['buildings']})
        result['metadata']['source_parts_clipped']+=supplement['metadata']['source_parts_clipped']
        result['metadata']['fallback_height_parts']+=supplement['metadata']['fallback_height_parts']
        all_polys=[Polygon(b['rings'][0],b['rings'][1:]) for b in result['buildings']]
        result['metadata']['footprint_area_m2']=round(union_all(all_polys).area)
        result['metadata']['volume_m3']=round(sum(poly.area*b['height'] for poly,b in zip(all_polys,result['buildings'])))
        result['metadata']['styles']=dict(Counter(b['style'] for b in result['buildings']))
    target=ROOT/("Data/east-kowloon-layout.json" if east_kowloon else "Data/west-coast-layout.json" if west_coast else "Data/tsuen-wan-layout.json" if tsuen_wan else "Data/kwai-chung-layout.json" if kwai_chung else "Data/lai-chi-kok-layout.json" if northwest else "Data/west-kowloon-layout.json" if west else "Data/kowloon-north-layout.json" if north else "Data/island-building-layout.json" if island else "Data/building-layout.json")
    if write:target.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")))
    print("BUILDING_LAYOUT_OK:", json.dumps(meta, ensure_ascii=False))
    return result


if __name__ == "__main__":
    if '--southwest-landmarks' in sys.argv:
        cache=Path(sys.argv[sys.argv.index('--southwest-landmarks')+1])
        (ROOT/'Data/southwest-landmarks-source.geojson').write_bytes(extract_southwest_landmarks(cache))
        build()
    else:
        if '--download' in sys.argv: download_island('--north' in sys.argv, '--west' in sys.argv, '--northwest' in sys.argv, '--kwai-chung' in sys.argv, '--tsuen-wan' in sys.argv, '--west-coast' in sys.argv, '--east-kowloon' in sys.argv)
        build('--island' in sys.argv, '--north' in sys.argv, '--west' in sys.argv, '--northwest' in sys.argv, '--kwai-chung' in sys.argv, '--tsuen-wan' in sys.argv, '--west-coast' in sys.argv, '--east-kowloon' in sys.argv)
