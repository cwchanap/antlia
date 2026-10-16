"""Regress building downloads and regional heights without changing shipped data."""
import copy
import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import import_buildings as importer


def check_download():
    saved = (importer.ROOT/'Data/kwai-chung-buildings.geojson').read_bytes()
    features = json.loads(saved)['features'][:2]
    def page(items):return dict(type='FeatureCollection',features=items)
    with tempfile.TemporaryDirectory(prefix='antila-building-download-') as directory:
        trial=Path(directory);(trial/'Data').mkdir()
        def refresh(responses, **mode):
            responses=iter(responses);queries=[]
            def response(url, **kwargs):
                queries.append(importer.urllib.parse.parse_qs(importer.urllib.parse.urlparse(url).query))
                payload=next(responses)
                if isinstance(payload,Exception):raise payload
                return io.BytesIO(payload if isinstance(payload,bytes) else json.dumps(payload).encode())
            with patch.object(importer,'ROOT',trial),patch.object(importer.urllib.request,'urlopen',response), \
                 contextlib.redirect_stdout(io.StringIO()):
                importer.download_island(**mode)
            return queries
        modes=[('island',{},importer.ISLAND_BBOX),('kowloon-north',dict(north=True),importer.KOWLOON_BBOX),
               ('west-kowloon',dict(west=True),importer.WEST_BBOX),
               ('lai-chi-kok',dict(northwest=True),importer.NORTHWEST_BBOX),
               ('kwai-chung',dict(kwai_chung=True),importer.KWAI_CHUNG_BBOX),
               ('tsuen-wan',dict(tsuen_wan=True),importer.TSUEN_WAN_BBOX),
               ('west-coast',dict(west_coast=True),importer.WEST_COAST_BBOX)]
        for name,mode,bbox in modes:
            target=trial/f'Data/{name}-buildings.geojson';target.write_bytes(saved)
            queries=refresh([dict(count=2),page(features[:1]),page(features[1:])],**mode)
            updated=json.loads(target.read_text())
            assert updated['type']=='FeatureCollection' and updated['features']==features
            assert updated['metadata']['source']==importer.SOURCE and updated['metadata']['bbox_wgs84']==list(bbox)
            assert importer.datetime.datetime.fromisoformat(updated['metadata']['retrieved_utc']).utcoffset()==importer.datetime.timedelta(0)
            assert [q['resultOffset'] for q in queries[1:]]==[['0'],['1']]
            assert all(q['geometry']==[','.join(map(str,bbox))] for q in queries)
        target=trial/'Data/kwai-chung-buildings.geojson';target.write_bytes(saved)
        rejected=[('zero_count',[dict(count=0)]),('invalid_count',[dict(count=True)]),
                  ('duplicate_ids',[dict(count=2),page(features[:1]*2)]),
                  ('empty_page',[dict(count=2),page(features[:1]),page([])]),
                  ('api_error',[dict(count=2),page(features[:1]),dict(error={'message':'service unavailable'})]),
                  ('network_error',[dict(count=2),page(features[:1]),OSError('connection lost')]),
                  ('invalid_json',[dict(count=2),b'not JSON'])]
        for key in ('OBJECTID','BuildingCSUID','BuildingBlockType'):
            bad=copy.deepcopy(features[0]);bad['properties'].pop(key)
            rejected.append(('missing_'+key,[dict(count=1),page([bad])]))
        for label,key,value in [('blank_identity','BuildingCSUID',' '),('invalid_height','TopHeight',float('nan')),
                                ('invalid_storeys','Storeys','three')]:
            bad=copy.deepcopy(features[0]);bad['properties'][key]=value
            rejected.append((label,[dict(count=1),page([bad])]))
        for label,geometry in [('missing_geometry',None),('wrong_geometry',dict(type='Point',coordinates=[114.13,22.35])),
                               ('bad_coordinates',dict(type='Polygon',coordinates=[[['bad',22.35]]*4])),
                               ('zero_area',dict(type='Polygon',coordinates=[[[114.13,22.35]]*4]))]:
            bad=copy.deepcopy(features[0]);bad['geometry']=geometry
            rejected.append((label,[dict(count=1),page([bad])]))
        for label,responses in rejected:
            try:refresh(responses,kwai_chung=True)
            except (ValueError,OSError):pass
            else:raise AssertionError(f'{label}: invalid download was accepted')
            assert target.read_bytes()==saved,f'{label}: rejected download replaced the previous cache'
            assert not list((trial/'Data').glob('*.part')),f'{label}: temporary file leaked'
        write_text=Path.write_text
        def interrupted_write(path,text,**kwargs):
            write_text(path,text[:20],**kwargs)
            raise OSError('write interrupted')
        for operation,error in [('write_text',interrupted_write),('replace',OSError('replace interrupted'))]:
            with patch.object(Path,operation,**({'new':error} if callable(error) else {'side_effect':error})):
                try:refresh([dict(count=2),page(features)],kwai_chung=True)
                except OSError:pass
                else:raise AssertionError(f'{operation}: file failure was swallowed')
            assert target.read_bytes()==saved,f'{operation}: file failure replaced the previous cache'
            assert not list((trial/'Data').glob('*.part')),f'{operation}: temporary file leaked'
    print(f'ANTILA_BUILDING_DOWNLOAD_OK: seven regional paginated refreshes; {len(rejected)} rejected responses and two file failures preserve cache bytes')


def check():
    root = importer.ROOT
    cases = {'3503618508T20260615': (149.6, None, 143.5),
             '3499118543T20260615': (None, 36, 115.2)}
    with tempfile.TemporaryDirectory(prefix='antila-building-check-') as directory:
        trial = Path(directory)
        (trial/'Data').mkdir()
        for name in ('nathan-road.json','cross-harbour.json','west-kowloon-coast.json',
                     'island-coast.json','buildings.geojson','west-kowloon-buildings.geojson','lai-chi-kok-buildings.geojson','kwai-chung-buildings.geojson','tsuen-wan-buildings.geojson','west-coast-buildings.geojson'):
            (trial/'Data'/name).symlink_to(root/'Data'/name)
        raw = json.loads((root/'Data/kowloon-north-buildings.geojson').read_text())
        for feature in raw['features']:
            props = feature['properties']
            if props['BuildingCSUID'] in cases:
                props['TopHeight'], props['Storeys'], _ = cases[props['BuildingCSUID']]
        # The northern revision must win even though the western file is loaded later.
        raw['metadata']['retrieved_utc'] = '2099-01-01T00:00:00+00:00'
        (trial/'Data/kowloon-north-buildings.geojson').write_text(json.dumps(raw))
        importer.ROOT = trial
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                importer.build()
                importer.build(north=True)
                importer.build(west=True)
            seen = {uid: set() for uid in cases}
            for source, layout in (('buildings','building-layout'),('kowloon-north-buildings','kowloon-north-layout'),
                                   ('west-kowloon-buildings','west-kowloon-layout')):
                features = json.loads((trial/f'Data/{source}.geojson').read_text())['features']
                ids = {f['properties']['OBJECTID']: f['properties']['BuildingCSUID'] for f in features}
                for building in json.loads((trial/f'Data/{layout}.json').read_text())['buildings']:
                    uid = ids[building['id']]
                    if uid in cases:
                        seen[uid].add(layout)
                        assert building['height'] == cases[uid][2], (uid,layout,building['height'],cases[uid][2])
            assert all(len(regions) >= 2 for regions in seen.values()), 'Refresh checks must cross region boundaries'
        finally:
            importer.ROOT = root
    print('ANTILA_BUILDING_REFRESH_OK: newest TopHeight and missing-height Storeys fallback agree across rebuilt regions')


if __name__ == '__main__':
    check_download()
    check()
