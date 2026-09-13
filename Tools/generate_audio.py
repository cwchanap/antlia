"""Process existing ElevenLabs downloads; this script makes no API calls."""
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
MANIFEST = ROOT / 'Art/Audio/generation.json'
RATE = 44100


def main():
    manifest = json.loads(MANIFEST.read_text())
    measurements = []
    for asset in manifest['assets']:
        name = asset['name']
        music = asset.get('kind') == 'music'
        channels = 2 if music else 1
        files = sorted((ROOT / 'Art/Audio/Source' / name).glob('*.mp3'))
        assert len(files) == 1, f'{name}: expected exactly one source MP3'
        source = files[0]
        samples = array('f')
        samples.frombytes(subprocess.check_output([
            'ffmpeg', '-v', 'error', '-i', str(source), '-f', 'f32le',
            '-ar', str(RATE), '-ac', str(channels), '-']))
        if sys.byteorder != 'little':
            samples.byteswap()
        assert len(samples) > RATE // 4, f'{name}: empty or truncated audio'
        if asset['loop']:
            overlap = int(RATE * (2 if music else .15))*channels
            blend = array('f', (samples[-overlap+i] * (1-(i//channels)/(overlap//channels-1)) +
                                samples[i] * (i//channels)/(overlap//channels-1) for i in range(overlap)))
            samples = samples[overlap:-overlap] + blend
        else:
            audible = [i for i, x in enumerate(samples) if abs(x) > .005]
            assert audible, f'{name}: silent source'
            samples = samples[max(0, audible[0]-441):min(len(samples), audible[-1]+882)]
            fade = min(441, len(samples)//4)
            for i in range(fade):
                samples[i] *= i/fade
                samples[-1-i] *= i/fade
        rms = math.sqrt(sum(x*x for x in samples)/len(samples))
        assert rms > .0001, f'{name}: silent decoded audio'
        target_db = -20 if music else -21 if name in ('city', 'rolling') else -17
        gain = min(10**(target_db/20)/rms, 10**(-3/20)/max(map(abs, samples)))
        pcm = array('h', (round(x*gain*32767) for x in samples))
        peak = max(map(abs, pcm))/32768
        assert .01 < peak < .72, f'{name}: clipping or near silence'
        if asset['loop']:
            seam = max(abs(pcm[-channels+c]-pcm[c])/32768 for c in range(channels))
            # Sample consecutive frames across the whole track without sorting millions of samples.
            differences = sorted(abs(pcm[i]-pcm[i-channels])/32768
                                 for i in range(channels, len(pcm), channels*max(1,len(pcm)//channels//10000)))
            typical = differences[int(len(differences)*.99)]
            assert seam <= max(.002, typical), f'{name}: loop discontinuity'
        output = ROOT / 'Assets/Audio' / (f'{name}.ogg' if music else f'{name}.wav')
        if sys.byteorder != 'little':
            pcm.byteswap()
        with tempfile.TemporaryDirectory() as temporary:
            wav = Path(temporary)/'music.wav' if music else output
            with wave.open(str(wav), 'wb') as stream:
                stream.setnchannels(channels)
                stream.setsampwidth(2)
                stream.setframerate(RATE)
                stream.writeframes(pcm.tobytes())
            if music:
                subprocess.run(['oggenc', '-Q', '-q', '4', '-o', str(output), str(wav)], check=True)
        asset['source'] = str(source.relative_to(ROOT))
        asset['output'] = str(output.relative_to(ROOT))
        asset['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        measurements.append({'name': name, 'seconds': round(len(pcm)/RATE/channels, 3), 'channels': channels,
                             'peak_dbfs': round(20*math.log10(peak), 2),
                             'rms_dbfs': round(20*math.log10(rms*gain), 2)})
    MANIFEST.write_text(json.dumps(manifest, indent=2)+'\n')
    (ROOT / 'evidence/audio-assets.json').write_text(json.dumps(measurements, indent=2)+'\n')
    print(f'ANTILA_AUDIO_ASSETS_OK: {len(measurements)} ElevenLabs clips; decoded, non-silent, no clipping, loop seams checked')


def check_recording():
    with wave.open(str(ROOT / 'evidence/game-audio-review.wav'), 'rb') as stream:
        rate, channels = stream.getframerate(), stream.getnchannels()
        assert stream.getsampwidth() == 2, 'review must contain 16-bit PCM'
        pcm = array('h', stream.readframes(stream.getnframes()))
    if sys.byteorder != 'little':
        pcm.byteswap()
    duration = len(pcm)/(rate*channels)
    peak = max(map(abs, pcm))/32768
    assert 22 < duration < 28 and .03 < peak < .95, 'silent, clipped or incomplete game mix'
    size = rate*channels//10
    quiet = []
    for i in range(0, len(pcm), size):
        block = pcm[i:i+size]
        rms = math.sqrt(sum((x/32768)**2 for x in block)/len(block))
        if rms < .00003:
            tick = i//size
            if not quiet or quiet[-1][1] != tick:
                quiet.append([tick, tick+1])
            else:
                quiet[-1][1] = tick+1
    assert any(b-a >= 10 and b/10 < duration-2 for a, b in quiet), 'map pause is not silent'
    assert quiet and quiet[-1][1]/10 >= duration and quiet[-1][1]-quiet[-1][0] >= 7, 'teardown leaves audio playing'
    result = {'duration_seconds': round(duration, 3), 'peak_dbfs': round(20*math.log10(peak), 2),
              'silent_spans_seconds': [[a/10, min(b/10, duration)] for a, b in quiet]}
    with wave.open(str(ROOT / 'evidence/music-loop-review.wav'), 'rb') as stream:
        rate, channels = stream.getframerate(), stream.getnchannels()
        music = array('h', stream.readframes(stream.getnframes()))
    if sys.byteorder != 'little':
        music.byteswap()
    def music_rms(start, end):
        block = music[int(start*rate*channels):int(end*rate*channels)]
        assert block, 'incomplete music recording'
        return math.sqrt(sum((x/32768)**2 for x in block)/len(block))
    assert 6 < len(music)/rate/channels < 8, 'incomplete music loop review'
    assert all(music_rms(a,b) > .001 for a,b in [(0.2,1),(1.6,2.7),(4.6,5)]), 'music silent before/after looping or resuming'
    assert music_rms(3.4,3.9) < .00003 and music_rms(5.6,6) < .00003, 'music pause/cleanup must be silent'
    assert max(map(abs,music))/32768 < .95, 'music recording clips'
    result['music_loop_pause_resume'] = 'passed'
    (ROOT / 'evidence/audio-mix.json').write_text(json.dumps(result, indent=2)+'\n')
    print('ANTILA_AUDIO_MIX_OK: native game output, music loop/resume, no clipping, silent map pause and teardown', result)


if __name__ == '__main__':
    check_recording() if '--check-review' in sys.argv else main()
