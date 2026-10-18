# Mio, the Japanese onboard guide

Mio is the onboard guide on the three fictional services. She welcomes passengers in Japanese, announces each next stop, opens and closes the doors with the usual courtesy lines, and talks to the driver when something goes wrong. Her lines are voiced with ElevenLabs. The game shows an English caption while she speaks.

Mio is a new character for this prototype. She is not modelled on any real operator's announcements. Hong Kong buses announce in Cantonese, English and Mandarin; a Japanese guide is a stylistic choice.

## Script as data

`Data/mio.json` holds everything she says, so a future Japanese UI can reuse it without touching code.

| Field | Meaning |
| --- | --- |
| `ja` | The display text for a future Japanese UI. Route numbers stay as H1/H2/H3. |
| `say` | Exactly what was sent to ElevenLabs: bracketed audio tags such as `[warmly]`, commas for pacing, and route numbers spelled out (エイチ・ワン). |
| `en` | The English caption shown in game today. |

`places` lists the district and stop names in English, Chinese and the katakana readings Mio uses. The readings are approximate transliterations chosen for this prototype (チムサーチョイ for Tsim Sha Tsui, モンコック for Mong Kok). They are not official Japanese names.

There are 25 lines: a welcome for each route, a next-stop line for each of the 15 stops (the terminus line adds 終点), and seven shared lines.

| Line | When Mio says it |
| --- | --- |
| `<route>.welcome`, then `<route>.next.<first stop>` | The route starts |
| `doors.open` | The doors first open in a bay. Skipped at the terminus. |
| `doors.close`, then `<route>.next.<stop>` | The doors close after boarding |
| `missed`, then `<route>.next.<stop>` | A stop is left 30 m behind |
| `red-light` | The bus crosses a red light on a route |
| `contact` | The bus hits something on a route |
| `complete` | Service complete; plays over the results |
| `abandoned` | Tab ends the route early; plays over the results |

Announcements queue and play in order. The two asides to the driver (`red-light`, `contact`) are dropped if Mio is already talking. Route select and free drives are silent. Pause and the map pause her with the other one-shots, and music drops 6 dB while she speaks.

## Voice cast

| Cast | ElevenLabs voice | Voice ID | Lines |
| --- | --- | --- | --- |
| `warm` (active) | Mio - Warm Japanese Narrator | `nBV906YvEOdwWKK9J8Hx` | All 25 |
| `casual` | Mio - Casual and Friendly | `EVmK7c3z026INySFvQLP` | Audition: H1 welcome, Kowloon Park, contact, complete |
| `bright` | Suzu - Cute, Clear and Calm | `6awt6FKyZGV0HyQEwisX` | Same four audition lines |

The voices come from the ElevenLabs voice library. `casual` and `bright` were recorded on four lines each so their tone can be compared before committing to a full cast. Their MP3s are in `Art/Audio/Mio/casual/` and `Art/Audio/Mio/bright/`; only full casts are encoded for the game.

To switch cast: record the remaining 21 lines in that voice, set `"active": true` on it in `Data/mio.json` (and remove it from `warm`), then rerun the encoder.

## Generation

Every line was generated with the ElevenLabs MCP `creative_generate_speech` tool on 18 October 2026: model `eleven_v4`, the cast's `voice_id`, the line's `say` text as the prompt, and the default four takes. All 33 generations sit on one flow: <https://elevenlabs.io/app/flows/CpPx3QF206cI4blyPali>. The estimate for the 52-character H1 welcome was 208 credits for four takes, so the whole set came to roughly 4,300 credits.

The kept take is the one whose length is closest to the median of the four, ignoring any take more than 35% from the median. Ties go to the earliest take. This rejects truncated or rambling takes, but nobody listened to every take, so a human should still audition the lines.

`Art/Audio/Mio/generation.json` records each line's cast, voice, model, prompt, flow node, all four take IDs and durations, the chosen take, its source MP3 and SHA-256, and the game file.

## Processing

`python3 Tools/generate_voice.py` makes no network calls. It needs `ffmpeg` with libvorbis.

1. Checks the script: unique IDs, no empty `ja`/`say`/`en`, kana in every `ja`, exactly one active cast.
2. Checks every recording against its hash and against the current `say` text, so a script edit flags the line for re-recording.
3. For every fully cast voice, decodes the MP3 to 44.1 kHz mono, trims silence (30 ms lead, 120 ms tail), adds 10 ms fades, and levels to −19 dBFS RMS with peaks at or below −3 dBFS.
4. Writes `Assets/Audio/Mio/<cast>/<line>.ogg` (Vorbis q5) and the per-line measurements to `evidence/mio-voice.json`.

`python3 Tools/generate_voice.py record TAKES.jsonl...` merges newly downloaded takes into the manifest.

The warm cast's 25 clips run 1.7 to 9.2 s, 90 s in all, and take 1.0 MB.

## Adding or re-recording a line

1. Add or edit the line in `Data/mio.json`: an `id` the game will ask for, `ja`, `say` and `en`. Keep the English caption to two lines.
2. Generate it with `creative_generate_speech`: `model_id` `eleven_v4`, the cast's `voice_id`, the `say` text as `prompt`, and this flow's `flow_id`. Leave the take count at its default. Each call is charged, so never repeat one to retry; poll `creative_get_flow_run_status` instead.
3. When the takes are done, pick one by the median rule above and download its `content_url` to `Art/Audio/Mio/<cast>/<id>.mp3`. The signed URL expires after about two hours.
4. Write one JSON line per take set (`cast`, `line`, `node_id`, `takes` with `generation_id`, `session_id` and `duration`, `chosen`, `file`) and run `python3 Tools/generate_voice.py record` on it, then `python3 Tools/generate_voice.py`.
5. Import in Godot so the `.ogg.import` files exist, wire the trigger in `Main.Mio.cs` if the id is new, update the line count in `CheckMio`, and run `--route-check`.

## Limits

- The voices are AI-generated. Pronunciation of the katakana place names was not checked line by line by a Japanese speaker.
- Japanese text is stored but not displayed. The HUD font list has no Japanese face, so a Japanese UI will need one.
- Captions are English only. They sit above the controls bar (near the top in the cab view, under the results panel at the end) and show only while her voice is playing, so pause and the map hide them.
- The headless checks run at 4× time scale, so announcements queue behind each other there. The order is checked, not the overlap with real playback.
- Commercial use of the output depends on the terms of the ElevenLabs plan that generated it.

## Checks

```sh
python3 Tools/generate_voice.py --check            # script, manifest hashes and game clips
./run.command --headless -- --route-check          # includes Mio's in-engine checks
```

`--route-check` first asserts the data: 25 lines covering every route welcome, every stop and every shared line, Japanese text in each, a non-looping Ogg clip of 0.4–12 s for each, and English captions that fit in two lines. It prints `ANTILA_MIO_LINES_OK`. It then checks what Mio does at each step of the menu run: the H2 welcome and first stop, pause holding her voice and resuming it, the missed-stop line and the next stop, the sign-off over the abandoned trip's results, and silence on route select and in free drives. Each fully driven route must produce exactly welcome, first stop, then doors open, doors close and next stop at every bay, then `complete`.

## Verification — 18 October 2026

These runs used Godot 4.6.2 .NET headless in a Linux container. The Renderpeople passenger GLBs are not in the repository, so plain box stand-ins sat at those git-ignored paths for the runs. None of Mio's checks depend on the passenger models.

- `python3 Tools/generate_voice.py` encoded the 25 warm clips; `--check` passes with both audition casts listed as partial.
- Build: **0 warnings / 0 errors**.
- `--self-test` exits 0 with `ANTILA_SELF_TEST_OK`. Its audio checks now count the voice channel among the bus's 11 players, and its route checks drove H1, H2 and H3 with 9, 24 and 12 announcements, all in the expected order.
- After pause started hiding the caption, `--route-check` was run again and exited 0, with the same drives and announcement counts and no contacts or red-light crossings.
- `--route-capture` exits 0 and now adds `mio-caption.png` (chase view, leaving Saigon Street) and `mio-caption-cab.png` (cab view, after a missed stop). `results-h1.png` shows the two-line `complete` caption under the results panel. All three were inspected. The capture slows Mio's voice to 1% speed, because software rendering takes seconds a frame and the lines would otherwise end before the frame is saved.
