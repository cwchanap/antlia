# ElevenLabs game audio

Nine SFX/ambience clips were generated using the connected ElevenLabs MCP `text_to_sound_effects` tool, plus a 90-second original instrumental track using `compose_music` with `music_v2` and instrumental mode. The source MP3s, prompts, requested duration/loop settings, output mapping and source hashes are retained in `Art/Audio/generation.json` and `Art/Audio/Source/`.

| Clip | Runtime trigger / mix |
| --- | --- |
| kowloon-drive | Continuous quiet instrumental music in stereo; lowers by 6 dB while doors are open or the boarding chime is playing, then smoothly recovers. |
| engine | Continuous diesel idle; pitch and gain smoothly follow speed and throttle. Quieter in the cab. |
| rolling | Continuous tire/road loop; fades in with road speed. |
| city | Low background street ambience; quieter in the cab with closed doors. |
| door-open / door-close | Accepted E-key door changes; reversing the door action cancels its previous sound. |
| air-brake | Once when braking down from a moving speed to a stop. |
| horn | H key, separate from engine/doors. |
| stop-bell | Boarding confirmation at each served stop, including completion. |
| contact | The existing collision feedback event and cooldown. |
| Mio (voice) | Japanese announcements on routes; music lowers by 6 dB while she speaks. Generated with ElevenLabs text to speech; see [MIO_VOICE.md](MIO_VOICE.md). |

The map and Pause suspend all active audio. Closing them resumes playback. V toggles the Master bus and the HUD shows Unmute when muted. Restart removes the old scene/audio; resets preserve music while discarding stale one-shots and closing the door visuals. Completing the service stops the continuous layers and plays the boarding chime.

`python3 Tools/generate_audio.py` decodes the existing downloads with installed FFmpeg, folds SFX to mono 44.1 kHz PCM, trims one-shot padding, applies short fades and a 150 ms overlap to SFX loops, and normalizes with at least 3 dB of asset headroom. Music preserves stereo, uses a two-second overlap to join its ends, and is encoded as Ogg Vorbis with installed `oggenc`; the resulting 88.024-second file is about 1.26 MB. It performs no network calls. Processed SFX loops are 4.85 seconds long; runtime loop endpoints cover the full clip instead of the old one-second engine loop. This prototype varies one engine recording by pitch/gain; gear-specific RPM layers are not simulated.

## Verification

- C# build: zero warnings/errors. All ten clips decoded, were non-silent and unclipped, and passed loop-seam checks (`evidence/audio-assets.json`).
- In-engine checks passed for imports, complete loops, music ducking/recovery, overlapping effects, map pause/resume, mute, reset preservation and service-completion cleanup. The existing 3,110 road queries, side-street drives and complete three-stop H1 run also passed (`evidence/self-test.log`).
- `./run.command -- --audio-review` records actual Godot Master-bus output while idling, using the horn/doors, accelerating, braking, boarding, pausing and contacting a barrier. A second recording, `evidence/music-loop-review.wav`, isolates the music across its wrap point, pause, resume and cleanup. Neither recording uses a microphone.
- `python3 Tools/generate_audio.py --check-review` verifies the recorded mix: 22.709 seconds, peak −9.78 dBFS, silence during map pause (16.3–17.7 s) and after audio cleanup (21.8 s onward). The separate music recording also passed checks for audible playback before and after the wrap point, resumed playback, and silent pause/cleanup. Results: `evidence/audio-mix.json`.

The normal launcher rebuilt and left the game running with music and SFX. An earlier native-keyboard mute check was blocked by the locked macOS session; the current in-engine mute/pause checks and native music/mix recordings passed.

[Play the recorded game mix](../evidence/game-audio-review.mp3).

[Music-only preview](../evidence/kowloon-music-preview.mp3). The preview has short fades for listening; the game uses the full stereo loop in `Assets/Audio/kowloon-drive.ogg`.
