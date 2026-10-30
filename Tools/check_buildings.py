"""Regress building downloads and regional heights without changing shipped data."""
import copy
import contextlib
import hashlib
import io
import json
import math
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


def check_east_kowloon_merge():
    root=importer.ROOT
    original=json.loads((root/'Data/east-kowloon-buildings.geojson').read_text())
    saved_metadata=original['metadata'].get('merge_provenance',{}).get('preserved_source_metadata',original['metadata'])
    old_bbox=saved_metadata['bbox_wgs84']
    old_north=importer.local([old_bbox[0],old_bbox[3]])[1]

    def geo(px,pz):
        return [importer.ORIGIN[0]+px/(111320*math.cos(math.radians(importer.ORIGIN[1]))),
                importer.ORIGIN[1]-pz/111320]
    def feature(object_id,x,z,csuid=None):
        ring=[geo(x-4,z-4),geo(x+4,z-4),geo(x+4,z+4),geo(x-4,z+4)]
        ring.append(ring[0])
        return {'type':'Feature','properties':{'OBJECTID':object_id,'BuildingCSUID':csuid or f'east-{object_id}',
                'BuildingBlockType':'Building','BaseHeight':4,'TopHeight':12,'Storeys':3,'BuildingNameEN':f'Building {object_id}'},
                'geometry':{'type':'Polygon','coordinates':[ring]}}

    old_features=[feature(71001,1000,-1500),feature(71002,1250,-4300)]
    previous={'type':'FeatureCollection','metadata':{'source':importer.SOURCE,'bbox_wgs84':old_bbox,
              'retrieved_utc':'2026-10-21T07:10:03+00:00'},'features':old_features}
    planned_bounds=(550,-6400,3150,-100)
    southwest=geo(planned_bounds[0],planned_bounds[3]);northeast=geo(planned_bounds[2],planned_bounds[1])
    planned_bbox=(southwest[0],southwest[1],northeast[0],northeast[1])
    northern=feature(71002,1500,(planned_bounds[1]+old_north)/2,'east-new-81001')
    southern=feature(81002,1800,-2500)
    multipart=feature(81003,1600,(planned_bounds[1]+old_north)/2)
    second_part=feature(81003,1650,(planned_bounds[1]+old_north)/2)
    multipart['geometry']={'type':'MultiPolygon','coordinates':[multipart['geometry']['coordinates'],second_part['geometry']['coordinates']]}
    local_multipart=importer.local_geometry(multipart['geometry'])
    assert local_multipart.geom_type=='MultiPolygon' and len(local_multipart.geoms)==2, 'MultiPolygon source parts were lost during local projection'
    expected_area=sum(importer.Polygon([importer.local(point) for point in rings[0]]).area for rings in multipart['geometry']['coordinates'])
    assert abs(local_multipart.area-expected_area)<.01, 'MultiPolygon projection changed the source area'
    changed_old=copy.deepcopy(old_features[0]);changed_old['properties'].update(OBJECTID=72001,TopHeight=999)
    refreshed=[changed_old,northern,southern,multipart]
    duplicate_csuid=copy.deepcopy(changed_old);duplicate_csuid['properties']['OBJECTID']=72002
    def page(items):return {'type':'FeatureCollection','features':items}

    with tempfile.TemporaryDirectory(prefix='antila-east-building-merge-') as directory:
        trial=Path(directory);(trial/'Data').mkdir()
        target=trial/'Data/east-kowloon-buildings.geojson'
        target.write_text(json.dumps(previous,separators=(',',':')))
        baseline_hash=hashlib.sha256(target.read_bytes()).hexdigest()
        def refresh(responses):
            responses=iter(responses);queries=[]
            def response(url,**kwargs):
                queries.append(importer.urllib.parse.parse_qs(importer.urllib.parse.urlparse(url).query))
                payload=next(responses)
                if isinstance(payload,Exception):raise payload
                return io.BytesIO(payload if isinstance(payload,bytes) else json.dumps(payload).encode())
            with patch.object(importer,'ROOT',trial),patch.object(importer,'EAST_KOWLOON_BBOX',planned_bbox), \
                 patch.object(importer.urllib.request,'urlopen',response), \
                 contextlib.redirect_stdout(io.StringIO()):
                importer.download_island(east_kowloon=True)
            return queries

        queries=refresh([{'count':4},page(refreshed[:2]),page(refreshed[2:])])
        updated=json.loads(target.read_text())
        assert updated['features'][:2]==old_features, 'Eastern merge changed or removed preserved records'
        assert len(updated['features'])==4 and updated['features'][3]['properties']['BuildingCSUID']==multipart['properties']['BuildingCSUID'], 'Merge admitted a southern feature or missed a northern multipart feature'
        assert updated['features'][2]['properties']['source_OBJECTID']==71002 and updated['features'][2]['properties']['OBJECTID']>81003, 'Colliding upstream ID was not preserved and remapped'
        assert len({f['properties']['OBJECTID'] for f in updated['features']})==4 and len({f['properties']['BuildingCSUID'] for f in updated['features']})==4
        assert updated['metadata']['bbox_wgs84']==list(planned_bbox)
        assert updated['metadata']['retrieved_utc']==previous['metadata']['retrieved_utc'], 'Mixed-vintage merge changed the file-level height ordering date'
        assert importer.datetime.datetime.fromisoformat(updated['metadata']['query_retrieved_utc']).utcoffset()==importer.datetime.timedelta(0)
        assert updated['metadata']['merge_provenance']['preserved_source_sha256']==baseline_hash
        assert updated['metadata']['merge_provenance']['query_feature_count']==4
        assert updated['metadata']['merge_provenance']['preserved_source_metadata']==previous['metadata']
        assert updated['metadata']['merge_provenance']['added_feature_count']==2
        assert updated['metadata']['merge_provenance']['added_csuids']==sorted([northern['properties']['BuildingCSUID'],multipart['properties']['BuildingCSUID']])
        assert updated['metadata']['merge_provenance']['missing_service_csuids']==['east-71002']
        assert updated['metadata']['merge_provenance']['objectid_remaps']==[{'BuildingCSUID':'east-new-81001','source_OBJECTID':71002,'internal_OBJECTID':81004}]
        assert queries[0]['geometry']==[','.join(map(str,planned_bbox))]

        saved=target.read_bytes()
        refresh([{'count':4},page(refreshed[:2]),page(refreshed[2:])])
        repeated=json.loads(target.read_text())
        assert repeated['features']==updated['features'], 'repeat refresh duplicated or rewrote eastern features'
        assert repeated['metadata']['merge_provenance']['preserved_source_sha256']==baseline_hash
        assert repeated['metadata']['merge_provenance']['donor_source_sha256']==hashlib.sha256(saved).hexdigest()
        assert repeated['metadata']['merge_provenance']['cumulative_added_feature_count']==2
        assert repeated['metadata']['merge_provenance']['added_feature_count']==2 and repeated['metadata']['merge_provenance']['incremental_added_feature_count']==0
        assert repeated['metadata']['merge_provenance']['added_csuids_sha256']==updated['metadata']['merge_provenance']['added_csuids_sha256']
        saved=target.read_bytes()
        for label,responses in [('duplicate_ids',[{'count':2},page([changed_old,changed_old])]),
                                ('duplicate_csuids',[{'count':2},page([changed_old,duplicate_csuid])]),
                                ('short_page',[{'count':4},page(refreshed[:3]),page([])])]:
            try:refresh(responses)
            except ValueError:pass
            else:raise AssertionError(f'{label}: incomplete east-kowloon response was accepted')
            assert target.read_bytes()==saved, f'{label}: incomplete east-kowloon refresh replaced the preserved source'
        assert not list((trial/'Data').glob('*.part')), 'temporary file leaked after rejected east refresh'
    print('ANTILA_EAST_BUILDING_MERGE_OK: old records preserved; only northern additions merged; incomplete refresh preserves cache bytes')


def check():
    root = importer.ROOT
    cases = {'3503618508T20260615': (149.6, None, 143.5),
             '3499118543T20260615': (None, 36, 115.2)}
    with tempfile.TemporaryDirectory(prefix='antila-building-check-') as directory:
        trial = Path(directory)
        (trial/'Data').mkdir()
        for name in ('nathan-road.json','cross-harbour.json','west-kowloon-coast.json',
                     'island-coast.json','buildings.geojson','west-kowloon-buildings.geojson','lai-chi-kok-buildings.geojson','kwai-chung-buildings.geojson','tsuen-wan-buildings.geojson','west-coast-buildings.geojson','east-kowloon-buildings.geojson'):
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
            # Real clipped podiums used to disappear when intersection returned a point or tiny second polygon.
            north=json.loads((trial/'Data/kowloon-north-layout.json').read_text())['buildings']
            for source_id,minimum_area in ((228041,1377),(263953,159),(226983,71),(82955,54)):
                parts=[importer.Polygon(b['rings'][0],b['rings'][1:]) for b in north if b['id']==source_id]
                assert sum(p.area for p in parts)>=minimum_area, f'Clipped building {source_id} lost its valid polygon'
                assert all(p.is_valid and p.area>=4 for p in parts), f'Invalid clipped building {source_id}'
        finally:
            importer.ROOT = root
    print('ANTILA_BUILDING_REFRESH_OK: newest TopHeight and missing-height Storeys fallback agree across rebuilt regions')
    print('ANTILA_BUILDING_COMPONENTS_OK: four real Mong Kok clipped parts retain their valid area')


if __name__ == '__main__':
    check_download()
    check_east_kowloon_merge()
    check()
