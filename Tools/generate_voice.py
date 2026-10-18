"""Process Mio's downloaded ElevenLabs voice takes; this script makes no API calls.

  python3 Tools/generate_voice.py record TAKES.jsonl...  merge downloaded takes into the manifest
  python3 Tools/generate_voice.py                        encode every fully cast voice into Assets/Audio/Mio
  python3 Tools/generate_voice.py --check                verify sources, hashes and game clips only
"""
from array import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'Data/mio.json'
MANIFEST = ROOT / 'Art/Audio/Mio/generation.json'
RATE = 44100


def load():
    script = json.loads(SCRIPT.read_text())
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        'provider': 'ElevenLabs MCP', 'tool': 'creative_generate_speech', 'takes_per_line': 4,
        'selection': 'Median-duration take of each line, ignoring takes more than 35% from the median.',
        'recordings': []}
    return script, manifest


def record(paths):
    script, manifest = load()
    lines = {line['id']: line for line in script['lines']}
    cast = {voice['id']: voice for voice in script['cast']}
    recordings = {(r['cast'], r['line']): r for r in manifest['recordings']}
    for path in paths:
        for row in Path(path).read_text().splitlines():
            if not row.strip():
                continue
            take = json.loads(row)
            voice, line = cast[take['cast']], lines[take['line']]
            source = ROOT / take['file']
            recordings[(voice['id'], line['id'])] = {
                'cast': voice['id'], 'line': line['id'], 'voice_id': voice['voice_id'], 'model': voice['model'],
                'say': line['say'], 'node_id': take['node_id'], 'chosen': take['chosen'],
                'takes': take['takes'], 'source': take['file'],
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    order = {voice: i for i, voice in enumerate(cast)}
    ids = [line['id'] for line in script['lines']]
    manifest['recordings'] = sorted(recordings.values(), key=lambda r: (order[r['cast']], ids.index(r['line'])))
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')
    print(f'{len(manifest["recordings"])} recordings in {MANIFEST.relative_to(ROOT)}')


def decode(source):
    samples = array('f')
    samples.frombytes(subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(source), '-f', 'f32le',
                                               '-ar', str(RATE), '-ac', '1', '-']))
    if sys.byteorder != 'little':
        samples.byteswap()
    return samples


def main(check):
    script, manifest = load()
    ids = [line['id'] for line in script['lines']]
    assert len(ids) == len(set(ids)), 'duplicate line ids'
    for line in script['lines']:
        assert line['ja'] and line['say'] and line['en'], f'{line["id"]}: empty text'
        assert any('぀' <= c <= 'ヿ' for c in line['ja']), f'{line["id"]}: ja has no kana'
    active = [voice['id'] for voice in script['cast'] if voice.get('active')]
    assert len(active) == 1, 'exactly one cast voice must be active'
    by_cast = {}
    for r in manifest['recordings']:
        source = ROOT / r['source']
        assert hashlib.sha256(source.read_bytes()).hexdigest() == r['source_sha256'], f'{r["source"]}: hash changed'
        assert r['say'] == next(l['say'] for l in script['lines'] if l['id'] == r['line']), f'{r["source"]}: script changed since recording'
        by_cast.setdefault(r['cast'], []).append(r)
    full = [cast for cast, rows in by_cast.items() if {r['line'] for r in rows} == set(ids)]
    assert active[0] in full, f'active cast {active[0]} is missing lines'
    measurements = []
    for cast in full:
        for r in by_cast[cast]:
            output = ROOT / 'Assets/Audio/Mio' / cast / f'{r["line"]}.ogg'
            if check:
                assert output.exists(), f'{output.relative_to(ROOT)} missing'
                continue
            samples = decode(ROOT / r['source'])
            audible = [i for i, x in enumerate(samples) if abs(x) > .01]
            assert audible, f'{r["line"]}: silent source'
            samples = samples[max(0, audible[0]-RATE*3//100):min(len(samples), audible[-1]+RATE*12//100)]
            fade = RATE//100
            for i in range(fade):
                samples[i] *= i/fade
                samples[-1-i] *= i/fade
            rms = math.sqrt(sum(x*x for x in samples)/len(samples))
            gain = min(10**(-19/20)/rms, 10**(-3/20)/max(map(abs, samples)))
            pcm = array('h', (round(x*gain*32767) for x in samples))
            peak = max(map(abs, pcm))/32768
            seconds = len(pcm)/RATE
            assert .4 < seconds < 15 and .05 < peak < .72, f'{r["line"]}: {seconds:.2f} s, peak {peak:.2f}'
            if sys.byteorder != 'little':
                pcm.byteswap()
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as temporary:
                wav = Path(temporary)/'line.wav'
                with wave.open(str(wav), 'wb') as stream:
                    stream.setnchannels(1)
                    stream.setsampwidth(2)
                    stream.setframerate(RATE)
                    stream.writeframes(pcm.tobytes())
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-c:a', 'libvorbis', '-q:a', '5',
                                str(output)], check=True)
            r['output'] = str(output.relative_to(ROOT))
            measurements.append({'cast': cast, 'line': r['line'], 'seconds': round(seconds, 3),
                                 'peak_dbfs': round(20*math.log10(peak), 2), 'rms_dbfs': round(20*math.log10(rms*gain), 2)})
    if not check:
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')
        (ROOT / 'evidence').mkdir(exist_ok=True)
        (ROOT / 'evidence/mio-voice.json').write_text(json.dumps(measurements, indent=2)+'\n')
    auditions = {cast: len(rows) for cast, rows in by_cast.items() if cast not in full}
    print(f'Mio voice OK: {len(ids)} lines, active cast {active[0]}, full casts {full}, auditions {auditions}')


if __name__ == '__main__':
    if sys.argv[1:2] == ['record']:
        record(sys.argv[2:])
    else:
        main('--check' in sys.argv)
