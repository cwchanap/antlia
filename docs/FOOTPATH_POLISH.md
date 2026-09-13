# Footpath polish — 12 September 2026

The pavement review found edging only on Nathan Road, no tactile crossing landings, and a continuous park wall with no entrances to the internal paths.

## Changes

- Continuous stone borders follow the combined road/pavement mask, including side streets and park paths. The old disconnected Nathan Road kerb boxes are replaced by the shared ground treatment, avoiding overlapping road surfaces at junctions.
- 73 clear crossing landing areas use five tactile pavers each. Six additional pavers mark unobstructed boarding positions at the three bus stops.
- 164 pedestrian railing panels flank crossing approaches. Placement leaves the landings open and avoids building lots, signal poles, tree trunks, shelters and other recorded street furniture.
- 885 small drainage grates add detail along pavement edges. All three new models use shared MultiMesh groups rather than individual scene nodes.
- Two 5.2 m openings at route distances 560 m and 735 m connect the roadside pavement to the park's existing paths. Trees and planters are kept clear of the new routes. Building placement is retained at 1,755 instances.

The visual reference is the Highways Department's [pedestrian crossing kerb/footway drawing H1117B](https://www.hyd.gov.hk/en/technical_references/standard_drawings/hyd_standard_drawings/doc/section_1/pdf/h1117b.pdf) and [tactile paving drawing catalogue](https://www.hyd.gov.hk/en/technical_references/standard_drawings/hyd_standard_drawings/section5.html). These are authored game approximations; placement is not a surveyed inventory. The prototype terrain stays flat: the borders do not model raised pavements or engineered dropped-kerb profiles. Pedestrian walking AI and pedestrian signal phases remain outside this polish pass.

## Assets

`Tools/model_footpaths.py` was executed through Blender MCP. It creates an isolated scene, exports each model at the origin, saves a spaced editable lineup in `Art/footpaths.blend`, and restores the prior Blender scene.

| Model | Triangles | Instances |
| --- | ---: | ---: |
| `Assets/Models/tactile-paver.glb` | 1,596 | 371 |
| `Assets/Models/pedestrian-railing.glb` | 596 | 164 |
| `Assets/Models/drain-grate.glb` | 108 | 885 |

All exports contain one mesh. The new models are decorative; the park wall openings also modify the actual collision bodies. Existing bus handling, service stops and traffic-light timings are retained. No performance benchmark is claimed.

The built-in imagegen tool generated `Assets/Textures/pavement-stone.png` (1254 × 1254). The terrain uses it for the stone border and the tactile model embeds a tinted version in its material. Mipmaps and anisotropic sampling are enabled for the ground texture. Existing herringbone paving is reused.

## Verification and views

```sh
./run.command --headless -- --footpath-check
./run.command --disable-vsync -- --footpath-review
./run.command --headless -- --self-test
```

The focused check verifies placement on pavement, road/building/pole/furniture clearance, crossing openings and continuous paved park connections. It uses 2.4 m wide physics probes to check both wall gaps, and verifies clearance beside recorded tree trunks and furniture. The full self-test includes these checks before its existing road, bus, traffic, audio and route checks.

Seven final renders are in `evidence/footpath-review/`. Four matching before views are retained in `evidence/before-footpath-review/`; the additional final views are `crossing-overview.png`, `park-connections.png` and `tactile-detail.png`. Earlier source files are retained in `Art/before-footpath-polish/` with `.cs.bak` extensions so .NET does not compile backup copies.

The C# build passed with zero warnings/errors. The full self-test passed all pedestrian, building, signal and audio checks, 3,110 bus-sized road-clearance queries, the 366 m Haiphong and 790 m Granville drives, and the complete 1.08 km route with three stops, 26 passengers, no route contacts and no new red-light crossings. See `evidence/footpath-self-test.log`.

The full test exited with code 0 but printed an ObjectDB leak warning and one resource still in use during shutdown. The focused verbose pavement check (`evidence/footpath-shutdown-check.log`) and final seven-view capture (`evidence/footpath-capture.log`) exited cleanly. The intermittent shutdown warning remains unresolved; it did not fail a gameplay assertion. No native keyboard acceptance is claimed for this pass.

## Exact imagegen prompt

Use case: photorealistic-natural. Asset type: seamless albedo texture for Hong Kong pavement kerbstones, pedestrian paving borders and concrete slabs in a Godot driving game. Generate a square 1024 by 1024 photographic material scan of one continuous flat expanse of weathered light neutral-grey fine-grained granite concrete. Exactly overhead orthographic, evenly lit diffuse overcast light, no cast shadows, no perspective. Tiny black and off-white mineral grains, fine pores, subtle dust and mild urban wear, a few tiny darker pits, realistic restrained colour variation. Medium-light grey, not white or beige, matt surface. Tile seamlessly on all four edges. No paving joints, no borders, no large cracks or stains, no objects, no text, no watermark. The image fills every pixel with the material and will repeat at a 0.6 metre physical scale.
