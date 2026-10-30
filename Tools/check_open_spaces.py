"""Regress government refreshes in temporary files; requires the twelve cached iB1000 ZIPs.

.venv-geodata/bin/python Tools/check_open_spaces.py CACHE_DIR TILE_SOURCES_JSON
"""
import contextlib
import copy
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import import_open_spaces as importer
from shapely import union_all
from shapely.geometry import Polygon, Point, LineString


def check_gardens(source,target):
    raw=json.loads(source);data=json.loads(target)
    expected={'1503005143':3646.11,'1503005266':3918.03,'1503005193':716.70,
              '1503005468':2267.98,'1810041992':1757.65}
    assert {g['site'] for g in data['gardens']}==set(expected)
    assert len(data['surfaces'])==17 and len(data['sports'])==15 and len(data['play_areas'])==1
    assert sum(s['fixtures'] for s in data['sites'] if s['id'] not in expected)==273
    def poly(rings):return Polygon(rings[0],rings[1:])
    buildings=union_all([poly(b['rings']) for name in ('kowloon-north-layout','west-kowloon-layout')
                        for b in json.loads((importer.ROOT/f'Data/{name}.json').read_text())['buildings']])
    roads=union_all([LineString([(p[0],p[2]) for p in r['points']]).buffer(max(12,r['width'])/2+3.5,join_style='mitre')
                    for r in json.loads((importer.ROOT/'Data/cross-harbour.json').read_text())['roads']
                    if not r['tunnel'] or r.get('ramp',False)])
    for garden in data['gardens']:
        uid=garden['site'];parts=[]
        for f in raw['features']:
            if f['properties'].get('SITEID')!=uid:continue
            rings=f['geometry']['coordinates']
            parts.append(poly([[importer.local(p) for p in ring] for ring in rings]))
        site=union_all(parts);paths=union_all([poly(r) for r in garden['paths']]);access=union_all([poly(r) for r in garden['access']])
        assert abs(site.area-expected[uid])<.02,uid+': source tile pieces lost'
        assert union_all([poly(r) for r in garden['rings']]).symmetric_difference(site).area<.01
        assert paths.area>80 and paths.difference(site).area<.01
        assert paths.intersection(buildings).area<.01 and paths.intersection(roads).area<.01
        fixtures=[f for f in data['fixtures'] if f['site']==uid]
        assert len(fixtures)>=3 and any(f['asset']=='bench' for f in fixtures)
        assert any(f['asset'] in ('street-tree','banyan','planter') for f in fixtures)
        for f in fixtures:
            p=Point(f['position']);r=f['radius']
            assert site.covers(p.buffer(r)),uid+': furniture leaves source boundary'
            assert access.distance(p)>=r-.01,uid+': entrance obstructed'
            assert buildings.distance(p)>r and roads.distance(p)>r
            if f['asset'] in ('street-tree','banyan'):assert paths.distance(p)>=r,uid+': tree on path'
    play=data['play_areas'][0];assert play['site']=='1503005266' and play['kind']=='authored_play'
    pad=poly(play['rings']);garden=next(g for g in data['gardens'] if g['site']==play['site'])
    assert union_all([poly(r) for r in garden['rings']]).covers(pad)
    assert pad.intersection(union_all([poly(r) for r in garden['paths']])).area<.01
    assert pad.intersection(buildings).area<.01 and pad.intersection(roads).area<.01
    assert abs(sum(Polygon(t).area for t in play['triangles'])-140)<.01
    print('ANTILA_POCKET_GARDEN_DATA_OK: five complete source sites; bounded paving, planting, clear access and separate authored play pad')


def check(cache,manifest_path):
    source=importer.SOURCE.read_bytes();target=importer.TARGET.read_bytes()
    check_gardens(source,target)
    manifest=json.loads(manifest_path.read_text())
    # A successful refresh must actually replace different bytes and update the source hash.
    manifest['retrieved_utc']='2099-01-01T00:00:00+00:00'
    with tempfile.TemporaryDirectory(prefix='antila-open-space-check-') as directory:
        trial=Path(directory);tiles=trial/'tiles';tiles.mkdir()
        for row in manifest['tiles']:(tiles/(row['tile']+'.zip')).symlink_to((cache/(row['tile']+'.zip')).resolve())
        src=trial/'source.geojson';dst=trial/'layout.json';mp=trial/'manifest.json'
        src.write_bytes(source);dst.write_bytes(target)
        def run(rows):
            mp.write_text(json.dumps(rows))
            with contextlib.redirect_stdout(io.StringIO()):importer.refresh(tiles,mp)
        rejected=[]
        def reject(label,action,exception):
            before=(src.read_bytes(),dst.read_bytes())
            try:action()
            except exception as error:print(label+': '+str(error))
            else:raise AssertionError(label+': invalid refresh accepted')
            assert (src.read_bytes(),dst.read_bytes())==before,label+': previous data changed'
            assert not list(trial.glob('.open-spaces-*')),label+': staging directory leaked'
            rejected.append(label)
        with patch.object(importer,'SOURCE',src),patch.object(importer,'TARGET',dst):
            missing=copy.deepcopy(manifest);missing['tiles']=[r for r in missing['tiles'] if r['tile']!='11-NW-15C']
            reject('missing_school_sheet',lambda:run(missing),ValueError)
            duplicate=copy.deepcopy(manifest);duplicate['tiles'][-1]=duplicate['tiles'][0]
            reject('duplicate_sheet',lambda:run(duplicate),ValueError)
            wrong=copy.deepcopy(manifest);wrong['tiles'][0]['tile']='11-NW-99A'
            reject('wrong_sheet',lambda:run(wrong),ValueError)
            bad_hash=copy.deepcopy(manifest);bad_hash['tiles'][0]['sha256']='0'*64
            reject('bad_zip_hash',lambda:run(bad_hash),ValueError)
            for layer,mutation in [('Site','missing'),('BuiltStructurePolygon','missing'),('Site','malformed'),
                                   ('Site','empty'),('BuiltStructurePolygon','empty'),
                                   ('Site','unrecognized'),('BuiltStructurePolygon','unrecognized')]:
                changed=copy.deepcopy(manifest);row=next(r for r in changed['tiles'] if r['tile']=='11-NW-15C')
                zpath=tiles/(row['tile']+'.zip');zpath.unlink()
                layer_path=row['tile']+'/Layers/Buildings/'+layer+'.gml'
                with zipfile.ZipFile(cache/zpath.name) as old,zipfile.ZipFile(zpath,'w') as new:
                    for name in old.namelist():
                        if name!=layer_path:new.writestr(name,old.read(name))
                        elif mutation=='malformed':new.writestr(name,b'<truncated>')
                        elif mutation!='missing':
                            doc=ET.fromstring(old.read(name));members=doc.findall('g:featureMember',importer.NS)
                            assert members,'Regression fixture must start with populated source data'
                            for member in members:
                                if mutation=='empty':doc.remove(member)
                                else:
                                    for feature in member:feature.tag='{urn:unexpected-schema}'+layer
                            new.writestr(name,ET.tostring(doc,encoding='utf-8',xml_declaration=True))
                row['sha256']=hashlib.sha256(zpath.read_bytes()).hexdigest()
                reject(mutation+'_'+layer,lambda:run(changed),ET.ParseError if mutation=='malformed' else ValueError)
                zpath.unlink();zpath.symlink_to((cache/zpath.name).resolve())
            with patch.object(importer,'build',side_effect=ValueError('derived layout rejected')):
                reject('derived_layout_failure',lambda:run(manifest),ValueError)

            # Exercise real extraction and derivation once before isolating filesystem failures.
            run(manifest)
            fresh_source=src.read_bytes();fresh_target=dst.read_bytes()
            assert fresh_source!=source and fresh_target!=target
            a=json.loads(fresh_target);b=json.loads(target)
            assert {k:v for k,v in a.items() if k!='metadata'}=={k:v for k,v in b.items() if k!='metadata'}
            assert a['metadata']['source_sha256']==hashlib.sha256(fresh_source).hexdigest()
            assert next(s for s in a['sites'] if s['id']=='1503005534')['source_area_m2']==77700.73
            src.write_bytes(source);dst.write_bytes(target)
            write_bytes=Path.write_bytes;replace=Path.replace
            def partial_write(path,payload):
                if path.name=='1.part':
                    write_bytes(path,payload[:20]);raise OSError('staging write interrupted')
                return write_bytes(path,payload)
            with patch.object(importer,'build',return_value=fresh_target):
                with patch.object(Path,'write_bytes',partial_write):
                    reject('partial_staging_write',lambda:run(manifest),OSError)
                for name,error in [('0.part',OSError('first replacement failed')),('1.part',OSError('second replacement failed')),
                                   ('1.part',KeyboardInterrupt('second replacement interrupted'))]:
                    def fail_replace(path,destination):
                        if path.name==name:raise error
                        return replace(path,destination)
                    with patch.object(Path,'replace',fail_replace):
                        reject(type(error).__name__+'_'+name,lambda:run(manifest),type(error))
            # The normal offline rebuild also checks its cached manifest before replacing runtime data.
            bad_source=json.loads(source);bad_source['metadata']['tiles']=missing['tiles']
            src.write_bytes(importer.encoded(bad_source))
            reject('partial_cached_source',lambda:importer.refresh(),ValueError)
            src.write_bytes(source)
            with contextlib.redirect_stdout(io.StringIO()):importer.refresh()
            assert src.read_bytes()==source and dst.read_bytes()==target,'unchanged offline build drifted'
    print(f'ANTILA_OPEN_SPACE_REFRESH_OK: complete refresh and unchanged offline rebuild; {len(rejected)} rejected refresh/file-failure cases preserve previous bytes')


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: check_open_spaces.py CACHE_DIR TILE_SOURCES_JSON')
    check(Path(sys.argv[1]),Path(sys.argv[2]))
