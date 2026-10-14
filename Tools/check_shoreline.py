"""Offline shoreline refresh regression: run with .venv-geodata/bin/python."""
import hashlib
import io
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import import_shoreline as shore


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


if __name__=='__main__':
    for island in (False,True):check_refresh(island)
