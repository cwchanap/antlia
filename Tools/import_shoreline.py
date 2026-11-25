"""Government shoreline data -> offline land polygons (approximate metres).

Run with .venv-geodata/bin/python Tools/import_shoreline.py [--island|--northwest|--kwai-chung|--tsuen-wan|--west-coast|--east-kowloon] [--download].
--download refreshes the requested archives, or the CEDD Kai Tak supplements
when --east-kowloon is set. Source features and provenance ship in Data.
"""
import datetime
import hashlib
import json
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from pyproj import Transformer
from shapely import STRtree, get_parts, make_valid, set_precision, union_all
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
from shapely.ops import polygonize, unary_union, linemerge, nearest_points, transform
from import_map import ROOT, local, ORIGIN
from import_open_spaces import replace_outputs
from import_tunnel import KOWLOON_CITY_NORTH_FILL_BOUNDS

BOUNDS = (-2700, -4800, 650, 50)
ISLAND = '--island' in sys.argv
NORTHWEST = '--northwest' in sys.argv
KWAI_CHUNG = '--kwai-chung' in sys.argv
TSUEN_WAN = '--tsuen-wan' in sys.argv
WEST_COAST = '--west-coast' in sys.argv
EAST_KOWLOON = '--east-kowloon' in sys.argv
SOURCE = 'https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0/query'
EAST_KOWLOON_BASE_BOUNDS = (550,-6400,3150,-100)
EAST_KOWLOON_BOUNDS = (550,-6400,4900,-100)
KAI_TAK_RECLAMATION_BOUNDS = (2750,-3250,3550,-2160)
KAI_TAK_SEA_FILL_BBOX = (114.196,22.294,114.221,22.353)
KAI_TAK_SEA_FILL_SOURCE = 'https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/411/query'
KAI_TAK_RECLAMATION_SOURCE = ('https://portal.csdi.gov.hk/csdi-webpage/file-api?'
                             'dataset_id=cedd_rcd_1636520962284_7237&format=geojson&layer_name=Coastline')
BBOX = (114.145, 22.290, 114.175, 22.339)
RAW = ROOT/'Data/west-kowloon-shoreline.geojson'
if EAST_KOWLOON:
    BOUNDS = EAST_KOWLOON_BASE_BOUNDS
    BBOX = (114.177,22.295,114.204,22.338)
    RAW = ROOT/'Data/east-kowloon-shoreline.geojson'
elif ISLAND:
    BOUNDS = (-2400,350,2050,2100)
    BBOX = (114.147,22.280,114.192,22.300)
    RAW = ROOT/'Data/island-shoreline.geojson'
elif WEST_COAST:
    BOUNDS = (-13800,-11200,-6400,-6900)
    BBOX = (114.038,22.356,114.111,22.396)
    RAW = ROOT/'Data/west-coast-shoreline.geojson'
elif TSUEN_WAN:
    BOUNDS = (-8500,-11000,-3900,-6900)
    BBOX = (114.089,22.356,114.135,22.394)
    RAW = ROOT/'Data/tsuen-wan-shoreline.geojson'
elif KWAI_CHUNG:
    BOUNDS = (-6500,-8500,-3100,-4400)
    BBOX = (114.108,22.334,114.143,22.372)
    RAW = ROOT/'Data/kwai-chung-shoreline.geojson'
elif NORTHWEST:
    # Continue the inland frame to the existing Kowloon/east-Kowloon join.
    # The retained coastline extract is unchanged and no new shoreline is inferred.
    BOUNDS = (-4600,-6000,650,-3900)
    BBOX = (114.127,22.329,114.173,22.350)
    RAW = ROOT/'Data/lai-chi-kok-shoreline.geojson'
NS = {'g':'http://www.opengis.net/gml','f':'http://www.safe.com/gml/fme'}


def connected_rock_outlines(features):
    # Rocky foreshore edges use a different source layer from high-water/seawall lines.
    # Include only rock outlines connected to the hydrography, not inland rock detail.
    base=[f for f in features if f['properties']['layer']!='CartoLandCoverLine']
    rocks=[f for f in features if f['properties']['layer']=='CartoLandCoverLine']
    lines=[LineString([local(p) for p in f['geometry']['coordinates']]) for f in rocks]
    tree=STRtree(lines);selected=set()
    pending=[LineString([local(p) for p in f['geometry']['coordinates']]) for f in base]
    while pending:
        for index in tree.query(pending.pop(),predicate='dwithin',distance=.1):
            index=int(index)
            if index not in selected:selected.add(index);pending.append(lines[index])
    return base+[f for i,f in enumerate(rocks) if i in selected]


def project_polygon(geometry):
    polygon=transform(lambda longitude, latitude, height=None: local((longitude, latitude)), shape(geometry))
    if polygon.is_valid:
        return polygon
    return union_all([part for part in get_parts(make_valid(polygon)) if part.geom_type in ('Polygon','MultiPolygon')])


def fetch_kai_tak_polygons(url, selected):
    with urllib.request.urlopen(url, timeout=60) as response:
        payload=response.read()
    data=json.loads(payload)
    if data.get('type')!='FeatureCollection' or data.get('exceededTransferLimit') or data.get('error'):
        raise ValueError('Incomplete Kai Tak coastline source: '+url)
    features=[feature for feature in data['features'] if selected(feature)]
    polygons=[project_polygon(feature['geometry']) for feature in features]
    if not polygons or any(not polygon.is_valid or polygon.geom_type not in ('Polygon','MultiPolygon')
                           for polygon in polygons):
        raise ValueError('Missing or invalid Kai Tak coastline polygons: '+url)
    return {
        'type':'FeatureCollection',
        'metadata':{
            'provider':'Civil Engineering and Development Department, HKSAR Government',
            'source':url,
            'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'response_sha256':hashlib.sha256(payload).hexdigest(),
            'terms':'https://portal.csdi.gov.hk/csdi-webpage/doc/TNC',
        },
        'features':features,
    }


def download_kai_tak_extension():
    raw=json.loads(RAW.read_text())
    query=dict(f='geojson',geometry=','.join(map(str,KAI_TAK_SEA_FILL_BBOX)),
               geometryType='esriGeometryEnvelope',inSR=4326,outSR=4326,
               spatialRel='esriSpatialRelIntersects',where="FEATURECODE='SEF'",
               outFields='*',returnGeometry='true',orderByFields='OBJECTID')
    sea_fill=fetch_kai_tak_polygons(
        KAI_TAK_SEA_FILL_SOURCE+'?'+urllib.parse.urlencode(query),
        lambda feature: feature['properties']['FEATURECODE']=='SEF' and feature['properties']['DATASTATUS']=='E')
    sea_fill['metadata']['source_scale']='1:5,000 (source records DATASOURCE 2)'
    sea_fill['metadata']['bbox_wgs84']=KAI_TAK_SEA_FILL_BBOX
    reclamation_extent=box(*KAI_TAK_RECLAMATION_BOUNDS)
    reclamation=fetch_kai_tak_polygons(
        KAI_TAK_RECLAMATION_SOURCE,
        lambda feature: project_polygon(feature['geometry']).intersects(reclamation_extent))
    reclamation['metadata']['source_scale']='1:100,000'
    reclamation['metadata']['local_clip_bounds']=KAI_TAK_RECLAMATION_BOUNDS
    # Preserve the complete published iB1000 line inventory that builds the established coast.
    raw['kai_tak_coast_sources']={'sea_fill':sea_fill,'reclamation':reclamation}
    if len(sea_fill['features'])!=2 or len(reclamation['features'])!=1:
        raise ValueError('The reviewed Kai Tak sea-fill and reclamation inventory changed')
    build(replacement_source=json.dumps(raw,separators=(',',':')).encode('utf-8'))


def extend_kai_tak_land(existing, sources):
    water=union_all([project_polygon(feature['geometry']) for feature in sources['sea_fill']['features']])
    east_edge=EAST_KOWLOON_BASE_BOUNDS[2]
    _, north, east, south=EAST_KOWLOON_BOUNDS
    east_land=box(east_edge,north,east,south).difference(water)
    retained_land=union_all([existing,east_land])
    reclamation=union_all([project_polygon(feature['geometry']) for feature in sources['reclamation']['features']])
    if not reclamation.covers(box(*KOWLOON_CITY_NORTH_FILL_BOUNDS)):
        raise ValueError('Government mainland polygon does not cover the northern fill')
    patches=reclamation.intersection(box(*KAI_TAK_RECLAMATION_BOUNDS)).difference(retained_land)
    runway_approach=Point(3050,-2700)
    runway_fill=next(part for part in get_parts(patches) if part.covers(runway_approach))
    combined=retained_land.union(runway_fill)
    land=next(part for part in get_parts(combined) if part.covers(Point(1200,-2000)))
    assert land.is_valid and existing.difference(land).area<.001, 'The Kai Tak shore must preserve the existing mainland'
    assert land.covers(Point(4200,-1360)) and land.covers(runway_approach), 'Kai Tak runway or runway approach is missing'
    assert not any(land.covers(Point(*p)) for p in [(2600,-2400),(3650,-2210),(4050,-2000),(4700,-1200)]), \
        'The Kai Tak shoreline must retain the harbour and approach channel'
    return land


def download():
    if EAST_KOWLOON:
        download_kai_tak_extension()
        return
    query=dict(f='json',geometry=','.join(map(str,BBOX)),geometryType='esriGeometryEnvelope',inSR=4326,
               spatialRel='esriSpatialRelIntersects',where='1=1',outFields='*',returnGeometry='false')
    with urllib.request.urlopen(SOURCE+'?'+urllib.parse.urlencode(query),timeout=60) as response:
        index=json.load(response)
    assert 'error' not in index and not index.get('exceededTransferLimit') and index.get('features'), index
    cache=Path('/tmp/antila-shoreline');cache.mkdir(exist_ok=True)
    transform=Transformer.from_crs(2326,4326,always_xy=True)
    features=[];sources=[]
    for row in index['features']:
        props=row['attributes'];tile=props['SHEETNO'];path=cache/(tile+'.zip')
        # Refresh before recording the index revision; curl uses the macOS certificate store.
        temp=path.with_suffix('.part')
        subprocess.run(['curl','--silent','--show-error','--fail','--location','--max-time','120',props['GML'],'-o',str(temp)],check=True)
        assert zipfile.is_zipfile(temp), 'Expected an iB1000 GML archive'
        with zipfile.ZipFile(temp) as archive:
            for layer in ('Shoreline','CartoHydroLine',*(['TransportPolygon'] if ISLAND or TSUEN_WAN or WEST_COAST or EAST_KOWLOON else []),*(['CartoLandCoverLine'] if WEST_COAST else [])):
                filename=tile+'/Layers/'+('LandCover' if layer=='CartoLandCoverLine' else 'Transportation' if layer=='TransportPolygon' else 'Hydrography')+'/'+layer+'.gml'
                if filename not in archive.namelist():continue
                root=ET.fromstring(archive.read(filename))
                assert all(e.get('srsName')=='EPSG:2326' for e in root.iter() if e.get('srsName')), 'Unexpected shoreline CRS'
                for feature in root.findall('g:featureMember/f:'+layer,NS):
                    fields={e.tag.split('}')[-1]:e.text for e in feature if e.tag.startswith('{'+NS['f']+'}')}
                    if layer=='Shoreline' and fields.get('STATUS')!='E':continue
                    if layer=='CartoHydroLine' and fields.get('CARTOHYDROLINETYPE') not in ('SW','HW'):continue
                    if layer=='TransportPolygon' and (fields.get('TRANSPORTPOLYGONTYPE')!='JPW' or fields.get('STATUS')!='E'):continue
                    if layer=='CartoLandCoverLine' and fields.get('LANDCOVERLINETYPE')!='RKA':continue
                    for positions in feature.findall('.//g:posList',NS):
                        values=list(map(float,positions.text.split()));assert len(values)%3==0
                        # EPSG:2326 GML uses northing/easting axis order; always_xy expects easting/northing.
                        coords=[list(transform.transform(values[i+1],values[i])) for i in range(0,len(values),3)]
                        features.append(dict(type='Feature',properties=fields|{'tile':tile,'layer':layer},geometry=dict(type='LineString',coordinates=coords)))
        temp.replace(path)
        sources.append(dict(tile=tile,url=props['GML'],revision_date=props['REVISIONDATE'],sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        print('SHORELINE_TILE_OK:',tile,flush=True)
    metadata=dict(provider='Lands Department, HKSAR Government',source=SOURCE,bbox_wgs84=BBOX,
                  retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_crs='EPSG:2326',axis_order='GML northing,easting,height',
                  terms='https://portal.csdi.gov.hk/csdi-webpage/doc/TNC',tiles=sources)
    if WEST_COAST:
        features=connected_rock_outlines(features)
        metadata['rock_outline_selection']='RKA outlines connected within 0.1 m to shoreline/seawall/pier source features'
    RAW.write_text(json.dumps(dict(type='FeatureCollection',metadata=metadata,features=features),separators=(',',':')))


def build(*, replacement_source=None):
    source=RAW.read_bytes() if replacement_source is None else replacement_source
    raw=json.loads(source)
    # The western shore joins the established district at x=-900; eastern TST is retained.
    region=box(*BOUNDS) if ISLAND or NORTHWEST or KWAI_CHUNG or TSUEN_WAN or WEST_COAST or EAST_KOWLOON else box(BOUNDS[0],BOUNDS[1],-900,BOUNDS[3])
    lines=[set_precision(LineString([local(p) for p in f['geometry']['coordinates']]),.001) for f in raw['features']]
    coast=unary_union(lines).intersection(region)
    parts=list(linemerge(coast).geoms);links=[]
    for i,line in enumerate(parts):
        if line.is_closed:continue
        for point in (Point(line.coords[0]),Point(line.coords[-1])):
            if region.boundary.distance(point)<.01:continue
            rest=unary_union(parts[:i]+parts[i+1:]);distance=point.distance(rest)
            # Source sheets have small discontinuities between seawall/high-water features.
            # Record every straight gap closure; never bridge a missing coastline wholesale.
            # Island and Tsuen Wan ferry-terminal outlines have longer interruptions than the western shore.
            # Every authored join is retained below; this is not surveyed terminal geometry.
            if 1e-6<distance<=(120 if ISLAND or WEST_COAST else 60 if TSUEN_WAN or EAST_KOWLOON else 12):links.append(LineString([point,nearest_points(point,rest)[1]]))
    joined=union_all([coast,*links],grid_size=.001 if WEST_COAST else None)
    if ISLAND:
        # A 10 cm weld closes near-coincident cartographic line ends; restore its inset afterwards.
        joined=union_all([coast,*links],grid_size=.001)
        mainland=next(p for p in region.difference(joined.buffer(.1)).geoms if p.contains(Point(0,1900)))
        land=Polygon(mainland.exterior).buffer(.1,join_style='mitre').intersection(region)
        assert 4e6<land.area<5e6 and not land.covers(Point(0,600)) and land.covers(Point(-1343,1080)), 'Island coast / Two IFC misplaced'
        shore=land.boundary.difference(region.boundary.buffer(.01)).simplify(.25)
        links=[p for p in links if p.intersection(shore.buffer(.3)).length>p.length*.8]
    else:
        faces=list(polygonize(union_all([joined,region.boundary],grid_size=.001 if WEST_COAST else None)))
        mainland=next(p for p in faces if p.contains(Point(1200,-2000) if EAST_KOWLOON else Point(-11000,-9800) if WEST_COAST else Point(-6500,-9200) if TSUEN_WAN else Point(-4400,-7300) if KWAI_CHUNG else Point(-3000,-5100) if NORTHWEST else Point(-1000,-4000)))
        land=Polygon(mainland.exterior) if NORTHWEST or KWAI_CHUNG or TSUEN_WAN or WEST_COAST or EAST_KOWLOON else unary_union([Polygon(mainland.exterior),box(-900,BOUNDS[1],BOUNDS[2],BOUNDS[3])])
        if EAST_KOWLOON:
            assert land.area>5e6 and land.covers(Point(1800,-1300)) and not land.covers(Point(2800,-800)), 'Eastern Kowloon mainland / sea misplaced'
        elif WEST_COAST:
            assert 24e6<land.area<25e6 and land.covers(Point(-11700,-9000)) and not land.covers(Point(-11500,-7200)), 'Sham Tseng mainland / sea misplaced'
        elif TSUEN_WAN:
            assert 15e6<land.area<16e6 and land.covers(Point(-6600,-9000)) and not land.covers(Point(-7200,-7600)), 'Tsuen Wan mainland / Rambler Channel misplaced'
        elif KWAI_CHUNG:
            assert land.area>6e6 and land.covers(Point(-4800,-6800)), 'Kwai Chung mainland missing'
        elif NORTHWEST:
            assert land.area>6e6 and land.covers(Point(-3400,-4800)), 'Lai Chi Kok mainland missing'
        else:
            assert land.area>5e6 and not land.covers(Point(-2600,-1000)) and land.covers(Point(-700,-4000)), 'Shoreline must separate mainland from sea'
            assert land.covers(Point(-1600,-700)) and not land.covers(Point(-2000,-800)), 'West Kowloon peninsula misplaced'
        # Fixed-precision intersections split rocky shores into tiny consecutive pieces;
        # recover the complete polygon edge before simplification and length filtering.
        shore=(land.boundary.difference(region.boundary.buffer(.01)) if WEST_COAST or EAST_KOWLOON else land.boundary.intersection(joined)).simplify(.25)
        if TSUEN_WAN or WEST_COAST or EAST_KOWLOON:links=[p for p in links if p.intersection(shore.buffer(.3)).length>p.length*.8]
    output_bounds=BOUNDS
    source_metadata=raw['metadata']
    if EAST_KOWLOON and 'kai_tak_coast_sources' in raw:
        sources=raw['kai_tak_coast_sources']
        land=extend_kai_tak_land(land,sources)
        output_bounds=EAST_KOWLOON_BOUNDS
        shore=land.boundary.difference(box(*output_bounds).boundary.buffer(.01)).simplify(.25)
        source_metadata=source_metadata|{
            'kai_tak_coast_sources':{key:source['metadata'] for key,source in sources.items()},
            'kai_tak_processing':(
                'Keep the established iB1000 land polygon. Extend east with the CEDD sea-fill complement. '
                'Use the CEDD geological coastline in the bounded runway reclamation where the precise '
                'sea-fill polygons predate the road. Omit detached land across the approach channel.'
            ),
        }
    parts=list(shore.geoms) if hasattr(shore,'geoms') else [shore]
    output=dict(metadata=source_metadata|dict(source_sha256=hashlib.sha256(source).hexdigest(),origin_wgs84=ORIGIN,
                processing='HK1980 Grid EPSG:2326 northing/easting to WGS84; approximate local metre projection; 1 mm topology grid; coast simplified within 0.25 m. Straight source gaps and map cuts are authored.'+(' Island: pier outlines included, 10 cm topology weld; ferry-terminal and tunnel-mouth joins up to 120 m are explicitly authored.' if ISLAND else ' Eastern Kowloon: source pier outlines included; recorded seawall joins up to 60 m are authored.' if EAST_KOWLOON else ' Tsuen Wan: source pier outlines included; recorded terminal and seawall joins up to 60 m are authored.' if TSUEN_WAN else ' Ting Kau / Sham Tseng: source pier and connected rocky-shore outlines included; recorded joins up to 120 m are authored.' if WEST_COAST else ''),
                gap_closures=[list(p.coords) for p in links],max_gap_closure_m=max((p.length for p in links),default=0)),
                bounds=output_bounds,land=mapping(land),coastline=[list(p.coords) for p in parts if p.length>.5])
    target=ROOT/('Data/east-kowloon-coast.json' if EAST_KOWLOON else 'Data/west-coast-coast.json' if WEST_COAST else 'Data/tsuen-wan-coast.json' if TSUEN_WAN else 'Data/kwai-chung-coast.json' if KWAI_CHUNG else 'Data/island-coast.json' if ISLAND else 'Data/lai-chi-kok-coast.json' if NORTHWEST else 'Data/west-kowloon-coast.json')
    coast_bytes=json.dumps(output,separators=(',',':')).encode('utf-8')
    if replacement_source is None:
        target.write_bytes(coast_bytes)
    else:
        replace_outputs([(RAW,source),(target,coast_bytes)])
    print('ANTILA_COAST_OK:',len(raw['features']),'source fragments;',round(land.area),'m² land;',round(shore.length),'m shoreline')


if __name__=='__main__':
    if '--download' in sys.argv:
        download()
        if not EAST_KOWLOON:
            build()
    else:
        build()
