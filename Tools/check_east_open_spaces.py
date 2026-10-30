"""Offline geometry and rejected-refresh checks. Pass CACHE_DIR MANIFEST_JSON."""
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
    '1503005076','1810011761','1910064509','1910069198'
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
    '1500001358'
}


def check(cache,manifest_path,preservation_baseline=None):
    for path in (importer.SOURCE,importer.TARGET):
        assert path.is_file(),'Missing eastern recreation data: '+str(path)
    source=importer.SOURCE.read_bytes();target=importer.TARGET.read_bytes()
    raw=json.loads(source);data=json.loads(target)
    site_ids={site['id'] for site in data['sites']}
    source_site_ids={str(feature.get('properties',{}).get('SITEID'))
        for feature in raw['features'] if feature.get('properties',{}).get('layer')=='Site'}
    sport_ids={str(feature.get('properties',{}).get('BUILTSTRUCTUREPOLYGONID'))
        for feature in raw['features'] if feature.get('properties',{}).get('layer')=='BuiltStructurePolygon'}
    assert len(WESTERN_SITE_IDS)==9 and WESTERN_SITE_IDS<=source_site_ids and WESTERN_SITE_IDS<=site_ids,'Western source sites missing from the integrated source/layout: '+repr(sorted(WESTERN_SITE_IDS-(source_site_ids&site_ids)))
    assert len(NEW_SPORT_IDS)==49 and NEW_SPORT_IDS<=sport_ids,'Western source sports missing from the integrated source: '+repr(sorted(NEW_SPORT_IDS-sport_ids))
    assert len(site_ids)==25 and len(sport_ids)==120,'Combined inventory must contain 25 sites and 120 unique sports IDs'
    importer.validate_layout(source,target)
    check_western_path_connectivity(data)
    assert {s['source_id'] for s in data['surfaces']}==importer.EXPECTED_SPORTS,'Mapped sport outline lost'
    assert len(raw['features'])==189 and data['metadata']['source_feature_count']==189,'Expected 189 exact Site and sport source fragments'
    assert data['metadata']['source_site_fragment_count']==54 and data['metadata']['source_sport_fragment_count']==135,'Source fragment counts changed'
    if preservation_baseline is not None:
        check_preservation(Path(preservation_baseline),raw,data)
    for uid,point in [('1503005881',(1989.2677387146189,-2149.3834432934027)),
                      ('1503005714',(1322.4574053629715,-4104.150947211618))]:
        garden=next(g for g in data['gardens'] if g['site']==uid)
        assert any(importer.Point(sample).distance(importer.Point(point))<.01 for sample in garden['samples']),\
            'Former isolated loop lost its in-engine connectivity probe: '+uid
    tracks=importer.union_all([importer.Polygon(p.exterior) for feature in raw['features']
        if feature['properties'].get('USAGETYPE')=='RAT' for p in importer.geometry_polygons(importer.source_local(feature))])
    paving=importer.union_all([importer.Polygon(t) for t in data['paving']])
    assert paving.intersection(tracks).area<.01,'Authored paving enters the running-track infield'
    assert all(not importer.Point(f['position']).buffer(f['radius']).intersects(tracks)
        for f in data['fixtures']),'Authored furniture or planting enters the running-track infield'
    assert data['metadata']['source_sha256']==hashlib.sha256(source).hexdigest()
    for name,digest in data['metadata']['inputs_sha256'].items():
        assert hashlib.sha256((importer.ROOT/name).read_bytes()).hexdigest()==digest,'Stale clearance input: '+name
    manifest=json.loads(manifest_path.read_bytes())
    manifest_bytes=manifest_path.read_bytes()
    assert raw['metadata']['tile_manifest_sha256']==hashlib.sha256(manifest_path.read_bytes()).hexdigest()
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
        for label,layer,id_field,source_id,tile_name in (
                ('missing_sport_fragment','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500001706','11-NE-21A'),
                ('missing_site_fragment','Site','SITEID','1503000199','6-SE-25B'),
                ('missing_western_sport_fragment','BuiltStructurePolygon','BUILTSTRUCTUREPOLYGONID','1500004928','7-SW-12C')):
            for mutation in ('missing','duplicate','wrong_tile'):
                case_label=label if mutation=='missing' else label+'_'+mutation
                invalid_source=json.loads(source)
                fragment=next(feature for feature in invalid_source['features']
                    if feature['properties'].get('layer')==layer and
                       feature['properties'].get(id_field)==source_id and
                       feature['properties'].get('tile')==tile_name)
                if mutation=='missing':invalid_source['features'].remove(fragment)
                elif mutation=='duplicate':invalid_source['features'].append(fragment.copy())
                else:fragment['properties']['tile']='review-wrong-sheet'
                saved_source.write_bytes(importer.encoded(invalid_source))
                before=saved_source.read_bytes(),saved_target.read_bytes()
                try:
                    with patch.object(importer,'build',return_value=target),patch.object(shared,'TARGET',saved_target):
                        importer.refresh(source_path=saved_source,target_path=saved_target)
                except AssertionError as error:
                    assert 'reviewed fragments' in str(error), case_label+' rejected for the wrong reason'
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
    print(f'ANTILA_EAST_OPEN_SPACE_REFRESH_OK: 25 sites across 54 Site fragments; 120 source sports across 135 sheet fragments; complete deterministic rebuild; {len(rejected)+saved_source_rejections} rejected cases ({len(rejected)} ZIP refreshes, {saved_source_rejections} direct saved-source rebuilds); outputs preserved')


def check_western_path_connectivity(data):
    _,lots,_,_,_,_,_,_,west_regions,pavement_patches,paving_margin=importer.safe_site_polygons()
    gardens={garden['site']:garden for garden in data['gardens']}
    for site_id in sorted(WESTERN_SITE_IDS):
        garden=gardens[site_id]
        paths=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden['paths']])
        access=importer.union_all([importer.Polygon(rings[0],rings[1:]) for rings in garden['access']])
        street_targets=west_regions[importer.WESTERN_SITE_COAST[site_id]][3]
        connected=importer.publicly_connected_path_components(
            paths,access,street_targets,lots,pavement_patches,paving_margin)
        components=importer.geometry_polygons(paths)
        assert components and all(any(public.intersects(component) for public in connected)
                                  for component in components),\
            'Western retained path component does not connect to public paving: '+site_id
        paved_components=importer.geometry_polygons(importer.union_all([paths,access]))
        assert all(any(importer.Point(sample).covered_by(component) for sample in garden['samples'])
                   for component in paved_components),\
            'Western paved component has no interior connectivity probe: '+site_id
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
    print('ANTILA_EAST_OPEN_SPACE_CONNECTIVITY_OK: 9 western sites; retained path components connect to public paving; Kwai Chung failed probe preserved')


def check_preservation(baseline_dir,raw,data):
    baseline_dir=Path(baseline_dir)
    old_source=json.loads((baseline_dir/'Data/east-kowloon-open-spaces-source.geojson').read_bytes())
    old_layout=json.loads((baseline_dir/'Data/east-kowloon-open-spaces.json').read_bytes())
    old_site_ids={str(site['id']) for site in old_layout['sites']}
    old_sport_ids={str(surface['source_id']) for surface in old_layout['surfaces']}
    def canonical(features):
        return Counter(json.dumps(feature,sort_keys=True,separators=(',',':')) for feature in features)
    def source_rows(collection,site_ids,sport_ids):
        return [feature for feature in collection['features']
                if (feature['properties'].get('layer')=='Site' and str(feature['properties'].get('SITEID')) in site_ids) or
                   (feature['properties'].get('layer')=='BuiltStructurePolygon' and
                    str(feature['properties'].get('BUILTSTRUCTUREPOLYGONID')) in sport_ids)]
    assert canonical(source_rows({'features':raw['features']},old_site_ids,old_sport_ids))==\
           canonical(source_rows(old_source,old_site_ids,old_sport_ids)),'Existing Site/sport source geometries or attributes changed'
    for field,key in [('sites','id'),('surfaces','source_id'),('sports','source_id')]:
        baseline=old_layout[field]
        retained=[row for row in data[field] if str(row[key]) in (old_site_ids if field=='sites' else old_sport_ids)]
        assert retained==baseline,'Existing recreation records changed: '+field
    old_gardens={garden['site'] for garden in old_layout['gardens']}
    assert [garden for garden in data['gardens'] if garden['site'] in old_gardens]==old_layout['gardens'],\
        'Existing site, path, access or connectivity sample arrays changed'
    assert [fixture for fixture in data['fixtures'] if fixture['site'] in old_site_ids]==old_layout['fixtures'],\
        'Existing authored fixture records changed'
    assert data['paving'][:len(old_layout['paving'])]==old_layout['paving'],'Existing paving triangles changed'
    assert len(old_layout['sites'])==16 and len(old_layout['surfaces'])==71 and \
           len(old_layout['sports'])==50 and len(old_layout['fixtures'])==1505 and \
           len(old_layout['paving'])==44518,'Unexpected Task 2 preservation baseline counts'
    for key,ids in [('source_revisions',old_site_ids),('sports_revisions',old_sport_ids)]:
        assert {uid:value for uid,value in data['metadata'][key].items() if uid in ids}==\
               {uid:value for uid,value in old_layout['metadata'][key].items() if uid in ids},\
            'Existing source revision records changed: '+key
    print('ANTILA_EAST_OPEN_SPACE_PRESERVATION_OK: 16 prior sites; 71 source outlines; 50 fittings; '
          '1,505 fixtures; 44,518 paving triangles; source geometry and arrays exact')


if __name__=='__main__':
    if len(sys.argv) not in (3,4):raise SystemExit(__doc__+' Optional: PRESERVATION_BASELINE_DIR')
    check(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]) if len(sys.argv)==4 else None)
