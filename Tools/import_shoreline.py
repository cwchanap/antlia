"""LandsD iB1000 tiles -> offline West Kowloon or island shore (approximate metres).

Run with .venv-geodata/bin/python Tools/import_shoreline.py [--island|--northwest|--kwai-chung] [--download].
--download refreshes all requested archives under /tmp; source features and provenance ship in Data.
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
from shapely import set_precision, union_all
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely.ops import polygonize, unary_union, linemerge, nearest_points
from import_map import ROOT, local, ORIGIN

BOUNDS = (-2700, -4800, 650, 50)
ISLAND = '--island' in sys.argv
NORTHWEST = '--northwest' in sys.argv
KWAI_CHUNG = '--kwai-chung' in sys.argv
SOURCE = 'https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0/query'
BBOX = (114.145, 22.290, 114.175, 22.339)
RAW = ROOT/'Data/west-kowloon-shoreline.geojson'
if ISLAND:
    BOUNDS = (-2400,350,2050,2100)
    BBOX = (114.147,22.280,114.192,22.300)
    RAW = ROOT/'Data/island-shoreline.geojson'
elif KWAI_CHUNG:
    BOUNDS = (-6500,-8500,-3100,-4400)
    BBOX = (114.108,22.334,114.143,22.372)
    RAW = ROOT/'Data/kwai-chung-shoreline.geojson'
elif NORTHWEST:
    BOUNDS = (-4600,-6000,0,-3900)
    BBOX = (114.127,22.329,114.173,22.350)
    RAW = ROOT/'Data/lai-chi-kok-shoreline.geojson'
NS = {'g':'http://www.opengis.net/gml','f':'http://www.safe.com/gml/fme'}


def download():
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
            for layer in ('Shoreline','CartoHydroLine',*(['TransportPolygon'] if ISLAND else [])):
                filename=tile+'/Layers/'+('Transportation' if layer=='TransportPolygon' else 'Hydrography')+'/'+layer+'.gml'
                if filename not in archive.namelist():continue
                root=ET.fromstring(archive.read(filename))
                assert all(e.get('srsName')=='EPSG:2326' for e in root.iter() if e.get('srsName')), 'Unexpected shoreline CRS'
                for feature in root.findall('g:featureMember/f:'+layer,NS):
                    fields={e.tag.split('}')[-1]:e.text for e in feature if e.tag.startswith('{'+NS['f']+'}')}
                    if layer=='Shoreline' and fields.get('STATUS')!='E':continue
                    if layer=='CartoHydroLine' and fields.get('CARTOHYDROLINETYPE') not in ('SW','HW'):continue
                    if layer=='TransportPolygon' and (fields.get('TRANSPORTPOLYGONTYPE')!='JPW' or fields.get('STATUS')!='E'):continue
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
    RAW.write_text(json.dumps(dict(type='FeatureCollection',metadata=metadata,features=features),separators=(',',':')))


def build():
    raw=json.loads(RAW.read_text())
    # The western shore joins the established district at x=-900; eastern TST is retained.
    region=box(*BOUNDS) if ISLAND or NORTHWEST or KWAI_CHUNG else box(BOUNDS[0],BOUNDS[1],-900,BOUNDS[3])
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
            # Island ferry-terminal outlines have longer interruptions than the western shore.
            # Every authored join is retained below; this is not surveyed terminal geometry.
            if 1e-6<distance<=(120 if ISLAND else 12):links.append(LineString([point,nearest_points(point,rest)[1]]))
    joined=unary_union([coast,*links])
    if ISLAND:
        # A 10 cm weld closes near-coincident cartographic line ends; restore its inset afterwards.
        joined=union_all([coast,*links],grid_size=.001)
        mainland=next(p for p in region.difference(joined.buffer(.1)).geoms if p.contains(Point(0,1900)))
        land=Polygon(mainland.exterior).buffer(.1,join_style='mitre').intersection(region)
        assert 4e6<land.area<5e6 and not land.covers(Point(0,600)) and land.covers(Point(-1343,1080)), 'Island coast / Two IFC misplaced'
        shore=land.boundary.difference(region.boundary.buffer(.01)).simplify(.25)
        links=[p for p in links if p.intersection(shore.buffer(.3)).length>p.length*.8]
    else:
        faces=list(polygonize(unary_union([joined,region.boundary])))
        mainland=next(p for p in faces if p.contains(Point(-4400,-7300) if KWAI_CHUNG else Point(-3000,-5100) if NORTHWEST else Point(-1000,-4000)))
        land=Polygon(mainland.exterior) if NORTHWEST or KWAI_CHUNG else unary_union([Polygon(mainland.exterior),box(-900,BOUNDS[1],BOUNDS[2],BOUNDS[3])])
        if KWAI_CHUNG:
            assert land.area>6e6 and land.covers(Point(-4800,-6800)), 'Kwai Chung mainland missing'
        elif NORTHWEST:
            assert land.area>6e6 and land.covers(Point(-3400,-4800)), 'Lai Chi Kok mainland missing'
        else:
            assert land.area>5e6 and not land.covers(Point(-2600,-1000)) and land.covers(Point(-700,-4000)), 'Shoreline must separate mainland from sea'
            assert land.covers(Point(-1600,-700)) and not land.covers(Point(-2000,-800)), 'West Kowloon peninsula misplaced'
        shore=land.boundary.intersection(joined).simplify(.25)
    parts=list(shore.geoms) if hasattr(shore,'geoms') else [shore]
    output=dict(metadata=raw['metadata']|dict(source_sha256=hashlib.sha256(RAW.read_bytes()).hexdigest(),origin_wgs84=ORIGIN,
                processing='HK1980 Grid EPSG:2326 northing/easting to WGS84; approximate local metre projection; 1 mm topology grid; coast simplified within 0.25 m. Straight source gaps and map cuts are authored.'+(' Island: pier outlines included, 10 cm topology weld; ferry-terminal and tunnel-mouth joins up to 120 m are explicitly authored.' if ISLAND else ''),
                gap_closures=[list(p.coords) for p in links],max_gap_closure_m=max((p.length for p in links),default=0)),
                bounds=BOUNDS,land=mapping(land),coastline=[list(p.coords) for p in parts if p.length>.5])
    (ROOT/('Data/kwai-chung-coast.json' if KWAI_CHUNG else 'Data/island-coast.json' if ISLAND else 'Data/lai-chi-kok-coast.json' if NORTHWEST else 'Data/west-kowloon-coast.json')).write_text(json.dumps(output,separators=(',',':')))
    print('ANTILA_COAST_OK:',len(raw['features']),'source fragments;',round(land.area),'m² land;',round(shore.length),'m shoreline')


if __name__=='__main__':
    if '--download' in sys.argv:download()
    build()
