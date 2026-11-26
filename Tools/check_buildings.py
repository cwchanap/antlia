"""Regress building downloads and regional heights without changing shipped data."""
import copy
import contextlib
import hashlib
import io
import json
import math
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from shapely import union_all
from shapely.geometry import LineString, Polygon, box, shape

import import_buildings as importer


EAST_BUILDING_SOURCE = 'Data/east-kowloon-buildings.geojson'
PRE_KAI_TAK_EAST_SOURCE_SHA256 = '681cb94ca655466dee779297dc543d0756097a998389d1dbc5dd928d3c85fb14'


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
                'BuildingBlockType':'Building','Status':'Active','BaseHeight':4,'TopHeight':12,'Storeys':3,'BuildingNameEN':f'Building {object_id}'},
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
        boundary_path='Data/kowloon-city-district-boundary.geojson'
        (trial/boundary_path).symlink_to(root/boundary_path)
        target=trial/'Data/east-kowloon-buildings.geojson'
        target.write_text(json.dumps(previous,separators=(',',':')))
        baseline_hash=hashlib.sha256(target.read_bytes()).hexdigest()
        def refresh(responses, query_bbox=planned_bbox):
            responses=iter(responses);queries=[]
            def response(url,**kwargs):
                queries.append(importer.urllib.parse.parse_qs(importer.urllib.parse.urlparse(url).query))
                payload=next(responses)
                if isinstance(payload,Exception):raise payload
                return io.BytesIO(payload if isinstance(payload,bytes) else json.dumps(payload).encode())
            with patch.object(importer,'ROOT',trial),patch.object(importer,'EAST_KOWLOON_BBOX',query_bbox), \
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
        assert all(query['where']==["Status='Active'"] for query in queries)

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

        # Extend the already refreshed northern snapshot east. A footprint that
        # crosses the strip boundary is eligible even when its centre is west.
        kai_tak_bbox=(*southwest, *geo(4900,planned_bounds[1]))
        eastern=feature(81003,3300,-4000,'kai-tak-collision')
        seam=feature(81005,3148,-3500,'kai-tak-seam')
        unseen_north=feature(81006,1500,-5900)
        outside=feature(81007,4500,-6000)
        inactive=feature(81008,3305,-3905)
        inactive['properties']['Status']='Demolished'
        boundary=json.loads((root/boundary_path).read_text())['features'][0]
        district=importer.local_geometry(boundary['geometry'])
        district_edge=district.intersection(LineString([(3000,-4000),(3500,-4000)])).bounds[2]
        crosses_district=feature(81009,district_edge+1,-4000,'district-border')
        current_service=[changed_old,northern,southern,eastern,seam,unseen_north,outside,inactive,crosses_district]
        for expected_increment in (3,0):
            refresh([{'count':len(current_service)},page(current_service)],kai_tak_bbox)
            eastern_update=json.loads(target.read_text())
            east_provenance=eastern_update['metadata']['merge_provenance']
            assert eastern_update['features'][:4]==repeated['features'], 'Kai Tak refresh changed pinned northern or original records'
            appended=eastern_update['features'][4:]
            assert [f['properties']['BuildingCSUID'] for f in appended]==['kai-tak-collision','kai-tak-seam','district-border']
            assert appended[-1]==crosses_district, 'Retain the full surveyed footprint of a boundary-crossing building'
            assert east_provenance['northern_strip_provenance']==repeated['metadata']['merge_provenance']
            assert east_provenance['cumulative_added_feature_count']==5
            assert east_provenance['incremental_added_feature_count']==expected_increment
            assert east_provenance['objectid_remaps'][-1]=={
                'BuildingCSUID':'kai-tak-collision','source_OBJECTID':81003,'internal_OBJECTID':81010}
        for bad_seed in (None,b'',b'null'):
            if bad_seed is None:target.unlink()
            else:target.write_bytes(bad_seed)
            try:refresh([],kai_tak_bbox)
            except (ValueError,FileNotFoundError):pass
            else:raise AssertionError('Refresh accepted a missing or invalid pinned Eastern Kowloon source')
    print('ANTILA_EAST_BUILDING_MERGE_OK: pinned original and northern records preserved; north and Kai Tak split, repeats and incomplete refresh checked')


def check_kai_tak_buildings():
    root=importer.ROOT
    source_bytes=(root/EAST_BUILDING_SOURCE).read_bytes()
    source=json.loads(source_bytes)
    metadata=source['metadata']
    wong_tai_sin_ids=set(metadata.get('wong_tai_sin_merge',{}).get('added_csuids',[]))
    features=[f for f in source['features'] if f['properties']['BuildingCSUID'] not in wong_tai_sin_ids]
    provenance=metadata['merge_provenance']
    northern_count=8153
    def digest(value,sort_keys=False):
        return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=sort_keys,
                                         separators=(',',':'),allow_nan=False).encode()).hexdigest()
    assert digest(features[:northern_count])=='089dc69fb0acce05ecf48d6e781a89410c9e360571c9d66fc34ebb0ba4dc5fb4', \
        'Kai Tak refresh changed a pinned Eastern Kowloon source feature'
    assert digest(provenance['northern_strip_provenance'],sort_keys=True)== \
        '34dccabf59266b80c0e3d0c4b12a20bfe605cd34f620f19c3963cb925bd79c95', \
        'Kai Tak refresh changed the original northern strip provenance'
    assert metadata['source']==importer.SOURCE
    west,south=importer.local(metadata['bbox_wgs84'][:2]);east,north=importer.local(metadata['bbox_wgs84'][2:])
    assert [west,north,east,south]==provenance['expanded_bounds_local']
    assert (metadata['query_feature_count'],metadata['query_features_sha256'])== \
        (provenance['query_feature_count'],provenance['query_features_sha256'])
    props=[feature['properties'] for feature in features]
    assert len({p['OBJECTID'] for p in props})==len({p['BuildingCSUID'] for p in props})==len(features), \
        'Duplicate building identity in updated Eastern Kowloon source'
    source_additions=features[provenance['preserved_feature_count']:]
    added_csuids=sorted(f['properties']['BuildingCSUID'] for f in source_additions)
    assert added_csuids==provenance['added_csuids']
    assert digest(added_csuids)==provenance['added_csuids_sha256']
    added_source_ids=sorted(f['properties'].get('source_OBJECTID',f['properties']['OBJECTID']) for f in source_additions)
    assert digest(added_source_ids)==provenance['added_objectids_sha256']
    assert len(source_additions)==provenance['cumulative_added_feature_count']

    east_edge=provenance['previous_east_boundary_local_x']
    _,north,east,south=provenance['expanded_bounds_local']
    district,district_sha256=importer.kowloon_city_boundary()
    assert provenance['district_boundary_feature_sha256']==district_sha256
    surveyed_strip=district.intersection(box(east_edge,north,east,south))
    assert all(f['properties']['Status']=='Active' and importer.local_geometry(f['geometry']).intersection(surveyed_strip).area>.01
               for f in features[northern_count:]), 'An appended building is inactive or outside the surveyed district strip'

    terminal_name='KAI TAK CRUISE TERMINAL'
    terminal=[f for f in features[northern_count:] if f['properties'].get('BuildingNameEN')==terminal_name]
    assert len(terminal)==20, 'Expected the Kai Tak Cruise Terminal podium and 19 tower parts'
    podium=next(f for f in terminal if f['properties']['BuildingCSUID']=='3995418638P20130520')
    podium_props=podium['properties']
    assert (podium_props['BuildingBlockType'],podium_props['BaseHeight'],podium_props['TopHeight'])==('Podium',5,31.6)

    layout=json.loads((root/'Data/east-kowloon-layout.json').read_text())
    source_sha=hashlib.sha256(source_bytes).hexdigest()
    assert layout['metadata']['source_sha256']==layout['metadata']['base_sources_sha256'][EAST_BUILDING_SOURCE]==source_sha
    assert layout['metadata']['source_parts']==len(source['features']), 'Stale Eastern Kowloon building layout'
    parts=[b for b in layout['buildings'] if b['name']==terminal_name]
    terminal_ids={f['properties']['OBJECTID'] for f in terminal}
    podium_parts=[b for b in parts if b['id']==podium_props['OBJECTID']]
    assert {b['id'] for b in parts}<=terminal_ids and podium_parts
    assert all(0<b['height']<=35.3 for b in parts) and all(25<=b['height']<=31.6 for b in podium_parts), \
        'Unexpected Kai Tak Cruise Terminal massing heights'
    source_footprint=union_all([importer.local_geometry(f['geometry']) for f in terminal])
    rendered_footprint=union_all([Polygon(b['rings'][0],b['rings'][1:]) for b in parts])
    assert rendered_footprint.is_valid and rendered_footprint.area>.85*source_footprint.area, \
        'Kai Tak Cruise Terminal lost substantial source footprint during clipping'
    assert rendered_footprint.difference(source_footprint.buffer(.15)).area<.01, \
        'Kai Tak Cruise Terminal footprint extends beyond its source geometry'
    print(f'ANTILA_KAI_TAK_BUILDINGS_OK: {len(features)-northern_count:,} official east-strip records; '
          f'preserved northern provenance; {rendered_footprint.area:,.0f} m² terminal massing')


def check_wong_tai_sin_merge():
    boundary_path=Path('Data/wong-tai-sin-district-boundary.geojson')
    feature,=json.loads((importer.ROOT/boundary_path).read_text())['features']
    district=importer.local_geometry(feature['geometry'])
    edge=district.intersection(LineString([(1000,-5000),(6000,-5000)])).bounds[2]

    def source_feature(ident,uid,x,z,status='Active'):
        scale_x=111320*math.cos(math.radians(importer.ORIGIN[1]))
        corners=[(x-4,z-4),(x+4,z-4),(x+4,z+4),(x-4,z+4),(x-4,z-4)]
        ring=[[importer.ORIGIN[0]+px/scale_x,importer.ORIGIN[1]-pz/111320] for px,pz in corners]
        return {'type':'Feature','properties':{'OBJECTID':ident,'BuildingCSUID':uid,'Status':status,
                'BuildingBlockType':'Tower','BaseHeight':10,'TopHeight':20},
                'geometry':{'type':'Polygon','coordinates':[ring]}}

    preserved=[source_feature(1,'prior-wong-tai-sin',2600,-5400),source_feature(2,'prior-kai-tak',4200,-1400)]
    old_metadata={'bbox_wgs84':list(importer.EAST_KOWLOON_BBOX),'retrieved_utc':'2026-10-21T00:00:00+00:00',
                  'merge_provenance':{'strategy':'Retain the existing Kai Tak provenance'}}
    baseline=dict(type='FeatureCollection',metadata=old_metadata,features=preserved)
    revised=source_feature(3,'prior-wong-tai-sin',2610,-5400)
    collision=source_feature(2,'new-estate',3900,-5350)
    crossing=source_feature(4,'district-edge',edge+1,-5000)
    inactive=source_feature(5,'inactive',3910,-5350,'Demolished')
    outside=source_feature(6,'outside',4200,-4000)
    assert district.intersection(importer.local_geometry(outside['geometry'])).area==0
    donor=[revised,collision,crossing,inactive,outside]

    with tempfile.TemporaryDirectory(prefix='antila-wong-tai-sin-building-merge-') as directory:
        trial=Path(directory);(trial/'Data').mkdir()
        (trial/boundary_path).symlink_to(importer.ROOT/boundary_path)
        cache=trial/EAST_BUILDING_SOURCE
        cache.write_text(json.dumps(baseline))
        baseline_hash=hashlib.sha256(cache.read_bytes()).hexdigest()
        for expected_increment in (2,0):
            responses=iter([{'count':len(donor)},{'type':'FeatureCollection','features':donor}])
            def response(url,**_):
                params=importer.urllib.parse.parse_qs(importer.urllib.parse.urlparse(url).query)
                assert params['where']==["Status='Active'"]
                return io.BytesIO(json.dumps(next(responses)).encode())
            with patch.object(importer,'ROOT',trial),patch.object(importer.urllib.request,'urlopen',response), \
                 contextlib.redirect_stdout(io.StringIO()):
                importer.download_island(wong_tai_sin=True)
            result=json.loads(cache.read_text())
            assert result['features'][:2]==preserved
            metadata=result['metadata'].copy()
            scope=metadata.pop('wong_tai_sin_merge')
            assert metadata==old_metadata and scope['preserved_source_sha256']==baseline_hash
            assert scope['preserved_feature_count']==2 and scope['incremental_added_feature_count']==expected_increment
            assert scope['added_csuids']==['district-edge','new-estate']
            assert scope['objectid_remaps']==[{'BuildingCSUID':'new-estate','source_OBJECTID':2,'internal_OBJECTID':7}]
            assert result['features'][-1]==crossing, 'The full surveyed footprint must remain after scope selection'
            assert len(result['features'])==4
    print('ANTILA_WONG_TAI_SIN_BUILDING_MERGE_OK: exact prior records and provenance, active district selection and repeat refresh')


def check_wong_tai_sin_buildings():
    source_bytes=(importer.ROOT/EAST_BUILDING_SOURCE).read_bytes()
    source=json.loads(source_bytes)
    features=source['features']
    scope=source['metadata']['wong_tai_sin_merge']
    preserved=scope['preserved_feature_count']
    assert preserved==8528
    canonical_prefix=json.dumps(features[:preserved],ensure_ascii=False,separators=(',',':'),allow_nan=False)
    assert hashlib.sha256(canonical_prefix.encode()).hexdigest()== \
        'bc0cfb725509bc5334fe3e6a77d1fec113902709c61757b7f33d118813d903c2', 'A previously pinned building feature changed'
    by_uid={f['properties']['BuildingCSUID']:f for f in features}
    assert len(by_uid)==len({f['properties']['OBJECTID'] for f in features})==len(features)
    feature,digest=importer.district_boundary_feature(importer.WONG_TAI_SIN_BOUNDARY,'Wong Tai Sin District')
    district=importer.local_geometry(feature['geometry'])
    assert scope['district_boundary_feature_sha256']==digest and scope['source']==importer.SOURCE
    assert scope['bbox_wgs84']==list(shape(feature['geometry']).bounds)
    added=scope['added_csuids']
    assert sorted(set(added))==added and len(added)==scope['added_feature_count']
    assert hashlib.sha256(json.dumps(added,separators=(',',':')).encode()).hexdigest()==scope['added_csuids_sha256']
    assert all(by_uid[uid]['properties']['Status']=='Active' and
               importer.local_geometry(by_uid[uid]['geometry']).intersection(district).area>.01 for uid in added)
    assert set(added).isdisjoint(f['properties']['BuildingCSUID'] for f in features[:preserved])

    layout=json.loads((importer.ROOT/'Data/east-kowloon-layout.json').read_text())
    assert layout['metadata']['source_sha256']==hashlib.sha256(source_bytes).hexdigest()
    assert layout['metadata']['source_parts']==len(features)
    coast=json.loads((importer.ROOT/'Data/east-kowloon-coast.json').read_text())
    west,south=importer.local(layout['metadata']['bbox_wgs84'][:2])
    east,north=importer.local(layout['metadata']['bbox_wgs84'][2:])
    assert all(abs(actual-expected)<.0001 for actual,expected in zip((west,north,east,south),coast['bounds'])), \
        'East layout metadata must use the effective coast bounds'
    revised=layout['metadata']['ma_chai_hang_footprint']
    source_path=importer.ROOT/importer.MA_CHAI_HANG_BUILDING_SOURCE
    source_bytes=source_path.read_bytes()
    survey,=json.loads(source_bytes)['features']
    props=survey['properties']
    source=by_uid[importer.MA_CHAI_HANG_CSUID]
    assert revised['path']==importer.MA_CHAI_HANG_BUILDING_SOURCE and revised['sha256']==hashlib.sha256(source_bytes).hexdigest()
    assert props['BuildingCSUID']==revised['BuildingCSUID']==importer.MA_CHAI_HANG_CSUID
    assert props['OBJECTID']==revised['source_OBJECTID']==341800 and source['properties']['OBJECTID']==revised['layout_OBJECTID']==341966
    assert (props['BaseHeight'],props['TopHeight'])==(46,56)
    parts=[b for b in layout['buildings'] if b['id']==revised['layout_OBJECTID']]
    assert parts and all(b['height']==10 for b in parts), 'Ma Chai Hang must retain its surveyed 10 m rise'
    footprint=union_all([Polygon(b['rings'][0],b['rings'][1:]) for b in parts])
    surveyed=importer.local_geometry(survey['geometry'])
    assert surveyed.area>890 and footprint.symmetric_difference(surveyed).area<1, 'Ma Chai Hang refined footprint is missing'
    landmarks={
        '3883422415T20050430':('Plaza Hollywood',13,44.8,15000),
        '3873722435T20050430':('MTR DIAMOND HILL STATION',13.2,17.6,175),
        '3871822802T20050430':('Fung Tak Shopping Centre',23.8,39.2,6800),
        '3881522494T20050430':('Galaxia Tower E',21.4,160.4,485),
        '3919522418T20050430':('Chi Lin Nunnery Main Hall',27.3,42.3,350),
        '3921122446T20050430':('Chi Lin Nunnery Scripture Library',32.8,46,280),
        '3909422310T20130731':('NAN LIAN GARDEN',17.5,23.2,165),
        '3944022543T20050430':('Grand View Garden Tower 1',39.7,149.4,580),
    }
    for uid,(name,base,top,min_area) in landmarks.items():
        source=by_uid[uid]
        props=source['properties']
        assert (props['BuildingNameEN'],props['BaseHeight'],props['TopHeight'])==(name,base,top)
        parts=[b for b in layout['buildings'] if b['id']==props['OBJECTID']]
        footprint=union_all([Polygon(b['rings'][0],b['rings'][1:]) for b in parts])
        assert footprint.area>=min_area, (name,footprint.area,min_area)
    print(f'ANTILA_WONG_TAI_SIN_BUILDINGS_OK: {len(added)} active district additions, {preserved:,} pinned rows and {len(landmarks)} named massing checks')


def check_chi_man_street():
    data=importer.ROOT/'Data'
    source=json.loads((data/'kowloon-north-buildings.geojson').read_text())
    spca=next(f for f in source['features'] if f['properties']['BuildingCSUID']=='3634519150T20050430')
    surveyed=importer.local_geometry(spca['geometry'])
    road=next(r for r in json.loads((data/'cross-harbour.json').read_text())['roads'] if r['id']==importer.CHI_MAN_STREET_ID)
    assert road['name']=='CHI MAN STREET' and road['width']==5 and not road['elevated'] and not road['tunnel']
    line=LineString([(x,z) for x,_,z in road['points']])
    radius=importer.building_road_clearance(road)
    assert radius==2.6
    assert importer.building_road_clearance({**road,'width':12})==9.5
    clearance=line.buffer(radius,quad_segs=2,join_style='mitre')
    assert surveyed.disjoint(clearance), 'Chi Man Street setback enters the surveyed SPCA footprint'
    layout=json.loads((data/'kowloon-north-layout.json').read_text())
    building_id=spca['properties']['OBJECTID']
    rendered=union_all([Polygon(b['rings'][0],b['rings'][1:]) for b in layout['buildings'] if b['id']==building_id])
    assert not rendered.is_empty and rendered.is_valid and rendered.disjoint(clearance)
    assert rendered.symmetric_difference(surveyed).area<1, 'Chi Man Street clearance removed surveyed SPCA massing'
    print(f'ANTILA_CHI_MAN_BUILDING_OK: {rendered.area:.2f} m² SPCA footprint retained at the 5 m carriageway')


def check_choi_hung_carriageway_clearance():
    # Pavement width, nearest surveyed building distance and LandsD OBJECTID.
    cases = {'TD_102856': (6, 6.794, 227804), 'TD_103858': (6, 8.941, 249530),
             'TD_103428': (6, 8.925, 246786), 'TD_103861': (6, 8.576, 179380),
             'TD_103672': (6, 8.6085, 112163), 'TD_103841': (11.5, 9.45855, 111197)}
    data = importer.ROOT/'Data'
    roads = {road['id']: road for road in json.loads((data/'cross-harbour.json').read_text())['roads']
             if road['id'] in cases}
    source = json.loads((data/'east-kowloon-buildings.geojson').read_text())
    building_ids = {building_id for _,_,building_id in cases.values()}
    surveyed = {feature['properties']['OBJECTID']: importer.local_geometry(feature['geometry'])
                for feature in source['features']
                if feature['properties']['OBJECTID'] in building_ids}
    for road_id, (width, building_gap, building_id) in cases.items():
        radius = importer.building_road_clearance({'id': road_id, 'width': width})
        assert radius < building_gap, (road_id, radius, building_gap)
        assert radius - width/2 == 3.5
        assert importer.building_road_clearance({'id': road_id, 'width': 12}) == 9.5
        if road_id in roads:
            road = roads[road_id]
            assert road['width'] == width
            line = LineString([(x,z) for x,_,z in road['points']])
            clearance = line.buffer(radius,quad_segs=2,join_style='mitre')
            assert surveyed[building_id].disjoint(clearance), (road_id,building_id)
    assert importer.building_road_clearance({'id': 'TD_103859', 'width': 6}) == 9.5
    print(f'ANTILA_CHOI_HUNG_BUILDING_CLEARANCE_OK: {len(cases)} surveyed carriageway setbacks preserve nearby footprints')


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
                importer.build(include_landmarks=False)
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
            district = json.loads((trial/'Data/building-layout.json').read_text())['buildings']
            for source_id, minimum_area in ((336429, 3900), (336430, 8600)):
                footprints = [importer.Polygon(b['rings'][0], b['rings'][1:]) for b in district if b['id'] == source_id]
                assert sum(p.area for p in footprints) >= minimum_area, f'Kowloon Park facility {source_id} lost its footprint'
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


def check_southwest_landmarks():
    root=importer.ROOT
    source=json.loads((root/'Data/southwest-landmarks-source.geojson').read_text())
    raw=source['features']
    source_by_id={int(f['properties']['SourceBuildingID']):f for f in raw}
    expected_source_ids={1108244351,1108244353,1108244354,1108244358,1108244367,1108244368,
                         1108244369,1108244370,1108244372,1108244377,1108244383,1108244386,
                         1108244389,1108244393,1108244397,1108244403,1108244416,1108247477,1810141373}
    assert set(source_by_id)==expected_source_ids and len(raw)==19
    assert {f['properties']['SourceSiteID'] for f in raw}==set(importer.LANDMARK_SITES)|{'AMO-M0043'}
    assert source['metadata']['source_tile']=='11-SW-4D'
    assert source['metadata']['source_tile_sha256']==importer.LANDMARK_TILE_SHA256
    assert source['metadata']['source']==importer.LANDMARK_GML_URL
    assert source['metadata']['features']==len(raw)

    missing={1108244368,1108244372,1108244377,1108244386,1108244389,1108244416}
    assert {ident for ident,f in source_by_id.items()
            if f['properties']['BaseHeight'] is None or f['properties']['TopHeight'] is None}==missing
    assert all(source_by_id[ident]['properties']['BuildingBlockType']=='Open-sided' for ident in missing)
    levels={1108244369:(4.1,60.5),1810141373:(3.9,31.7),1108244351:(3.8,13.0),
            1108244354:(4.0,13.0),1108244403:(4.2,44.4)}
    for ident,(base,top) in levels.items():
        props=source_by_id[ident]['properties']
        assert (props['BaseHeight'],props['TopHeight'])==(base,top)
        assert props['BUILDINGSTATUS']=='E' and props['CERTAINTY']=='1'
        assert props['LASTUPDATEDATE']=='20230903'
    tower=importer.local_geometry(source_by_id[1108244403]['geometry'])
    assert tower.centroid.distance(importer.Point(-286.5,156.6))<1.5
    assert min(importer.local_geometry(f['geometry']).bounds[1] for f in raw)>50.094

    expected_layout={1108244369:56.4,1108244358:42.3,1108244403:40.2,1108244397:33.9,
                     1810141373:27.8,1108244353:19.2,1108244393:15.1,1108244367:14.5,
                     1108244354:10.2,1108244351:10.2,1108247477:4.2,1108244383:2.1,1108244370:1.5}
    with tempfile.TemporaryDirectory(prefix='antila-southwest-building-check-') as directory:
        trial=Path(directory);data=trial/'Data';data.mkdir()
        inputs=('southwest-landmarks-source.geojson','buildings.geojson','kowloon-north-buildings.geojson',
                'west-kowloon-buildings.geojson','lai-chi-kok-buildings.geojson','kwai-chung-buildings.geojson',
                'tsuen-wan-buildings.geojson','west-coast-buildings.geojson','east-kowloon-buildings.geojson',
                'nathan-road.json','cross-harbour.json')
        for name in inputs:(data/name).symlink_to(root/'Data'/name)
        previous_root=importer.ROOT;importer.ROOT=trial
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                baseline=importer.build(include_landmarks=False,write=False)
                combined=importer.build()
            parts=combined['buildings'][len(baseline['buildings']):]
            supplement=combined['metadata']['southwest_landmark_supplement']
            assert {b['id'] for b in parts}==set(expected_layout) and len(parts)==18
            assert supplement['source']['source_tile_sha256']==importer.LANDMARK_TILE_SHA256
            assert supplement['source']['source']==importer.LANDMARK_GML_URL
            assert supplement['derived']['fallback_height_parts']==0
            assert supplement['derived']['source_parts_clipped']==0
            assert supplement['derived']['source_sha256']==hashlib.sha256((data/'southwest-landmarks-source.geojson').read_bytes()).hexdigest()
            for part in parts:
                poly=importer.Polygon(part['rings'][0],part['rings'][1:])
                assert poly.is_valid and poly.area>=4
                assert part['height']==expected_layout[part['id']]
                assert 0<part['height']<=source_by_id[part['id']]['properties']['TopHeight']
                roofs=[importer.Polygon(ring) for ring in part['roof']]
                assert abs(sum(roof.area for roof in roofs)-poly.area)<.01
            assert combined['buildings'][:len(baseline['buildings'])]==baseline['buildings']
            assert combined['pavement_patches']==baseline['pavement_patches']
            assert combined['metadata']['rendered_parts']==len(combined['buildings'])
            saved=json.loads((data/'building-layout.json').read_text())
            assert saved==json.loads(json.dumps(combined,ensure_ascii=False,allow_nan=False))
            old_ids={b['id'] for b in baseline['buildings']};new_ids={b['id'] for b in parts}
            assert not old_ids&new_ids, 'Landmark IDs collide with the original layout'
            old_polys=[importer.Polygon(b['rings'][0],b['rings'][1:]) for b in baseline['buildings']]
            old_tree=importer.STRtree(old_polys)
            assert all(not any(poly.intersection(old_polys[int(i)]).area>.01 for i in old_tree.query(poly))
                       for poly in (importer.Polygon(b['rings'][0],b['rings'][1:]) for b in parts))
        finally:
            importer.ROOT=previous_root
    print('ANTILA_SOUTHWEST_LANDMARKS_OK: 19 official source footprints; 13 height-backed records render as 18 appended parts; default generation preserves baseline layout and pavement')


def check_kowloon_tong_extension():
    root=importer.ROOT
    source_path=root/'Data/kowloon-tong-buildings-source.geojson'
    source=json.loads(source_path.read_text())
    source_metadata=source['metadata']
    assert source['type']=='FeatureCollection' and len(source['features'])==importer.KOWLOON_TONG_RAW_FEATURE_COUNT==222
    assert source_metadata['source']==importer.SOURCE
    assert source_metadata['query_response_sha256']==importer.KOWLOON_TONG_SOURCE_RESPONSE_SHA256
    assert source_metadata['query_local_bounds_m']==list(importer.NORTHWEST_EXTENSION_BOUNDS)
    assert (root/'Data/kowloon-tong-buildings-source-response.geojson').exists() is False, \
        'The bundled source must remain the provenance-wrapped FeatureCollection'

    with contextlib.redirect_stdout(io.StringIO()):
        derived=importer.build(northwest=True,include_landmarks=False,write=False)
    official=derived['metadata']['source_supplement']['official_gap_source']
    assert official['path']=='Data/kowloon-tong-buildings-source.geojson'
    assert official['query_feature_count']==222 and official['existing_source_csuids_excluded']==19
    assert official['selected_feature_count']==145
    assert official['selected_clipped_union_area_m2']==58082.886
    assert official['selected_csuids_sha256']==importer.KOWLOON_TONG_SELECTED_CSUIDS_SHA256
    assert official['rendered_source_record_count']==144
    assert official['source_OBJECTIDs_pruned_after_clearance']==[110069]
    remaps={row['source_OBJECTID']:row['internal_OBJECTID']
            for row in official['selected_source_objectid_remaps']}
    source_ids=set(official['selected_source_OBJECTIDs'])
    internal_ids={remaps.get(ident,ident) for ident in source_ids}
    buildings=derived['buildings']
    rendered_ids={building['id'] for building in buildings}
    rendered_source_ids={ident for ident in source_ids
                         if remaps.get(ident,ident) in rendered_ids}
    assert source_ids-rendered_source_ids=={110069}
    assert internal_ids-{110069} <= rendered_ids
    by_source_id={feature['properties']['OBJECTID']:feature for feature in source['features']}
    for ident,name_fragment in ((1517,'Cornwall Street Squash & Table Tennis Centre'),
                                (111858,'YEW CHUNG INTERNATIONAL SCHOOL'),
                                (30458,'One Beacon Hill Tower 1'),
                                (112190,'Tak Chee Yuen Block 11'),
                                (112321,'Tak Chee Yuen Block 12'),
                                (112053,'Tak Chee Yuen Block 13'),
                                (111949,'Tak Chee Yuen Block 14')):
        source_name=by_source_id[ident]['properties']['BuildingNameEN']
        layout_id=remaps.get(ident,ident)
        assert name_fragment.lower() in source_name.lower()
        assert any(building['id']==layout_id and name_fragment.lower() in building['name'].lower()
                   for building in buildings), f'Missing named Kowloon Tong building {ident}: {source_name}'
    assert official['selected_source_objectid_remaps']==[
        {'BuildingCSUID':'3619322148T20050430','source_OBJECTID':111858,'internal_OBJECTID':342191},
        {'BuildingCSUID':'3585622433T20050430','source_OBJECTID':111998,'internal_OBJECTID':342192},
        {'BuildingCSUID':'3588322216T20050430','source_OBJECTID':112053,'internal_OBJECTID':342193},
        {'BuildingCSUID':'3593022436T20050430','source_OBJECTID':136693,'internal_OBJECTID':342194},
        {'BuildingCSUID':'3617722387T20050430','source_OBJECTID':249230,'internal_OBJECTID':342195},
    ]
    saved=json.loads((root/'Data/lai-chi-kok-layout.json').read_text())
    expected=json.loads(json.dumps(derived,ensure_ascii=False,allow_nan=False))
    saved_east_hash=saved['metadata']['base_sources_sha256'][EAST_BUILDING_SOURCE]
    rebuilt_east_hash=expected['metadata']['base_sources_sha256'][EAST_BUILDING_SOURCE]
    east_source=json.loads((root/EAST_BUILDING_SOURCE).read_text())
    prior_source_hash=east_source['metadata'].get('wong_tai_sin_merge',{}).get('preserved_source_sha256')
    assert saved_east_hash in (PRE_KAI_TAK_EAST_SOURCE_SHA256,prior_source_hash,rebuilt_east_hash)
    expected['metadata']['base_sources_sha256'][EAST_BUILDING_SOURCE]=saved_east_hash
    assert saved.keys()==expected.keys() and saved['metadata']==expected['metadata'], \
        'The Northwest layout metadata does not match the source-backed build'
    assert len(saved['buildings'])==len(expected['buildings']), \
        'The Northwest building part count changed during road re-import'
    for index,(stored,rebuilt) in enumerate(zip(saved['buildings'],expected['buildings'])):
        assert stored.keys()==rebuilt.keys()
        assert {k:v for k,v in stored.items() if k not in ('rings','roof')} == \
               {k:v for k,v in rebuilt.items() if k not in ('rings','roof')}, \
            f'Northwest building metadata changed at part {index}'
        assert len(stored['rings'])==len(rebuilt['rings']) and \
               [len(ring) for ring in stored['rings']]==[len(ring) for ring in rebuilt['rings']], \
            f'Northwest building ring counts changed at part {index}'
        assert len(stored['roof'])==len(rebuilt['roof']) and \
               [len(triangle) for triangle in stored['roof']]==[len(triangle) for triangle in rebuilt['roof']], \
            f'Northwest roof triangle counts changed at part {index}'
        stored_footprint=Polygon(stored['rings'][0],stored['rings'][1:])
        rebuilt_footprint=Polygon(rebuilt['rings'][0],rebuilt['rings'][1:])
        stored_roof=union_all([Polygon(triangle) for triangle in stored['roof']])
        rebuilt_roof=union_all([Polygon(triangle) for triangle in rebuilt['roof']])
        for kind,left,right in (('footprint',stored_footprint,rebuilt_footprint),
                                ('roof',stored_roof,rebuilt_roof)):
            assert left.is_valid and right.is_valid and \
                   left.symmetric_difference(right).area<=1e-8 and \
                   left.hausdorff_distance(right)<=1e-8, \
                f'Northwest {kind} geometry changed at part {index}'

    stored_patches=saved['pavement_patches'];rebuilt_patches=expected['pavement_patches']
    assert len(stored_patches)==len(rebuilt_patches), 'Northwest pavement patch count changed'
    def patches_by_center(patches):
        keyed={tuple(round(value,6) for value in patch['center']):patch for patch in patches}
        assert len(keyed)==len(patches), 'Northwest pavement patch centers are not unique'
        return keyed
    stored_by_center=patches_by_center(stored_patches);rebuilt_by_center=patches_by_center(rebuilt_patches)
    assert stored_by_center.keys()==rebuilt_by_center.keys(), 'Northwest pavement patch locations changed'
    for center,stored_patch in stored_by_center.items():
        rebuilt_patch=rebuilt_by_center[center]
        assert max(abs(a-b) for a,b in zip(stored_patch['center'],rebuilt_patch['center']))<=1e-6
        stored_polygon=Polygon(stored_patch['polygon']);rebuilt_polygon=Polygon(rebuilt_patch['polygon'])
        assert stored_polygon.is_valid and rebuilt_polygon.is_valid and \
               stored_polygon.symmetric_difference(rebuilt_polygon).area<=1e-5 and \
               stored_polygon.hausdorff_distance(rebuilt_polygon)<=1e-3, \
            f'Northwest pavement geometry changed near {center}'
    assert derived['metadata']['base_sources_sha256'][official['path']]==hashlib.sha256(source_path.read_bytes()).hexdigest()
    print('ANTILA_KOWLOON_TONG_BUILDINGS_OK: 222 official records; 145 missing source footprints; 144 retained after Cornwall Street clearance; named buildings and source ID remaps verified')


if __name__ == '__main__':
    if '--kowloon-tong' in sys.argv:
        check_kowloon_tong_extension()
    elif '--kai-tak' in sys.argv:
        check_kai_tak_buildings()
    elif '--wong-tai-sin-district' in sys.argv:
        check_wong_tai_sin_merge()
        check_wong_tai_sin_buildings()
    elif '--chi-man-street' in sys.argv:
        check_chi_man_street()
    elif '--choi-hung-clearance' in sys.argv:
        check_choi_hung_carriageway_clearance()
    elif '--southwest-landmarks' in sys.argv:
        check_southwest_landmarks()
    else:
        check_download()
        check_east_kowloon_merge()
        check_kai_tak_buildings()
        check_wong_tai_sin_merge()
        check_wong_tai_sin_buildings()
        check_chi_man_street()
        check_choi_hung_carriageway_clearance()
        check()
