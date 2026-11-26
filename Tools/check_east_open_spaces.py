"""Check recreation data with --bundled or pass CACHE_DIR MANIFEST_JSON."""
import hashlib
import io
import json
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import import_east_open_spaces as importer
import import_open_spaces as shared

WESTERN_SITE_IDS={
    '1503000390','1503000414','1503000381','1503005413','1503000199',
    '1503005076','1810011761','1910064509','1910069198','1910053970','1910053968',
    '1503005535','1503005281','1810014504','1810044652','1503005514',
    '1910056230','1810032161','1910062401','1503005115','1503005152',
    '1503005112','1503005184','1503005071','1503005077','1503005450',
    '1503005180','1503005170','1503005157','1503005144','1503005135','1503005123',
    '1503005508',
    '1810015202','1503005628',
    '1503005539','1503005553','1503005627','1503005605','1502005648'
}
NEW_SPORT_IDS={
    '1910088626','1910088625','1910088624','1500001823','1500004939','1500004938',
    '1500004937','1500001822','1500001817','1500001813','1500001812','1500001811',
    '1500004986','1500004985','1500001930','1500001929','1500001928','1500001927',
    '1500001926','1500001925','1500001924','1500001923','1500001913','1500001906',
    '1500004916','1500004915','1500000753','1500000750','1910088666','1910086770',
    '1910085686','1910085685','1500004918','1500004917','1500000760','1500000757',
    '1500000756','1810061752','1810018589','1500004928','1500001289','1500001287',
    '1500004927','1500001285','1500001283','1500001361','1500001360','1500001359',
    '1500001358','1500001977','1500001978','1500002016','1500002017','1500002018',
    '1500002019','1500002020','1500002021','1500002074','1500002075','1500004994','1500004995',
    '1500001861','1500001862','1500001863','1500001864','1500002076','1500002077',
    '1500002078','1500002080','1500002081','1500002082','1500002090','1500002093',
    '1500002094','1500005007','1500005008','1810017066','1810025769',
    '1500001910','1500001941','1500001955'
}
KOWLOON_TONG_SITE_NAMES={
    '1503005539':'To Yuen Street Playground',
    '1503005553':'Kent Road Garden',
    '1503005688':'Kam Shing Road Recreation Ground',
    '1503005627':"Cornwall Street Children's Playground",
    '1503005605':'Cornwall Street/Ede Road Garden',
    '1502005648':'Dorset Crescent Rest Garden',
}
KOWLOON_TONG_COURT_SITES={
    '1500001910':'1503005539', '1500001941':'1503005553', '1500001955':'1503005688',
}
CLEARANCE_REBUILT_SITE_IDS={'1503005508','1502005648'}
BENCH_RELAYOUT_SITE_IDS={
    '1503000199','1503000381','1503000390','1503000414','1503005076',
    '1503005535','1503005714','1503005718','1503005853','1503005863',
    '1503005871','1503005881','1810014504','1810044652','1910059822',
    '1910069198'
}
BENCH_COUNT_DELTAS={
    '1503000199':1,'1503000390':-1,'1503000414':-1,'1503005076':-1,
    '1503005535':1,'1503005714':-2,'1503005718':1,'1503005863':-1,
    '1503005881':2,'1910069198':1
}
GROUND_CLIPPED_ACCESS_SITE_ID='1910071209'


def check(cache,manifest_path,preservation_baseline=None):
    check_touching_paving()
    check_supplemental_fixture_refresh()
    for path in (importer.SOURCE,importer.KOWLOON_CITY_SOURCE,importer.WONG_TAI_SIN_SOURCE,
                 importer.WONG_TAI_SIN_DISTRICT_SOURCE,importer.TARGET):
        assert path.is_file(),'Missing eastern recreation data: '+str(path)
    source=importer.SOURCE.read_bytes();target=importer.TARGET.read_bytes()
    raw=importer.combined_source(source);data=json.loads(target)
    site_ids={site['id'] for site in data['sites']}
    source_site_ids={str(feature.get('properties',{}).get('SITEID'))
        for feature in raw['features'] if feature.get('properties',{}).get('layer')=='Site'}
    sport_ids={str(feature.get('properties',{}).get('BUILTSTRUCTUREPOLYGONID'))
        for feature in raw['features'] if feature.get('properties',{}).get('layer')=='BuiltStructurePolygon'}
    assert len(WESTERN_SITE_IDS)==40 and WESTERN_SITE_IDS<=source_site_ids and WESTERN_SITE_IDS<=site_ids,'Western source sites missing from the integrated source/layout: '+repr(sorted(WESTERN_SITE_IDS-(source_site_ids&site_ids)))
    assert len(NEW_SPORT_IDS)==81 and NEW_SPORT_IDS<=sport_ids,'Western source sports missing from the integrated source: '+repr(sorted(NEW_SPORT_IDS-sport_ids))
    assert site_ids==importer.EXPECTED_SITE_IDS|{'1503005422','1910058892'} and len(sport_ids)==188,'Expected 78 surveyed sites plus two supplemental southwest spaces, and 188 unique sports IDs'
    survey_sports={(surface['source_id'],surface['site'],surface['usage']) for surface in data['surfaces']
                    if surface['source_id'] in importer.KOWLOON_CITY_SPORTS}
    assert survey_sports=={(uid,site,usage) for uid,(site,usage) in importer.KOWLOON_CITY_SPORTS.items()},\
        'A Kowloon City sport outline is missing or assigned to the wrong site'
    assert {uid:site['name'] for uid,site in ((s['id'],s) for s in data['sites']) if uid in KOWLOON_TONG_SITE_NAMES}==KOWLOON_TONG_SITE_NAMES,\
        'A reviewed Kowloon Tong site is missing or mislabeled'
    court_sites={surface['source_id']:surface['site'] for surface in data['surfaces']
                 if surface['source_id'] in KOWLOON_TONG_COURT_SITES}
    assert court_sites==KOWLOON_TONG_COURT_SITES,'A Kowloon Tong basketball court is missing or assigned to the wrong site'
    court_fittings={fitting['source_id']:fitting for fitting in data['sports']
                    if fitting['source_id'] in KOWLOON_TONG_COURT_SITES}
    assert {uid:fitting['site'] for uid,fitting in court_fittings.items()}==KOWLOON_TONG_COURT_SITES,\
        'A Kowloon Tong basketball court is missing its fitted recreation model'
    cedd_fittings={fitting['source_id']:fitting for fitting in data['sports']
                   if fitting['source_id'] in importer.SUPPLEMENTAL_SPORTS}
    assert {'1500002030','1500004996'}<=cedd_fittings.keys(),'Ho Man Tin Park lost its two source-backed fittings'
    assert importer.WONG_TAI_SIN_FOOTBALL_INSETS.keys()<=cedd_fittings.keys(),'A Hammer Hill or Po Kong pitch lost its source-backed fitting'
    expected_wts_kinds={'1810044219':'track','1810017967':'field','1500001624':'court',
                        '1810009262':'field','1810009261':'field'}
    assert {surface['source_id']:surface['kind'] for surface in data['surfaces']
            if surface['source_id'] in expected_wts_kinds}==expected_wts_kinds,'A Wong Tai Sin track or soccer surface is missing'
    assert {(surface['source_id'],surface['site'],surface['usage']) for surface in data['surfaces']
            if surface['source_id'] in importer.WONG_TAI_SIN_SPORTS}=={
                (uid,site,usage) for uid,(site,usage) in importer.WONG_TAI_SIN_SPORTS.items()},\
        'A Wong Tai Sin sport outline is missing or assigned to the wrong site'
    assert {(surface['source_id'],surface['site'],surface['usage']) for surface in data['surfaces']
            if surface['source_id'] in importer.WONG_TAI_SIN_DISTRICT_SPORTS}=={
                (uid,site,usage) for uid,(site,usage) in importer.WONG_TAI_SIN_DISTRICT_SPORTS.items()},\
        'A Wong Tai Sin district sport outline is missing or assigned to the wrong site'
    checked_fittings={'1500001941':court_fittings['1500001941']} | cedd_fittings
    for source_id,fitting in checked_fittings.items():
        cx,cz=fitting['center'];fx,fz=fitting['forward'];rx,rz=fz,-fx
        half_width=fitting['width']/2;half_length=fitting['length']/2
        rectangle=importer.Polygon([
            (cx-rx*half_width-fx*half_length,cz-rz*half_width-fz*half_length),
            (cx+rx*half_width-fx*half_length,cz+rz*half_width-fz*half_length),
            (cx+rx*half_width+fx*half_length,cz+rz*half_width+fz*half_length),
            (cx-rx*half_width+fx*half_length,cz-rz*half_width+fz*half_length),
        ])
        source_surface=importer.union_all([
            importer.Polygon(surface['rings'][0],surface['rings'][1:])
            for surface in data['surfaces'] if surface['source_id']==source_id
        ])
        tolerance=.01 if source_id=='1500001941' else 1e-6
        assert rectangle.difference(source_surface).area<=tolerance,\
            'A fitted court extends outside its surveyed surface: '+source_id
    kent=court_fittings['1500001941']
    assert abs(kent['width']-14.018553)<.001 and abs(kent['length']-25.379270)<.001,\
        'Kent Road Garden fitting lost its source-contained 0.5m inscribed rectangle'
    importer.validate_layout(source,target)
    check_district_fitting_rejections(data['sports'])
    check_path_connectivity(data)
    assert {s['source_id'] for s in data['surfaces']}==importer.EXPECTED_SPORTS,'Mapped sport outline lost'
    football_kinds={surface['source_id']:surface['kind'] for surface in data['surfaces']
                    if surface['source_id'] in {'1500001977','1500002075','1500002078','1500002094','1500002093'}}
    assert football_kinds=={'1500001977':'court','1500002075':'court','1500002078':'court',
                            '1500002094':'court','1500002093':'court'},'LCSD hard-surface football courts were not retained'
    gateball_kinds={surface['source_id']:surface['kind'] for surface in data['surfaces']
                    if surface['source_id'] in importer.GATEBALL_IDS}
    assert gateball_kinds=={uid:'court' for uid in importer.GATEBALL_IDS},'Tai Hang Tung gateball outlines were not treated as courts'
    west_layout=json.loads((importer.ROOT/'Data/west-kowloon-layout.json').read_bytes())
    tung_chau_shell=next((importer.Polygon(building['rings'][0]) for building in west_layout['buildings']
                          if building['id']==214665),None)
    assert tung_chau_shell is not None and not any(
        importer.Point(f['position']).buffer(f['radius']).intersects(tung_chau_shell)
        for f in data['fixtures'] if f['site']=='1503005112'),\
        'Tung Chau Street Park fixture circle enters building 214665 outer shell'
    assert len(raw['features'])==341 and data['metadata']['source_feature_count']==341,'Expected 341 exact Site and sport source records'
    assert data['metadata']['source_site_fragment_count']==136 and data['metadata']['source_sport_fragment_count']==205,'Source record counts changed'
    if preservation_baseline is not None:
        check_preservation(Path(preservation_baseline),raw,data)
    for uid,point in [('1503005881',(1989.2677387146189,-2149.3834432934027)),
                      ('1503005714',(1322.4574053629715,-4104.150947211618))]:
        garden=next(g for g in data['gardens'] if g['site']==uid)
        assert any(importer.Point(sample).distance(importer.Point(point))<.01 for sample in garden['samples']),\
            'Former isolated loop lost its in-engine connectivity probe: '+uid
    stage2=next(g for g in data['gardens'] if g['site']=='1503005077')
    stage2_paths=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in stage2['paths']])
    stage2_access=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in stage2['access']])
    stage2_route=importer.LineString([(-1501,-4110),(-1556,-4043)]).buffer(1.8,cap_style='flat')
    assert stage2_access.symmetric_difference(stage2_route).area<.01 and \
           stage2_paths.intersection(stage2_route).area>8 and len(stage2['samples'])>=2,\
        'Sham Shui Po Park Stage 2 lost its surveyed safe route and path probes'
    assert all(any(f['site']==uid and f['asset']=='bench' for f in data['fixtures'])
               for uid in importer.SIT_OUT_SITE_IDS),\
        'A Nam Cheong Street sitting-out area lost its authored bench'
    tracks=importer.union_all([importer.Polygon(p.exterior) for feature in raw['features']
        if feature['properties'].get('USAGETYPE')=='RAT' for p in importer.geometry_polygons(importer.source_local(feature))])
    paving=importer.union_all([importer.Polygon(t) for t in data['paving']])
    assert paving.intersection(tracks).area<.01,'Authored paving enters the running-track infield'
    safe_landscape=importer.union_all([importer.Polygon(row['rings'][0],row['rings'][1:])
                                    for garden in data['gardens'] for row in garden.get('exclusions',[])])
    assert paving.intersection(safe_landscape).area<.01,'Rendered paving enters a surveyed pond or pavilion'
    assert all(not importer.Point(f['position']).buffer(f['radius']).intersects(tracks)
        for f in data['fixtures']),'Authored furniture or planting enters the running-track infield'
    assert data['metadata']['source_sha256']==hashlib.sha256(source).hexdigest()
    assert data['metadata']['source_manifests']==raw['metadata']['source_manifests'],'Stale supplemental survey provenance'
    for name,digest in data['metadata']['inputs_sha256'].items():
        assert hashlib.sha256((importer.ROOT/name).read_bytes()).hexdigest()==digest,'Stale clearance input: '+name
    manifest=json.loads(manifest_path.read_bytes())
    manifest_bytes=manifest_path.read_bytes()
    assert raw['metadata']['tile_manifest_sha256']==hashlib.sha256(manifest_bytes).hexdigest()
    if cache is None:
        print(f'ANTILA_EAST_OPEN_SPACE_BUNDLED_OK: {len(site_ids)} sites; {len(sport_ids)} sports; geometry and input hashes verified')
        return
    rejected=[]
    saved_source_rejections=0
    with tempfile.TemporaryDirectory(prefix='antila-east-check-') as directory:
        trial=Path(directory);tiles=trial/'tiles';tiles.mkdir()
        for row in manifest['tiles']:
            (tiles/(row['tile']+'.zip')).symlink_to((cache/(row['tile']+'.zip')).resolve())
        saved_source=trial/'source.geojson';saved_target=trial/'layout.json';saved_manifest=trial/'manifest.json'
        saved_source.write_bytes(source);saved_target.write_bytes(target)
        def run(rows):
            saved_manifest.write_bytes(manifest_bytes if rows==manifest else json.dumps(rows,separators=(',',':')).encode())
            with patch.object(shared,'TARGET',saved_target):
                importer.refresh(tiles,saved_manifest,source_path=saved_source,target_path=saved_target)
        def reject(label,rows,expected=None):
            before=saved_source.read_bytes(),saved_target.read_bytes()
            try:run(rows)
            except (AssertionError,OSError,ValueError,KeyError,zipfile.BadZipFile,ET.ParseError) as error:
                print('EXPECTED_REJECTION:',label,str(error))
                if expected is not None and expected not in str(error):
                    raise AssertionError('Refresh rejected for the wrong reason: '+label) from error
            else:raise AssertionError('Invalid refresh accepted: '+label)
            assert (saved_source.read_bytes(),saved_target.read_bytes())==before,'Prior outputs changed: '+label
            rejected.append(label)
        for label,change in [('missing_tile',lambda m:m['tiles'].pop()),
            ('duplicate_tile',lambda m:m['tiles'].__setitem__(-1,m['tiles'][0])),
            ('unexpected_tile',lambda m:m['tiles'][0].__setitem__('tile','11-NW-99A')),
            ('bad_hash',lambda m:m['tiles'][0].__setitem__('sha256','0'*64))]:
            bad=json.loads(json.dumps(manifest));change(bad);reject(label,bad)
        row=manifest['tiles'][0];tile=tiles/(row['tile']+'.zip');original=tile.resolve()
        tile.unlink();reject('missing_archive',manifest);tile.symlink_to(original)
        damage_row=next(row for row in manifest['tiles']
                        if any(row['tile'] in sheets for sheets in importer.EXPECTED_SPORT_FRAGMENTS.values()))
        damage_tile=tiles/(damage_row['tile']+'.zip');damage_original=damage_tile.resolve()
        original_bytes=damage_original.read_bytes()
        for label in ('truncated_archive','missing_layer','empty_layer','wrong_crs','malformed_xml'):
            if label=='truncated_archive':payload=b'not a ZIP'
            else:
                stream=io.BytesIO()
                with zipfile.ZipFile(io.BytesIO(original_bytes)) as old,zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as fresh:
                    for name in old.namelist():
                        body=old.read(name)
                        if name.endswith('/BuiltStructurePolygon.gml'):
                            if label=='missing_layer':continue
                            if label=='empty_layer':
                                doc=ET.fromstring(body)
                                for member in list(doc):
                                    if member.tag=='{'+importer.NS['g']+'}featureMember':doc.remove(member)
                                body=ET.tostring(doc)
                            elif label=='wrong_crs':body=body.replace(b'EPSG:2326',b'EPSG:4326')
                            elif label=='malformed_xml':body=b'<unfinished>'
                        fresh.writestr(name,body)
                payload=stream.getvalue()
            bad=json.loads(json.dumps(manifest));bad['tiles'][next(i for i,row in enumerate(bad['tiles']) if row['tile']==damage_row['tile'])]['sha256']=hashlib.sha256(payload).hexdigest()
            damage_tile.unlink();damage_tile.write_bytes(payload)
            try:reject(label,bad)
            finally:damage_tile.unlink();damage_tile.symlink_to(damage_original)
        def reject_removed_polygon_patch(tile_name,layer,id_field,source_id,label):
            target_tile=tiles/(tile_name+'.zip');target_original=target_tile.resolve();target_bytes=target_original.read_bytes()
            stream=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(target_bytes)) as old,zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as fresh:
                for name in old.namelist():
                    body=old.read(name)
                    if name==tile_name+'/Layers/Buildings/'+layer+'.gml':
                        doc=ET.fromstring(body);removed=0
                        for member in doc.findall('g:featureMember/f:'+layer,importer.NS):
                            ident=member.find('f:'+id_field,importer.NS)
                            if ident is None or ident.text!=source_id:continue
                            patch=member.find('.//g:PolygonPatch',importer.NS)
                            if patch is None:continue
                            parent=next(parent for parent in member.iter() if patch in list(parent))
                            parent.remove(patch);removed=1;break
                        assert removed==1,'Expected one '+source_id+' source fragment in '+tile_name
                        body=ET.tostring(doc)
                    fresh.writestr(name,body)
            payload=stream.getvalue();bad=json.loads(json.dumps(manifest))
            bad['tiles'][next(i for i,row in enumerate(bad['tiles']) if row['tile']==tile_name)]['sha256']=hashlib.sha256(payload).hexdigest()
            target_tile.unlink();target_tile.write_bytes(payload)
            try:reject(label,bad,source_id)
            finally:target_tile.unlink();target_tile.symlink_to(target_original)
        reject_removed_polygon_patch('11-NE-16C','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500001703','missing_sport_source_id_1500001703')
        reject_removed_polygon_patch('11-NE-21A','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500001706','missing_sport_fragment_1500001706_11-NE-21A')
        reject_removed_polygon_patch('11-NE-6A','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1910085624','missing_sport_fragment_1910085624_11-NE-6A')
        reject_removed_polygon_patch('7-SW-12C','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500004928',
                                     'missing_western_sport_fragment_1500004928_7-SW-12C')
        reject_removed_polygon_patch('6-SE-25B','Site','SITEID','1503000199',
                                     'missing_same_sheet_site_patch_1503000199_6-SE-25B')
        reject_removed_polygon_patch('11-NW-19D','Site','SITEID','1810014504',
                                     'missing_kings_park_same_sheet_patch_1810014504_11-NW-19D')
        reject_removed_polygon_patch('11-NW-18D','Site','SITEID','1810032161',
                                     'missing_hoi_fai_prom_same_sheet_patch_1810032161_11-NW-18D')
        reject_removed_polygon_patch('11-NW-24B','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500002016',
                                     'missing_kings_park_sport_patch_1500002016_11-NW-24B')
        reject_removed_polygon_patch('11-SW-4D','Site','SITEID','1810015202',
                                     'missing_salisbury_site_patch_1810015202_11-SW-4D')
        reject_removed_polygon_patch('11-SW-5C','Site','SITEID','1503005628',
                                     'missing_tst_promenade_site_patch_1503005628_11-SW-5C')
        for label,layer,id_field,source_id,tile_name in (
                ('missing_sport_fragment','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500001706','11-NE-21A'),
                ('missing_site_fragment','Site','SITEID','1503000199','6-SE-25B'),
                ('missing_art_park_source_fragment_1910053970_11-NW-23D','Site','SITEID','1910053970','11-NW-23D'),
                ('missing_salisbury_source_fragment_1810015202_11-SW-4D','Site','SITEID','1810015202','11-SW-4D'),
                ('missing_tst_promenade_source_fragment_1503005628_11-SW-5C','Site','SITEID','1503005628','11-SW-5C'),
                ('missing_western_sport_fragment','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500004928','7-SW-12C')):
            for mutation in ('missing','duplicate','wrong_tile'):
                case_label=label if mutation=='missing' else label+'_'+mutation
                invalid_source=json.loads(source)
                fragment=next(feature for feature in invalid_source['features']
                    if feature['properties'].get('layer')==layer and
                       feature['properties'].get(id_field)==source_id and
                       feature['properties'].get('tile')==tile_name)
                if mutation=='missing':
                    invalid_source['features'].remove(fragment)
                    if source_id=='1910053970':
                        assert any(feature['properties'].get('SITEID')==source_id and
                                   feature['properties'].get('tile')==tile_name
                                   for feature in invalid_source['features']),\
                            'Art Park source fragment check must leave another same-ID fragment on the same tile'
                elif mutation=='duplicate':invalid_source['features'].append(fragment.copy())
                else:fragment['properties']['tile']='review-wrong-sheet'
                saved_source.write_bytes(importer.encoded(invalid_source))
                before=saved_source.read_bytes(),saved_target.read_bytes()
                try:
                    with patch.object(importer,'build',return_value=target),patch.object(shared,'TARGET',saved_target):
                        importer.refresh(source_path=saved_source,target_path=saved_target)
                except AssertionError as error:
                    expected='reviewed IDs' if source_id=='1810015202' and mutation=='missing' else 'reviewed fragments'
                    assert expected in str(error), case_label+' rejected for the wrong reason'
                else:raise AssertionError('Invalid saved source accepted by direct rebuild: '+case_label)
                assert (saved_source.read_bytes(),saved_target.read_bytes())==before,'Direct rebuild changed prior outputs: '+case_label
                saved_source_rejections+=1
        saved_source.write_bytes(source)
        with patch.object(importer,'extract',return_value=b'{"type":"FeatureCollection","features":[],"metadata":{}}'):
            reject('empty_source',manifest)
        component_layout=json.loads(target)
        garden=next(g for g in component_layout['gardens'] if g['site']=='1503005871')
        paths=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden['paths']])
        access=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden['access']])
        components=importer.geometry_polygons(importer.union_all([paths,access]))
        detached=min(components,key=lambda part:part.area)
        assert 30<detached.area<40,'Expected Hutchison Park detached paving component'
        probe=next(sample for sample in garden['samples'] if detached.covers(importer.Point(sample)))
        garden['samples'].remove(probe)
        assert garden['samples'] and all(max(components,key=lambda part:part.area).covers(importer.Point(sample))
            for sample in garden['samples']),'Main Hutchison paving probes must remain'
        with patch.object(importer,'build',return_value=importer.encoded(component_layout)):
            reject('hutchison_detached_path_without_probe',manifest,'retained paving component has no connectivity probe')
        missing_surface_layout=json.loads(target)
        assert any(surface['source_id']=='1500001703' for surface in missing_surface_layout['surfaces'])
        missing_surface_layout['surfaces']=[surface for surface in missing_surface_layout['surfaces']
            if surface['source_id']!='1500001703']
        with patch.object(importer,'build',return_value=importer.encoded(missing_surface_layout)):
            reject('missing_derived_sport_id_1500001703',manifest,'Derived surfaces differ from reviewed source IDs')
        run(manifest)
        assert saved_source.read_bytes()==source and saved_target.read_bytes()==target,'Complete rebuild is not deterministic'
    print(f'ANTILA_EAST_OPEN_SPACE_REFRESH_OK: {len(site_ids)} sites across {data["metadata"]["source_site_fragment_count"]} Site records; {len(sport_ids)} source sports across {data["metadata"]["source_sport_fragment_count"]} survey records; complete deterministic rebuild; {len(rejected)+saved_source_rejections} rejected cases ({len(rejected)} ZIP refreshes, {saved_source_rejections} direct saved-source rebuilds); outputs preserved')


def check_district_fitting_rejections(sports):
    tennis_id='1500001653'
    tennis=next(fitting for fitting in sports if fitting['source_id']==tennis_id)
    without_tennis=[fitting for fitting in sports if fitting['source_id']!=tennis_id]
    for invalid in (
            without_tennis,
            without_tennis+[tennis | {'site':'1503005950'}],
            without_tennis+[tennis | {'usage':'BAC'}]):
        try:
            importer.validate_wong_tai_sin_district_fittings(invalid)
        except ValueError as error:
            assert tennis_id in str(error), 'District fitting error must identify the affected court'
        else:
            raise AssertionError('Invalid Shek Ku Lung Road tennis fitting was accepted')


def check_supplemental_fixture_refresh():
    uid = '1503005679'
    ring = [[0,0],[12,0],[12,12],[0,12]]
    manifest = {'path':'Data/kowloon-city-open-spaces-source.geojson','sha256':'1'*64}
    road_path = 'Data/cross-harbour.json'
    network = {
        'metadata': {'retrieved_utc':'2026-11-25T00:00:00Z'},
        'bounds':[0,0,50,50], 'ground_triangles':[[[0,0],[50,50],[50,0]]],
        'roads':[{'name':'A ROAD','tunnel':False,'width':12,'points':[[5,0,10],[25,0,10]]}],
    }
    replay = network | {'metadata':{'retrieved_utc':'2026-11-25T01:00:00Z'}}
    moved_road = network['roads'][0] | {'points':[[5,0,11],[25,0,11]]}
    moved = network | {'roads':[moved_road]}
    excluded = {'source_id':'1101167247','kind':'pond','rings':[[[3,3],[4,3],[4,4],[3,4]]]}

    def layout(supplemental_manifest, fixture_position, roads, *, legacy=False, stale_garden=False):
        payload = importer.encoded(roads)
        metadata = {'source_sha256':'2'*64,'inputs_sha256':{road_path:hashlib.sha256(payload).hexdigest()},
                    'source_manifests':[supplemental_manifest]}
        if not legacy:
            metadata['clearance_inputs_sha256'] = {road_path:importer.clearance_input_sha256(road_path,payload)}
        nan_lian = {'site':importer.NAN_LIAN_SITE_ID,'rings':[[ring]],'paths':[[ring]],'access':[],
                    'samples':[[6,6]]}
        if not stale_garden:
            nan_lian['exclusions'] = [excluded]
        return importer.encoded({
            'metadata':metadata,
            'sites':[{'id':uid,'name':'Ho Man Tin Park','bounds':[0,0,12,12],
                      'source_area_m2':144,'fixtures':1},
                     {'id':importer.NAN_LIAN_SITE_ID,'name':'Nan Lian Garden','bounds':[0,0,12,12],
                      'source_area_m2':144,'fixtures':0}],
            'gardens':[{'site':uid,'rings':[[ring]],'paths':[[ring]],'access':[],
                        'samples':[[6,6]]},nan_lian],
            'fixtures':[{'site':uid,'asset':'bench','position':fixture_position}],
            'surfaces':[],'sports':[],'paving':[]})

    old_position = [2,2]
    new_position = [9,9]
    with tempfile.TemporaryDirectory(prefix='antila-supplemental-fixture-check-') as directory:
        source_path = Path(directory)/'source.geojson'
        source_path.write_bytes(b'fixture refresh uses a mocked geodata build')
        target_path = Path(directory)/'layout.json'
        for current_manifest, roads, legacy, expected_position in (
                (manifest, network, True, old_position),
                (manifest, replay, True, new_position),
                (manifest, replay, False, old_position),
                (manifest, moved, False, new_position),
                (manifest | {'sha256':'4'*64}, replay, False, new_position),
                (manifest | {'path':'Data/reviewed-resurvey.geojson'}, replay, False, new_position)):
            target_path.write_bytes(layout(manifest,old_position,network,legacy=legacy,stale_garden=True))
            rebuilt = layout(current_manifest,new_position,roads)
            with patch.object(importer,'build',return_value=rebuilt), \
                    patch.object(importer,'validate_source_fragments'), patch.object(importer,'validate_layout'), \
                    patch.object(shared,'TARGET',target_path):
                importer.refresh(source_path=source_path,target_path=target_path)
            refreshed = json.loads(target_path.read_bytes())
            assert refreshed['metadata']==json.loads(rebuilt)['metadata'],'Refresh must publish current provenance'
            assert refreshed['fixtures'][0]['position']==expected_position, \
                'Fixture reuse must require unchanged source manifests and clearance geometry'
            assert refreshed['gardens'][1]['exclusions']==[excluded],'Refresh must recover current Nan Lian exclusions'
    print('ANTILA_SUPPLEMENTAL_FIXTURE_REFRESH_OK: timestamp-only replay preserves fixtures, geometry and source changes regenerate fixtures, stale garden exclusions repaired')


def check_touching_paving():
    site=importer.Polygon([(0,0),(41,2),(39,30),(-1,28)]);target=importer.box(2,5,4,25)
    paths,access,_,_,_=importer.path_network('touching-paving',site,site,importer.Polygon(),target,
        importer.Polygon(),importer.box(-100,-100,100,100),importer.Polygon(),importer.Polygon(),importer.Polygon(),0)
    assert not access.is_empty and access.intersects(paths) and access.intersects(target) and site.covers(access),\
        'A path joining paving that touches its boundary must retain an in-site pedestrian access corridor'


def check_path_connectivity(data):
    _,lots,east_roads,east_prop_roads,east_land,east_targets,east_carriageways,ground,west_regions,pavement_patches,paving_margin=importer.safe_site_polygons()
    east_region=(east_roads,east_prop_roads,east_land,east_targets,east_carriageways)
    district_roads=json.loads((importer.ROOT/'Data/nathan-road.json').read_text())
    road_network=json.loads((importer.ROOT/'Data/cross-harbour.json').read_text())
    gardens={garden['site']:garden for garden in data['gardens']}
    for site_id in sorted(WESTERN_SITE_IDS | importer.WONG_TAI_SIN_PATH_SITES):
        garden=gardens[site_id]
        site=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden['rings']])
        paths=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden['paths']])
        access=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden['access']])
        region=west_regions[importer.WESTERN_SITE_COAST[site_id]] if site_id in WESTERN_SITE_IDS else east_region
        if site_id in importer.GROUND_SCOPE_SITE_IDS:
            region=importer.ground_scope_region(region,east_region,ground)
        region=importer.site_road_scope(site_id,site,region,district_roads)
        if site_id=='1503005115':
            region=(*region[:3],importer.lok_kwan_street_targets(site,road_network),region[4])
        street_targets=region[3]
        if site_id=='1910053968':
            assert paths.covers(importer.Point(-1600,-415.5)),\
                'West Kowloon Waterfront Promenade lost its narrow source-strip path'
            art_park=gardens['1910053970']
            art_park_paths=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in art_park['paths']])
            art_park_access=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in art_park['access']])
            assert not art_park_access.is_empty,'West Kowloon Art Park must retain pedestrian access'
            art_park_paving=importer.union_all([art_park_paths,art_park_access])
            assert access.intersects(art_park_paving),\
                'West Kowloon Waterfront Promenade access must overlap Art Park paths/access'
            street_targets=importer.union_all([street_targets,art_park_paving])
        connected=importer.publicly_connected_path_components(
            paths,access,street_targets,lots,pavement_patches,paving_margin)
        components=importer.geometry_polygons(paths)
        assert components and all(any(public.intersects(component) for public in connected)
                                  for component in components),\
            'Retained path component does not connect to public paving: '+site_id
        paved_components=importer.geometry_polygons(importer.union_all([paths,access]))
        assert all(any(importer.Point(sample).covered_by(component) for sample in garden['samples'])
                   for component in paved_components),\
            'Paved component has no interior connectivity probe: '+site_id
        if site_id in importer.WONG_TAI_SIN_PATH_SITES:
            assert access.difference(east_land).area<=.01 and access.intersection(east_carriageways).area<=.01,\
                'Wong Tai Sin access leaves ground or enters a carriageway: '+site_id
    kwai=gardens['1910069198']
    failed_probe=importer.Point(-5460.90744575262,-6427.402350829019)
    kwai_paths=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in kwai['paths']])
    assert kwai_paths.covers(failed_probe) and any(
        failed_probe.distance(importer.Point(sample))<.001 for sample in kwai['samples']),\
        'Kwai Chung native failure probe was removed instead of reconnecting its path component'
    rejected=data['metadata'].get('western_path_component_rejections',[])
    assert not any(row.get('site')=='1910069198' and row.get('component')=='1910069198:02'
                   for row in rejected),\
        'Kwai Chung disconnected source component was rejected rather than connected'
    print(f'ANTILA_EAST_OPEN_SPACE_CONNECTIVITY_OK: {len(WESTERN_SITE_IDS)} western and {len(importer.WONG_TAI_SIN_PATH_SITES)} Wong Tai Sin sites; retained path components connect to public paving; Kwai Chung failed probe preserved')


def garden_geometry(garden,field):
    return importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden[field]])


def check_reviewed_paving_change(uid,baseline,current,old_paths,new_paths,old_access,new_access):
    if uid=='1910059822' and old_paths.symmetric_difference(new_paths).area>.01:
        # The lower Lung Cheung Road approach changes the Water Feature Park's path clearance.
        removed=old_paths.difference(new_paths);added=new_paths.difference(old_paths)
        assert removed.area<=4.36 and added.area<=2.10 and removed.union(added).difference(
            importer.box(2679.65,-5073.50,2923.70,-4949.04)).area<=.01,\
            'Diamond Hill Water Feature Park path change exceeds the reviewed area'
        assert old_access.symmetric_difference(new_access).area<=.01, 'Water Feature Park entrance changed'
        assert len(baseline['samples'])==len(current['samples']) and all(
            importer.Point(old).distance(importer.Point(new))<=2.02
            for old,new in zip(baseline['samples'],current['samples'])),\
            'Water Feature Park probes moved beyond the reviewed path adjustment'
    elif uid==importer.NAN_LIAN_SITE_ID and old_access.symmetric_difference(new_access).area>.01:
        # The new road network changes the generated public entrance, while retaining the garden walk.
        assert old_paths.symmetric_difference(new_paths).area<=.01, 'Nan Lian perimeter walk changed'
        added=new_access.difference(old_access)
        assert abs(old_access.difference(new_access).area-213.27)<.02 and abs(added.area-115.66)<.02,\
            'Unexpected Nan Lian entrance change'
        network=json.loads((importer.ROOT/'Data/cross-harbour.json').read_bytes())
        approach=next(road for road in network['roads'] if road['id']=='TD_103841')
        target=importer.LineString([(x,z) for x,_,z in approach['points']]).buffer(max(12,approach['width'])/2+3,join_style='mitre')
        assert new_access.intersection(new_paths).area>.1 and added.distance(target)<=.01 and added.difference(
            importer.box(3188.90,-4911.81,3210.02,-4883.20)).area<=.01, 'Unexpected Nan Lian entrance location'
        interior=lambda garden: [sample for sample in garden['samples'] if new_paths.covers(importer.Point(sample))]
        current_interior=interior(current)
        assert interior(baseline)==current_interior and len(baseline['samples'])==len(current['samples']) and all(
            new_access.covers(importer.Point(sample)) for sample in current['samples'] if sample not in current_interior),\
            'Nan Lian interior or entrance probes changed beyond the reviewed relocation'
    else:
        return None
    old_paved=old_paths.union(old_access)
    new_paved=new_paths.union(new_access)
    assert baseline['paving_area_m2']==round(old_paved.area,2) and current['paving_area_m2']==round(new_paved.area,2),\
        'Paving area does not match retained path and access geometry: '+uid
    return baseline['paving_area_m2']-current['paving_area_m2']


def check_preservation(baseline_dir,raw,data):
    baseline_dir=Path(baseline_dir)
    old_source_bytes=(baseline_dir/'Data/east-kowloon-open-spaces-source.geojson').read_bytes()
    old_source=json.loads(old_source_bytes)
    old_layout=json.loads((baseline_dir/'Data/east-kowloon-open-spaces.json').read_bytes())
    old_metadata=old_layout['metadata']
    if 'source_sha256' in old_metadata:
        assert hashlib.sha256(old_source_bytes).hexdigest()==old_metadata['source_sha256'],\
            'Baseline layout does not match its primary source extract'
    included_sources={row['path']:row for row in old_source.get('metadata',{}).get('source_manifests',())}
    for manifest in old_metadata.get('source_manifests',()):
        path=Path(manifest['path'])
        if manifest['path'] in included_sources:
            assert manifest==included_sources[manifest['path']], 'Baseline source manifest differs: '+str(path)
            continue
        assert not path.is_absolute() and '..' not in path.parts, 'Invalid baseline source path: '+str(path)
        payload=(baseline_dir/path).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==manifest['sha256'], 'Baseline supplemental source differs: '+str(path)
        old_source['features'].extend(json.loads(payload)['features'])
    old_site_ids={str(site['id']) for site in old_layout['sites']}
    old_sport_ids={str(surface['source_id']) for surface in old_layout['surfaces']}
    def canonical(features):
        return Counter(json.dumps(feature,sort_keys=True,separators=(',',':')) for feature in features)
    def source_rows(collection,site_ids,sport_ids):
        layer_keys={'Site':('SITEID',site_ids),'BuiltStructurePolygon':('BUILTSTRUCTUREPOLYGONID',sport_ids)}
        for feature in collection['features']:
            properties=feature['properties']
            if properties.get('layer') in layer_keys:
                key,ids=layer_keys[properties['layer']]
                uid=str(properties.get(key))
                if uid in ids:
                    yield {**feature,'properties':{**properties,key:uid}}
    assert canonical(source_rows(raw,old_site_ids,old_sport_ids))==\
           canonical(source_rows(old_source,old_site_ids,old_sport_ids)),'Existing Site/sport source geometries or attributes changed'
    old_sites={str(site['id']):site for site in old_layout['sites']}
    new_sites={str(site['id']):site for site in data['sites']}
    assert set(old_sites)<=set(new_sites),'An existing park site was removed'
    for uid,baseline in old_sites.items():
        current=new_sites[uid]
        for key in ('id','name','source_area_m2','bounds'):
            assert current[key]==baseline[key],'Existing site geometry or identity changed: '+uid
        count_delta=current['fixtures']-baseline['fixtures']
        if uid in CLEARANCE_REBUILT_SITE_IDS:
            assert current['fixtures']==sum(f['site']==uid for f in data['fixtures']),\
                'Site fixture count differs from regenerated furniture: '+uid
        else:
            assert uid in BENCH_RELAYOUT_SITE_IDS or count_delta==0,'Existing fixture count changed: '+uid
            assert count_delta in (0,BENCH_COUNT_DELTAS.get(uid,0)),'Unexpected legacy bench count change: '+uid
    for field,key in [('surfaces','source_id'),('sports','source_id')]:
        baseline=old_layout[field]
        retained=[row for row in data[field] if str(row[key]) in old_sport_ids]
        assert retained==baseline,'Existing sports records changed: '+field
    old_gardens={garden['site']:garden for garden in old_layout['gardens']}
    new_gardens={garden['site']:garden for garden in data['gardens']}
    site_geometry=None

    def current_site_geometry():
        nonlocal site_geometry
        if site_geometry is None:
            site_geometry=importer.safe_site_polygons(include_southwest_landmarks=False)
        return site_geometry

    lost_access_area=0
    reviewed_paving_delta=0
    for uid,baseline in old_gardens.items():
        current=new_gardens[uid]
        assert garden_geometry(baseline,'rings').symmetric_difference(garden_geometry(current,'rings')).area<=.01,\
            'Existing site boundary changed: '+uid
        assert current.get('exclusions')==baseline.get('exclusions'), 'Existing surveyed landscape exclusions changed: '+uid
        if uid in CLEARANCE_REBUILT_SITE_IDS:
            # Rebuilt paths and entrances are validated against current clearance by check().
            continue
        old_paths=garden_geometry(baseline,'paths');new_paths=garden_geometry(current,'paths')
        old_access=garden_geometry(baseline,'access');new_access=garden_geometry(current,'access')
        reviewed_delta=check_reviewed_paving_change(uid,baseline,current,old_paths,new_paths,old_access,new_access)
        if reviewed_delta is not None:
            reviewed_paving_delta+=reviewed_delta
            continue
        assert old_paths.symmetric_difference(new_paths).area<=.01, 'Existing path geometry changed: '+uid
        if uid==GROUND_CLIPPED_ACCESS_SITE_ID:
            retained=new_access.area/old_access.area
            assert .99<=retained<=1 and len(importer.geometry_polygons(new_access))==1,\
                'Hung Hom access clip lost too much area or disconnected the corridor'
            _,_,_,_,_,east_targets,_,ground,_,_,_=current_site_geometry()
            expected_access=old_access.intersection(ground)
            assert new_access.symmetric_difference(expected_access).area<=.01,\
                'Hung Hom access is not the exact shared-ground intersection'
            assert new_access.difference(ground).area<=.01,'Hung Hom access retains unsupported ground'
            assert new_access.intersects(east_targets) and new_access.intersection(garden_geometry(current,'paths')).area>.1,\
                'Hung Hom clipped access lost its street or path join'
            path= garden_geometry(current,'paths')
            old_path_samples=[sample for sample in baseline['samples'] if path.covers(importer.Point(sample))]
            new_path_samples=[sample for sample in current['samples'] if path.covers(importer.Point(sample))]
            assert old_path_samples==new_path_samples,'Hung Hom interior path connectivity probes changed'
            assert len(baseline['samples'])==len(current['samples']) and all(
                new_access.covers(importer.Point(sample)) for sample in current['samples']
                if not path.covers(importer.Point(sample))),\
                'Hung Hom access connectivity probe is missing'
            lost_access_area=old_access.area-new_access.area
            assert abs((baseline['paving_area_m2']-current['paving_area_m2'])-lost_access_area)<.02,\
                'Hung Hom paving area changed beyond the supported access clip'
        else:
            assert old_access.symmetric_difference(new_access).area<=.01,'Existing park access geometry changed: '+uid
            assert current['samples']==baseline['samples'],'Existing path connectivity probes changed: '+uid
            assert current['paving_area_m2']==baseline['paving_area_m2'],'Existing path paving volume changed: '+uid
    old_volume=sum(garden['paving_area_m2'] for uid,garden in old_gardens.items()
                   if uid not in CLEARANCE_REBUILT_SITE_IDS)
    new_volume=sum(new_gardens[uid]['paving_area_m2'] for uid in old_gardens
                   if uid not in CLEARANCE_REBUILT_SITE_IDS)
    assert abs((old_volume-new_volume)-lost_access_area-reviewed_paving_delta)<.02,\
        'Historical paving volume changed beyond the reviewed path and access changes'

    old_fixtures={uid:[fixture for fixture in old_layout['fixtures'] if fixture['site']==uid] for uid in old_site_ids}
    new_fixtures={uid:[fixture for fixture in data['fixtures'] if fixture['site']==uid] for uid in old_site_ids}
    clearance=None
    for uid in old_site_ids:
        previous=old_fixtures[uid];current=new_fixtures[uid]
        if uid in CLEARANCE_REBUILT_SITE_IDS:
            if clearance is None:
                clearance=current_site_geometry()[1].buffer(4)
            assert all(clearance.intersection(importer.Point(fixture['position']).buffer(fixture['radius'])).area<=.01
                       for fixture in current),\
                'Regenerated fixture enters current building clearance: '+uid
            continue
        if uid not in BENCH_RELAYOUT_SITE_IDS:
            assert current==previous,'Existing authored fixtures changed: '+uid
            continue
        canonical_rows=lambda rows:Counter(json.dumps(row,sort_keys=True,separators=(',',':')) for row in rows)
        old_nonbench=[row for row in previous if row['asset']!='bench']
        new_nonbench=[row for row in current if row['asset']!='bench']
        assert canonical_rows(new_nonbench)==canonical_rows(old_nonbench),'Existing non-bench fixtures changed: '+uid
        old_benches=[row for row in previous if row['asset']=='bench']
        new_benches=[row for row in current if row['asset']=='bench']
        assert len(new_benches)-len(old_benches) in (0,BENCH_COUNT_DELTAS.get(uid,0)),\
            'Unexpected bench count change: '+uid
    baseline_counts=(len(old_layout['sites']),len(old_layout['surfaces']),len(old_layout['sports']),
                     len(old_layout['fixtures']),len(old_layout['paving']))
    assert baseline_counts in ((16,71,50,1505,44518),(25,120,88,3068,81836),
                               (27,120,88,3302,86722),(41,132,94,3620,103444),
                               (53,149,106,3976,111845),(64,161,111,4073,120908),
                               (68,166,115,4296,132744)),\
        'Unexpected preservation baseline counts: '+repr(baseline_counts)
    for key,ids in [('source_revisions',old_site_ids),('sports_revisions',old_sport_ids)]:
        assert {uid:value for uid,value in data['metadata'][key].items() if uid in ids}==\
               {uid:value for uid,value in old_layout['metadata'][key].items() if uid in ids},\
            'Existing source revision records changed: '+key
    print(f'ANTILA_EAST_OPEN_SPACE_PRESERVATION_OK: {baseline_counts[0]} prior sites; '
          f'{baseline_counts[1]} source outlines; {baseline_counts[2]} fittings; '
          f'{baseline_counts[3]:,} prior fixtures; source geometry preserved; '
          f'{lost_access_area+reviewed_paving_delta:.2f}m² reviewed paving reduction; approved bench-only changes retained')


if __name__=='__main__':
    if sys.argv[1:]==['--bundled']:
        check(None,importer.ROOT/'Data/kowloon-open-spaces-tile-manifest.json')
    elif len(sys.argv) in (3,4):
        check(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]) if len(sys.argv)==4 else None)
    else:
        raise SystemExit(__doc__+' Optional: PRESERVATION_BASELINE_DIR')
