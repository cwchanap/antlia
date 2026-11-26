"""Offline shoreline refresh regression: run with .venv-geodata/bin/python."""
import hashlib
import io
import json
import runpy
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import import_shoreline as shore
import import_map
import import_open_spaces
from shapely.geometry import box, mapping, shape


def archive_at(easting):
    gml=f'''<gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml" xmlns:f="http://www.safe.com/gml/fme">
<gml:featureMember><f:Shoreline><f:STATUS>E</f:STATUS><f:geometry><gml:LineString srsName="EPSG:2326">
<gml:posList>817000 {easting} 0 817010 {easting+10} 0</gml:posList>
</gml:LineString></f:geometry></f:Shoreline></gml:featureMember></gml:FeatureCollection>'''
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        archive.writestr('REVIEW/Layers/Hydrography/Shoreline.gml',gml)
    return output.getvalue()


def check_refresh(island):
    with tempfile.TemporaryDirectory() as folder:
        cache=Path(folder);raw=cache/'source.geojson';tile=cache/'REVIEW.zip'
        props={'SHEETNO':'REVIEW','GML':'https://example.invalid/tile.zip','REVISIONDATE':'old'}
        payload=archive_at(835000);calls=[]
        def index(*args,**kwargs):
            return io.BytesIO(json.dumps({'features':[{'attributes':props}]}).encode())
        def fetch(args,**kwargs):
            calls.append(args)
            assert kwargs['check'] and args[args.index('-o')-1]==props['GML']
            if isinstance(payload,Exception):raise payload
            Path(args[args.index('-o')+1]).write_bytes(payload)
        with patch.object(shore,'Path',return_value=cache),patch.object(shore,'RAW',raw), \
             patch.object(shore,'ISLAND',island),patch.object(shore.urllib.request,'urlopen',index), \
             patch.object(shore.subprocess,'run',fetch):
            shore.download()
            first=json.loads(raw.read_text());assert tile.read_bytes()==payload
            props['REVISIONDATE']='new';payload=archive_at(835100)
            shore.download()
            second=json.loads(raw.read_text())
            assert len(calls)==2,'Explicit refresh reused the old tile archive'
            assert second['features']!=first['features'],'Refresh kept old shoreline geometry'
            assert second['metadata']['tiles'][0]==dict(tile='REVIEW',url=props['GML'],revision_date='new',
                                                       sha256=hashlib.sha256(payload).hexdigest())
            saved_raw=raw.read_bytes();saved_tile=tile.read_bytes()
            malformed=io.BytesIO()
            with zipfile.ZipFile(malformed,'w') as archive:
                archive.writestr('REVIEW/Layers/Hydrography/Shoreline.gml','<broken')
            for payload,error in [(subprocess.CalledProcessError(22,'curl'),subprocess.CalledProcessError),
                                  (b'not a ZIP',AssertionError),(malformed.getvalue(),ET.ParseError)]:
                try:shore.download()
                except error:pass
                else:raise AssertionError('Failed refresh must report its error')
                assert raw.read_bytes()==saved_raw and tile.read_bytes()==saved_tile,'Failed refresh replaced prior data'
    print('ANTILA_SHORELINE_REFRESH_OK:', 'island' if island else 'west',
          'fresh/revised geometry and provenance; download, ZIP and XML failures preserve prior data')


def check_kai_tak_refresh():
    data=shore.ROOT/'Data'
    raw_bytes=(data/'east-kowloon-shoreline.geojson').read_bytes()
    coast_bytes=(data/'east-kowloon-coast.json').read_bytes()
    supplements=json.loads(raw_bytes)['kai_tak_coast_sources']
    sea_rows=supplements['sea_fill']['features']
    mainland_rows=supplements['reclamation']['features']
    script=Path(shore.__file__)

    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        target=root/'Data'
        target.mkdir()
        raw=target/'east-kowloon-shoreline.geojson'
        coast=target/'east-kowloon-coast.json'
        raw.write_bytes(raw_bytes)
        coast.write_bytes(coast_bytes)
        wong_tai_sin='wong_tai_sin_district_land' in json.loads(coast_bytes)['metadata']
        if wong_tai_sin:
            name='wong-tai-sin-district-boundary.geojson'
            (target/name).write_bytes((data/name).read_bytes())

        def refresh(sea, mainland):
            def download(url, **kwargs):
                if url.startswith(shore.KAI_TAK_SEA_FILL_SOURCE+'?'):
                    features=sea
                elif url==shore.KAI_TAK_RECLAMATION_SOURCE:
                    features=mainland
                else:
                    raise AssertionError(f'Unexpected request: {url}')
                return io.BytesIO(json.dumps({'type':'FeatureCollection','features':features}).encode())

            with patch.object(import_map,'ROOT',root), \
                 patch.object(import_open_spaces,'TARGET',coast), \
                 patch.object(shore.urllib.request,'urlopen',download), \
                 patch.object(sys,'argv',[str(script),'--east-kowloon','--download']):
                runpy.run_path(str(script),run_name='__main__')

        def reject(sea, mainland, expected):
            try:
                refresh(sea,mainland)
            except (AssertionError,ValueError) as error:
                assert expected in str(error), error
            else:
                raise AssertionError(f'Invalid Kai Tak source passed: {expected}')
            assert (raw.read_bytes(),coast.read_bytes())==(raw_bytes,coast_bytes), \
                'Rejected Kai Tak refresh altered the saved raw/derived pair'

        # Complete counts and valid geometries can still place the shoreline incorrectly.
        wrong_sea=[feature|{'geometry':mapping(box(114.218,22.335,114.219,22.336))}
                   for feature in sea_rows]
        reject(wrong_sea,mainland_rows,'harbour and approach channel')

        narrowed=shape(mainland_rows[0]['geometry']).intersection(box(114.196,22.300,114.209,22.325))
        reject(sea_rows,[mainland_rows[0]|{'geometry':mapping(narrowed)}],'northern fill')
        if wong_tai_sin:
            narrowed=shape(mainland_rows[0]['geometry']).intersection(box(113,22,115,22.352))
            reject(sea_rows,[mainland_rows[0]|{'geometry':mapping(narrowed)}],'Wong Tai Sin district and inland margin')

        replace=Path.replace
        def fail_coast_publish(path, destination):
            if destination==coast:
                raise OSError('test: cannot replace derived coast')
            return replace(path,destination)

        with patch.object(Path,'replace',fail_coast_publish):
            try:
                refresh(sea_rows,mainland_rows)
            except OSError as error:
                assert 'test: cannot replace derived coast' in str(error), error
            else:
                raise AssertionError('Derived coast replacement failure must be reported')
        assert (raw.read_bytes(),coast.read_bytes())==(raw_bytes,coast_bytes), \
            'Failed publication altered the saved raw/derived pair'

        refresh(sea_rows,mainland_rows)
        updated_raw=raw.read_bytes()
        updated_coast=json.loads(coast.read_bytes())
        assert updated_raw!=raw_bytes and coast.read_bytes()!=coast_bytes
        assert updated_coast['metadata']['source_sha256']==hashlib.sha256(updated_raw).hexdigest()
        assert updated_coast['land']==json.loads(coast_bytes)['land']
        if wong_tai_sin:
            assert updated_coast['metadata']['wong_tai_sin_district_land']['margin_m']==shore.WONG_TAI_SIN_MARGIN_M
    print('ANTILA_KAI_TAK_SHORELINE_REFRESH_OK: same-count rejection, north fill, rollback and linked publication')


if __name__=='__main__':
    for island in (False,True):check_refresh(island)
    check_kai_tak_refresh()
